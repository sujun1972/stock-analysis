'use client'

import React, { useCallback, useState } from 'react'
import { Sparkles, RefreshCcw, BookOpen, RotateCcw } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { apiClient } from '@/lib/api-client'
import { renderBold } from './text-utils'
import { ProsConsList } from './sections'
import { StructuredAnalysisContent } from './StructuredAnalysisContent'
import { MarkdownContent } from './markdown'
import {
  EXPERTS,
  EXPERT_BY_KEY,
  scoreToneClass,
  safeParseJSON,
  extractScore,
  extractKeyQuote,
  extractRating,
  type ExpertMeta,
} from './expert-meta'
import { useAnalysisHistory } from './useAnalysisHistory'
import {
  TradeDateVersionPager,
  RecordActionToolbar,
  DeleteConfirmDialog,
  EditAnalysisDialog,
  ViewSourceDialog,
} from './RecordActions'
import type { StockAnalysisRecord } from '@/types'

type TabExpertKey = Exclude<ExpertMeta['key'], 'cio'>

const REVIEW_ANALYSIS_TYPE: Record<TabExpertKey, string> = {
  hot_money: 'hot_money_review',
  midline: 'midline_review',
  longterm: 'longterm_review',
}

// Subject identity referenced in the review-trigger button tooltip.
// 游资=短线 / 中线=中线 / 价值=长线 — labels the user sees, not the API enum.
const REVIEW_SUBJECT_LABEL: Record<TabExpertKey, string> = {
  hot_money: '短线',
  midline: '中线',
  longterm: '长线',
}

const TAB_EXPERTS = EXPERTS.filter((e) => e.key !== 'cio') as Array<
  ExpertMeta & { key: TabExpertKey }
>

export interface ExpertDetailCardProps {
  /** ts_code (e.g. 601615.SH) — required to drive history fetch. */
  tsCode: string
  /** Stock display name + plain code, used by AI generation calls. */
  stockName: string
  stockCode: string
  /** Active expert tab (controlled). */
  activeExpert: TabExpertKey
  onActiveExpertChange: (k: TabExpertKey) => void
  /** Optional escape hatch — opens the legacy modal for prompt viewing. */
  onOpenHistory?: (defaultTab: ExpertMeta['key']) => void
  /** Single-expert "重新分析" trigger. */
  onRegenerate?: (expert: ExpertMeta) => void
  regeneratingKey?: ExpertMeta['key'] | null
  /** Bumped externally (one-key-analysis / regenerate) → re-fetch every tab's
   *  history. Internal mutations (edit/delete/review) bump it via onChange. */
  refreshKey?: number
  /** Notify parent that records changed so it can refresh latestByExpert
   *  (drives the radar / summary card / quote-panel key_quote). */
  onChange?: () => void
  id?: string
}

/**
 * Three-expert detail card (card ④).
 *
 * Inline-everything refactor: each expert tab now owns:
 *   - sub-tab segmented control: 原报告 | 复盘
 *   - inline history pager + action toolbar (edit / del / source / 复盘)
 *   - delete-confirm / edit / view-source popups
 *
 * The user no longer needs to click a "历史" button to flip versions or trigger
 * a review. The legacy modal is still reachable for prompt viewing only.
 */
