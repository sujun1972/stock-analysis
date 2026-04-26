'use client'

import React from 'react'
import { Checkbox } from '@/components/ui/checkbox'
import { ScoreBadge } from '@/components/shared'
import type { StockInfo, CioFollowupTriggers } from '@/types'
import type { StockColumnId } from '../hooks/useStockTableColumns'
import { fmtAmount, fmtMarketCap, fmtPE } from './format-utils'

function toTsCode(code: string): string {
  if (code.includes('.')) return code.toUpperCase()
  if (code.startsWith('6')) return `${code}.SH`
  if (code.startsWith('4') || code.startsWith('8')) return `${code}.BJ`
  return `${code}.SZ`
}

// 4 个 AI 评分列的显示参数：列 id（控制可见性） + 读取 StockInfo 的哪个 analysis 字段 + ARIA 标签
// 放在模块级避免每次渲染重建数组
const SCORE_COLUMNS: ReadonlyArray<{
  id: StockColumnId
  field: 'latest_analysis_hot_money' | 'latest_analysis_midline' | 'latest_analysis_longterm' | 'latest_analysis_cio'
  aria: string
}> = [
  { id: 'score_hot_money', field: 'latest_analysis_hot_money', aria: '游资评分' },
  { id: 'score_midline',   field: 'latest_analysis_midline',   aria: '中线评分' },
  { id: 'score_longterm',  field: 'latest_analysis_longterm',  aria: '价值评分' },
  { id: 'score_cio',       field: 'latest_analysis_cio',       aria: 'CIO 评分' },
]

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
  isVisible: (id: StockColumnId) => boolean
  onToggleSelect: (tsCode: string) => void
}

export const StockTableRow = React.memo(function StockTableRow({
  stock,
  isAuthenticated,
  isSelected,
  isVisible,
  onToggleSelect,
}: StockTableRowProps) {
  const tsCode = toTsCode(stock.code)

  return (
    <tr
      className={`transition-colors duration-fast ${isSelected ? 'bg-primary/[0.08]' : 'hover:bg-surface-hover'}`}
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
        {/* 股票名称跟随当日涨跌染色 —— 用户偏好（"一眼看到是否上涨"）。
            注意：仅"最新价/涨跌幅/股票名"三处用红绿；成交额/换手率/市值/PE-TTM 是
            活跃度/估值指标，不携带方向语义，保持中性以免误导 */}
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
      {isVisible('latest_price') && (
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
      )}
      {isVisible('pct_change') && (
        <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium tabular-nums">
          {stock.pct_change != null ? (
            <span className={stock.pct_change > 0 ? 'text-positive' : stock.pct_change < 0 ? 'text-negative' : 'text-gray-900 dark:text-white'}>
              {stock.pct_change > 0 ? '+' : ''}{stock.pct_change.toFixed(2)}%
            </span>
          ) : '-'}
        </td>
      )}
      {isVisible('amount') && (
        <td className="px-4 py-4 whitespace-nowrap text-right text-sm font-medium tabular-nums text-gray-900 dark:text-gray-100">
          {fmtAmount(stock.amount)}
        </td>
      )}
      {isVisible('turnover_rate') && (
        <td className="px-4 py-4 whitespace-nowrap text-right text-sm font-medium tabular-nums text-gray-700 dark:text-gray-300">
          {stock.turnover_rate != null ? `${stock.turnover_rate.toFixed(2)}%` : '—'}
        </td>
      )}
      {isVisible('total_mv') && (
        <td className="px-4 py-4 whitespace-nowrap text-right text-sm font-medium tabular-nums text-gray-700 dark:text-gray-300">
          {fmtMarketCap(stock.total_mv)}
        </td>
      )}
      {isVisible('pe_ttm') && (
        <td className="px-4 py-4 whitespace-nowrap text-right text-sm font-medium tabular-nums">
          {(() => {
            const { text, tone } = fmtPE(stock.pe_ttm)
            const cls = tone === 'warn'
              ? 'text-warning'
              : tone === 'muted'
              ? 'text-gray-300 dark:text-gray-600'
              : 'text-gray-900 dark:text-gray-100'
            return <span className={cls}>{text}</span>
          })()}
        </td>
      )}
      {SCORE_COLUMNS.map(({ id, field, aria }) => isVisible(id) && (
        <td key={id} className="px-4 py-4 whitespace-nowrap text-right" onClick={(e) => e.stopPropagation()}>
          <ScoreBadge score={stock[field]?.score} ariaPrefix={aria} />
        </td>
      ))}
      {isVisible('cio_last_date') && (
        <td className="px-4 py-4 whitespace-nowrap text-right text-xs text-gray-600 dark:text-gray-400 tabular-nums" onClick={(e) => e.stopPropagation()}>
          {stock.latest_analysis_cio?.created_at ? (
            stock.latest_analysis_cio.created_at.slice(0, 10)
          ) : (
            <span className="text-gray-300 dark:text-gray-600">—</span>
          )}
        </td>
      )}
      {/* 价值度量三列：ROC / EY / 内在价值安全边际（《股市稳赚》+《聪明的投资者》）*/}
      {isVisible('roc') && (
        <td className="px-4 py-4 whitespace-nowrap text-right" onClick={(e) => e.stopPropagation()}>
          <PercentCell value={stock.value_metrics?.roc} />
        </td>
      )}
      {isVisible('earnings_yield') && (
        <td className="px-4 py-4 whitespace-nowrap text-right" onClick={(e) => e.stopPropagation()}>
          <PercentCell value={stock.value_metrics?.earnings_yield} />
        </td>
      )}
      {isVisible('intrinsic_margin') && (
        <td className="px-4 py-4 whitespace-nowrap text-right" onClick={(e) => e.stopPropagation()}>
          <IntrinsicCell
            iv={stock.value_metrics?.intrinsic_value}
            margin={stock.value_metrics?.intrinsic_margin}
            gRate={stock.value_metrics?.g_rate}
            gSource={stock.value_metrics?.g_source}
          />
        </td>
      )}
      {isVisible('followup_price') && (
        <td className="px-4 py-4 text-xs" onClick={(e) => e.stopPropagation()}>
          <FollowupPriceCell triggers={stock.latest_analysis_cio?.followup_triggers ?? null} />
        </td>
      )}
      {isVisible('followup_time') && (
        <td className="px-4 py-4 text-xs" onClick={(e) => e.stopPropagation()}>
          <FollowupTimeCell triggers={stock.latest_analysis_cio?.followup_triggers ?? null} />
        </td>
      )}
    </tr>
  )
})
