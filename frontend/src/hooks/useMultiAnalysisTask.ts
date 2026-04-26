'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { apiClient } from '@/lib/api-client'

const POLL_INTERVAL_MS = 3000
const PROBE_INTERVAL_MS = 3000

export interface UseMultiAnalysisTaskOptions {
  /** 当前股票 ts_code; 为 null 时所有操作 no-op */
  tsCode: string | null
  /** 股票名称 + 纯代码; submit 时必传, null 则按钮 disabled */
  stockName?: string | null
  stockCode?: string | null
  /** 是否允许 mount 后每 3s 探活跃任务 (主页 true / 弹窗 false) */
  enableProbe?: boolean
  /** 仅在 enabled=true 时启动 (例如弹窗 open=true) */
  enabled?: boolean
  /** 任务终态后回调; 主页用来 bump expertsRefreshKey, 弹窗用来 refreshKey + onSaved */
  onFinish?: (success: boolean) => void
}

export interface UseMultiAnalysisTaskResult {
  /** 按钮显示"分析中..." 时为 true (提交中 + 轮询中 + 探活命中后) */
  generating: boolean
  /** 当前活跃任务 id; 提交/探活命中时填充, 终态后清空 */
  taskId: string | null
  /** 完成 / 失败 / "已续上进度" 文案; 调用方负责渲染 */
  message: { type: 'success' | 'error'; text: string } | null
  /** 触发一键分析: 先查活跃任务, 命中续轮询, 否则提交新任务 */
  start: () => Promise<void>
  /** 主动复位 (弹窗关闭时调用) */
  reset: () => void
}

/**
 * 单只股票"一键多专家分析"任务钩子: 共用提交 / 轮询 / 探活 / 终态收尾逻辑。
 *
 * 后端协议: POST /generate-multi 返回 celery_task_id, 通过 GET /batch/{id} 3s 轮询;
 * 终态后再补拉一次拿最终 metadata.items (兜底 task_success 信号与最后一次 _flush_progress
 * 抢跑的丢帧)。enableProbe=true 时 mount 后每 3s 探一次 GET /active/by-ts-code/{ts_code},
 * 命中则进轮询 (同步 /stocks 批量分析或多 tab 状态)。
 */
