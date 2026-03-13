/**
 * 全局任务轮询 Hook（升级版）
 *
 * 功能：
 * 1. 轮询所有 Celery 任务状态，即使离开页面也会继续轮询
 * 2. 任务完成时显示全局 toast 通知
 * 3. 使用 Zustand Store 管理任务状态
 * 4. 应用启动时自动恢复活动任务
 * 5. 支持任务进度实时更新
 */

import { useEffect, useRef } from 'react'
import { toast } from 'sonner'
import { apiClient } from '@/lib/api-client'
import { useTaskStore, Task, TaskType, TaskStatus } from '@/stores/task-store'

let pollingInterval: NodeJS.Timeout | null = null

/**
 * 轮询单个任务状态
 */
async function pollTaskStatus(taskId: string): Promise<boolean> {
  try {
    // 调用统一的任务状态查询接口
    const response = await apiClient.get(`/api/sentiment/sync/status/${taskId}`)

    if (response.code !== 200 || !response.data) {
      return false
    }

    const { status, message, result, progress } = response.data
    const taskStore = useTaskStore.getState()

    // 更新任务状态
    if (status === 'PROGRESS' || status === 'STARTED') {
      // 任务进行中
      taskStore.updateTask(taskId, {
        status: 'progress',
        progress: progress || (result?.percent || 50)
      })
      return false // 继续轮询
    }

    if (status === 'SUCCESS') {
      // 任务成功完成
      const task = taskStore.tasks.get(taskId)
      const taskName = task?.displayName || '未知任务'

      taskStore.updateTask(taskId, {
        status: 'success',
        progress: 100,
        result
      })

      // 显示成功通知
      if (result?.status === 'success') {
        toast.success(`${taskName}完成`, {
          description: generateSuccessMessage(result),
          duration: 5000
        })
      } else if (result?.status === 'skipped') {
        toast.info(`${taskName}已跳过`, {
          description: result.reason || '非交易日',
          duration: 5000
        })
      } else if (result?.status === 'locked') {
        toast.warning(`${taskName}未执行`, {
          description: result.message || '已有同步任务正在进行',
          duration: 5000
        })
      } else {
        toast.success(`${taskName}完成`, {
          description: message || '任务已完成',
          duration: 5000
        })
      }

      // 3秒后自动移除已完成任务
      setTimeout(() => {
        taskStore.removeTask(taskId)
      }, 3000)

      return true // 任务完成，停止轮询
    }

    if (status === 'FAILURE') {
      // 任务失败
      const task = taskStore.tasks.get(taskId)
      const taskName = task?.displayName || '未知任务'
      const errorMsg = response.data.error || message || '未知错误'

      taskStore.updateTask(taskId, {
        status: 'failure',
        error: errorMsg
      })

      toast.error(`${taskName}失败`, {
        description: errorMsg,
        duration: 7000
      })

      // 5秒后自动移除失败任务
      setTimeout(() => {
        taskStore.removeTask(taskId)
      }, 5000)

      return true // 任务失败，停止轮询
    }

    // 任务仍在进行中
    return false
  } catch (error) {
    console.error(`轮询任务 ${taskId} 状态失败:`, error)
    return false
  }
}

/**
 * 生成成功消息
 */
function generateSuccessMessage(result: any): string {
  if (result.date && result.tokens_used) {
    // AI分析任务
    return `${result.date} AI分析已生成 | Tokens: ${result.tokens_used}`
  } else if (result.success !== undefined && result.total !== undefined) {
    // 同步任务
    const parts = []
    if (result.date_range) {
      parts.push(`范围: ${result.date_range}`)
    }
    parts.push(`成功: ${result.success}`)
    if (result.failed > 0) {
      parts.push(`失败: ${result.failed}`)
    }
    if (result.skipped > 0) {
      parts.push(`跳过: ${result.skipped}`)
    }
    parts.push(`总计: ${result.total}`)
    return parts.join(' | ')
  } else if (result.date) {
    return `${result.date} 数据同步成功`
  }
  return '任务完成'
}

/**
 * 轮询所有任务
 */
async function pollAllTasks() {
  const taskStore = useTaskStore.getState()
  const activeTasks = taskStore.getActiveTasks()

  if (activeTasks.length === 0) {
    // 没有任务时停止轮询
    if (pollingInterval) {
      clearInterval(pollingInterval)
      pollingInterval = null
    }
    return
  }

  const tasksToRemove: string[] = []

  for (const task of activeTasks) {
    const shouldRemove = await pollTaskStatus(task.taskId)

    if (shouldRemove) {
      tasksToRemove.push(task.taskId)
    } else {
      // 检查任务是否超时（超过 30 分钟）
      const elapsedTime = Date.now() - task.startTime
      if (elapsedTime > 30 * 60 * 1000) {
        toast.error(`${task.displayName}超时`, {
          description: '任务执行时间超过 30 分钟',
          duration: 7000
        })
        taskStore.updateTask(task.taskId, {
          status: 'failure',
          error: '任务超时'
        })
        tasksToRemove.push(task.taskId)
      }
    }
  }

  // 移除已完成/失败的任务
  tasksToRemove.forEach((taskId) => {
    taskStore.removeTask(taskId)
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
export function addTaskToQueue(
  taskId: string,
  taskName: string,
  displayName?: string,
  taskType: TaskType = 'other'
) {
  const taskStore = useTaskStore.getState()

  taskStore.addTask({
    taskId,
    taskName,
    displayName: displayName || taskName,
    taskType,
    status: 'pending',
    startTime: Date.now()
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
      const taskStore = useTaskStore.getState()

      if (tasks.length > 0) {
        console.log(`🔄 恢复 ${tasks.length} 个正在执行的任务到轮询队列`)
      }

      tasks.forEach((task: any) => {
        const { task_id, task_name, display_name, task_type, status } = task

        // 添加到 Store（避免重复）
        if (!taskStore.tasks.has(task_id)) {
          taskStore.addTask({
            taskId: task_id,
            taskName: task_name,
            displayName: display_name || task_name || '未知任务',
            taskType: (task_type as TaskType) || 'other',
            status: (status === 'running' ? 'running' : 'pending') as TaskStatus,
            startTime: Date.now()
          })
        }
      })

      // 如果有任务，启动轮询
      if (taskStore.getActiveTaskCount() > 0) {
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
    const taskStore = useTaskStore.getState()
    if (taskStore.getActiveTaskCount() > 0) {
      startPolling()
    }

    // 组件卸载时不停止轮询（因为这是全局的）
  }, [])

  return {
    addTask: addTaskToQueue
  }
}