export function ExpertDetailCard({
  tsCode,
  stockName,
  stockCode,
  activeExpert,
  onActiveExpertChange,
  onOpenHistory,
  onRegenerate,
  regeneratingKey,
  refreshKey,
  onChange,
  id,
}: ExpertDetailCardProps) {
  return (
    <section
      id={id}
      className="rounded-lg border border-gray-200 dark:border-gray-700 bg-card overflow-hidden"
      aria-label="三专家详情"
    >
      <Tabs value={activeExpert} onValueChange={(v) => onActiveExpertChange(v as TabExpertKey)}>
        <header className="flex items-center justify-between gap-3 px-3 sm:px-5 py-2 border-b border-gray-100 dark:border-gray-800">
          <TabsList className="bg-transparent gap-1 p-0">
            {TAB_EXPERTS.map((e) => {
              const Icon = e.icon
              return (
                <TabsTrigger
                  key={e.key}
                  value={e.key}
                  className="gap-1.5 data-[state=active]:bg-muted data-[state=active]:shadow-none"
                >
                  <Icon className="h-3.5 w-3.5" style={{ color: `hsl(var(${e.colorVar}))` }} aria-hidden />
                  <span>{e.label}</span>
                </TabsTrigger>
              )
            })}
          </TabsList>
          {/* Action buttons: icon + label on ≥sm, icon-only on <sm so the
              tab list keeps room on mobile (390px viewport). */}
          <div className="flex items-center gap-1.5 shrink-0">
            <button
              type="button"
              onClick={() => onRegenerate?.(EXPERT_BY_KEY[activeExpert])}
              disabled={regeneratingKey === activeExpert}
              className="inline-flex items-center gap-1 px-1.5 sm:px-2 py-1 rounded text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors duration-fast disabled:opacity-50 focus-ring"
              title={`让${EXPERT_BY_KEY[activeExpert].label}专家重新分析`}
              aria-label={`让${EXPERT_BY_KEY[activeExpert].label}专家重新分析`}
            >
              {regeneratingKey === activeExpert ? (
                <RefreshCcw className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Sparkles className="h-3.5 w-3.5" />
              )}
              <span className="hidden sm:inline">重新分析</span>
            </button>
            {onOpenHistory && (
              <button
                type="button"
                onClick={() => onOpenHistory(activeExpert)}
                className="inline-flex items-center gap-1 px-1.5 sm:px-2 py-1 rounded text-xs text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors duration-fast focus-ring"
                title="打开提示词查看视图（仅模板，不影响内容）"
                aria-label="查看提示词模板"
              >
                <BookOpen className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">提示词</span>
              </button>
            )}
          </div>
        </header>

        {TAB_EXPERTS.map((e) => (
          <TabsContent key={e.key} value={e.key} className="m-0 p-3 sm:p-5">
            <ExpertBody
              expert={e}
              tsCode={tsCode}
              stockName={stockName}
              stockCode={stockCode}
              externalRefresh={refreshKey ?? 0}
              isActive={activeExpert === e.key}
              onChange={onChange}
            />
          </TabsContent>
        ))}
      </Tabs>
    </section>
  )
}

interface ExpertBodyProps {
  expert: ExpertMeta & { key: TabExpertKey }
  tsCode: string
  stockName: string
  stockCode: string
  externalRefresh: number
  /** Only fetch when this tab is the active one — saves 2 wasted history calls. */
  isActive: boolean
  onChange?: () => void
}

