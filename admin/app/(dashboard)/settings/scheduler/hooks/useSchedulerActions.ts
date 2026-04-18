'use client'

import { useState, useCallback } from 'react'
import { schedulerApi } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import type { ScheduledTask } from '../components/constants'
import { getTaskInfo } from '../components/constants'

interface UseSchedulerActionsOptions {
  tasks: ScheduledTask[]
  setTasks: React.Dispatch<React.SetStateAction<ScheduledTask[]>>
  loadTasks: () => Promise<void>
}

export function useSchedulerActions({ tasks, setTasks, loadTasks }: UseSchedulerActionsOptions) {
  const [editingTask, setEditingTask] = useState<ScheduledTask | null>(null)
  const [showEditModal, setShowEditModal] = useState(false)
  const [executingTasks, setExecutingTasks] = useState<Set<number>>(new Set())
  const { addTask, triggerPoll } = useTaskStore()

  const handleToggle = useCallback(async (taskId: number) => {
    try {
      // 乐观更新UI，立即切换状态
      setTasks(prevTasks =>
        prevTasks.map(task =>
          task.id === taskId
            ? { ...task, enabled: !task.enabled }
            : task
        )
      )

      // 调用API更新后端
      await schedulerApi.toggleScheduledTask(taskId)

      // 静默刷新，只更新数据不影响UI状态
      const response = await schedulerApi.getScheduledTasks()
      if (response.data) {
        setTasks(response.data)
      }
    } catch (err: any) {
      // 如果失败，回滚状态并显示错误
      await loadTasks()
      toast.error('操作失败', {
        description: err.message || '切换任务状态失败'
      })
    }
  }, [loadTasks, setTasks])

  const handleEdit = useCallback((task: ScheduledTask) => {
    setEditingTask(task)
    setShowEditModal(true)
  }, [])

  const handleExecute = useCallback(async (task: ScheduledTask) => {
    const taskInfo = getTaskInfo(task)

    try {
      setExecutingTasks(prev => new Set(prev).add(task.id))

      const response = await schedulerApi.executeScheduledTask(task.id)

      // 兼容 success/code 两种响应格式
      const isSuccess = response.success || response.code === 200
      const responseData = response.data

      if (isSuccess && responseData) {
        addTask({
          taskId: responseData.celery_task_id,
          taskName: responseData.task_name,
          displayName: taskInfo.name,
          taskType: 'scheduler',
          status: 'running',
          progress: 0,
          startTime: Date.now()
        })
        triggerPoll()
        toast.success('任务已提交', {
          description: `"${taskInfo.name}" 已开始执行，可在任务面板查看进度`
        })
        // 静默刷新任务列表（延迟1s等待后端写入）
        setTimeout(async () => {
          const refreshed = await schedulerApi.getScheduledTasks().catch(() => null)
          if (refreshed?.data) setTasks(refreshed.data)
        }, 1000)
      } else {
        throw new Error(response.message || '执行失败')
      }
    } catch (err: any) {
      toast.error('执行失败', {
        description: err.message || '未知错误'
      })
    } finally {
      setExecutingTasks(prev => {
        const next = new Set(prev)
        next.delete(task.id)
        return next
      })
    }
  }, [addTask, triggerPoll, setTasks])

  const handleSaveEdit = useCallback(async () => {
    if (!editingTask) return

    try {
      await schedulerApi.updateScheduledTask(editingTask.id, {
        display_name: editingTask.display_name,
        description: editingTask.description,
        category: editingTask.category,
        display_order: editingTask.display_order,
        points_consumption: editingTask.points_consumption,
        cron_expression: editingTask.cron_expression,
        params: editingTask.params
      })
      setShowEditModal(false)
      setEditingTask(null)

      toast.success('更新成功', {
        description: '定时任务配置已更新'
      })

      await loadTasks()
    } catch (err: any) {
      toast.error('更新失败', {
        description: err.message || '更新任务失败'
      })
    }
  }, [editingTask, loadTasks])

  const handleCloseEditModal = useCallback((open: boolean) => {
    setShowEditModal(open)
    if (!open) setEditingTask(null)
  }, [])

  return {
    editingTask,
    setEditingTask,
    showEditModal,
    setShowEditModal,
    executingTasks,
    handleToggle,
    handleEdit,
    handleExecute,
    handleSaveEdit,
    handleCloseEditModal,
  }
}
