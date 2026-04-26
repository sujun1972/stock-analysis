'use client'

import React, { useEffect, useMemo, useState } from 'react'
import {
  ChevronLeft,
  ChevronRight,
  Pencil,
  Trash2,
  Code,
  RotateCcw,
  AlertTriangle,
  Copy,
  Check,
  Save,
  X,
  Clock,
} from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import type { StockAnalysisRecord } from '@/types'

// ── HistoryPager ─────────────────────────────────────────────────────────────

export interface HistoryPagerProps {
  /** Total records cached in memory (we cap at 50 from the API today). */
  total: number
  /** Position within the cached array (0-based). */
  index: number
  /** Underlying total in the database — shown when > total fetched. */
  totalInDb?: number
  current: StockAnalysisRecord | null
  loading?: boolean
  onPrev: () => void
  onNext: () => void
}

// Records are sorted DESC (latest first), so navigating to a newer version
// decrements index. Left chevron = older (idx+1), right chevron = newer (idx-1).
export function HistoryPager({
  total,
  index,
  totalInDb,
  current,
  loading,
  onPrev,
  onNext,
}: HistoryPagerProps) {
  const hasMultiple = total > 1
  const dbExtra = typeof totalInDb === 'number' && totalInDb > total ? totalInDb - total : 0
  const olderDisabled = !hasMultiple || index >= total - 1 || !!loading
  const newerDisabled = !hasMultiple || index <= 0 || !!loading

  const dateLabel = useMemo(() => {
    if (!current?.created_at) return ''
    return current.created_at.replace('T', ' ').slice(0, 16)
  }, [current])

  return (
    <div className="inline-flex items-center gap-1.5 text-xs">
      {/* Version + date pill — date hides on <sm so the pill stays compact on
          mobile (390px viewport) without losing the version anchor. */}
      <div
        className="inline-flex items-center gap-1.5 rounded border border-border/70 bg-muted/40 px-2 py-1 font-mono tabular-nums text-muted-foreground"
        title={dateLabel ? `生成于 ${dateLabel}` : undefined}
      >
        <Clock className="h-3 w-3 shrink-0 opacity-70" aria-hidden />
        <span className="text-foreground/80">v{current?.version ?? '—'}</span>
        <span className="hidden sm:inline opacity-50">·</span>
        <span className="hidden sm:inline">{dateLabel || '—'}</span>
      </div>
      {hasMultiple && (
        <div className="inline-flex items-center gap-0.5">
          <button
            type="button"
            onClick={onPrev}
            disabled={olderDisabled}
            className="inline-flex h-6 w-6 items-center justify-center rounded text-muted-foreground transition-colors duration-fast hover:bg-surface-hover hover:text-foreground disabled:cursor-not-allowed disabled:opacity-30 focus-ring"
            aria-label="更早版本"
            title="更早版本（→ 索引 +1）"
          >
            <ChevronLeft className="h-3.5 w-3.5" aria-hidden />
          </button>
          <span className="min-w-[40px] sm:min-w-[44px] text-center font-mono tabular-nums text-muted-foreground">
            {index + 1}/{total}
            {dbExtra > 0 && <span className="opacity-60">+{dbExtra}</span>}
          </span>
          <button
            type="button"
            onClick={onNext}
            disabled={newerDisabled}
            className="inline-flex h-6 w-6 items-center justify-center rounded text-muted-foreground transition-colors duration-fast hover:bg-surface-hover hover:text-foreground disabled:cursor-not-allowed disabled:opacity-30 focus-ring"
            aria-label="更新版本"
            title="更新版本（→ 索引 -1）"
          >
            <ChevronRight className="h-3.5 w-3.5" aria-hidden />
          </button>
        </div>
      )}
    </div>
  )
}

// ── RecordActionToolbar ──────────────────────────────────────────────────────

export interface RecordActionToolbarProps {
  disabled?: boolean
  onEdit?: () => void
  onDelete?: () => void
  onView?: () => void
  /** Review trigger — only present for hot_money / midline / longterm originals. */
  onReview?: () => void
  reviewing?: boolean
  reviewLabel?: string
}

