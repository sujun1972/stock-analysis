'use client'

import React from 'react'
import { Loader2 } from 'lucide-react'
import { Checkbox } from '@/components/ui/checkbox'
import { ScoreBadge } from '@/components/shared'
import type { StockInfo, CioFollowupTriggers } from '@/types'
import { fmtAmount, fmtMarketCap, fmtPE } from './format-utils'

// 与 StockTableRow / page.tsx 保持同一套代码→ts_code 规则（见 frontend/CLAUDE.md 股票代码规范）
function toTsCode(code: string): string {
  if (code.includes('.')) return code.toUpperCase()
  if (code.startsWith('6')) return `${code}.SH`
  if (code.startsWith('4') || code.startsWith('8')) return `${code}.BJ`
  return `${code}.SZ`
}

/** 价值度量小百分比（ROC / EY 共用）— A股配色：正红/负绿/零黑/缺数据灰 */
function PctMetric({ label, value }: { label: string; value: number | null | undefined }) {
  if (value == null || !isFinite(value)) {
    return <span className="text-gray-400">{label} —</span>
  }
  const pct = value * 100
  const cls =
    pct > 0 ? 'text-positive'
    : pct < 0 ? 'text-negative'
    : 'text-gray-600 dark:text-gray-400'
  return <span className={cls}>{label} {pct.toFixed(1)}%</span>
}

function cioFollowupSummary(triggers: CioFollowupTriggers | null): string | null {
  if (!triggers) return null
  const breakUp = triggers.price_triggers?.find(t => t.direction === 'break_up' && t.price != null)
  const breakDown = triggers.price_triggers?.find(t => t.direction === 'break_down' && t.price != null)
  const parts: string[] = []
  if (breakUp?.price != null) parts.push(`▲${breakUp.price.toFixed(2)}`)
  if (breakDown?.price != null) parts.push(`▼${breakDown.price.toFixed(2)}`)
  const nearestTime = (triggers.time_triggers ?? [])
    .filter(t => !!t.expected_date)
    .sort((a, b) => String(a.expected_date).localeCompare(String(b.expected_date)))[0]
  if (nearestTime) parts.push(`⏱${String(nearestTime.expected_date)}`)
  return parts.length ? parts.join(' · ') : null
}

interface StockCardProps {
  stock: StockInfo
  selectable: boolean
  isSelected: boolean
  // 该股票是否正在 AI 分析中（来自 /stocks 页面的 3s 轮询）
  isAnalyzing?: boolean
  onToggleSelect: (tsCode: string) => void
}

