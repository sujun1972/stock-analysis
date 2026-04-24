'use client'

import React from 'react'

export type ScoreBadgeVariant = 'table' | 'card'

const TIER_TOOLTIP = '≥8 强烈信号 / ≥6 关注 / <6 中性'

function resolveTone(score: number | null | undefined, variant: ScoreBadgeVariant) {
  if (score == null) {
    return variant === 'card'
      ? 'bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-600'
      : 'bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500'
  }
  if (score >= 8) {
    return 'bg-red-600 text-white dark:bg-red-500 dark:text-white'
  }
  if (score >= 6) {
    return 'bg-yellow-300 text-yellow-900 dark:bg-yellow-500 dark:text-yellow-950'
  }
  return 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-200'
}

function formatScore(score: number | null | undefined): string {
  if (score == null) return '—'
  return Number.isInteger(score) ? score.toFixed(1) : score.toString()
}

function tierLabel(score: number | null | undefined): string {
  if (score == null) return '无评分数据'
  if (score >= 8) return '强烈信号'
  if (score >= 6) return '关注'
  return '中性'
}

interface ScoreBadgeProps {
  score?: number | null
  label?: string
  variant?: ScoreBadgeVariant
  ariaPrefix?: string
}

export function ScoreBadge({
  score,
  label,
  variant = 'table',
  ariaPrefix,
}: ScoreBadgeProps) {
  const tone = resolveTone(score, variant)
  const tip = score == null
    ? '无评分数据'
    : `评分 ${formatScore(score)}（${tierLabel(score)}）· 分档：${TIER_TOOLTIP}`
  const ariaLabel = `${ariaPrefix ?? label ?? '评分'} ${formatScore(score)} ${tierLabel(score)}`

  if (variant === 'card') {
    return (
      <div
        className={`flex flex-col items-center justify-center px-2 py-1 rounded ${tone} min-w-[44px]`}
        title={tip}
        aria-label={ariaLabel}
      >
        {label && <span className="text-[10px] leading-none opacity-80">{label}</span>}
        <span className="text-sm font-semibold leading-tight mt-0.5 tabular-nums">
          {formatScore(score)}
        </span>
      </div>
    )
  }

  if (score == null) {
    return (
      <span
        className="inline-block text-xs text-gray-300 dark:text-gray-600 tabular-nums"
        title={tip}
        aria-label={ariaLabel}
      >
        —
      </span>
    )
  }

  return (
    <span
      className={`inline-flex items-center justify-center min-w-[32px] px-1.5 py-0.5 rounded text-xs font-semibold tabular-nums ${tone}`}
      title={tip}
      aria-label={ariaLabel}
    >
      {formatScore(score)}
    </span>
  )
}