function ExpertBody({
  expert,
  tsCode,
  stockName,
  stockCode,
  externalRefresh,
  isActive,
  onChange,
}: ExpertBodyProps) {
  const [subTab, setSubTab] = useState<'original' | 'review'>('original')

  // Two histories — one for the original analysis_type, one for the *_review
  // counterpart; both re-fetch when externalRefresh bumps.
  const originalHistory = useAnalysisHistory(
    tsCode,
    expert.analysisType,
    externalRefresh,
    isActive,
  )
  const reviewHistory = useAnalysisHistory(
    tsCode,
    REVIEW_ANALYSIS_TYPE[expert.key],
    externalRefresh,
    isActive,
  )

  const active = subTab === 'original' ? originalHistory : reviewHistory
  const isReviewSub = subTab === 'review'

  const [showDelete, setShowDelete] = useState(false)
  const [showEdit, setShowEdit] = useState(false)
  const [showSource, setShowSource] = useState(false)

  const [reviewing, setReviewing] = useState(false)
  const [actionMsg, setActionMsg] = useState<{
    type: 'success' | 'error' | 'info'
    text: string
  } | null>(null)

  const handleReview = useCallback(
    async (force = false): Promise<void> => {
      if (!originalHistory.current) return
      setReviewing(true)
      setActionMsg(null)

      // Backend rejects pre-window-deadline reviews with a "建议..." hint
      // (建议中线 ≥20 天 / 长线 ≥90 天). When that's the only error, prompt
      // the user to retry with force=true rather than just showing the message.
      const handleSoftReject = async (msg: string) => {
        if (force || !msg.includes('建议')) {
          setActionMsg({ type: 'error', text: msg })
          return
        }
        if (window.confirm(`${msg}\n\n是否仍要强制生成复盘？`)) {
          await handleReview(true)
          return
        }
        setActionMsg({ type: 'info', text: '已取消复盘' })
      }

      try {
        const res = await apiClient.generateReviewAnalysis({
          ts_code: tsCode,
          stock_name: stockName,
          stock_code: stockCode,
          original_analysis_id: originalHistory.current.id,
          review_type: expert.key,
          force,
        })
        if (res?.code === 200 && res.data?.analysis_text) {
          setActionMsg({ type: 'success', text: '复盘完成，已切换到复盘视图' })
          await reviewHistory.refresh()
          setSubTab('review')
          onChange?.()
        } else {
          await handleSoftReject(res?.message ?? '复盘失败')
        }
      } catch (e: any) {
        await handleSoftReject(e?.response?.data?.message ?? '复盘失败')
      } finally {
        setReviewing(false)
      }
    },
    [
      originalHistory.current,
      reviewHistory,
      tsCode,
      stockName,
      stockCode,
      expert.key,
      onChange,
    ],
  )

  const contextLabel = `${expert.label}${isReviewSub ? '复盘' : '观点'}`

  return (
    <div className="space-y-4">
      <SubTabBar
        expert={expert}
        subTab={subTab}
        onSubTabChange={setSubTab}
        originalCount={originalHistory.records.length}
        originalTotalDb={originalHistory.total}
        reviewCount={reviewHistory.records.length}
        reviewTotalDb={reviewHistory.total}
        active={active}
        canReview={!isReviewSub && !!originalHistory.current}
        reviewing={reviewing}
        onReview={() => handleReview(false)}
        onEdit={() => setShowEdit(true)}
        onDelete={() => setShowDelete(true)}
        onView={() => setShowSource(true)}
        reviewLabel={`让${REVIEW_SUBJECT_LABEL[expert.key]}专家复盘此报告`}
      />

      {actionMsg && (
        <p
          className={`text-xs ${
            actionMsg.type === 'success'
              ? 'text-emerald-600'
              : actionMsg.type === 'error'
              ? 'text-negative'
              : 'text-muted-foreground'
          }`}
        >
          {actionMsg.text}
        </p>
      )}

      {/* Body */}
      {active.loading && active.records.length === 0 ? (
        <div className="rounded-md border border-dashed border-gray-200 dark:border-gray-700 py-10 text-center text-sm text-muted-foreground">
          加载中…
        </div>
      ) : active.current ? (
        <ExpertRecordBody expert={expert} record={active.current} isReview={isReviewSub} />
      ) : (
        <EmptyExpertState
          expert={expert}
          isReview={isReviewSub}
          onJumpOriginal={() => setSubTab('original')}
        />
      )}

      <DeleteConfirmDialog
        open={showDelete}
        record={active.current}
        onClose={() => setShowDelete(false)}
        contextLabel={contextLabel}
        onConfirm={async () => {
          if (!active.current) return { ok: false, message: '无可删除记录' }
          const r = await active.remove(active.current.id)
          if (r.ok) onChange?.()
          return r
        }}
      />
      <EditAnalysisDialog
        open={showEdit}
        record={active.current}
        onClose={() => setShowEdit(false)}
        contextLabel={contextLabel}
        onSave={async (params) => {
          if (!active.current) return { ok: false, message: '无可编辑记录' }
          const r = await active.update(active.current.id, params)
          if (r.ok) onChange?.()
          return r
        }}
      />
      <ViewSourceDialog
        open={showSource}
        record={active.current}
        onClose={() => setShowSource(false)}
        contextLabel={contextLabel}
      />
    </div>
  )
}

