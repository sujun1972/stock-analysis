'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  getStockAnalysisHistory,
  updateStockAnalysis,
  deleteStockAnalysis,
} from '@/lib/api/stocks'
import type { StockAnalysisRecord } from '@/types'
import { groupRecordsByTradeDate, type TradeDateGroup } from './trade-date-utils'

export interface UseAnalysisHistoryResult {
  /** 后端原始历史（按 created_at DESC，DEFAULT_LIMIT 内）。 */
  records: StockAnalysisRecord[]
  /** 后端 total（可能 > records.length）。 */
  total: number
  /** 后端 records 按交易日分组（DESC，每组同日版本 ASC + displayVersion 1..N）。 */
  groups: TradeDateGroup[]
  /** 当前选中的交易日 'YYYY-MM-DD'；无记录时为 null。 */
  selectedTradeDate: string | null
  /** 切换到指定交易日（必须在 groups 范围内，否则无操作）。 */
  setSelectedTradeDate: (d: string) => void
  /** 当前选中日的版本组（已按 displayVersion 排好）；无则空数组。 */
  versions: TradeDateGroup['versions']
  /** 当前选中版本在 versions 中的索引（0-based）。 */
  versionIndex: number
  /** 切到同日内更早/更晚的版本（displayVersion 1 → 2 = 更新）。 */
  goNewerVersion: () => void
  goOlderVersion: () => void
  /** 当前展示的记录（versions[versionIndex]）；无则 null。 */
  current: (StockAnalysisRecord & { displayVersion: number; displayTotal: number }) | null
  loading: boolean
  refresh: () => Promise<void>
  remove: (id: number) => Promise<{ ok: boolean; message?: string }>
  update: (
    id: number,
    params: { analysis_text: string; score?: number },
  ) => Promise<{ ok: boolean; message?: string }>
}

const DEFAULT_LIMIT = 50

/**
 * 历史记录 + 编辑/删除 hook，用于主页专家卡 / CIO 卡。
 *
 * 核心模型：AI 分析的标的是"交易日"，同一交易日可能有多个版本（重新生成 / 改提示词 /
 * 切模型），同日版本号在 UI 上按时间正序从 1 重排，避免后端全局 version 跨日跳号造成误解。
 *
 * - 默认选中"最近一个有分析的交易日"的"最新一个版本"
 * - 编辑后通过 `lastViewedIdRef` 锚回原记录所在交易日 + 版本
 * - 删除后若该交易日还有其他版本则继续停留，否则跳到下一个最近有数据的交易日
 */