export function RecordActionToolbar({
  disabled,
  onEdit,
  onDelete,
  onView,
  onReview,
  reviewing,
  reviewLabel,
}: RecordActionToolbarProps) {
  return (
    <div className="inline-flex items-center gap-0.5 rounded border border-border/70 bg-background px-0.5 py-0.5">
      {onView && (
        <ToolbarIconBtn
          onClick={onView}
          disabled={disabled}
          title="查看源代码（原始 JSON）"
          aria-label="查看源代码"
          tone="primary"
        >
          <Code className="h-3.5 w-3.5" aria-hidden />
        </ToolbarIconBtn>
      )}
      {onEdit && (
        <ToolbarIconBtn
          onClick={onEdit}
          disabled={disabled}
          title="编辑"
          aria-label="编辑"
          tone="info"
        >
          <Pencil className="h-3.5 w-3.5" aria-hidden />
        </ToolbarIconBtn>
      )}
      {onReview && (
        <ToolbarIconBtn
          onClick={onReview}
          disabled={disabled || reviewing}
          title={reviewLabel ?? '让专家复盘此报告'}
          aria-label={reviewLabel ?? '复盘'}
          tone="warning"
        >
          <RotateCcw
            className={`h-3.5 w-3.5 ${reviewing ? 'animate-spin' : ''}`}
            aria-hidden
          />
        </ToolbarIconBtn>
      )}
      {onDelete && (
        <ToolbarIconBtn
          onClick={onDelete}
          disabled={disabled}
          title="删除"
          aria-label="删除"
          tone="danger"
        >
          <Trash2 className="h-3.5 w-3.5" aria-hidden />
        </ToolbarIconBtn>
      )}
    </div>
  )
}

function ToolbarIconBtn({
  children,
  onClick,
  disabled,
  title,
  tone,
  ...rest
}: {
  children: React.ReactNode
  onClick: () => void
  disabled?: boolean
  title: string
  tone: 'primary' | 'info' | 'warning' | 'danger'
} & React.AriaAttributes) {
  // Resting state stays monochrome — semantic tone surfaces only on hover/focus.
  const toneCls =
    tone === 'danger'
      ? 'hover:bg-negative-soft hover:text-negative'
      : tone === 'warning'
      ? 'hover:bg-warning-soft hover:text-warning'
      : tone === 'info'
      ? 'hover:bg-primary/10 hover:text-primary'
      : 'hover:bg-surface-hover hover:text-foreground'
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={`inline-flex h-6 w-6 items-center justify-center rounded text-muted-foreground transition-colors duration-fast disabled:cursor-not-allowed disabled:opacity-40 focus-ring ${toneCls}`}
      {...rest}
    >
      {children}
    </button>
  )
}

// ── DeleteConfirmDialog ──────────────────────────────────────────────────────

export interface DeleteConfirmDialogProps {
  open: boolean
  record: StockAnalysisRecord | null
  onClose: () => void
  onConfirm: () => Promise<{ ok: boolean; message?: string }>
  /** Display name for the subject line, e.g. 游资观点 v3. */
  contextLabel?: string
}

