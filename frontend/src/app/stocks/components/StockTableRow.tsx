'use client'

import React from 'react'
import { Loader2 } from 'lucide-react'
import { Checkbox } from '@/components/ui/checkbox'
import type { StockInfo, CioFollowupTriggers } from '@/types'

function toTsCode(code: string): string {
  if (code.includes('.')) return code.toUpperCase()
  if (code.startsWith('6')) return `${code}.SH`
  if (code.startsWith('4') || code.startsWith('8')) return `${code}.BJ`
  return `${code}.SZ`
}

/**
 * 股票列表"下次关注"列：紧凑展示 CIO 复查触发器摘要
 *   - 上方触发价（break_up）与下方触发价（break_down），带箭头
 *   - 最近一个时间触发器（事件+日期）
 * 完整明细在 CIO Tab 弹窗展示，这里只给决策一瞥。
 */
function FollowupTriggersCell({ triggers }: { triggers: CioFollowupTriggers | null }) {
  if (!triggers) {
    return <span className="text-gray-300 dark:text-gray-600">—</span>
  }

  const breakUp = triggers.price_triggers?.find(t => t.direction === 'break_up' && t.price != null)
  const breakDown = triggers.price_triggers?.find(t => t.direction === 'break_down' && t.price != null)
  const nearestTime = (triggers.time_triggers ?? [])
    .filter(t => !!t.expected_date)
    .sort((a, b) => String(a.expected_date).localeCompare(String(b.expected_date)))[0]

  const hasAny = breakUp || breakDown || nearestTime
  if (!hasAny) {
    return <span className="text-gray-300 dark:text-gray-600">—</span>
  }

  return (
    <div className="flex flex-col gap-0.5 min-w-[110px]">
      {breakUp && (
        <span className="text-red-600 dark:text-red-400 whitespace-nowrap" title={breakUp.price_basis ?? ''}>
          ▲ {breakUp.price?.toFixed(2)}
        </span>
      )}
      {breakDown && (
        <span className="text-green-600 dark:text-green-400 whitespace-nowrap" title={breakDown.price_basis ?? ''}>
          ▼ {breakDown.price?.toFixed(2)}
        </span>
      )}
      {nearestTime && (
        <span className="text-gray-500 dark:text-gray-400 whitespace-nowrap" title={nearestTime.reason ?? ''}>
          ⏱ {String(nearestTime.expected_date).slice(5)}
        </span>
      )}
    </div>
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
            aria-label={`选择 ${stock.name}`}
          />
        </td>
      )}
      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium" onClick={(e) => e.stopPropagation()}>
        <a
          href={`/analysis?code=${stock.code}`}
          className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
        >
          {stock.name}({stock.code})
        </a>
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">
        {stock.latest_price ? (
          <span className={
            stock.pct_change != null
              ? stock.pct_change > 0 ? 'text-red-600 dark:text-red-400'
              : stock.pct_change < 0 ? 'text-green-600 dark:text-green-400'
              : 'text-gray-900 dark:text-white'
              : 'text-gray-900 dark:text-white'
          }>
            {stock.latest_price.toFixed(2)}
          </span>
        ) : '-'}
      </td>
      <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">
        {stock.pct_change != null ? (
          <span className={stock.pct_change > 0 ? 'text-red-600 dark:text-red-400' : stock.pct_change < 0 ? 'text-green-600 dark:text-green-400' : 'text-gray-600 dark:text-gray-400'}>
            {stock.pct_change > 0 ? '+' : ''}{stock.pct_change.toFixed(2)}%
          </span>
        ) : '-'}
      </td>
      {[
        stock.latest_analysis_hot_money,
        stock.latest_analysis_midline,
        stock.latest_analysis_longterm,
      ].map((analysis, idx) => (
        <td key={idx} className="px-4 py-4 whitespace-nowrap text-right" onClick={(e) => e.stopPropagation()}>
          {analysis?.score != null ? (
            <span className={`text-sm font-semibold ${
              analysis.score >= 8 ? 'text-red-600 dark:text-red-400'
              : analysis.score >= 6 ? 'text-yellow-600 dark:text-yellow-400'
              : 'text-gray-500 dark:text-gray-400'
            }`}>
              {analysis.score}
            </span>
          ) : (
            <span className="text-xs text-gray-300 dark:text-gray-600">—</span>
          )}
        </td>
      ))}
      <td className="px-4 py-4 whitespace-nowrap text-right text-xs text-gray-600 dark:text-gray-400" onClick={(e) => e.stopPropagation()}>
        {stock.latest_analysis_cio?.created_at ? (
          stock.latest_analysis_cio.created_at.slice(0, 10)
        ) : (
          <span className="text-gray-300 dark:text-gray-600">—</span>
        )}
      </td>
      <td className="px-4 py-4 text-xs" onClick={(e) => e.stopPropagation()}>
        <FollowupTriggersCell triggers={stock.latest_analysis_cio?.followup_triggers ?? null} />
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
            onClick={() => onOpenAnalysis(stock)}
            className="text-xs px-2 py-1 rounded border border-yellow-400 text-yellow-600 hover:bg-yellow-50 dark:border-yellow-500 dark:text-yellow-400 dark:hover:bg-yellow-900/20 transition-colors whitespace-nowrap"
          >
            AI 分析
          </button>
        )}
      </td>
    </tr>
  )
})
