'use client'

import React from 'react'
import { Loader2 } from 'lucide-react'
import { Checkbox } from '@/components/ui/checkbox'
import type { StockInfo } from '@/types'

function toTsCode(code: string): string {
  if (code.includes('.')) return code.toUpperCase()
  if (code.startsWith('6')) return `${code}.SH`
  if (code.startsWith('4') || code.startsWith('8')) return `${code}.BJ`
  return `${code}.SZ`
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
