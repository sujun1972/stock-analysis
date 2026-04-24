'use client'

import React from 'react'
import { Loader2 } from 'lucide-react'
import { Checkbox } from '@/components/ui/checkbox'
import { ScoreBadge } from '@/components/shared'
import type { StockInfo, CioFollowupTriggers } from '@/types'

function toTsCode(code: string): string {
  if (code.includes('.')) return code.toUpperCase()
  if (code.startsWith('6')) return `${code}.SH`
  if (code.startsWith('4') || code.startsWith('8')) return `${code}.BJ`
  return `${code}.SZ`
}

// AI 评分单元格：委托共享 ScoreBadge，色阶 + 数值 + tooltip 分档说明（色盲辅助）
const SCORE_ARIA_LABELS = ['游资评分', '中线评分', '价值评分', 'CIO 评分'] as const

function FollowupPriceCell({ triggers }: { triggers: CioFollowupTriggers | null }) {
  if (!triggers) {
    return <span className="text-gray-300 dark:text-gray-600">—</span>
  }
  const breakUp = triggers.price_triggers?.find(t => t.direction === 'break_up' && t.price != null)
  const breakDown = triggers.price_triggers?.find(t => t.direction === 'break_down' && t.price != null)
  if (!breakUp && !breakDown) {
    return <span className="text-gray-300 dark:text-gray-600">—</span>
  }
  return (
    <div className="flex flex-col gap-0.5 min-w-[80px]">
      {breakUp && (
        <span className="text-positive whitespace-nowrap tabular-nums" title={breakUp.price_basis ?? ''}>
          ▲ {breakUp.price?.toFixed(2)}
        </span>
      )}
      {breakDown && (
        <span className="text-negative whitespace-nowrap tabular-nums" title={breakDown.price_basis ?? ''}>
          ▼ {breakDown.price?.toFixed(2)}
        </span>
      )}
    </div>
  )
}

// 价值度量单元格：百分比 / 数值渲染，数据不足显示 —
// A 股配色：正数红、负数绿、0 黑
function PercentCell({ value, decimals = 1 }: { value?: number | null; decimals?: number }) {
  if (value == null || !isFinite(value)) {
    return <span className="text-gray-300 dark:text-gray-600">—</span>
  }
  const pct = value * 100
  const tone =
    pct > 0 ? 'text-positive'
    : pct < 0 ? 'text-negative'
    : 'text-gray-900 dark:text-white'
  return <span className={`text-sm font-medium tabular-nums ${tone}`}>{pct.toFixed(decimals)}%</span>
}

function IntrinsicCell({ iv, margin, gRate, gSource }: {
  iv?: number | null
  margin?: number | null
  gRate?: number | null
  gSource?: 'analyst' | 'history' | 'na' | null
}) {
  if (iv == null || margin == null) {
    return <span className="text-gray-300 dark:text-gray-600">—</span>
  }
  const marginPct = margin * 100
  const tone =
    marginPct > 0 ? 'text-positive'
    : marginPct < 0 ? 'text-negative'
    : 'text-gray-900 dark:text-white'
  const gLabel = gSource === 'analyst' ? '研报' : gSource === 'history' ? '历史' : ''
  const tip = `内在价值 ${iv.toFixed(2)} 元（g=${((gRate ?? 0) * 100).toFixed(1)}% · ${gLabel}）`
  return (
    <span className={`text-sm font-medium tabular-nums ${tone}`} title={tip}>
      {marginPct > 0 ? '+' : ''}{marginPct.toFixed(0)}%
    </span>
  )
}

function FollowupTimeCell({ triggers }: { triggers: CioFollowupTriggers | null }) {
  if (!triggers) {
    return <span className="text-gray-300 dark:text-gray-600">—</span>
  }
  const nearestTime = (triggers.time_triggers ?? [])
    .filter(t => !!t.expected_date)
    .sort((a, b) => String(a.expected_date).localeCompare(String(b.expected_date)))[0]
  if (!nearestTime) {
    return <span className="text-gray-300 dark:text-gray-600">—</span>
  }
  return (
    <span className="text-gray-600 dark:text-gray-400 whitespace-nowrap tabular-nums" title={nearestTime.reason ?? ''}>
      ⏱ {String(nearestTime.expected_date)}
    </span>
  )
}

interface StockTableRowProps {
  stock: StockInfo
  isAuthenticated: boolean
  isSelected: boolean
  isAnalyzing?: boolean
  onToggleSelect: (tsCode: string) => void
  onOpenAnalysis: (stock: StockInfo) => void
}

