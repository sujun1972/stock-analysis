'use client'

import React from 'react'
import { Loader2, Sparkles, MoreVertical } from 'lucide-react'
import { Checkbox } from '@/components/ui/checkbox'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import type { StockInfo, CioFollowupTriggers } from '@/types'

// 与 StockTableRow / page.tsx 保持同一套代码→ts_code 规则（见 frontend/CLAUDE.md 股票代码规范）
function toTsCode(code: string): string {
  if (code.includes('.')) return code.toUpperCase()
  if (code.startsWith('6')) return `${code}.SH`
  if (code.startsWith('4') || code.startsWith('8')) return `${code}.BJ`
  return `${code}.SZ`
}

// 卡片评分 Badge：带标签的矩形色块（移动端），与桌面端 ScoreCell 的纯色数字风格分离
function ScoreBadge({ label, score }: { label: string; score?: number | null }) {
  const tone =
    score == null ? 'bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-600'
    : score >= 8 ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
    : score >= 6 ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
    : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
  return (
    <div className={`flex flex-col items-center justify-center px-2 py-1 rounded ${tone} min-w-[44px]`}>
      <span className="text-[10px] leading-none opacity-80">{label}</span>
      <span className="text-sm font-semibold leading-tight mt-0.5">
        {score == null ? '—' : score}
      </span>
    </div>
  )
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
  isAuthenticated: boolean
  isSelected: boolean
  isAnalyzing?: boolean
  onToggleSelect: (tsCode: string) => void
  onOpenAnalysis: (stock: StockInfo) => void
}

export const StockCard = React.memo(function StockCard({
  stock,
  isAuthenticated,
  isSelected,
  isAnalyzing = false,
  onToggleSelect,
  onOpenAnalysis,
}: StockCardProps) {
  const tsCode = toTsCode(stock.code)
  const pct = stock.pct_change
  const pctTone =
    pct == null ? 'text-gray-500 dark:text-gray-400'
    : pct > 0 ? 'text-red-600 dark:text-red-400'
    : pct < 0 ? 'text-green-600 dark:text-green-400'
    : 'text-gray-500 dark:text-gray-400'
  const cioDate = stock.latest_analysis_cio?.created_at?.slice(0, 10)
  const followup = cioFollowupSummary(stock.latest_analysis_cio?.followup_triggers ?? null)

  return (
    <div
      className={`rounded-lg border bg-white dark:bg-gray-900 transition-colors p-3 ${
        isSelected
          ? 'border-blue-500 bg-blue-50/60 dark:border-blue-500 dark:bg-blue-900/20 ring-1 ring-blue-500/30'
          : 'border-gray-200 dark:border-gray-700'
      }`}
      onClick={isAuthenticated ? () => onToggleSelect(tsCode) : undefined}
      style={isAuthenticated ? { cursor: 'pointer' } : undefined}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2 min-w-0 flex-1">
          {isAuthenticated && (
            <div className="pt-0.5" onClick={(e) => e.stopPropagation()}>
              <Checkbox
                checked={isSelected}
                onCheckedChange={() => onToggleSelect(tsCode)}
                aria-label={`选择 ${stock.name}`}
              />
            </div>
          )}
          <div className="min-w-0 flex-1" onClick={(e) => e.stopPropagation()}>
            <a
              href={`/analysis?code=${stock.code}`}
              className="block text-sm font-semibold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 truncate"
            >
              {stock.name}
            </a>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{stock.code}</div>
          </div>
        </div>

        <div className="flex flex-col items-end flex-shrink-0">
          <span className="text-base font-semibold text-gray-900 dark:text-white tabular-nums">
            {stock.latest_price != null ? stock.latest_price.toFixed(2) : '-'}
          </span>
          <span className={`text-xs font-medium tabular-nums ${pctTone}`}>
            {pct == null ? '-' : `${pct > 0 ? '+' : ''}${pct.toFixed(2)}%`}
          </span>
        </div>

        <div className="flex-shrink-0" onClick={(e) => e.stopPropagation()}>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <button
                className="p-1.5 -mr-1 -mt-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 dark:text-gray-400"
                aria-label="股票操作菜单"
              >
                <MoreVertical className="h-4 w-4" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onClick={() => onOpenAnalysis(stock)}
                disabled={isAnalyzing}
              >
                {isAnalyzing ? (
                  <><Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />分析中</>
                ) : (
                  <><Sparkles className="h-3.5 w-3.5 mr-2" />AI 分析</>
                )}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-4 gap-1.5" onClick={(e) => e.stopPropagation()}>
        <ScoreBadge label="游资" score={stock.latest_analysis_hot_money?.score} />
        <ScoreBadge label="中线" score={stock.latest_analysis_midline?.score} />
        <ScoreBadge label="价值" score={stock.latest_analysis_longterm?.score} />
        <ScoreBadge label="CIO" score={stock.latest_analysis_cio?.score} />
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