export function useAnalysisHistory(
  tsCode: string | null | undefined,
  analysisType: string,
  refreshKey?: number,
  enabled: boolean = true,
): UseAnalysisHistoryResult {
  const [records, setRecords] = useState<StockAnalysisRecord[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  // 用户的显式选择优先于"默认最近"；refresh 时若该日还在 groups 里就保留
  const [selectedTradeDate, setSelectedTradeDateState] = useState<string | null>(null)
  const [versionIndex, setVersionIndex] = useState(0)
  const lastViewedIdRef = useRef<number | null>(null)

  const fetchHistory = useCallback(async () => {
    if (!tsCode || !analysisType || !enabled) {
      setRecords([])
      setTotal(0)
      return
    }
    setLoading(true)
    try {
      const res = await getStockAnalysisHistory(tsCode, analysisType, DEFAULT_LIMIT, 0)
      if (res?.code === 200 && res.data) {
        const items = res.data.items ?? []
        setRecords(items)
        setTotal(res.data.total ?? items.length)
      } else {
        setRecords([])
        setTotal(0)
      }
    } catch {
      setRecords([])
      setTotal(0)
    } finally {
      setLoading(false)
    }
  }, [tsCode, analysisType, enabled])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory, refreshKey])

  // 切股票/类型时重置选择，避免上一只的日期被错误地继承
  useEffect(() => {
    setSelectedTradeDateState(null)
    setVersionIndex(0)
    lastViewedIdRef.current = null
  }, [tsCode, analysisType])

  const groups = useMemo(() => groupRecordsByTradeDate(records), [records])

  // 锚点选中**只在 groups 引用变化时跑一次**（即 fetchHistory 后或股票切换后）。
  // 不依赖 selectedTradeDate / versionIndex —— 否则用户手动切日期/版本会触发回锚循环。
  // 优先级：① sticky id 命中 → 锚回该记录；② 当前选择仍有效 → 保持；③ 默认最近一天 + 最新版本。
  useEffect(() => {
    if (groups.length === 0) {
      setSelectedTradeDateState((d) => (d === null ? d : null))
      setVersionIndex((i) => (i === 0 ? i : 0))
      return
    }

    const stickyId = lastViewedIdRef.current
    if (stickyId != null) {
      for (const g of groups) {
        const idx = g.versions.findIndex((r) => r.id === stickyId)
        if (idx >= 0) {
          setSelectedTradeDateState(g.tradeDate)
          setVersionIndex(idx)
          return
        }
      }
      // sticky 已被删除，清锚点走默认
      lastViewedIdRef.current = null
    }

    // 用 functional updater 读最新 selectedTradeDate，避免把它列入 deps 触发回锚循环
    setSelectedTradeDateState((prev) => {
      if (prev) {
        const g = groups.find((x) => x.tradeDate === prev)
        if (g) {
          // 当前日期仍有效 → 保持日期；versionIndex 由下面的 setVersionIndex 兜底 clamp
          setVersionIndex((i) => Math.min(i, g.versions.length - 1))
          return prev
        }
      }
      // 当前日期失效或未选 → 默认最近一天 + 最新版本
      const first = groups[0]
      setVersionIndex(first.versions.length - 1)
      return first.tradeDate
    })
  }, [groups])

  // 暴露 current，stash 它的 id 以便 refresh 后锚回
  const versions = useMemo(() => {
    if (!selectedTradeDate) return [] as TradeDateGroup['versions']
    const g = groups.find((x) => x.tradeDate === selectedTradeDate)
    return g?.versions ?? []
  }, [groups, selectedTradeDate])

  const safeIdx = Math.max(0, Math.min(versionIndex, Math.max(0, versions.length - 1)))
  const current = versions[safeIdx] ?? null

  useEffect(() => {
    if (current) lastViewedIdRef.current = current.id
  }, [current])

  const setSelectedTradeDate = useCallback(
    (d: string) => {
      const g = groups.find((x) => x.tradeDate === d)
      if (!g) return
      // 切日期默认跳到该日最新版本（用户期望"看 4-25 那天" → 显示当天最终结论）
      setSelectedTradeDateState(d)
      setVersionIndex(g.versions.length - 1)
    },
    [groups],
  )

  const goNewerVersion = useCallback(() => {
    if (versions.length === 0) return
    setVersionIndex((i) => Math.min(versions.length - 1, i + 1))
  }, [versions.length])

  const goOlderVersion = useCallback(() => {
    if (versions.length === 0) return
    setVersionIndex((i) => Math.max(0, i - 1))
  }, [versions.length])

  const remove = useCallback(
    async (id: number): Promise<{ ok: boolean; message?: string }> => {
      try {
        const res = await deleteStockAnalysis(id)
        if (res?.code === 200) {
          if (lastViewedIdRef.current === id) lastViewedIdRef.current = null
          await fetchHistory()
          return { ok: true }
        }
        return { ok: false, message: res?.message ?? '删除失败' }
      } catch (e: any) {
        return { ok: false, message: e?.response?.data?.message ?? '删除失败' }
      }
    },
    [fetchHistory],
  )

  const update = useCallback(
    async (
      id: number,
      params: { analysis_text: string; score?: number },
    ): Promise<{ ok: boolean; message?: string }> => {
      try {
        const res = await updateStockAnalysis(id, params)
        if (res?.code === 200) {
          await fetchHistory()
          return { ok: true }
        }
        return { ok: false, message: res?.message ?? '修改失败' }
      } catch (e: any) {
        return { ok: false, message: e?.response?.data?.message ?? '修改失败' }
      }
    },
    [fetchHistory],
  )

  return {
    records,
    total,
    groups,
    selectedTradeDate,
    setSelectedTradeDate,
    versions,
    versionIndex: safeIdx,
    goNewerVersion,
    goOlderVersion,
    current,
    loading,
    refresh: fetchHistory,
    remove,
    update,
  }
}
