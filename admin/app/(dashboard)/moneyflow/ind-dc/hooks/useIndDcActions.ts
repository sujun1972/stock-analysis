'use client'

import { useState } from 'react'
import { moneyflowApi } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { toast } from 'sonner'
import { useTaskStore } from '@/stores/task-store'
import type { useIndDcData } from './useIndDcData'

type IndDcDataReturn = ReturnType<typeof useIndDcData>

export function useIndDcActions(dp: IndDcDataReturn['dp'], loadTopSectors: IndDcDataReturn['loadTopSectors']) {
  // 同步弹窗额外状态（该页面同步弹窗含自定义字段）
  const [syncDate, setSyncDate] = useState<Date | undefined>(undefined)
  const [syncContentType, setSyncContentType] = useState<string>('all')

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()

  // 自定义同步确认（该页面同步逻辑特殊：全部时提交三个任务）
  const handleSyncConfirm = async () => {
    dp.setSyncDialogOpen(false)
    try {
      const syncDateStr = syncDate ? toDateStr(syncDate) : undefined
      const ct = syncContentType !== 'all' ? syncContentType : undefined

      const types = ct ? [ct] : ['行业', '概念', '地域']

      for (const type of types) {
        const response = await moneyflowApi.syncMoneyflowIndDcAsync(
          syncDateStr ? { trade_date: syncDateStr, content_type: type } : { content_type: type }
        )

        if (response.code === 200 && response.data) {
          const taskId = response.data.celery_task_id
          addTask({
            taskId,
            taskName: response.data.task_name,
            displayName: response.data.display_name + `(${type})`,
            taskType: 'data_sync',
            status: 'running',
            progress: 0,
            startTime: Date.now()
          })

          const completionCallback = (task: { status: string }) => {
            if (task.status === 'success') {
              dp.loadData(1)
              loadTopSectors().catch(() => {})
              toast.success(`${type}数据同步完成`)
            }
            unregisterCompletionCallback(taskId, completionCallback)
          }
          registerCompletionCallback(taskId, completionCallback)
          triggerPoll()
        } else {
          toast.error(response.message || `提交${type}同步任务失败`)
        }
      }

      toast.success(ct ? '同步任务已提交' : '已提交行业/概念/地域三个同步任务')
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '提交同步任务失败'
      toast.error(message)
    }
  }

  return {
    syncDate,
    setSyncDate,
    syncContentType,
    setSyncContentType,
    handleSyncConfirm,
  }
}