export const StockCard = React.memo(function StockCard({
  stock,
  selectable,
  isSelected,
  isAnalyzing = false,
  onToggleSelect,
}: StockCardProps) {
  const tsCode = toTsCode(stock.code)
  const pct = stock.pct_change
  // A 股配色：涨红 / 跌绿 / 平黑；数据缺失退灰
  const pctTone =
    pct == null ? 'text-gray-500 dark:text-gray-400'
    : pct > 0 ? 'text-positive'
    : pct < 0 ? 'text-negative'
    : 'text-gray-900 dark:text-white'
  const nameTone =
    pct == null ? 'text-gray-900 dark:text-white'
    : pct > 0 ? 'text-positive'
    : pct < 0 ? 'text-negative'
    : 'text-gray-900 dark:text-white'
  const cioDate = stock.latest_analysis_cio?.created_at?.slice(0, 10)
  const followup = cioFollowupSummary(stock.latest_analysis_cio?.followup_triggers ?? null)

  return (
    <div
      className={`rounded-lg border bg-card transition-colors duration-fast p-3 ${
        isSelected
          ? 'border-primary bg-primary/[0.08] ring-1 ring-primary/30'
          : 'border-border'
      }`}
      onClick={selectable ? () => onToggleSelect(tsCode) : undefined}
      style={selectable ? { cursor: 'pointer' } : undefined}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2 min-w-0 flex-1">
          {selectable && (
            <div className="pt-0.5" onClick={(e) => e.stopPropagation()}>
              <Checkbox
                checked={isSelected}
                onCheckedChange={() => onToggleSelect(tsCode)}
                aria-label={`选中 ${stock.name}（${stock.code}）`}
              />
            </div>
          )}
          <div className="min-w-0 flex-1" onClick={(e) => e.stopPropagation()}>
            {/* min-w-0：让内层 <span class="truncate"> 在 flex 父项中真正生效（默认 min-width:auto 会拒绝收缩） */}
            <a
              href={`/analysis?code=${stock.code}`}
              className={`flex items-center gap-1.5 min-w-0 text-sm font-semibold hover:underline ${nameTone}`}
            >
              {isAnalyzing && (
                <span title="AI 分析中" className="inline-flex shrink-0">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-info" aria-label="AI 分析中" />
                </span>
              )}
              <span className="truncate">{stock.name}</span>
            </a>
            <div className={`text-xs mt-0.5 ${nameTone}`}>{stock.code}</div>
          </div>
        </div>

        <div className="flex flex-col items-end flex-shrink-0">
          <span className={`text-base font-semibold tabular-nums ${nameTone}`}>
            {stock.latest_price != null ? stock.latest_price.toFixed(2) : '-'}
          </span>
          <span className={`text-xs font-medium tabular-nums ${pctTone}`}>
            {pct == null ? '-' : `${pct > 0 ? '+' : ''}${pct.toFixed(2)}%`}
          </span>
        </div>
      </div>

      {/* 量价 + 估值行：辅助信息统一中灰，与桌面表格同步 */}
      <div className="mt-2.5 flex items-center justify-between gap-1 text-[11px] text-muted-foreground tabular-nums">
        <span>{fmtAmount(stock.amount)}</span>
        <span className="text-muted-foreground/40" aria-hidden>·</span>
        <span>换 {stock.turnover_rate != null ? `${stock.turnover_rate.toFixed(2)}%` : '—'}</span>
        <span className="text-muted-foreground/40" aria-hidden>·</span>
        <span>{fmtMarketCap(stock.total_mv)}</span>
        <span className="text-muted-foreground/40" aria-hidden>·</span>
        {(() => {
          const { text, tone } = fmtPE(stock.pe_ttm)
          return <span className={tone === 'warn' ? 'text-warning' : ''}>PE {text}</span>
        })()}
      </div>

      {/* 价值度量行：ROC / EY / 安全边际 — 价值投资视角，与桌面价值列同语义 */}
      {(stock.value_metrics?.roc != null || stock.value_metrics?.earnings_yield != null || stock.value_metrics?.intrinsic_margin != null) && (
        <div className="mt-1 flex items-center justify-between gap-1 text-[11px] tabular-nums">
          <PctMetric label="ROC" value={stock.value_metrics?.roc} />
          <span className="text-muted-foreground/40" aria-hidden>·</span>
          <PctMetric label="EY" value={stock.value_metrics?.earnings_yield} />
          <span className="text-muted-foreground/40" aria-hidden>·</span>
          {(() => {
            // 安全边际单独：需要"+"前缀和整数小数位（与 PctMetric 默认 1 位不同）
            const m = stock.value_metrics?.intrinsic_margin
            if (m == null || !isFinite(m)) return <span className="text-gray-400">边际 —</span>
            const pct = m * 100
            const cls = pct > 0 ? 'text-positive' : pct < 0 ? 'text-negative' : 'text-gray-600 dark:text-gray-400'
            return <span className={cls}>边际 {pct > 0 ? '+' : ''}{pct.toFixed(0)}%</span>
          })()}
        </div>
      )}

      <div className="mt-2.5 grid grid-cols-4 gap-1.5" onClick={(e) => e.stopPropagation()}>
        <ScoreBadge variant="card" label="游资" score={stock.latest_analysis_hot_money?.score} />
        <ScoreBadge variant="card" label="中线" score={stock.latest_analysis_midline?.score} />
        <ScoreBadge variant="card" label="价值" score={stock.latest_analysis_longterm?.score} />
        <ScoreBadge variant="card" label="CIO" score={stock.latest_analysis_cio?.score} />
      </div>

      {(cioDate || followup) && (
        <div className="mt-2 flex items-center justify-between gap-2 text-[11px] text-gray-500 dark:text-gray-400">
          {cioDate && <span className="tabular-nums">CIO {cioDate}</span>}
          {followup && <span className="truncate tabular-nums text-right">{followup}</span>}
        </div>
      )}
    </div>
  )
})
