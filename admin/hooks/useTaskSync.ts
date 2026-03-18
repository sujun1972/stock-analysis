/**
 * 任务同步 Hook
 *
 * 定期从后端同步任务历史到前端 store，确保前端能观察到：
 * 1. 后端自动启动的定时任务
 * 2. 历史任务记录（运行中和已完成）
 * 3. 其他客户端创建的任务
 *
 * 采用智能合并策略：只添加新任务，不覆盖已有任务
 */

import { useEffect, useRef } from 'react'
import { useTaskStore } from '@/stores/task-store'
import { apiClient } from '@/lib/api-client'
import logger from '@/lib/logger'

/**
 * 使用任务同步
 *
 * @param enabled 是否启用同步
 * @param interval 同步间隔（毫秒），默认30秒
 */
export function useTaskSync(enabled: boolean = true, interval: number = 30000) {
  const setTasks = useTaskStore((state) => state.setTasks)
  const syncRef = useRef<NodeJS.Timeout>()

  useEffect(() => {
    if (!enabled) {
      if (syncRef.current) {
        clearInterval(syncRef.current)
      }
      return
    }

    const syncAllTasks = async () => {
      try {
        // 从后端获取任务历史（包括运行中的和已完成的）
        const response = await apiClient.get('/api/celery/task-history?limit=100') as any

        if (response.code === 200 && response.data?.tasks) {
          const historyTasks = response.data.tasks.map((t: any) => ({
            taskId: t.celery_task_id,
            taskName: t.task_name,
            displayName: t.display_name || t.task_name,
            taskType: t.task_type || 'other',
            status: t.status,
            progress: t.progress || 0,
            startTime: t.started_at ? new Date(t.started_at).getTime() : new Date(t.created_at).getTime(),
            endTime: t.completed_at ? new Date(t.completed_at).getTime() : undefined,
            result: t.result,
            error: t.error,
            worker: t.worker
          }))

          // 统计各类任务
          const runningCount = historyTasks.filter((t: any) => t.status === 'running' || t.status === 'pending').length
          const completedCount = historyTasks.filter((t: any) => t.status === 'success' || t.status === 'failure').length

          logger.info(`[TaskSync] 同步任务: ${runningCount} 个运行中, ${completedCount} 个已完成`)

          // 合并到现有任务列表（智能合并，不覆盖）
          const currentTasks = useTaskStore.getState().tasks
          const mergedTasks = new Map(currentTasks)

          let newTaskCount = 0
          historyTasks.forEach((task: any) => {
            if (!mergedTasks.has(task.taskId)) {
              mergedTasks.set(task.taskId, task)
              newTaskCount++
              if (task.status === 'running' || task.status === 'pending') {
                logger.info(`  + 新增运行中任务: ${task.displayName} (${task.taskId.substring(0, 8)}...)`)
              }
            }
          })

          if (newTaskCount > 0) {
            logger.info(`[TaskSync] 新增 ${newTaskCount} 个任务到 store`)
            setTasks(Array.from(mergedTasks.values()))
          }
        }
      } catch (error) {
        logger.error('[TaskSync] 同步任务失败:', error)
      }
    }

    // 立即执行一次
    syncAllTasks()

    // 设置定时同步
    syncRef.current = setInterval(syncAllTasks, interval)

    return () => {
      if (syncRef.current) {
        clearInterval(syncRef.current)
      }
    }
  }, [enabled, interval, setTasks])
}
