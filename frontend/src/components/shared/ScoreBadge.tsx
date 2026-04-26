'use client'

import React from 'react'

export type ScoreBadgeVariant = 'table' | 'card'

const TIER_TOOLTIP = '≥8 强烈信号 / ≥6 关注 / <6 中性'

// 单色相紫罗兰 4 档（避主色蓝 + 消多重灰底）：
//   ≥8 强信号 = 深紫实底 + 白字（醒目）
//   6-8 关注  = 中紫实底 + 白字（次醒目）
//   4-6 中性  = 浅紫描边 + 紫字（轻量 outline，与实底形成视觉重量差）
//   <4 弱     = 紫字无块（避免再出一个灰背景）
//   null     = card variant 灰底占位；table variant 由组件 JSX 早 return 渲染 "—"，不进此函数
function resolveTone(score: number | null | undefined) {
  if (score == null) {
    return 'bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-600'
  }
  if (score >= 8) return 'bg-score-high text-white dark:text-gray-950'
  if (score >= 6) return 'bg-score-mid text-white dark:text-gray-950'
  if (score >= 4) return 'bg-score-low text-score-high ring-1 ring-inset ring-score-mid/40 dark:bg-score-low dark:text-score-high'
  return 'text-score-mid dark:text-score-high'
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
  const tone = resolveTone(score)
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
