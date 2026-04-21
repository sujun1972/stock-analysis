'use client'

import { cn } from '@/lib/utils'

type Impact = 'bullish' | 'bearish' | 'neutral' | null | undefined

interface Props {
  score?: number | null
  impact?: Impact
  reason?: string | null
  size?: 'sm' | 'md'
}

/**
 * 舆情打分徽章：bullish 绿 / bearish 红 / neutral 灰；未打分时灰色占位。
 */
export function SentimentBadge({ score, impact, reason, size = 'sm' }: Props) {
  if (score === null || score === undefined || !impact) {
    return (
      <span
        className={cn(
          'inline-flex items-center text-gray-400 tracking-wide',
          size === 'sm' ? 'text-xs' : 'text-sm'
        )}
      >
        未打分
      </span>
    )
  }
  const cls =
    impact === 'bullish'
      ? 'bg-green-50 text-green-700 border-green-200'
      : impact === 'bearish'
        ? 'bg-red-50 text-red-700 border-red-200'
        : 'bg-gray-50 text-gray-600 border-gray-200'
  const icon = impact === 'bullish' ? '🟢' : impact === 'bearish' ? '🔴' : '⚪'
  const signed = (score >= 0 ? '+' : '') + score.toFixed(2)
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded border px-1.5 py-0.5 font-medium tabular-nums',
        cls,
        size === 'sm' ? 'text-xs' : 'text-sm'
      )}
      title={reason || undefined}
    >
      <span>{icon}</span>
      <span>{signed}</span>
    </span>
  )
}
