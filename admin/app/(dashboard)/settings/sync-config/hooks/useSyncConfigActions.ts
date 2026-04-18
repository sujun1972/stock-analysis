'use client'

import { useState, useCallback, useRef, useEffect } from 'react'
import { toast } from 'sonner'
import { syncDashboardApi, type SyncOverviewItem, type SyncConfigUpdate, type ScheduleUpdate } from '@/lib/api/sync-dashboard'
import { axiosInstance } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { useConfigStore } from '@/stores/config-store'

export function useSyncConfigActions({
  loadData,
  setItems,
}: {
  loadData: (silent?: boolean) => Promise<void>
  setItems: React.Dispatch<React.SetStateAction<SyncOverviewItem[]>>
}) {
  const { dataSource: configData } = useConfigStore()
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()
  const callbacksRef = useRef<Map<string, () => void>>(new Map())

  // 清除进度确认
  const [clearProgressItem, setClearProgressItem] = useState<SyncOverviewItem | null>(null)

  // 测试数据源弹窗
  const [testDialogOpen, setTestDialogOpen] = useState(false)
  const [testingItem, setTestingItem] = useState<SyncOverviewItem | null>(null)

  // 编辑配置弹窗
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [editingItem, setEditingItem] = useState<SyncOverviewItem | null>(null)
  const [editForm, setEditForm] = useState<SyncConfigUpdate>({})
  const [scheduleForm, setScheduleForm] = useState<ScheduleUpdate>({})
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    return () => {
      callbacksRef.current.forEach((cb, taskId) => unregisterCompletionCallback(taskId, cb))
      callbacksRef.current.clear()
    }
  }, [unregisterCompletionCallback])

  const handleSync = useCallback(async (item: SyncOverviewItem, type: 'incremental' | 'full') => {
    if (!item.api_prefix) return
    try {
      // 若增量和全量共用同一 Celery 任务（没有独立的 /sync-full-history 路由），
      // 全量同步直接调用 /sync-async 并传入 start_date，由后端以全量模式处理。
      const isSharedTask = type === 'full' && item.full_sync_task_name === item.incremental_task_name
      const endpoint = type === 'full' && !isSharedTask
        ? `/api${item.api_prefix}/sync-full-history`
        : `/api${item.api_prefix}/sync-async`
      const params: Record<string, string | number> = {}
      if (type === 'full') {
        if (!isSharedTask) {
          if (item.full_sync_concurrency) params.concurrency = item.full_sync_concurrency
          // 独立全量任务：start_date 由后端从任务默认值读取
          // 全量同步前先清除 Redis 续继进度，确保从头开始而非续继上次
          try {
            await syncDashboardApi.clearProgress(item.table_key)
          } catch {
            // 清除失败不阻止全量同步（Redis 可能无进度记录）
          }
        } else {
          // 共用任务（基础数据类）：传入 earliest_history_date 作为 start_date
          const earliest = configData?.earliest_history_date
          if (earliest) {
            params.start_date = earliest.replace(/-/g, '')
          }
        }
      }
      const resp = await axiosInstance.post(endpoint, null, { params }) as any
      if (resp.code === 200 && resp.data) {
        const taskId = resp.data.celery_task_id
        addTask({
          taskId,
          taskName: resp.data.task_name,
          displayName: resp.data.display_name,
          taskType: 'data_sync',
          status: 'running',
          progress: 0,
          startTime: Date.now(),
        })
        const cb = () => {
          loadData(true)
          unregisterCompletionCallback(taskId, cb)
          callbacksRef.current.delete(taskId)
        }
        callbacksRef.current.set(taskId, cb)
        registerCompletionCallback(taskId, cb)
        triggerPoll()
        toast.success(`${item.display_name} ${type === 'incremental' ? '增量' : '全量'}同步已提交`)
      } else {
        throw new Error(resp.message || '提交失败')
      }
    } catch (err: any) {
      toast.error(`提交失败: ${err.message}`)
    }
  }, [addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, loadData, configData])

  const handleClearProgress = useCallback(async () => {
    if (!clearProgressItem) return
    try {
      const resp = await syncDashboardApi.clearProgress(clearProgressItem.table_key)
      if (resp.code === 200) {
        toast.success(`${clearProgressItem.display_name} 进度已清除`)
        loadData(true)
      } else {
        throw new Error(resp.message)
      }
    } catch (err: any) {
      toast.error(`清除失败: ${err.message}`)
    } finally {
      setClearProgressItem(null)
    }
  }, [clearProgressItem, loadData])

  const openEditDialog = (item: SyncOverviewItem) => {
    setEditingItem(item)
    setEditForm({
      incremental_default_days: item.incremental_default_days,
      incremental_sync_strategy: item.incremental_sync_strategy ?? undefined,
      full_sync_strategy: item.full_sync_strategy ?? undefined,
      full_sync_concurrency: item.full_sync_concurrency,
      passive_sync_enabled: item.passive_sync_enabled,
      passive_sync_task_name: item.passive_sync_task_name,
      notes: item.notes,
      data_source: item.data_source ?? 'tushare',
      max_requests_per_minute: item.max_requests_per_minute ?? null,
    })
    setScheduleForm({
      enabled: item.incremental_schedule?.enabled ?? undefined,
      cron_expression: item.incremental_schedule?.cron_expression ?? undefined,
    })
    setEditDialogOpen(true)
  }

  const handleSave = async () => {
    if (!editingItem) return
    setIsSaving(true)
    try {
      const configResp = await syncDashboardApi.updateConfig(editingItem.table_key, editForm)
      if (configResp.code !== 200) {
        toast.error(configResp.message || '保存失败')
        return
      }

      // 若该表有增量调度任务，同步更新调度配置
      if (editingItem.incremental_schedule && (scheduleForm.enabled !== undefined || scheduleForm.cron_expression !== undefined)) {
        const schedResp = await syncDashboardApi.updateSchedule(editingItem.table_key, scheduleForm)
        if (schedResp.code !== 200) {
          toast.error(schedResp.message || '调度配置保存失败')
          return
        }
        const now = new Date().toISOString()
        setItems(prev => prev.map(i =>
          i.table_key === editingItem.table_key
            ? {
                ...i, ...editForm, updated_at: now,
                incremental_schedule: i.incremental_schedule
                  ? { ...i.incremental_schedule, ...scheduleForm }
                  : i.incremental_schedule,
              } as SyncOverviewItem
            : i
        ))
      } else {
        const now = new Date().toISOString()
        setItems(prev => prev.map(i =>
          i.table_key === editingItem.table_key ? { ...i, ...editForm, updated_at: now } as SyncOverviewItem : i
        ))
      }

      toast.success('配置已保存')
      setEditDialogOpen(false)
    } catch {
      toast.error('保存失败，请重试')
    } finally {
      setIsSaving(false)
    }
  }

  const openTestDialog = (item: SyncOverviewItem) => {
    setTestingItem(item)
    setTestDialogOpen(true)
  }

  const closeTestDialog = (open: boolean) => {
    setTestDialogOpen(open)
    if (!open) setTestingItem(null)
  }

  return {
    // Clear progress
    clearProgressItem,
    setClearProgressItem,
    handleClearProgress,
    // Test dialog
    testDialogOpen,
    testingItem,
    openTestDialog,
    closeTestDialog,
    // Edit dialog
    editDialogOpen,
    setEditDialogOpen,
    editingItem,
    editForm,
    setEditForm,
    scheduleForm,
    setScheduleForm,
    isSaving,
    openEditDialog,
    handleSave,
    // Sync
    handleSync,
  }
}