export function useMultiAnalysisTask({
  tsCode,
  stockName,
  stockCode,
  enableProbe = false,
  enabled = true,
  onFinish,
}: UseMultiAnalysisTaskOptions): UseMultiAnalysisTaskResult {
  const [generating, setGenerating] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pollCancelledRef = useRef(false)
  // 探活 effect 用 ref 读最新 taskId, 避免列入 deps 后每次 setTaskId 触发 effect 重建 → 按钮闪动
  const taskIdRef = useRef<string | null>(null)
  useEffect(() => { taskIdRef.current = taskId }, [taskId])

  // 切股票 / disable 时清理: 用 lastTsCodeRef 比较 "上一次实际生效的 tsCode",
  // 仅在真切到不同值时清状态; 首次 (null → X) 不清, 否则会把刚由探活设上的状态误清掉。
  const lastTsCodeRef = useRef<string | null>(null)

  const clearPoll = useCallback(() => {
    pollCancelledRef.current = true
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current)
      pollTimerRef.current = null
    }
  }, [])

  const reset = useCallback(() => {
    clearPoll()
    setGenerating(false)
    setTaskId(null)
    setMessage(null)
  }, [clearPoll])

  const finish = useCallback(
    (data: any) => {
      const items = (data?.items as Array<{ status?: string; error?: string | null; expert_count?: number }> | undefined) ?? []
      const item = items[0]
      const errorText = item?.error
      const success = data?.status === 'success' && item?.status !== 'error' && !errorText
      setMessage({
        type: success ? 'success' : 'error',
        text: success
          ? `${item?.expert_count ?? 0} 位专家完成`
          : (errorText || data?.error || '一键分析失败'),
      })
      setGenerating(false)
      setTaskId(null)
      onFinish?.(success)
    },
    [onFinish],
  )

  const poll = useCallback(
    async (id: string) => {
      if (pollCancelledRef.current) return
      try {
        const res = await apiClient.getBatchAnalysisProgress(id)
        if (pollCancelledRef.current) return
        if (res?.code === 200 && res.data) {
          const terminal = res.data.status === 'success' || res.data.status === 'failure'
          if (terminal) {
            // task_success 信号写 status 与任务体最后一次 _flush_progress 是两条独立 SQL,
            // 信号若先到这一轮拿到的 metadata.items 还是上一帧。终态后再补拉一次兜底。
            try {
              const final = await apiClient.getBatchAnalysisProgress(id)
              if (!pollCancelledRef.current && final?.code === 200 && final.data) {
                finish(final.data)
                return
              }
            } catch {
              /* 兜底失败仍按当前数据收尾 */
            }
            if (!pollCancelledRef.current) finish(res.data)
            return
          }
        }
      } catch {
        /* 网络抖动忽略, 下个 tick 重试 */
      }
      if (!pollCancelledRef.current) {
        pollTimerRef.current = setTimeout(() => poll(id), POLL_INTERVAL_MS)
      }
    },
    [finish],
  )

  const start = useCallback(async () => {
    if (!tsCode || !stockName || !stockCode) return
    clearPoll()
    pollCancelledRef.current = false
    setGenerating(true)
    setMessage(null)
    try {
      // 先查活跃任务: 用户可能已在 /stocks 批量分析里包含本股, 或多 tab 重复点击
      const active = await apiClient.getActiveTaskByTsCode(tsCode)
      const existingId = active?.data?.celery_task_id
      if (existingId) {
        setTaskId(existingId)
        setMessage({ type: 'success', text: '该股已有正在进行的分析任务，已续上进度' })
        poll(existingId)
        return
      }
      const res = await apiClient.generateMultiAnalysis({
        ts_code: tsCode,
        stock_name: stockName,
        stock_code: stockCode,
        analysis_types: ['hot_money_view', 'midline_industry_expert', 'longterm_value_watcher'],
        include_cio: true,
      })
      if (res?.code === 200 && res.data?.celery_task_id) {
        setTaskId(res.data.celery_task_id)
        poll(res.data.celery_task_id)
      } else {
        setMessage({ type: 'error', text: res?.message || '一键分析提交失败' })
        setGenerating(false)
      }
    } catch (e: any) {
      setMessage({ type: 'error', text: e?.response?.data?.message || '一键分析失败' })
      setGenerating(false)
    }
  }, [tsCode, stockName, stockCode, clearPoll, poll])

  // 切股票 / 失能时复位 (但不在 null → X 的首次 mount 时清, 避免误清探活已设上的状态)
  useEffect(() => {
    if (!enabled) {
      reset()
      lastTsCodeRef.current = null
      return
    }
    if (!tsCode) return
    if (lastTsCodeRef.current && lastTsCodeRef.current !== tsCode) {
      reset()
    }
    lastTsCodeRef.current = tsCode
  }, [tsCode, enabled, reset])

  // 卸载时停止轮询 (与切股票分开, 避免 deps 抖动误清)
  useEffect(() => () => clearPoll(), [clearPoll])

  // mount 后每 3s 探活跃任务 (仅 enableProbe && enabled)
  // 解决: /stocks 批量分析包含本股, 或另一窗口提交一键 → 当前页自动跟进禁用按钮
  useEffect(() => {
    if (!enableProbe || !enabled || !tsCode) return
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | null = null

    const probe = async () => {
      // 已有 polling 在跑, 跳过探活, 下次 tick 再说
      if (pollTimerRef.current || taskIdRef.current) {
        if (!cancelled) timer = setTimeout(probe, PROBE_INTERVAL_MS)
        return
      }
      try {
        const res = await apiClient.getActiveTaskByTsCode(tsCode)
        if (cancelled) return
        const id = res?.data?.celery_task_id
        if (id) {
          pollCancelledRef.current = false
          setTaskId(id)
          setGenerating(true)
          setMessage(null)
          poll(id)
          return // 进入轮询后探活退出, 由 finish 收尾
        }
      } catch {
        /* 网络抖动忽略 */
      }
      if (!cancelled) timer = setTimeout(probe, PROBE_INTERVAL_MS)
    }

    probe()
    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [enableProbe, enabled, tsCode, poll])

  return { generating, taskId, message, start, reset }
}
