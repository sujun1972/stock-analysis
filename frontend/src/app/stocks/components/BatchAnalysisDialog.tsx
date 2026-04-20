'use client'

import { useEffect, useRef, useState } from 'react'
import { apiClient } from '@/lib/api-client'
import type { BatchAnalysisItem, BatchAnalysisProgress } from '@/lib/api/stocks'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog'
import { Sparkles, CheckCircle2, XCircle, Loader2 } from 'lucide-react'

interface BatchAnalysisDialogProps {
  open: boolean
  onClose: () => void
  selectedTsCodes: string[]
  onSuccess: () => void
}

const POLL_INTERVAL_MS = 3000

function tsCodeToPlain(tsCode: string): string {
  return tsCode.split('.')[0]
}

export function BatchAnalysisDialog({
  open,
  onClose,
  selectedTsCodes,
  onSuccess,
}: BatchAnalysisDialogProps) {
  const [submitting, setSubmitting] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [progress, setProgress] = useState<BatchAnalysisProgress | null>(null)
  const [error, setError] = useState<string | null>(null)
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pollCancelledRef = useRef(false)
  const onSuccessCalledRef = useRef(false)

  const clearPoll = () => {
    pollCancelledRef.current = true
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }

  // 弹窗关闭时清理状态；打开时重置取消标志（供下一次提交）
  useEffect(() => {
    if (!open) {
      clearPoll()
      setSubmitting(false)
      setTaskId(null)
      setProgress(null)
      setError(null)
      onSuccessCalledRef.current = false
    } else {
      pollCancelledRef.current = false
    }
  }, [open])

  useEffect(() => () => clearPoll(), [])

  // 递归 setTimeout 轮询；cancelled 标志确保关闭弹窗后 in-flight 请求的回调不再 setState。
  const pollProgress = async (id: string) => {
    if (pollCancelledRef.current) return
    try {
      const res = await apiClient.getBatchAnalysisProgress(id)
      if (pollCancelledRef.current) return
      if (res?.code === 200 && res.data) {
        setProgress(res.data)
        const terminal = res.data.status === 'success' || res.data.status === 'failure'
        if (terminal) {
          if (!onSuccessCalledRef.current) {
            onSuccessCalledRef.current = true
            onSuccess()
          }
          return
        }
      }
    } catch (e: unknown) {
      if (pollCancelledRef.current) return
      const err = e as { message?: string }
      setError(err?.message || '查询进度失败')
    }
    if (!pollCancelledRef.current) {
      pollTimerRef.current = setTimeout(() => pollProgress(id), POLL_INTERVAL_MS)
    }
  }

  const handleStart = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const res = await apiClient.submitBatchAnalysis({
        ts_codes: selectedTsCodes,
        // 后端默认 3 专家 + CIO
      })
      if (res?.code === 200 && res.data?.celery_task_id) {
        const id = res.data.celery_task_id
        setTaskId(id)
        pollProgress(id)
      } else {
        setError(res?.message || '提交批量分析失败')
      }
    } catch (e: unknown) {
      const err = e as { response?: { data?: { message?: string; detail?: string } }; message?: string }
      setError(err?.response?.data?.message || err?.response?.data?.detail || err?.message || '提交失败')
    } finally {
      setSubmitting(false)
    }
  }

  // 派生展示数据（任务提交后读 progress.items，未提交前读 selectedTsCodes）
  const displayItems: BatchAnalysisItem[] = progress?.items?.length
    ? progress.items
    : selectedTsCodes.map((ts) => ({
        ts_code: ts,
        stock_name: '',
        status: 'pending' as const,
      }))

  const total = progress?.total_items ?? selectedTsCodes.length
  const successCount = progress?.success_items ?? 0
  const failedCount = progress?.failed_items ?? 0
  const completedCount = progress?.completed_items ?? 0
  const runningCount = displayItems.filter((i) => i.status === 'running').length
  const isFinished = progress?.status === 'success' || progress?.status === 'failure'
  const isRunning = Boolean(taskId) && !isFinished

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-[640px] max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>批量 AI 分析</DialogTitle>
          <DialogDescription>
            {taskId
              ? `任务后台运行中，关闭窗口不会中断。任务 ID：${taskId.slice(0, 8)}...`
              : `对选中的 ${total} 只股票生成 3 专家 + CIO，由后端并发 2 只执行。`}
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center gap-4 text-sm border rounded-md px-3 py-2 bg-gray-50 dark:bg-gray-800">
          <div>进度：<strong>{completedCount}</strong> / {total}</div>
          <div className="text-green-600 flex items-center gap-1">
            <CheckCircle2 className="h-3.5 w-3.5" />成功 {successCount}
          </div>
          <div className="text-red-500 flex items-center gap-1">
            <XCircle className="h-3.5 w-3.5" />失败 {failedCount}
          </div>
          {isRunning && (
            <div className="text-blue-600 flex items-center gap-1">
              <Loader2 className="h-3.5 w-3.5 animate-spin" />进行中 {runningCount}
            </div>
          )}
          {isFinished && (
            <div className="ml-auto text-gray-500">已完成</div>
          )}
        </div>

        {error && (
          <div className="text-sm text-red-600 border border-red-200 bg-red-50 rounded-md px-3 py-2">
            {error}
          </div>
        )}

        <div className="flex-1 overflow-y-auto min-h-0 border rounded-md">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-gray-100 dark:bg-gray-800 text-left">
              <tr>
                <th className="px-3 py-2 font-medium">股票</th>
                <th className="px-3 py-2 font-medium">状态</th>
                <th className="px-3 py-2 font-medium text-right">耗时</th>
              </tr>
            </thead>
            <tbody>
              {displayItems.map((t) => (
                <tr key={t.ts_code} className="border-t">
                  <td className="px-3 py-2">
                    <span className="font-medium">{t.stock_name || '—'}</span>
                    <span className="text-gray-500 ml-2">{tsCodeToPlain(t.ts_code)}</span>
                  </td>
                  <td className="px-3 py-2">
                    {t.status === 'pending' && <span className="text-gray-400">等待中</span>}
                    {t.status === 'running' && (
                      <span className="text-blue-600 flex items-center gap-1">
                        <Loader2 className="h-3 w-3 animate-spin" />分析中
                      </span>
                    )}
                    {t.status === 'success' && (
                      <span className="text-green-600 flex items-center gap-1">
                        <CheckCircle2 className="h-3 w-3" />完成
                      </span>
                    )}
                    {t.status === 'error' && (
                      <span className="text-red-500 flex items-center gap-1" title={t.error ?? undefined}>
                        <XCircle className="h-3 w-3" />失败
                        {t.error && <span className="ml-1 text-xs truncate max-w-[220px]">{t.error}</span>}
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right text-gray-500">
                    {t.duration_sec != null ? `${t.duration_sec}s` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {isRunning ? '后台继续（关闭窗口）' : '关闭'}
          </Button>
          {!taskId && (
            <Button
              onClick={handleStart}
              disabled={submitting || selectedTsCodes.length === 0}
              className="gap-1.5"
            >
              <Sparkles className="h-3.5 w-3.5" />
              {submitting ? '提交中...' : '开始分析'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