interface SubTabBarProps {
  expert: ExpertMeta & { key: TabExpertKey }
  subTab: 'original' | 'review'
  onSubTabChange: (s: 'original' | 'review') => void
  originalCount: number
  originalTotalDb: number
  reviewCount: number
  reviewTotalDb: number
  active: ReturnType<typeof useAnalysisHistory>
  canReview: boolean
  reviewing: boolean
  onReview: () => void
  onEdit: () => void
  onDelete: () => void
  onView: () => void
  reviewLabel: string
}

function SubTabBar({
  expert,
  subTab,
  onSubTabChange,
  originalCount,
  originalTotalDb,
  reviewCount,
  reviewTotalDb,
  active,
  canReview,
  reviewing,
  onReview,
  onEdit,
  onDelete,
  onView,
  reviewLabel,
}: SubTabBarProps) {
  const expertColor = `hsl(var(${expert.colorVar}))`
  return (
    // Both flex layers wrap so pager and toolbar can drop below the segmented
    // control (or each other) on narrow viewports.
    <div className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1.5 -mt-1">
      <div className="inline-flex items-center rounded-md border border-border bg-background p-0.5">
        <SubTabBtn
          active={subTab === 'original'}
          onClick={() => onSubTabChange('original')}
          activeColor={expertColor}
          label="原报告"
          count={originalCount}
          totalDb={originalTotalDb}
        />
        <SubTabBtn
          active={subTab === 'review'}
          onClick={() => onSubTabChange('review')}
          activeColor={expertColor}
          label="复盘"
          count={reviewCount}
          totalDb={reviewTotalDb}
        />
      </div>

      <div className="flex flex-wrap items-center gap-x-2 gap-y-1.5">
        <TradeDateVersionPager
          groups={active.groups}
          selectedTradeDate={active.selectedTradeDate}
          onSelectTradeDate={active.setSelectedTradeDate}
          versions={active.versions}
          versionIndex={active.versionIndex}
          onPrevVersion={active.goOlderVersion}
          onNextVersion={active.goNewerVersion}
          loading={active.loading}
        />
        {active.current && (
          <RecordActionToolbar
            onView={onView}
            onEdit={onEdit}
            onDelete={onDelete}
            onReview={canReview ? onReview : undefined}
            reviewing={reviewing}
            reviewLabel={reviewLabel}
          />
        )}
      </div>
    </div>
  )
}

