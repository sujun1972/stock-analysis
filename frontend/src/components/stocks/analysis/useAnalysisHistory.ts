'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import {
  getStockAnalysisHistory,
  updateStockAnalysis,
  deleteStockAnalysis,
} from '@/lib/api/stocks'
import type { StockAnalysisRecord } from '@/types'

export interface UseAnalysisHistoryResult {
  records: StockAnalysisRecord[]
  total: number
  index: number
  setIndex: (n: number) => void
  current: StockAnalysisRecord | null
  loading: boolean
  refresh: () => Promise<void>
  remove: (id: number) => Promise<{ ok: boolean; message?: string }>
  update: (
    id: number,
    params: { analysis_text: string; score?: number },
  ) => Promise<{ ok: boolean; message?: string }>
  /** index 0 (latest); newer increases index toward 0 (we keep DESC sort). */
  goNewer: () => void
  goOlder: () => void
}

const DEFAULT_LIMIT = 50

/**
 * Paginated history + edit/delete hook used by the in-page expert/CIO cards.
 *
 * Records are returned newest-first (index 0 = latest). The hook keeps the
 * cursor stable across refreshes by re-finding the previously-viewed record id;
 * if it's been deleted, falls back to clamp.
 */
export function useAnalysisHistory(
  tsCode: string | null | undefined,
  analysisType: string,
  refreshKey?: number,
  enabled: boolean = true,
): UseAnalysisHistoryResult {
  const [records, setRecords] = useState<StockAnalysisRecord[]>([])
  const [total, setTotal] = useState(0)
  const [index, setIndex] = useState(0)
  const [loading, setLoading] = useState(false)
  const lastViewedIdRef = useRef<number | null>(null)

  const fetchHistory = useCallback(async () => {
    if (!tsCode || !analysisType || !enabled) {
      setRecords([])
      setTotal(0)
      setIndex(0)
      return
    }
    setLoading(true)
    try {
      const res = await getStockAnalysisHistory(tsCode, analysisType, DEFAULT_LIMIT, 0)
      if (res?.code === 200 && res.data) {
        const items = res.data.items ?? []
        setRecords(items)
        setTotal(res.data.total ?? items.length)
        // Re-anchor cursor to the previously-viewed record (e.g. after edit
        // where its id stays the same but its position may have shifted).
        const stickyId = lastViewedIdRef.current
        const stickyIdx = stickyId != null ? items.findIndex((r) => r.id === stickyId) : -1
        setIndex(stickyIdx >= 0 ? stickyIdx : 0)
      } else {
        setRecords([])
        setTotal(0)
        setIndex(0)
      }
    } catch {
      setRecords([])
      setTotal(0)
      setIndex(0)
    } finally {
      setLoading(false)
    }
  }, [tsCode, analysisType, enabled])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory, refreshKey])

  // Stash the viewed record id so refresh() can re-anchor the cursor.
  useEffect(() => {
    if (records[index]) {
      lastViewedIdRef.current = records[index].id
    }
  }, [records, index])

  const safeSetIndex = useCallback(
    (n: number) => {
      if (records.length === 0) return
      const clamped = Math.max(0, Math.min(n, records.length - 1))
      setIndex(clamped)
    },
    [records.length],
  )

  const goNewer = useCallback(() => safeSetIndex(index - 1), [index, safeSetIndex])
  const goOlder = useCallback(() => safeSetIndex(index + 1), [index, safeSetIndex])

  const remove = useCallback(
    async (id: number): Promise<{ ok: boolean; message?: string }> => {
      try {
        const res = await deleteStockAnalysis(id)
        if (res?.code === 200) {
          // Drop the sticky id so the post-delete fetch falls back to clamp(0).
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

  const current = records[index] ?? null

  return {
    records,
    total,
    index,
    setIndex: safeSetIndex,
    current,
    loading,
    refresh: fetchHistory,
    remove,
    update,
    goNewer,
    goOlder,
  }
}