export function DeleteConfirmDialog({
  open,
  record,
  onClose,
  onConfirm,
  contextLabel,
}: DeleteConfirmDialogProps) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) {
      setBusy(false)
      setError(null)
    }
  }, [open])

  const handle = async () => {
    setBusy(true)
    setError(null)
    const res = await onConfirm()
    if (res.ok) {
      setBusy(false)
      onClose()
    } else {
      setBusy(false)
      setError(res.message ?? '删除失败，请重试')
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && !busy && onClose()}>
      <DialogContent className="max-w-[calc(100vw-2rem)] sm:max-w-sm">
        <div className="-mx-6 -mt-6 px-6 pt-6 pb-3 border-b border-negative/20 bg-negative-soft/40">
          <DialogHeader className="space-y-1">
            <DialogTitle className="flex items-center gap-2 text-negative">
              <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden />
              确认删除分析记录
            </DialogTitle>
            <DialogDescription className="text-xs">
              此操作不可恢复，请确认。
            </DialogDescription>
          </DialogHeader>
        </div>

        <div className="space-y-2 text-sm">
          <p className="text-muted-foreground">即将删除：</p>
          <div className="rounded-md border border-border bg-muted/30 px-3 py-2 font-mono tabular-nums text-xs">
            <div className="flex items-center justify-between text-foreground">
              <span className="font-semibold">
                {contextLabel ?? '分析记录'} · v{record?.version ?? '—'}
              </span>
              {record?.score != null && (
                <span className="text-muted-foreground">评分 {record.score}</span>
              )}
            </div>
            <div className="mt-0.5 text-muted-foreground">
              {record?.created_at?.replace('T', ' ').slice(0, 19) ?? '—'}
            </div>
          </div>
          {error && <p className="text-xs text-negative">{error}</p>}
        </div>

        <DialogFooter className="gap-2 sm:gap-2">
          <Button variant="outline" size="sm" onClick={onClose} disabled={busy}>
            取消
          </Button>
          <Button variant="destructive" size="sm" onClick={handle} disabled={busy}>
            <Trash2 className="h-3.5 w-3.5" aria-hidden />
            {busy ? '删除中…' : '永久删除'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── EditAnalysisDialog ───────────────────────────────────────────────────────
// Pretty-prints JSON on open so individual fields are easy to edit; re-compacts
// to single-line on save so the rendering layer sees the same shape it stored.

export interface EditAnalysisDialogProps {
  open: boolean
  record: StockAnalysisRecord | null
  onClose: () => void
  onSave: (params: {
    analysis_text: string
    score?: number
  }) => Promise<{ ok: boolean; message?: string }>
  contextLabel?: string
}

export function EditAnalysisDialog({
  open,
  record,
  onClose,
  onSave,
  contextLabel,
}: EditAnalysisDialogProps) {
  const [text, setText] = useState('')
  const [score, setScore] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open && record) {
      let initial = record.analysis_text ?? ''
      try {
        const parsed = JSON.parse(initial)
        if (parsed && typeof parsed === 'object') {
          initial = JSON.stringify(parsed, null, 2)
        }
      } catch {
        /* leave verbatim */
      }
      setText(initial)
      setScore(record.score != null ? String(record.score) : '')
      setError(null)
      setBusy(false)
    }
  }, [open, record])

  const handle = async () => {
    if (!text.trim()) {
      setError('分析内容不能为空')
      return
    }
    let parsedScore: number | undefined
    if (score.trim()) {
      const n = Number(score)
      if (!Number.isFinite(n) || n < 0 || n > 10) {
        setError('评分需在 0 ~ 10 之间')
        return
      }
      parsedScore = n
    }
    setBusy(true)
    setError(null)
    let payloadText = text
    try {
      const reparsed = JSON.parse(text)
      if (reparsed && typeof reparsed === 'object') {
        payloadText = JSON.stringify(reparsed)
      }
    } catch {
      /* keep as-is */
    }
    const res = await onSave({ analysis_text: payloadText, score: parsedScore })
    setBusy(false)
    if (res.ok) {
      onClose()
    } else {
      setError(res.message ?? '保存失败')
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && !busy && onClose()}>
      <DialogContent className="flex max-h-[100dvh] sm:max-h-[90vh] max-w-[calc(100vw-1rem)] sm:max-w-3xl flex-col gap-3 sm:gap-4 p-4 sm:p-6">
        <DialogHeader className="space-y-1">
          <DialogTitle className="flex items-center gap-2 pr-8">
            <Pencil className="h-4 w-4 text-primary" aria-hidden />
            编辑分析记录
          </DialogTitle>
          <DialogDescription className="font-mono text-xs tabular-nums break-all">
            {contextLabel ?? '分析记录'} · v{record?.version ?? '—'} ·{' '}
            {record?.created_at?.replace('T', ' ').slice(0, 16) ?? '—'}
          </DialogDescription>
        </DialogHeader>

        <div className="flex items-center gap-3">
          <label
            htmlFor="edit-score"
            className="text-xs font-medium text-muted-foreground shrink-0"
          >
            评分（0–10，可空）
          </label>
          <input
            id="edit-score"
            type="number"
            min={0}
            max={10}
            step={0.1}
            value={score}
            onChange={(e) => setScore(e.target.value)}
            placeholder="留空则保持原值"
            className="h-8 w-32 rounded border border-input bg-background px-2 font-mono text-sm tabular-nums focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        <div className="flex min-h-0 flex-1 flex-col gap-1.5">
          <div className="flex items-center justify-between gap-2">
            <span className="text-xs font-medium text-muted-foreground">
              <span className="hidden sm:inline">分析正文（JSON 已自动展开 — 保存时会重新压缩）</span>
              <span className="sm:hidden">分析正文</span>
            </span>
            <span className="font-mono text-[10px] tabular-nums text-muted-foreground/70 shrink-0">
              {text.length.toLocaleString()} 字符
            </span>
          </div>
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            spellCheck={false}
            className="min-h-[240px] sm:min-h-[320px] flex-1 resize-none rounded-md border border-input bg-muted/30 p-2 sm:p-3 font-mono text-xs leading-relaxed scrollbar-thin focus:outline-none focus:ring-2 focus:ring-ring"
          />
        </div>

        {error && <p className="text-xs text-negative">{error}</p>}

        <DialogFooter className="gap-2 sm:gap-2">
          <Button variant="outline" size="sm" onClick={onClose} disabled={busy}>
            <X className="h-3.5 w-3.5" aria-hidden />
            取消
          </Button>
          <Button size="sm" onClick={handle} disabled={busy || !text.trim()}>
            <Save className="h-3.5 w-3.5" aria-hidden />
            {busy ? '保存中…' : '保存修改'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── ViewSourceDialog ─────────────────────────────────────────────────────────

export interface ViewSourceDialogProps {
  open: boolean
  record: StockAnalysisRecord | null
  onClose: () => void
  contextLabel?: string
}

export function ViewSourceDialog({
  open,
  record,
  onClose,
  contextLabel,
}: ViewSourceDialogProps) {
  const [copied, setCopied] = useState(false)

  const pretty = useMemo(() => {
    const raw = record?.analysis_text ?? ''
    try {
      const parsed = JSON.parse(raw)
      if (parsed && typeof parsed === 'object') return JSON.stringify(parsed, null, 2)
    } catch {
      /* fall through */
    }
    return raw
  }, [record])

  useEffect(() => {
    if (!open) setCopied(false)
  }, [open])

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(pretty)
    } catch {
      const el = document.createElement('textarea')
      el.value = pretty
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="flex max-h-[100dvh] sm:max-h-[90vh] max-w-[calc(100vw-1rem)] sm:max-w-4xl flex-col gap-3 p-0">
        <div className="space-y-2 border-b border-border bg-muted/40 p-3 sm:p-5">
          <DialogHeader className="space-y-1">
            <DialogTitle className="flex items-center gap-2 pr-8">
              <Code className="h-4 w-4 text-primary" aria-hidden />
              源代码视图
            </DialogTitle>
            <DialogDescription className="sr-only">
              查看分析记录原始 JSON 内容
            </DialogDescription>
          </DialogHeader>
          {/* Metadata pills are siblings to DialogHeader, not nested in
              DialogDescription (which is a <p>) — avoids hydration warnings. */}
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-[11px] tabular-nums">
            <Pill label="记录" value={contextLabel ?? '分析记录'} />
            <Pill label="ID" value={String(record?.id ?? '—')} />
            <Pill label="版本" value={`v${record?.version ?? '—'}`} />
            {record?.score != null && (
              <Pill label="评分" value={String(record.score)} />
            )}
            <Pill
              label="生成于"
              value={record?.created_at?.replace('T', ' ').slice(0, 16) ?? '—'}
            />
            {record?.ai_provider && (
              <Pill
                label="模型"
                value={`${record.ai_provider}/${record.ai_model ?? '—'}`}
              />
            )}
          </div>
        </div>

        <div className="min-h-0 flex-1 px-3 sm:px-5">
          <pre className="h-full max-h-[55vh] sm:max-h-[60vh] overflow-auto whitespace-pre-wrap break-words rounded-md border border-border bg-background p-2 sm:p-3 font-mono text-xs leading-relaxed text-foreground/90 scrollbar-thin">
            {pretty || '（空）'}
          </pre>
        </div>

        <DialogFooter className="gap-2 border-t border-border bg-muted/40 p-3 sm:p-4 sm:gap-2">
          <Button variant="outline" size="sm" onClick={handleCopy}>
            {copied ? (
              <Check className="h-3.5 w-3.5 text-emerald-500" aria-hidden />
            ) : (
              <Copy className="h-3.5 w-3.5" aria-hidden />
            )}
            {copied ? '已复制' : '复制'}
          </Button>
          <Button size="sm" onClick={onClose}>
            关闭
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function Pill({ label, value }: { label: string; value: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded border border-border/70 bg-background px-1.5 py-0.5">
      <span className="text-muted-foreground">{label}</span>
      <span className="text-foreground">{value}</span>
    </span>
  )
}