function SubTabBtn({
  active,
  onClick,
  activeColor,
  label,
  count,
  totalDb,
}: {
  active: boolean
  onClick: () => void
  activeColor: string
  label: string
  count: number
  totalDb: number
}) {
  // Active state tints with the expert identity color so each expert "owns"
  // their tab — broker-platform convention.
  const style = active
    ? {
        background: `${activeColor.replace('hsl(', 'hsla(').replace(')', ' / 0.10)')}`,
        color: activeColor,
      }
    : undefined
  const dbExtra = totalDb > count ? totalDb - count : 0
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded px-2.5 py-1 text-xs font-medium transition-colors duration-fast focus-ring ${
        active ? '' : 'text-muted-foreground hover:text-foreground hover:bg-surface-hover'
      }`}
      style={style}
      aria-pressed={active}
    >
      <span>{label}</span>
      <span className="font-mono tabular-nums opacity-80">
        {count}
        {dbExtra > 0 && <span className="opacity-60">+{dbExtra}</span>}
      </span>
    </button>
  )
}

function ExpertRecordBody({
  expert,
  record,
  isReview,
}: {
  expert: ExpertMeta
  record: StockAnalysisRecord
  isReview: boolean
}) {
  const parsed = safeParseJSON(record.analysis_text)
  const score = extractScore(parsed) ?? record.score
  const rating = extractRating(parsed)
  const keyQuote = extractKeyQuote(parsed)
  const fs = parsed?.final_score
  const bull = Array.isArray(fs?.bull_factors)
    ? fs.bull_factors
    : Array.isArray(fs?.pros)
    ? fs.pros
    : []
  const bear = Array.isArray(fs?.bear_factors)
    ? fs.bear_factors
    : Array.isArray(fs?.cons)
    ? fs.cons
    : []

  const analysisType = isReview
    ? REVIEW_ANALYSIS_TYPE[expert.key as TabExpertKey]
    : expert.analysisType

  return (
    <div className="space-y-4">
      <header className="flex items-start justify-between gap-3 pb-3 border-b border-gray-100 dark:border-gray-800">
        <div className="flex items-baseline gap-3 flex-wrap">
          {score != null && (
            <span className={`text-3xl font-bold tabular-nums leading-none ${scoreToneClass(score)}`}>
              {Number.isInteger(score) ? Number(score).toFixed(1) : score}
            </span>
          )}
          {rating && (
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{rating}</span>
          )}
          {isReview && (
            <span className="rounded border border-warning/40 bg-warning-soft/50 px-1.5 py-0.5 text-[10px] font-medium text-warning">
              复盘
            </span>
          )}
        </div>
      </header>

      {keyQuote && (
        <p
          className="px-3 py-2 rounded-md text-sm font-medium leading-relaxed"
          style={{
            background: `hsl(var(${expert.colorVar}) / 0.10)`,
            color: `hsl(var(${expert.colorVar}))`,
          }}
        >
          {renderBold(keyQuote)}
        </p>
      )}

      {(bull.length > 0 || bear.length > 0) && (
        <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {bull.length > 0 && (
            <div>
              <div className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 mb-1">
                ▲ 正向因子
              </div>
              <ProsConsList items={bull} variant="pros" />
            </div>
          )}
          {bear.length > 0 && (
            <div>
              <div className="text-sm font-semibold text-red-600 dark:text-red-400 mb-1">
                ▼ 负向因子
              </div>
              <ProsConsList items={bear} variant="cons" />
            </div>
          )}
        </section>
      )}

      {parsed ? (
        <StructuredAnalysisContent
          d={parsed}
          analysisType={analysisType}
          hideFinalScore
          hideTitleHeader
        />
      ) : (
        <MarkdownContent text={record.analysis_text} />
      )}
    </div>
  )
}

function EmptyExpertState({
  expert,
  isReview,
  onJumpOriginal,
}: {
  expert: ExpertMeta
  isReview: boolean
  onJumpOriginal: () => void
}) {
  if (isReview) {
    return (
      <div className="rounded-md border border-dashed border-gray-200 dark:border-gray-700 py-8 text-center text-sm text-muted-foreground space-y-2">
        <div>
          {expert.label}专家暂无复盘记录。
        </div>
        <div className="text-xs">
          切到{' '}
          <button
            type="button"
            onClick={onJumpOriginal}
            className="text-primary underline-offset-2 hover:underline"
          >
            原报告
          </button>{' '}
          后点击工具栏的{' '}
          <RotateCcw className="inline-block h-3.5 w-3.5 align-text-bottom" aria-hidden />{' '}
          按钮触发复盘
          {expert.key === 'midline' && '（建议原报告 ≥20 天）'}
          {expert.key === 'longterm' && '（建议原报告 ≥90 天）'}
          。
        </div>
      </div>
    )
  }
  return (
    <div className="text-center py-10 text-sm text-gray-500 dark:text-gray-400 border border-dashed border-gray-200 dark:border-gray-700 rounded-md">
      尚未生成 {expert.label}专家分析，点击右上"重新分析"
    </div>
  )
}
