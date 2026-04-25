'use client'

import React from 'react'
import { History, Sparkles, RefreshCcw } from 'lucide-react'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { renderBold } from './text-utils'
import { ProsConsList } from './sections'
import { StructuredAnalysisContent } from './StructuredAnalysisContent'
import { MarkdownContent } from './markdown'
import {
  EXPERTS,
  EXPERT_BY_KEY,
  scoreToneClass,
  safeParseJSON,
  extractScore,
  extractKeyQuote,
  extractRating,
  type ExpertMeta,
} from './expert-meta'
import type { LatestAnalysisRecord } from './ExpertSummaryCard'

export interface ExpertDetailCardProps {
  /** 4 个 analysis_type → 最新一条记录 */
  latestByExpert: Record<ExpertMeta['key'], LatestAnalysisRecord | null>
  /** 当前激活的专家 Tab（受控） */
  activeExpert: Exclude<ExpertMeta['key'], 'cio'>
  /** Tab 切换 */
  onActiveExpertChange: (k: Exclude<ExpertMeta['key'], 'cio'>) => void
  /** 点击 "历史·" 触发弹窗（弹窗作为高级视图：版本翻页/编辑/复盘/源码/提示词） */
  onOpenHistory?: (defaultTab: ExpertMeta['key']) => void
  /** 点击单专家"重新分析" */
  onRegenerate?: (expert: ExpertMeta) => void
  /** 单专家正在重新生成 */
  regeneratingKey?: ExpertMeta['key'] | null
  /** 唯一锚点 id，主页 scrollIntoView 用 */
  id?: string
}

const TAB_EXPERTS = EXPERTS.filter((e) => e.key !== 'cio') as Array<
  ExpertMeta & { key: Exclude<ExpertMeta['key'], 'cio'> }
>

/**
 * 三专家详情卡（卡 ④）
 * 主页内嵌 Tab：游资 / 中线 / 价值；右上角："历史·" 唤起弹窗（高级视图）。
 * Tab 内部：评分 / rating / key_quote / 正反因子双栏 / 完整 SECTION_CONFIGS 渲染。
 */
export function ExpertDetailCard({
  latestByExpert,
  activeExpert,
  onActiveExpertChange,
  onOpenHistory,
  onRegenerate,
  regeneratingKey,
  id,
}: ExpertDetailCardProps) {
  return (
    <section
      id={id}
      className="rounded-lg border border-gray-200 dark:border-gray-700 bg-card overflow-hidden"
      aria-label="三专家详情"
    >
      <Tabs value={activeExpert} onValueChange={(v) => onActiveExpertChange(v as Exclude<ExpertMeta['key'], 'cio'>)}>
        <header className="flex items-center justify-between gap-3 px-3 sm:px-5 py-2 border-b border-gray-100 dark:border-gray-800">
          <TabsList className="bg-transparent gap-1 p-0">
            {TAB_EXPERTS.map((e) => {
              const Icon = e.icon
              return (
                <TabsTrigger
                  key={e.key}
                  value={e.key}
                  className="gap-1.5 data-[state=active]:bg-muted data-[state=active]:shadow-none"
                >
                  <Icon className="h-3.5 w-3.5" style={{ color: `hsl(var(${e.colorVar}))` }} aria-hidden />
                  <span>{e.label}</span>
                </TabsTrigger>
              )
            })}
          </TabsList>
          <div className="flex items-center gap-1.5 shrink-0">
            <button
              type="button"
              onClick={() => onRegenerate?.(EXPERT_BY_KEY[activeExpert])}
              disabled={regeneratingKey === activeExpert}
              className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors duration-fast disabled:opacity-50 focus-ring"
              title={`让${EXPERT_BY_KEY[activeExpert].label}专家重新分析`}
            >
              {regeneratingKey === activeExpert ? (
                <RefreshCcw className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Sparkles className="h-3.5 w-3.5" />
              )}
              <span>重新分析</span>
            </button>
            <button
              type="button"
              onClick={() => onOpenHistory?.(activeExpert)}
              className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors duration-fast focus-ring"
              title="打开历史视图（含版本翻页/编辑/复盘/提示词）"
            >
              <History className="h-3.5 w-3.5" />
              <span>历史</span>
            </button>
          </div>
        </header>

        {TAB_EXPERTS.map((e) => (
          <TabsContent key={e.key} value={e.key} className="m-0 p-5">
            <ExpertBody expert={e} record={latestByExpert[e.key]} />
          </TabsContent>
        ))}
      </Tabs>
    </section>
  )
}

function ExpertBody({ expert, record }: { expert: ExpertMeta; record: LatestAnalysisRecord | null }) {
  if (!record) {
    return (
      <div className="text-center py-10 text-sm text-gray-500 dark:text-gray-400 border border-dashed border-gray-200 dark:border-gray-700 rounded-md">
        尚未生成 {expert.label}专家分析，点击右上"重新分析"
      </div>
    )
  }

  const parsed = safeParseJSON(record.analysis_text)
  const score = extractScore(parsed) ?? record.score
  const rating = extractRating(parsed)
  const keyQuote = extractKeyQuote(parsed)
  const fs = parsed?.final_score
  const bull = Array.isArray(fs?.bull_factors) ? fs.bull_factors
    : Array.isArray(fs?.pros) ? fs.pros : []
  const bear = Array.isArray(fs?.bear_factors) ? fs.bear_factors
    : Array.isArray(fs?.cons) ? fs.cons : []

  return (
    <div className="space-y-4">
      {/* 头部：评分 + rating + 时间 */}
      <header className="flex items-start justify-between gap-3 pb-3 border-b border-gray-100 dark:border-gray-800">
        <div className="flex items-baseline gap-3 flex-wrap">
          {score != null && (
            <span className={`text-3xl font-bold tabular-nums leading-none ${scoreToneClass(score)}`}>
              {Number.isInteger(score) ? Number(score).toFixed(1) : score}
            </span>
          )}
          {rating && (
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{rating}</span>
          )}
        </div>
        <span className="text-xs text-gray-500 dark:text-gray-400 tabular-nums shrink-0">
          版本 {record.version} · {record.created_at?.replace('T', ' ').slice(0, 16)}
        </span>
      </header>

      {/* key_quote 高亮 */}
      {keyQuote && (
        <p
          className="px-3 py-2 rounded-md text-sm font-medium leading-relaxed"
          style={{
            background: `hsl(var(${expert.colorVar}) / 0.10)`,
            color: `hsl(var(${expert.colorVar}))`,
          }}
        >
          {renderBold(keyQuote)}
        </p>
      )}

      {/* 正反因子双栏 */}
      {(bull.length > 0 || bear.length > 0) && (
        <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {bull.length > 0 && (
            <div>
              <div className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 mb-1">
                ▲ 正向因子
              </div>
              <ProsConsList items={bull} variant="pros" />
            </div>
          )}
          {bear.length > 0 && (
            <div>
              <div className="text-sm font-semibold text-red-600 dark:text-red-400 mb-1">
                ▼ 负向因子
              </div>
              <ProsConsList items={bear} variant="cons" />
            </div>
          )}
        </section>
      )}

      {/* SECTION_CONFIGS 完整渲染（除 final_score 已在头部） */}
      {parsed ? (
        <StructuredAnalysisContent
          d={parsed}
          analysisType={expert.analysisType}
          hideFinalScore
          hideTitleHeader
        />
      ) : (
        <MarkdownContent text={record.analysis_text} />
      )}
    </div>
  )
}
