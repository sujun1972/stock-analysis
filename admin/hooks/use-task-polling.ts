/**
 * 全局任务轮询 Hook
 *
 * 用于轮询 Celery 任务状态，即使离开页面也会继续轮询
 * 任务完成时显示全局 toast 通知
 */

import { useEffect, useRef } from 'react'
import { toast } from 'sonner'
import { apiClient } from '@/lib/api-client'

export interface TaskInfo {
  taskId: string
  taskName: string
  startTime: number
}

// 全局任务队列（存储在内存中，跨页面共享）
const globalTaskQueue: Map<string, TaskInfo> = new Map()
let pollingInterval: NodeJS.Timeout | null = null

/**
 * 轮询单个任务状态
 */
async function pollTaskStatus(taskId: string, taskName: string): Promise<boolean> {
  try {
    // 根据 taskId 前缀判断调用不同的 API
    // AI分析任务使用通用状态查询接口
    const response = taskId.startsWith('ai_analysis_')
      ? await apiClient.get(`/api/sentiment/sync/status/${taskId}`)
      : await apiClient.getSyncTaskStatus(taskId)

    if (response.code !== 200 || !response.data) {
      return false
    }

    const { status, message, result } = response.data

    // 任务完成
    if (status === 'SUCCESS') {
      const taskResult = result || {}

      // AI分析任务特殊处理
      if (taskId.startsWith('ai_analysis_')) {
        if (taskResult.success) {
          toast.success(`${taskName}完成`, {
            description: `${taskResult.date || ''} AI分析已生成 | Tokens: ${taskResult.tokens_used || 0}`,
            duration: 5000,
          })
        } else {
          toast.warning(`${taskName}完成但有警告`, {
            description: taskResult.error || message || '请查看详情',
            duration: 5000,
          })
        }
      } else if (taskResult.status === 'success') {
        toast.success(`${taskName}完成`, {
          description: `${taskResult.date || ''} 数据同步成功`,
          duration: 5000,
        })
      } else if (taskResult.status === 'skipped') {
        toast.info(`${taskName}已跳过`, {
          description: taskResult.reason || '非交易日',
          duration: 5000,
        })
      } else if (taskResult.status === 'locked') {
        // 任务因锁冲突被跳过
        toast.warning(`${taskName}未执行`, {
          description: taskResult.message || '已有同步任务正在进行',
          duration: 5000,
        })
      } else {
        toast.warning(`${taskName}完成`, {
          description: message || '任务已完成',
          duration: 5000,
        })
      }

      return true // 任务完成，移除
    }

    // 任务失败
    if (status === 'FAILURE') {
      const errorMsg = response.data.error || '未知错误'
      toast.error(`${taskName}失败`, {
        description: errorMsg,
        duration: 7000,
      })
      return true // 任务失败，移除
    }

    // 任务仍在进行中
    return false

  } catch (error) {
    console.error(`轮询任务 ${taskId} 状态失败:`, error)
    return false
  }
}

/**
 * 轮询所有任务
 */
async function pollAllTasks() {
  if (globalTaskQueue.size === 0) {
    // 没有任务时停止轮询
    if (pollingInterval) {
      clearInterval(pollingInterval)
      pollingInterval = null
    }
    return
  }

  const tasksToRemove: string[] = []

  for (const [taskId, taskInfo] of globalTaskQueue.entries()) {
    const shouldRemove = await pollTaskStatus(taskId, taskInfo.taskName)

    if (shouldRemove) {
      tasksToRemove.push(taskId)
    } else {
      // 检查任务是否超时（超过 10 分钟）
      const elapsedTime = Date.now() - taskInfo.startTime
      if (elapsedTime > 10 * 60 * 1000) {
        toast.error(`${taskInfo.taskName}超时`, {
          description: '任务执行时间超过 10 分钟',
          duration: 7000,
        })
        tasksToRemove.push(taskId)
      }
    }
  }

  // 移除已完成/失败的任务
  tasksToRemove.forEach(taskId => {
    globalTaskQueue.delete(taskId)
  })
}

/**
 * 开始轮询
 */
function startPolling() {
  if (pollingInterval) {
    return // 已经在轮询中
  }

  pollingInterval = setInterval(pollAllTasks, 3000) // 每 3 秒轮询一次
}

/**
 * 添加任务到轮询队列
 */
export function addTaskToQueue(taskId: string, taskName: string) {
  globalTaskQueue.set(taskId, {
    taskId,
    taskName,
    startTime: Date.now(),
  })

  startPolling()
}

/**
 * 从后端恢复正在执行的任务
 */
async function restoreActiveTasks() {
  try {
    const response = await apiClient.get('/api/sentiment/tasks/active')

    if (response.code === 200 && response.data?.tasks) {
      const tasks = response.data.tasks

      if (tasks.length > 0) {
        console.log(`🔄 恢复 ${tasks.length} 个正在执行的任务到轮询队列`)
      }

      tasks.forEach((task: any) => {
        const { task_id, display_name } = task

        // 添加到全局队列（避免重复）
        if (!globalTaskQueue.has(task_id)) {
          globalTaskQueue.set(task_id, {
            taskId: task_id,
            taskName: display_name || '未知任务',
            startTime: Date.now(),
          })
        }
      })

      // 如果有任务，启动轮询
      if (globalTaskQueue.size > 0) {
        startPolling()
      }
    }
  } catch (error) {
    console.error('恢复活动任务失败:', error)
  }
}

/**
 * 全局任务轮询 Hook
 *
 * 在应用根组件中使用，确保任务轮询持续运行
 */
export function useTaskPolling() {
  const isInitialized = useRef(false)

  useEffect(() => {
    if (isInitialized.current) {
      return
    }

    isInitialized.current = true

    // 启动时恢复正在执行的任务
    restoreActiveTasks()

    // 立即检查一次
    pollAllTasks()

    // 开始轮询
    if (globalTaskQueue.size > 0) {
      startPolling()
    }

    // 组件卸载时不停止轮询（因为这是全局的）
  }, [])

  return {
    addTask: addTaskToQueue,
    activeTasks: globalTaskQueue.size,
  }
}
