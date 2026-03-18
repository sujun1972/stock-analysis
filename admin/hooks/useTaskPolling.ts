/**
 * 任务状态轮询 Hook
 * 自动轮询活动任务的状态并更新
 */

import { useEffect, useRef } from 'react'
import { useTaskStore } from '@/stores/task-store'
import { apiClient } from '@/lib/api-client'
import logger from '@/lib/logger'

/**
 * 使用任务状态轮询
 * @param enabled 是否启用轮询
 * @param interval 轮询间隔（毫秒），默认3秒
 */
export function useTaskPolling(enabled: boolean = true, interval: number = 3000) {
  const updateTask = useTaskStore((state) => state.updateTask)
  const setPollTrigger = useTaskStore((state) => state.setPollTrigger)
  const pollingRef = useRef<NodeJS.Timeout>()

  useEffect(() => {
    if (!enabled) {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
      // 清除触发器
      setPollTrigger(null)
      return
    }

    const pollTaskStatus = async () => {
      // 直接从 store 获取最新的任务列表（避免闭包问题）
      const tasks = Array.from(useTaskStore.getState().tasks.values())

      // 只轮询活动任务
      const activeTasks = tasks.filter(
        (t) => t.status === 'pending' || t.status === 'running' || t.status === 'progress'
      )

      if (activeTasks.length === 0) {
        return
      }

      // 并发查询所有活动任务的状态
      await Promise.allSettled(
        activeTasks.map(async (task) => {
          try {
            const response = await fetchTaskStatus(task.taskId, task.taskName)

            if (response) {
              const updates: any = {
                status: response.status
              }

              // 添加完成时间
              if (response.status === 'success' || response.status === 'failure') {
                updates.endTime = Date.now()
                logger.info(`[TaskPolling] 任务完成: ${task.displayName} - ${response.status === 'success' ? '成功' : '失败'}`)
              }

              // 添加进度
              if (response.progress !== undefined) {
                updates.progress = response.progress
              }

              // 添加结果或错误
              if (response.result) {
                updates.result = response.result
              }
              if (response.error) {
                updates.error = response.error
              }

              updateTask(task.taskId, updates)
            }
          } catch (error) {
            logger.error(`[TaskPolling] 轮询任务失败: ${task.displayName}`, error)
          }
        })
      )
    }

    // 将轮询函数注册到 store，供外部手动触发
    setPollTrigger(pollTaskStatus)

    // 立即执行一次
    pollTaskStatus()

    // 设置定时轮询
    pollingRef.current = setInterval(pollTaskStatus, interval)

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
      }
      // 清除触发器
      setPollTrigger(null)
    }
  }, [enabled, interval, setPollTrigger])
}

/**
 * 获取任务状态
 * 尝试多个API端点以兼容不同类型的任务
 */
async function fetchTaskStatus(taskId: string, taskName: string) {
  try {
    // 1. 尝试通用的 Celery 任务状态查询
    const celeryResponse = await apiClient.get(`/api/celery/task/${taskId}`)
    if (celeryResponse.data) {
      return mapCeleryStatus(celeryResponse.data)
    }
  } catch (error: any) {
    // Celery API 不存在或失败，继续尝试其他API
  }

  try {
    // 2. 尝试回测任务API
    if (taskName.includes('backtest')) {
      const response = await apiClient.getBacktestTaskStatus(taskId)
      if (response.success && response.data) {
        return {
          status: mapStatus(response.data.status),
          progress: response.data.progress,
          result: response.data.result,
          error: response.data.error
        }
      }
    }
  } catch (error) {
    // 继续
  }

  try {
    // 3. 尝试AI策略生成任务API
    if (taskName.includes('ai_strategy') || taskName.includes('generate_strategy')) {
      const response = await apiClient.get(`/api/ai-strategy/task/${taskId}`)
      if (response.data) {
        return {
          status: mapStatus(response.data.state),
          progress: response.data.progress,
          result: response.data.result,
          error: response.data.error
        }
      }
    }
  } catch (error) {
    // 继续
  }

  try {
    // 4. 尝试市场情绪任务API
    if (taskName.includes('sentiment')) {
      const response = await apiClient.get(`/api/sentiment/task/${taskId}`)
      if (response.data) {
        return {
          status: mapStatus(response.data.status),
          progress: response.data.progress,
          result: response.data.result,
          error: response.data.error
        }
      }
    }
  } catch (error) {
    // 继续
  }

  // 5. 默认返回 null，保持当前状态
  return null
}

/**
 * 映射 Celery 状态到应用状态
 */
function mapCeleryStatus(celeryData: any) {
  const state = celeryData.state || celeryData.status
  return {
    status: mapStatus(state),
    progress: celeryData.progress || celeryData.current,
    result: celeryData.result,
    error: celeryData.error || (state === 'FAILURE' ? celeryData.traceback : undefined)
  }
}

/**
 * 统一状态映射
 */
function mapStatus(status: string): 'pending' | 'running' | 'success' | 'failure' | 'progress' {
  const upperStatus = status?.toUpperCase()

  switch (upperStatus) {
    case 'PENDING':
    case 'WAITING':
      return 'pending'
    case 'STARTED':
    case 'RUNNING':
      return 'running'
    case 'PROGRESS':
      return 'progress'
    case 'SUCCESS':
    case 'COMPLETED':
      return 'success'
    case 'FAILURE':
    case 'FAILED':
    case 'ERROR':
      return 'failure'
    default:
      return 'pending'
  }
}