export const StockTableRow = React.memo(function StockTableRow({
  stock,
  isAuthenticated,
  isSelected,
  isAnalyzing = false,
  onToggleSelect,
  onOpenAnalysis,
}: StockTableRowProps) {
  const tsCode = toTsCode(stock.code)

  return (
    <tr
      className={`transition-colors ${isSelected ? 'bg-blue-50 dark:bg-blue-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-800/50'}`}
      onClick={isAuthenticated ? () => onToggleSelect(tsCode) : undefined}
      style={isAuthenticated ? { cursor: 'pointer' } : undefined}
    >
      {isAuthenticated && (
        <td className="px-4 py-4 w-10" onClick={(e) => e.stopPropagation()}>
          <Checkbox
            checked={isSelected}
            onCheckedChange={() => onToggleSelect(tsCode)}
            aria-label={`选中 ${stock.name}（${stock.code}）`}
          />
        </td>
      )}
      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium" onClick={(e) => e.stopPropagation()}>
        <a
          href={`/analysis?code=${stock.code}`}
          className={`hover:underline ${
            stock.pct_change != null
              ? stock.pct_change > 0 ? 'text-positive'
              : stock.pct_change < 0 ? 'text-negative'
              : 'text-gray-900 dark:text-white'
              : 'text-gray-900 dark:text-white'
          }`}
        >
          {stock.name}({stock.code})
        </a>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium tabular-nums">
        {stock.latest_price ? (
          <span className={
            stock.pct_change != null
              ? stock.pct_change > 0 ? 'text-positive'
              : stock.pct_change < 0 ? 'text-negative'
              : 'text-gray-900 dark:text-white'
              : 'text-gray-900 dark:text-white'
          }>
            {stock.latest_price.toFixed(2)}
          </span>
        ) : '-'}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium tabular-nums">
        {stock.pct_change != null ? (
          <span className={stock.pct_change > 0 ? 'text-positive' : stock.pct_change < 0 ? 'text-negative' : 'text-gray-900 dark:text-white'}>
            {stock.pct_change > 0 ? '+' : ''}{stock.pct_change.toFixed(2)}%
          </span>
        ) : '-'}
      </td>
      {[
        stock.latest_analysis_hot_money,
        stock.latest_analysis_midline,
        stock.latest_analysis_longterm,
        stock.latest_analysis_cio,
      ].map((analysis, idx) => (
        <td key={idx} className="px-4 py-4 whitespace-nowrap text-right" onClick={(e) => e.stopPropagation()}>
          <ScoreBadge score={analysis?.score} ariaPrefix={SCORE_ARIA_LABELS[idx]} />
        </td>
      ))}
      <td className="px-4 py-4 whitespace-nowrap text-right text-xs text-gray-600 dark:text-gray-400 tabular-nums" onClick={(e) => e.stopPropagation()}>
        {stock.latest_analysis_cio?.created_at ? (
          stock.latest_analysis_cio.created_at.slice(0, 10)
        ) : (
          <span className="text-gray-300 dark:text-gray-600">—</span>
        )}
      </td>
      {/* 价值度量三列：ROC / EY / 内在价值安全边际（《股市稳赚》+《聪明的投资者》）*/}
      <td className="px-4 py-4 whitespace-nowrap text-right" onClick={(e) => e.stopPropagation()}>
        <PercentCell value={stock.value_metrics?.roc} />
      </td>
      <td className="px-4 py-4 whitespace-nowrap text-right" onClick={(e) => e.stopPropagation()}>
        <PercentCell value={stock.value_metrics?.earnings_yield} />
      </td>
      <td className="px-4 py-4 whitespace-nowrap text-right" onClick={(e) => e.stopPropagation()}>
        <IntrinsicCell
          iv={stock.value_metrics?.intrinsic_value}
          margin={stock.value_metrics?.intrinsic_margin}
          gRate={stock.value_metrics?.g_rate}
          gSource={stock.value_metrics?.g_source}
        />
      </td>
      <td className="px-4 py-4 text-xs" onClick={(e) => e.stopPropagation()}>
        <FollowupPriceCell triggers={stock.latest_analysis_cio?.followup_triggers ?? null} />
      </td>
      <td className="px-4 py-4 text-xs" onClick={(e) => e.stopPropagation()}>
        <FollowupTimeCell triggers={stock.latest_analysis_cio?.followup_triggers ?? null} />
      </td>
      <td className="px-4 py-4 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
        {isAnalyzing ? (
          <span
            className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded border border-blue-400 text-blue-600 bg-blue-50 dark:border-blue-500 dark:text-blue-400 dark:bg-blue-900/20 whitespace-nowrap"
            title="正在批量 AI 分析中"
          >
            <Loader2 className="h-3 w-3 animate-spin" />分析中
          </span>
        ) : (
          <button
            type="button"
            onClick={() => onOpenAnalysis(stock)}
            aria-label={`打开 ${stock.name} 的 AI 分析`}
            className="text-xs px-2 py-1 rounded border border-yellow-400 text-yellow-600 hover:bg-yellow-50 dark:border-yellow-500 dark:text-yellow-400 dark:hover:bg-yellow-900/20 transition-colors whitespace-nowrap focus-ring"
          >
            AI 分析
          </button>
        )}
      </td>
    </tr>
  )
})
