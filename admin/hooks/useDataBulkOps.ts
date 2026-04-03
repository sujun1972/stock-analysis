/**
 * useDataBulkOps
 *
 * 通用的"全量同步"和"清空数据"逻辑，供各数据页面复用。
 *
 * 使用方式：
 *   const { handleFullSync, handleClear, isClearDialogOpen, setIsClearDialogOpen } =
 *     useDataBulkOps({
 *       tableKey: 'daily_basic',          // data_ops 白名单中的 key
 *       syncFn: () => api.syncAsync({}),  // 调用各自的 sync-async 接口（不传日期）
 *       taskName: 'tasks.sync_daily_basic',
 *       onSuccess: loadData,              // 同步/清空成功后刷新页面数据
 *     })
 *
 * 注意：syncFn 会由 hook 内部传入 start_date（从配置读取的最早历史日期），
 * 因此 syncFn 需要接受可选的 start_date 参数。
 */

import { useRef, useState, useCallback } from 'react'
import { toast } from 'sonner'
import { apiClient } from '@/lib/api-client'
import { useTaskStore } from '@/stores/task-store'
import { useConfigStore } from '@/stores/config-store'

export interface DataBulkOpsOptions {
  /** data_ops 白名单中的 table_key */
  tableKey: string
  /**
   * 各页面自己的 sync-async 函数。
   * hook 会在调用时传入 { start_date: 'YYYYMMDD' }，
   * 函数应该将其透传给后端 sync-async 接口。
   */
  syncFn: (params: { start_date: string }) => Promise<{
    code: number
    data?: {
      celery_task_id: string
      task_name: string
      display_name: string
    }
    message?: string
  }>
  /** Celery 任务名，用于 isTaskRunning 派生状态（全量同步时用） */
  taskName: string
  /** 同步或清空完成后的回调（通常是 loadData） */
  onSuccess?: () => void
}

export function useDataBulkOps(options: DataBulkOpsOptions) {
  const { tableKey, syncFn, taskName, onSuccess } = options

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } =
    useTaskStore()
  const { dataSource } = useConfigStore()

  const activeCallbacksRef = useRef<Map<string, () => void>>(new Map())

  // 清空确认弹窗
  const [isClearDialogOpen, setIsClearDialogOpen] = useState(false)
  const [isClearing, setIsClearing] = useState(false)

  // 从配置读取最早历史日期，格式 YYYY-MM-DD → YYYYMMDD
  const getEarliestDate = useCallback((): string => {
    const raw = dataSource?.earliest_history_date || '2021-01-04'
    return raw.replace(/-/g, '')
  }, [dataSource])

  /** 全量历史同步 */
  const handleFullSync = useCallback(async () => {
    try {
      const startDate = getEarliestDate()
      const response = await syncFn({ start_date: startDate })

      if (response.code === 200 && response.data) {
        const taskId = response.data.celery_task_id

        addTask({
          taskId,
          taskName: response.data.task_name,
          displayName: response.data.display_name,
          taskType: 'data_sync',
          status: 'running',
          progress: 0,
          startTime: Date.now(),
        })

        const cb = () => {
          onSuccess?.()
          unregisterCompletionCallback(taskId, cb)
          activeCallbacksRef.current.delete(taskId)
        }
        activeCallbacksRef.current.set(taskId, cb)
        registerCompletionCallback(taskId, cb)
        triggerPoll()

        toast.success('全量同步任务已提交', {
          description: `将从 ${dataSource?.earliest_history_date || '2021-01-04'} 开始全量同步，可在任务面板查看进度`,
        })
      } else {
        throw new Error(response.message || '提交失败')
      }
    } catch (err: any) {
      toast.error('全量同步失败', { description: err.message })
    }
  }, [
    syncFn,
    getEarliestDate,
    addTask,
    triggerPoll,
    registerCompletionCallback,
    unregisterCompletionCallback,
    onSuccess,
    dataSource,
  ])

  /** 清空数据（全表 TRUNCATE） */
  const handleClear = useCallback(async () => {
    try {
      setIsClearing(true)
      const response = await apiClient.clearTableData({ table_key: tableKey })
      if (response.code === 200) {
        toast.success('数据已清空', { description: `表 ${tableKey} 已清空` })
        onSuccess?.()
      } else {
        throw new Error(response.message || '清空失败')
      }
    } catch (err: any) {
      toast.error('清空失败', { description: err.message })
    } finally {
      setIsClearing(false)
      setIsClearDialogOpen(false)
    }
  }, [tableKey, onSuccess])

  /** 组件卸载时清理回调 */
  const cleanup = useCallback(() => {
    const callbacks = activeCallbacksRef.current
    callbacks.forEach((cb, taskId) => {
      unregisterCompletionCallback(taskId, cb)
    })
    callbacks.clear()
  }, [unregisterCompletionCallback])

  const fullSyncing = isTaskRunning(taskName)

  return {
    handleFullSync,
    handleClear,
    fullSyncing,
    isClearing,
    isClearDialogOpen,
    setIsClearDialogOpen,
    cleanup,
    earliestHistoryDate: dataSource?.earliest_history_date || '2021-01-04',
  }
}
