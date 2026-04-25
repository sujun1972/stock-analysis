'use client'

import React from 'react'
import { Sparkles, ArrowRight, Clock, RefreshCcw } from 'lucide-react'
import {
  EXPERTS,
  scoreToneClass,
  safeParseJSON,
  extractScore,
  extractKeyQuote,
  extractRating,
  extractBullBearCount,
  type ExpertMeta,
} from './expert-meta'

export interface LatestAnalysisRecord {
  id: number
  score: number | null
  version: number
  analysis_text: string
  created_at: string
}

export interface ExpertSummaryCardProps {
  /** 4 个 analysis_type → 最新一条记录（null 表示未生成） */
  latestByExpert: Record<ExpertMeta['key'], LatestAnalysisRecord | null>
  /** 是否正在加载（4 条全部）；用于骨架占位 */
  loading: boolean
  /** 用户点专家卡的"详情→"按钮：跳到对应专家详情区 */
  onExpertSelect?: (expertKey: ExpertMeta['key']) => void
  /** 用户点头部"一键分析"按钮 */
  onMultiGenerate?: () => void
  /** 一键分析进行中 */
  multiGenerating?: boolean
  /** 一键分析后端返回的提示文案 */
  multiMessage?: { type: 'success' | 'error'; text: string } | null
}

/**
 * AI 决策摘要卡（卡 ②）
 * 一行 4 列：CIO / 游资 / 中线 / 价值；每张卡 = 评分 + rating + key_quote + 因子计数 + 详情链接。
 * 桌面 grid-cols-4，平板 sm:grid-cols-2，手机 grid-cols-1。
 * 顶部 4px 色条用专家身份色。
 */
export function ExpertSummaryCard({
  latestByExpert,
  loading,
  onExpertSelect,
  onMultiGenerate,
  multiGenerating,
  multiMessage,
}: ExpertSummaryCardProps) {
  return (
    <section
      className="rounded-lg border border-gray-200 dark:border-gray-700 bg-card text-card-foreground shadow-sm"
      aria-label="AI 决策摘要"
    >
      {/* 头部 toolbar：标题 + 一键分析按钮 */}
      <header className="flex items-center justify-between gap-3 px-5 py-3 border-b border-gray-100 dark:border-gray-800">
        <div className="flex items-baseline gap-2">
          <h2 className="text-base font-semibold">AI 决策摘要</h2>
          <span className="text-xs text-gray-500 dark:text-gray-400">4 位专家最新观点</span>
        </div>
        <div className="flex items-center gap-3">
          {multiMessage && (
            <span className={`text-xs ${multiMessage.type === 'success' ? 'text-emerald-600' : 'text-red-500'}`}>
              {multiMessage.text}
            </span>
          )}
          {onMultiGenerate && (
            <button
              type="button"
              onClick={onMultiGenerate}
              disabled={multiGenerating}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium bg-primary text-primary-foreground hover:opacity-90 disabled:opacity-50 transition-opacity duration-fast focus-ring"
              aria-label="对所有专家发起一键 AI 分析"
            >
              {multiGenerating ? (
                <RefreshCcw className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Sparkles className="h-3.5 w-3.5" />
              )}
              {multiGenerating ? '分析中...' : '一键分析'}
            </button>
          )}
        </div>
      </header>

      {/* 4 列卡片网格 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 p-5">
        {EXPERTS.map((expert) => (
          <ExpertCell
            key={expert.key}
            expert={expert}
            record={latestByExpert[expert.key]}
            loading={loading}
            onSelect={onExpertSelect}
          />
        ))}
      </div>
    </section>
  )
}

function ExpertCell({
  expert,
  record,
  loading,
  onSelect,
}: {
  expert: ExpertMeta
  record: LatestAnalysisRecord | null
  loading: boolean
  onSelect?: (k: ExpertMeta['key']) => void
}) {
  const Icon = expert.icon
  const colorStyle = { color: `hsl(var(${expert.colorVar}))` }

  // 解析最新一条
  const parsed = safeParseJSON(record?.analysis_text)
  const score = extractScore(parsed) ?? record?.score ?? null
  const keyQuote = extractKeyQuote(parsed)
  const rating = extractRating(parsed)
  const { bull, bear } = extractBullBearCount(parsed)

  return (
    <button
      type="button"
      onClick={() => record && onSelect?.(expert.key)}
      disabled={!record}
      className={`relative text-left rounded-md border border-gray-200 dark:border-gray-700 bg-background p-3 transition-colors duration-fast hover:bg-gray-50 dark:hover:bg-gray-800/40 disabled:cursor-default disabled:hover:bg-background focus-ring ${expert.borderClass} border-l-4`}
      aria-label={`查看${expert.label}详情`}
    >
      {/* 顶部专家头 */}
      <div className="flex items-center gap-1.5 mb-2">
        <Icon className="h-3.5 w-3.5 shrink-0" style={colorStyle} aria-hidden />
        <span className="font-semibold text-sm">{expert.label}</span>
        <span className="text-xs text-gray-400 dark:text-gray-500 truncate">· {expert.subtitle}</span>
      </div>

      {/* 评分 + rating */}
      {loading ? (
        <div className="space-y-2">
          <div className="h-7 w-20 rounded bg-gray-100 dark:bg-gray-800 animate-pulse" />
          <div className="h-4 w-32 rounded bg-gray-100 dark:bg-gray-800 animate-pulse" />
          <div className="h-4 w-full rounded bg-gray-100 dark:bg-gray-800 animate-pulse" />
        </div>
      ) : record ? (
        <>
          <div className="flex items-baseline gap-2 mb-1.5">
            <span className={`text-2xl font-bold tabular-nums leading-none ${scoreToneClass(score)}`}>
              {score == null ? '—' : Number.isInteger(score) ? score.toFixed(1) : score}
            </span>
            {rating && (
              <span className="text-xs text-gray-700 dark:text-gray-300 truncate" title={rating}>
                {rating}
              </span>
            )}
          </div>
          {keyQuote && (
            <p
              className="text-xs text-gray-600 dark:text-gray-300 line-clamp-2 mb-2"
              title={keyQuote}
            >
              "{keyQuote}"
            </p>
          )}
          <div className="flex items-center justify-between text-[11px] text-gray-500 dark:text-gray-400">
            <span className="inline-flex items-center gap-2">
              {bull > 0 && (
                <span className="inline-flex items-center gap-0.5 text-emerald-600 dark:text-emerald-400">
                  <span aria-hidden>▲</span>
                  <span className="tabular-nums">{bull}</span>
                </span>
              )}
              {bear > 0 && (
                <span className="inline-flex items-center gap-0.5 text-red-500 dark:text-red-400">
                  <span aria-hidden>▼</span>
                  <span className="tabular-nums">{bear}</span>
                </span>
              )}
            </span>
            <span className="inline-flex items-center gap-1 tabular-nums">
              <Clock className="h-3 w-3" aria-hidden />
              {record.created_at?.slice(5, 10)}
              <ArrowRight className="h-3 w-3 ml-0.5 opacity-60" aria-hidden />
            </span>
          </div>
        </>
      ) : (
        <div className="text-xs text-gray-400 dark:text-gray-500 py-3">
          尚未生成，点击右上"一键分析"
        </div>
      )}
    </button>
  )
}
