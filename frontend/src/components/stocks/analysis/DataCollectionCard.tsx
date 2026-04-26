'use client'

import React, { useCallback, useState } from 'react'
import { Database, ChevronDown, ChevronUp, Sparkles, RefreshCcw } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { MarkdownContent } from './markdown'
import { useAnalysisHistory } from './useAnalysisHistory'
import {
  TradeDateVersionPager,
  RecordActionToolbar,
  DeleteConfirmDialog,
  EditAnalysisDialog,
  ViewSourceDialog,
} from './RecordActions'

export interface DataCollectionCardProps {
  /** ts_code drives the in-card history fetch (pager → 1/N versions). */
  tsCode: string
  /** Stock display name (passed to collectStockData). */
  stockName: string
  /** External refresh trigger (e.g. one-key analysis bumped key). */
  refreshKey?: number
  /** Bumped after inline edit/delete/generate so /analysis page can re-fetch latest. */
  onChange?: () => void
  /** Anchor id for scrollIntoView. */
  id?: string
}

/**
 * 数据收集卡（"AI 看到的原料"）
 *
 * 与 4 位专家卡的差异：
 *   1. analysis_text 是 Markdown + YAML（非 JSON），用 MarkdownContent 渲染；无评分 / 无 key_quote
 *   2. 默认折叠（5k-15k 字 Markdown 太长，不该默认占屏）
 *   3. "生成数据"按钮直连 collectStockData（同步 1-3 秒，不走 LLM / Celery）
 *   4. 不需要复盘
 */
export function DataCollectionCard({
  tsCode,
  stockName,
  refreshKey,
  onChange,
  id,
}: DataCollectionCardProps) {
  const [open, setOpen] = useState(false)
  const history = useAnalysisHistory(tsCode, 'stock_data_collection', refreshKey)

  const [showDelete, setShowDelete] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const [showSource, setShowSource] = useState(false)

  const [generating, setGenerating] = useState(false)
  const [genMsg, setGenMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const handleGenerate = useCallback(async () => {
    if (!tsCode || !stockName) return
    setGenerating(true)
    setGenMsg(null)
    try {
      const res = await apiClient.collectStockData(tsCode, stockName)
      if (res?.code === 200 && res.data?.text) {
        setGenMsg({ type: 'success', text: '数据收集完成' })
        await history.refresh()
        onChange?.()
      } else {
        setGenMsg({ type: 'error', text: res?.message || '数据收集失败' })
      }
    } catch (e: any) {
      setGenMsg({ type: 'error', text: e?.response?.data?.message || '数据收集失败' })
    } finally {
      setGenerating(false)
    }
  }, [tsCode, stockName, history, onChange])

  const current = history.current
  const charCount = current?.analysis_text?.length ?? 0

  const dialogs = (
    <>
      <DeleteConfirmDialog
        open={showDelete}
        record={current}
        onClose={() => setShowDelete(false)}
        contextLabel="数据收集"
        onConfirm={async () => {
          if (!current) return { ok: false, message: '无可删除记录' }
          const r = await history.remove(current.id)
          if (r.ok) onChange?.()
          return r
        }}
      />
      <EditAnalysisDialog
        open={showEdit}
        record={current}
        onClose={() => setShowEdit(false)}
        contextLabel="数据收集"
        onSave={async (params) => {
          if (!current) return { ok: false, message: '无可编辑记录' }
          const r = await history.update(current.id, params)
          if (r.ok) onChange?.()
          return r
        }}
      />
      <ViewSourceDialog
        open={showSource}
        record={current}
        onClose={() => setShowSource(false)}
        contextLabel="数据收集"
      />
    </>
  )

  const generateButton = (
    <button
      type="button"
      onClick={handleGenerate}
      disabled={generating}
      className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium border border-border text-muted-foreground hover:bg-surface-hover hover:text-foreground disabled:opacity-50 transition-colors duration-fast focus-ring"
      aria-label="同步生成最新数据收集"
    >
      {generating ? (
        <RefreshCcw className="h-3.5 w-3.5 animate-spin" />
      ) : (
        <Sparkles className="h-3.5 w-3.5" />
      )}
      {generating ? '收集中...' : '生成数据'}
    </button>
  )

  // 空态：没有任何历史记录时也允许触发"生成数据"
  if (!current) {
    return (
      <section
        id={id}
        className="rounded-lg border border-gray-200 dark:border-gray-700 bg-card p-3 sm:p-5"
      >
        <header className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <Database className="h-5 w-5 text-muted-foreground" aria-hidden />
          <h2 className="text-base font-semibold">数据收集</h2>
          <span className="text-xs text-gray-500 dark:text-gray-400">AI 看到的原料</span>
          <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">
            {history.loading ? '加载中…' : '尚未生成'}
          </span>
          <div className="ml-auto">{generateButton}</div>
        </header>
        {genMsg && (
          <p className={`mt-2 text-xs ${genMsg.type === 'success' ? 'text-emerald-600' : 'text-red-500'}`}>
            {genMsg.text}
          </p>
        )}
        {dialogs}
      </section>
    )
  }

  return (
    <section
      id={id}
      className="rounded-lg border border-gray-200 dark:border-gray-700 bg-card overflow-hidden"
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 px-3 sm:px-5 py-3 border-b border-gray-100 dark:border-gray-800">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex flex-1 min-w-[200px] items-center gap-3 text-left rounded transition-colors duration-fast hover:bg-gray-50 dark:hover:bg-gray-800/40 -mx-2 px-2 py-1 focus-ring"
          aria-expanded={open}
          aria-controls={id ? `${id}-body` : undefined}
        >
          <Database className="h-5 w-5 text-muted-foreground shrink-0" aria-hidden />
          <div className="flex-1 min-w-0">
            <div className="flex items-baseline gap-2 flex-wrap">
              <h2 className="text-base font-semibold">数据收集</h2>
              <span className="text-xs text-gray-500 dark:text-gray-400">AI 看到的原料</span>
              {charCount > 0 && (
                <span className="text-xs text-gray-400 dark:text-gray-500 tabular-nums">
                  · {charCount.toLocaleString()} 字
                </span>
              )}
            </div>
          </div>
          {open ? (
            <ChevronUp className="h-4 w-4 text-gray-400" aria-hidden />
          ) : (
            <ChevronDown className="h-4 w-4 text-gray-400" aria-hidden />
          )}
        </button>

        <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5 shrink-0 ml-auto">
          <TradeDateVersionPager
            groups={history.groups}
            selectedTradeDate={history.selectedTradeDate}
            onSelectTradeDate={history.setSelectedTradeDate}
            versions={history.versions}
            versionIndex={history.versionIndex}
            onPrevVersion={history.goOlderVersion}
            onNextVersion={history.goNewerVersion}
            loading={history.loading}
          />
          <RecordActionToolbar
            onView={() => setShowSource(true)}
            onEdit={() => setShowEdit(true)}
            onDelete={() => setShowDelete(true)}
          />
          {generateButton}
        </div>
      </div>

      {genMsg && (
        <p className={`px-3 sm:px-5 pt-2 text-xs ${genMsg.type === 'success' ? 'text-emerald-600' : 'text-red-500'}`}>
          {genMsg.text}
        </p>
      )}

      {open && (
        <div
          id={id ? `${id}-body` : undefined}
          className="border-t border-gray-100 dark:border-gray-800 p-3 sm:p-5"
        >
          <MarkdownContent text={current.analysis_text} />
        </div>
      )}

      {dialogs}
    </section>
  )
}
