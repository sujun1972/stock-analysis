'use client'

import React, { useCallback, useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Components } from 'react-markdown'
import { apiClient } from '@/lib/api-client'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Copy,
  Check,
  Save,
  Pencil,
  Trash2,
  X,
  Sparkles,
  Code,
  BookOpen,
  RotateCcw,
} from 'lucide-react'

import type { StockAnalysisRecord } from '@/types'

// ── 类型 ──────────────────────────────────────────────────────

export type AnalysisRecord = StockAnalysisRecord

export interface HotMoneyViewDialogProps {
  open: boolean
  onClose: () => void
  stockName: string
  stockCode: string   // 纯代码，如 000001
  tsCode: string      // ts_code，如 000001.SZ
  // 游资观点提示词
  promptContent: string
  promptLoading: boolean
  // 数据收集提示词
  dataCollectionPrompt: string
  dataCollectionPromptLoading: boolean
  // 中线产业趋势专家观点
  midlinePrompt: string
  midlinePromptLoading: boolean
  // 长线价值守望者观点
  longtermPrompt: string
  longtermPromptLoading: boolean
  // 首席投资官（CIO）指令
  cioPrompt: string
  cioPromptLoading: boolean
  onSaved?: () => void
}

// ── 分析内容渲染 ──────────────────────────────────────────────

/** 将 **加粗** 标记拆分为带 <strong> 的 React 节点数组，避免 dangerouslySetInnerHTML */
function renderBold(text: string): React.ReactNode {
  const parts = text.split(/\*\*(.+?)\*\*/g)
  return parts.map((part, i) =>
    i % 2 === 1 ? <strong key={i}>{part}</strong> : part
  )
}

/** 高亮【标签】为蓝色粗体 */
function highlightTags(text: string): React.ReactNode {
  const parts = text.split(/(【[^】]+】)/g)
  if (parts.length === 1) return text
  return parts.map((part, i) =>
    /^【[^】]+】$/.test(part)
      ? <span key={i} className="font-semibold text-blue-700 dark:text-blue-400">{part}</span>
      : part
  )
}

/** react-markdown 自定义组件，保留【标签】高亮 + 表格样式 */
const markdownComponents: Components = {
  h1: ({ children }) => (
    <h1 className="text-lg font-bold mt-4 mb-2 text-gray-900 dark:text-gray-100">{children}</h1>
  ),
  h2: ({ children }) => (
    <h2 className="text-base font-bold mt-3 mb-1 text-gray-900 dark:text-gray-100">{children}</h2>
  ),
  h3: ({ children }) => (
    <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mt-2 mb-1">{children}</h3>
  ),
  h4: ({ children }) => (
    <h4 className="text-sm font-semibold mt-2 mb-1 text-gray-800 dark:text-gray-200">{children}</h4>
  ),
  p: ({ children }) => {
    // 对纯文本子节点做【标签】高亮
    const processed = React.Children.map(children, child =>
      typeof child === 'string' ? highlightTags(child) : child
    )
    return <p className="mb-1.5 leading-relaxed">{processed}</p>
  },
  strong: ({ children }) => (
    <strong className="font-semibold text-gray-900 dark:text-gray-100">{children}</strong>
  ),
  ul: ({ children }) => (
    <ul className="list-disc list-inside space-y-0.5 mb-2 pl-1">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="list-decimal list-inside space-y-0.5 mb-2 pl-1">{children}</ol>
  ),
  li: ({ children }) => {
    const processed = React.Children.map(children, child =>
      typeof child === 'string' ? highlightTags(child) : child
    )
    return <li className="leading-relaxed">{processed}</li>
  },
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-blue-300 dark:border-blue-600 pl-3 py-1 my-2 text-gray-600 dark:text-gray-400 bg-blue-50/50 dark:bg-blue-900/20 rounded-r">
      {children}
    </blockquote>
  ),
  hr: () => (
    <hr className="border-gray-200 dark:border-gray-700 my-2" />
  ),
  table: ({ children }) => (
    <div className="overflow-x-auto my-2">
      <table className="min-w-full text-sm border-collapse border border-gray-200 dark:border-gray-700">
        {children}
      </table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-gray-100 dark:bg-gray-800">{children}</thead>
  ),
  tbody: ({ children }) => (
    <tbody className="divide-y divide-gray-200 dark:divide-gray-700">{children}</tbody>
  ),
  tr: ({ children }) => (
    <tr className="hover:bg-gray-50 dark:hover:bg-gray-800/50">{children}</tr>
  ),
  th: ({ children }) => (
    <th className="px-3 py-1.5 text-left font-semibold text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 whitespace-nowrap">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-3 py-1.5 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700">
      {children}
    </td>
  ),
  code: ({ children, className }) => {
    const isBlock = className?.includes('language-')
    if (isBlock) {
      return (
        <code className="block bg-gray-100 dark:bg-gray-800 rounded-lg p-3 text-xs font-mono overflow-x-auto my-2">
          {children}
        </code>
      )
    }
    return (
      <code className="bg-gray-100 dark:bg-gray-800 rounded px-1.5 py-0.5 text-xs font-mono">
        {children}
      </code>
    )
  },
  pre: ({ children }) => (
    <pre className="my-2">{children}</pre>
  ),
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline dark:text-blue-400">
      {children}
    </a>
  ),
}

/** 完整 Markdown 渲染（react-markdown + GFM 表格支持） */
function MarkdownContent({ text }: { text: string }) {
  return (
    <div className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {text}
      </ReactMarkdown>
    </div>
  )
}

// ── 各专家 Section 配置 ────────────────────────────────────────
// 每种 analysisType 对应一组 section 声明，每个 section 声明一个 JSON 顶层 key
// 和该 section 下嵌套字段的中文标签映射。
//
// 约定：value 是 string 时作为『标签：值』条目展示；
//       value 是嵌套对象时作为子卡片展示（进一步查 FIELD_LABELS 映射）；
//       value 是数组（final_score.bull_factors）由 ProsConsList 特殊渲染；
//       value 是 {probability, trigger_condition} 时（next_day_scenarios 三档）特殊处理。

interface SectionConfig {
  key: string          // JSON 顶层字段名
  title: string        // section 中文标题
  labels?: Record<string, string>  // 子字段 key → 中文标签
}

const SECTION_CONFIGS: Record<string, SectionConfig[]> = {
  // 游资观点 v3.1.0（顶级游资 + 日内动能专家）
  hot_money_view: [
    {
      key: 'seat_analysis',
      title: '龙虎榜 · 席位分析',
      labels: {
        on_billboard_60d: '近 60 日上榜',
        buyer_seat_type: '买方席位性质',
        seat_signal: '席位信号',
        key_seats: '关键席位',
      },
    },
    {
      key: 'theme_position',
      title: '题材身位与板位',
      labels: {
        limit_status_today: '本日涨停状态',
        sector_rank: '板块地位',
        relative_position: '相对位置',
        ecology_note: '市场情绪生态',
      },
    },
    {
      key: 'limit_gene',
      title: '打板基因（近 60 日）',
      labels: {
        limit_up_count_60d: '涨停次数',
        t1_win_rate: 'T+1 胜率',
        t1_avg_pct: 'T+1 平均涨跌',
        gene_verdict: '基因判定',
      },
    },
    {
      key: 'capital_structure',
      title: '资金与筹码结构',
      labels: {
        main_flow_signal: '主力资金信号',
        divergence_flag: '分歧/一致',
      },
    },
    {
      key: 'momentum_signal',
      title: '竞价 · 量价动能',
      labels: {
        auction_signal: '竞价信号',
        volume_structure: '量能结构',
        technical_verdict: '技术共振',
      },
    },
    {
      key: 'next_day_scenarios',
      title: '次日三档情景概率',
      labels: {
        bull_pct_ge_3: '强势溢价（≥+3%）',
        neutral_minus2_to_3: '震荡平开（-2%~+3%）',
        bear_pct_le_minus2: '破板低开（≤-2%）',
        key_observation_window: '重点观察窗口',
      },
    },
    {
      key: 'execution_plan',
      title: '执行计划',
      labels: {
        entry_zones: '分批介入价位',
        stop_loss: '止损价位',
        add_position_trigger: '加仓触发',
        t0_reduce_signal: 'T+0 减仓信号',
      },
    },
  ],
  // 中线产业趋势专家·事后复盘 v1.0.0
  midline_review: [
    {
      key: 'review_adequacy',
      title: '复盘时效性',
    },
    {
      key: 'prediction_summary',
      title: '原预测摘要',
    },
    {
      key: 'hit_rate',
      title: '命中度评估',
      labels: {
        industry_cycle: '产业景气度演变',
        earnings_fulfillment: '业绩兑现度',
        technical_evolution: '技术结构演变',
        price_target: '目标价区间命中',
        score_rating: '评分档位',
      },
    },
    {
      key: 'mispriced_factors',
      title: '误判归因',
    },
    {
      key: 'execution_retrospective',
      title: '中线持有复盘',
      labels: {
        entry_executed_result: '按计划买入结果',
        stop_loss_triggered: '是否触发止损',
        catalyst_fulfilled: '催化剂兑现状态',
        overall_verdict: '整体战果',
      },
    },
    {
      key: 'prompt_improvement_hints',
      title: 'Prompt 改进建议',
    },
    {
      key: 'lesson_for_future',
      title: '可迁移经验',
    },
  ],
  // 长线价值守望者·事后复盘 v1.0.0
  longterm_review: [
    {
      key: 'review_adequacy',
      title: '复盘时效性',
    },
    {
      key: 'prediction_summary',
      title: '原预测摘要',
    },
    {
      key: 'hit_rate',
      title: '命中度评估',
      labels: {
        moat_validation: '护城河验证',
        earnings_quality_fulfillment: '盈利质量兑现',
        valuation_mean_reversion: '估值回归进度',
        expected_return: '预期回报拆解',
        risk_exposure: '风险暴露',
        score_rating: '评分档位',
      },
    },
    {
      key: 'mispriced_factors',
      title: '误判归因',
    },
    {
      key: 'execution_retrospective',
      title: '长线持有复盘',
      labels: {
        entry_executed_result: '按计划买入结果',
        dividend_received: '持有期间派息',
        dca_opportunity: '加仓机会',
        overall_verdict: '整体战果',
      },
    },
    {
      key: 'prompt_improvement_hints',
      title: 'Prompt 改进建议',
    },
    {
      key: 'lesson_for_future',
      title: '可迁移经验',
    },
  ],
  // 顶级游资观点·事后复盘 v1.0.0
  hot_money_review: [
    {
      key: 'prediction_summary',
      title: '原预测摘要',
    },
    {
      key: 'hit_rate',
      title: '命中度评估',
      labels: {
        next_day_scenario: '次日情景预测',
        seat_signal: '席位信号预测',
        theme_position: '题材身位预测',
        score_rating: '评分档位',
      },
    },
    {
      key: 'mispriced_factors',
      title: '误判归因',
    },
    {
      key: 'execution_retrospective',
      title: '执行计划复盘',
      labels: {
        entry_executed_result: '按计划买入结果',
        stop_loss_triggered: '是否触发止损',
        add_position_triggered: '是否触发加仓',
        overall_verdict: '整体战果',
      },
    },
    {
      key: 'prompt_improvement_hints',
      title: 'Prompt 改进建议',
    },
    {
      key: 'lesson_for_future',
      title: '可迁移经验',
    },
  ],
  // 中线产业趋势专家 v2.0.0
  midline_industry_expert: [
    {
      key: 'industry_cycle',
      title: '产业景气度',
      labels: {
        sector_name: '板块归属',
        cycle_stage: '景气周期阶段',
        relative_strength: '板块 vs 个股相对强度',
        catalyst_note: '中线催化要点',
      },
    },
    {
      key: 'fundamental_quality',
      title: '公司基本面质地',
      labels: {
        latest_earnings_trend: '最新业绩趋势',
        profitability_level: '盈利能力',
        valuation_signal: '估值信号',
        quality_verdict: '质地判定',
      },
    },
    {
      key: 'technical_structure',
      title: '中线技术结构',
      labels: {
        weekly_macd: '周线 MACD',
        monthly_boll_position: '月线布林',
        ma_anchor: '均线锚点',
        structure_verdict: '结构判定',
      },
    },
    {
      key: 'price_target',
      title: '目标价区间（3~12 个月）',
      labels: {
        time_horizon: '时间窗口',
        target_range_low: '下沿目标价',
        target_range_high: '上沿目标价',
        target_method: '推演方法',
        stop_loss: '中线止损',
      },
    },
    {
      key: 'catalysts_and_risks',
      title: '催化剂与风险',
      labels: {
        catalysts: '催化剂',
        risks: '风险',
      },
    },
  ],
  // 长线价值守望者 v2.0.0
  longterm_value_watcher: [
    {
      key: 'moat_assessment',
      title: '护城河评估',
      labels: {
        moat_type: '护城河类型',
        moat_width: '护城河宽度',
        inference_basis: '推断依据',
      },
    },
    {
      key: 'earnings_quality',
      title: '长期盈利质量',
      labels: {
        roe_level: 'ROE 水平',
        gross_margin: '毛利率',
        repurchase_signal: '回购信号',
        earnings_trend: '业绩趋势',
        quality_verdict: '质地判定',
      },
    },
    {
      key: 'valuation_margin',
      title: '估值安全边际',
      labels: {
        current_pe: '当前 PE',
        pe_band_position: 'PE Band 分位',
        forward_pe_deviation: 'Forward PE 偏离',
        margin_verdict: '安全边际判定',
      },
    },
    {
      key: 'long_term_risk',
      title: '长线持有风险',
      labels: {
        shareholder_concentration: '股东集中度',
        northbound_trend: '北向资金趋势',
        pledge_risk: '股权质押',
        unlock_risk: '解禁风险',
        risk_verdict: '风险判定',
      },
    },
    {
      key: 'expected_return',
      title: '预期回报拆解（3~5 年）',
      labels: {
        time_horizon: '时间窗口',
        earnings_growth_contribution: '盈利增长贡献',
        valuation_expansion_contribution: '估值修复贡献',
        dividend_contribution: '股息贡献',
        total_annualized_return: '预期年化总回报',
      },
    },
  ],
}

// ── probability_metrics 字段的中文标签映射（兼容旧 schema）──────────
const PM_FIELD_LABELS: Record<string, { label: string; prefix?: string }> = {
  next_day_plus_2_percent_prob: { label: '次日 +2% 概率' },
  confidence_level:             { label: '置信度' },
  key_observation_window:       { label: '观察窗口' },
  three_month_positive_return_prob: { label: '3 个月正收益概率' },
  trend_stage:                  { label: '趋势阶段' },
  key_catalyst:                 { label: '核心催化' },
  one_year_intrinsic_return_prob:   { label: '1 年内在回报概率' },
  valuation_level:              { label: '估值水位' },
  safety_margin:                { label: '安全边际' },
  short_term_signal:            { label: '短线信号' },
  mid_term_signal:              { label: '中线信号' },
  long_term_signal:             { label: '长线信号' },
}

// ── 共用子组件 ────────────────────────────────────────────────

/** 评分色块 */
function ScoreBadge({ score, rating }: { score: number; rating?: string }) {
  const colorCls = score >= 8
    ? 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400'
    : score >= 6
    ? 'bg-yellow-50 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400'
    : 'bg-gray-50 text-gray-500 dark:bg-gray-800'
  return (
    <span className="flex items-center gap-2 flex-wrap">
      <span className={`font-bold px-2 py-0.5 rounded text-base ${colorCls}`}>
        {score} / 10
      </span>
      {rating && <span className="text-sm text-gray-600 dark:text-gray-300">{rating}</span>}
    </span>
  )
}

/** 带 +/− 前缀的列表（优势/劣势） */
function ProsConsList({ items, variant }: { items: string[]; variant: 'pros' | 'cons' }) {
  if (!items.length) return null
  const icon = variant === 'pros'
    ? <span className="text-green-500 shrink-0">+</span>
    : <span className="text-red-400 shrink-0">−</span>
  return (
    <ul className="mt-0.5 space-y-0.5 pl-1">
      {items.map((item, i) => (
        <li key={i} className="flex gap-1.5">{icon}<span>{renderBold(item)}</span></li>
      ))}
    </ul>
  )
}

/** 一个分析维度节（蓝色标题 + 正文） */
function DimensionSection({ title, content }: { title: string; content: string }) {
  return (
    <section>
      <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-1">{title}</h3>
      <div className="text-sm leading-relaxed">
        {content.split('\n').map((line, i) => (
          line.trim() ? <p key={i} className="mb-0.5">{renderBold(line)}</p> : null
        ))}
      </div>
    </section>
  )
}

/** 渲染单个字段的值（支持嵌套对象、数组、字符串、next_day_scenarios 特殊结构）*/
function FieldValue({ value }: { value: any }): React.ReactElement | null {
  if (value == null || value === '') return <span className="text-gray-400">-</span>

  // 数组：逐条列出（catalysts/risks 等）
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-gray-400">-</span>
    return (
      <ul className="mt-0.5 space-y-0.5">
        {value.map((item, i) => (
          <li key={i} className="flex gap-1.5">
            <span className="text-gray-400 shrink-0">·</span>
            <span>{renderBold(String(item ?? '-'))}</span>
          </li>
        ))}
      </ul>
    )
  }

  // next_day_scenarios 三档的子对象 { probability, trigger_condition }
  if (typeof value === 'object') {
    if ('probability' in value || 'trigger_condition' in value) {
      return (
        <span>
          <strong className="text-base">{renderBold(String(value.probability ?? '-'))}</strong>
          {value.trigger_condition && (
            <span className="text-gray-600 dark:text-gray-400 ml-2 text-xs">
              ／ {renderBold(String(value.trigger_condition))}
            </span>
          )}
        </span>
      )
    }
    // 通用嵌套对象：把每个键值对作为小标签渲染（适用于 hit_rate 各维度的 predicted/actual/verdict/evidence）
    const entries = Object.entries(value).filter(([, v]) => v != null && v !== '')
    if (entries.length === 0) return <span className="text-gray-400">-</span>
    return (
      <div className="mt-0.5 space-y-0.5">
        {entries.map(([k, v]) => (
          <div key={k} className="text-xs">
            <span className="text-gray-500 dark:text-gray-400">{k.replace(/_/g, ' ')}：</span>
            <span>{renderBold(String(v ?? '-'))}</span>
          </div>
        ))}
      </div>
    )
  }

  // 字符串 / 数字：直接显示，支持 **加粗** 标记
  return <span>{renderBold(String(value))}</span>
}

/** 渲染一个 section：标题 + 带字段标签的条目列表 */
function GenericSection({
  title,
  data,
  labels,
}: {
  title: string
  data: Record<string, any>
  labels?: Record<string, string>
}) {
  const entries = Object.entries(data).filter(([, v]) => v != null && v !== '')
  if (entries.length === 0) return null
  return (
    <section>
      <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-1">{title}</h3>
      <ul className="space-y-1 pl-1">
        {entries.map(([key, val]) => {
          const label = labels?.[key] ?? key.replace(/_/g, ' ')
          return (
            <li key={key} className="flex gap-1.5">
              <span className="text-gray-400 shrink-0">·</span>
              <span className="flex-1">
                <span className="text-gray-500 dark:text-gray-400">{label}：</span>
                <FieldValue value={val} />
              </span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

/**
 * 通用 JSON 结构化分析渲染器。
 * 根据 analysisType 查找 SECTION_CONFIGS，按声明的 section 顺序渲染；
 * 配置外的顶层字段（如 risk_warning / final_score）由专门逻辑处理；
 * 兼容旧 schema（probability_metrics / dimensions / trading_strategy / pros/cons）。
 */
function StructuredAnalysisContent({ d, analysisType }: { d: Record<string, any>; analysisType: string }) {
  const sections = SECTION_CONFIGS[analysisType] ?? []
  const fs = d.final_score as Record<string, any> | undefined
  const score = fs?.score != null ? parseFloat(String(fs.score)) : null

  // 兼容字段：新 schema 用 bull_factors/bear_factors + key_quote；旧用 pros/cons
  const bullFactors = Array.isArray(fs?.bull_factors) ? fs.bull_factors : (Array.isArray(fs?.pros) ? fs.pros : [])
  const bearFactors = Array.isArray(fs?.bear_factors) ? fs.bear_factors : (Array.isArray(fs?.cons) ? fs.cons : [])

  // 兼容旧 schema
  const pm = d.probability_metrics as Record<string, any> | undefined
  const ts = d.trading_strategy    as Record<string, any> | undefined

  return (
    <div className="text-sm text-gray-800 dark:text-gray-200 leading-relaxed space-y-3">

      {/* 标题行：专家身份 · 标的 · 日期 */}
      <div className="pb-2 border-b border-gray-100 dark:border-gray-700">
        <p className="font-bold text-base">
          {d.expert_identity ?? '专家'}{d.stock_target ? ` · ${d.stock_target}` : ''}
        </p>
        {d.analysis_date && (
          <p className="text-xs text-gray-400 mt-0.5">{d.analysis_date}</p>
        )}
      </div>

      {/* 新 schema：按 SECTION_CONFIGS 声明顺序渲染每个 section */}
      {sections.map(cfg => {
        const sectionData = d[cfg.key]
        if (sectionData == null || sectionData === '') return null

        // 字符串：以段落形式渲染（如 prediction_summary / lesson_for_future）
        if (typeof sectionData === 'string') {
          return (
            <section key={cfg.key}>
              <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-1">{cfg.title}</h3>
              <p className="text-sm leading-relaxed">{renderBold(sectionData)}</p>
            </section>
          )
        }

        // 数组：子元素可能是字符串（简单列表）或对象（每条一个卡片，如 mispriced_factors）
        if (Array.isArray(sectionData)) {
          if (sectionData.length === 0) return null
          return (
            <section key={cfg.key}>
              <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-1">{cfg.title}</h3>
              <ul className="space-y-1.5 pl-1">
                {sectionData.map((item, i) => (
                  <li key={i} className="flex gap-1.5">
                    <span className="text-gray-400 shrink-0">·</span>
                    {typeof item === 'string' ? (
                      <span className="flex-1">{renderBold(item)}</span>
                    ) : item && typeof item === 'object' ? (
                      <div className="flex-1 space-y-0.5">
                        {Object.entries(item).map(([k, v]) => (
                          <div key={k} className="text-xs">
                            <span className="text-gray-500 dark:text-gray-400">{k.replace(/_/g, ' ')}：</span>
                            <span>{renderBold(String(v ?? '-'))}</span>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </li>
                ))}
              </ul>
            </section>
          )
        }

        // 对象：走通用渲染
        if (typeof sectionData === 'object') {
          return <GenericSection key={cfg.key} title={cfg.title} data={sectionData} labels={cfg.labels} />
        }
        return null
      })}

      {/* 旧 schema 兼容：probability_metrics 核心指标区
          只在没有任何新 schema section 字段时降级显示（避免新旧 schema 同时重复渲染） */}
      {pm && Object.keys(pm).length > 0 && !sections.some(cfg => d[cfg.key]) && (
        <GenericSection title="核心指标" data={pm} labels={Object.fromEntries(
          Object.entries(PM_FIELD_LABELS).map(([k, v]) => [k, v.label])
        )} />
      )}

      {/* 旧 schema 兼容：dimensions 维度分析 */}
      {d.dimensions && Object.values(d.dimensions).map((dim: any, i: number) =>
        dim?.title && dim?.content
          ? <DimensionSection key={i} title={dim.title} content={dim.content} />
          : null
      )}

      {/* 旧 schema 兼容：trading_strategy */}
      {ts && (ts.action_plan || ts.risk_warning) && (
        <section>
          <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-1">交易策略</h3>
          {ts.action_plan && (
            <div className="mb-1">
              <span className="font-semibold text-gray-700 dark:text-gray-300">操作方案　</span>
              <span>{renderBold(ts.action_plan)}</span>
            </div>
          )}
          {ts.risk_warning && (
            <div>
              <span className="font-semibold text-gray-700 dark:text-gray-300">风险提示　</span>
              <span>{renderBold(ts.risk_warning)}</span>
            </div>
          )}
        </section>
      )}

      {/* 顶层 risk_warning（新游资 schema 单独字段）*/}
      {typeof d.risk_warning === 'string' && d.risk_warning.trim() && (
        <section>
          <h3 className="text-sm font-semibold text-red-600 dark:text-red-400 mb-1">风险提示</h3>
          <p className="text-sm">{renderBold(d.risk_warning)}</p>
        </section>
      )}

      {/* 综合评分区 */}
      {fs && score != null && (
        <section className="border-t border-gray-100 dark:border-gray-700 pt-3">
          <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-2">综合评分</h3>
          <ScoreBadge score={score} rating={fs.rating} />
          {typeof fs.key_quote === 'string' && fs.key_quote.trim() && (
            <p className="mt-2 px-3 py-2 bg-blue-50 dark:bg-blue-900/20 rounded-md text-sm font-semibold text-blue-800 dark:text-blue-200">
              {renderBold(fs.key_quote)}
            </p>
          )}
          {bullFactors.length > 0 && (
            <div className="mt-2">
              <span className="font-semibold text-gray-700 dark:text-gray-300">正向因子</span>
              <ProsConsList items={bullFactors} variant="pros" />
            </div>
          )}
          {bearFactors.length > 0 && (
            <div className="mt-1.5">
              <span className="font-semibold text-gray-700 dark:text-gray-300">负向因子</span>
              <ProsConsList items={bearFactors} variant="cons" />
            </div>
          )}
        </section>
      )}
    </div>
  )
}

/**
 * 分析内容渲染入口。
 * JSON 类型 → StructuredAnalysisContent（结构化卡片渲染）
 * 其他类型 → MarkdownContent（react-markdown + GFM 表格）
 */
const JSON_ANALYSIS_TYPES = new Set([
  'hot_money_view', 'hot_money_review',
  'midline_industry_expert', 'midline_review',
  'longterm_value_watcher', 'longterm_review',
  'cio_directive', 'macro_risk_expert',
])

function AnalysisContent({ text, analysisType }: { text: string; analysisType: string }) {
  if (JSON_ANALYSIS_TYPES.has(analysisType)) {
    try {
      const d = JSON.parse(text)
      if (d && typeof d === 'object' && !Array.isArray(d)) {
        return <StructuredAnalysisContent d={d} analysisType={analysisType} />
      }
    } catch {
      // JSON 解析失败，降级为 Markdown 渲染
    }
  }

  return <MarkdownContent text={text} />
}

// ── 单个 Tab 内容（抽离为子组件） ──────────────────────────────

interface AnalysisTabProps {
  tsCode: string
  stockName?: string
  stockCode?: string
  analysisType: string
  templateKey?: string   // 用于 AI 直接生成，传入后显示"AI 分析"按钮
  promptContent: string
  promptLoading: boolean
  open: boolean
  refreshKey?: number    // 外部触发刷新（如一键分析完成后 +1）
  onSaved?: () => void
  enableReview?: boolean // 是否在每条记录上显示"复盘此报告"按钮
  reviewType?: 'hot_money' | 'midline' | 'longterm'  // 复盘类型，enableReview=true 时必填
  onReviewCreated?: (reviewType: 'hot_money' | 'midline' | 'longterm') => void
}

function AnalysisTab({
  tsCode, stockName, stockCode, analysisType, templateKey, promptContent, promptLoading, open, refreshKey, onSaved,
  enableReview, reviewType, onReviewCreated,
}: AnalysisTabProps) {
  const [copied, setCopied] = useState(false)
  const [promptExpanded, setPromptExpanded] = useState(false)

  const [history, setHistory] = useState<AnalysisRecord[]>([])
  const [historyTotal, setHistoryTotal] = useState(0)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [currentIndex, setCurrentIndex] = useState(0)

  // 源文本/渲染视图切换
  const [showRawText, setShowRawText] = useState(false)

  // 编辑状态
  const [editMode, setEditMode] = useState(false)
  const [editText, setEditText] = useState('')
  const [editScore, setEditScore] = useState('')
  const [editSaving, setEditSaving] = useState(false)
  const [editMsg, setEditMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null)

  // 删除确认
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [deleting, setDeleting] = useState(false)

  // 生成分析（数据收集 tab 专用）
  const [generating, setGenerating] = useState(false)
  const [genMsg, setGenMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null)

  // AI 直接生成（游资观点 tab 专用）
  const [aiGenerating, setAiGenerating] = useState(false)
  const [aiGenMsg, setAiGenMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null)

  // 复盘（enableReview 为 true 时显示按钮；每条历史记录可独立触发一次复盘）
  const [reviewing, setReviewing] = useState(false)
  const [reviewMsg, setReviewMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null)

  const currentRecord: AnalysisRecord | null = history[currentIndex] ?? null

  useEffect(() => {
    if (!open || !tsCode) return
    setHistory([])
    setHistoryTotal(0)
    setCurrentIndex(0)
    setPromptExpanded(false)
    setCopied(false)
    setEditMode(false)
    setDeleteConfirm(false)
    setGenMsg(null)
    setAiGenMsg(null)

    setHistoryLoading(true)
    apiClient.getStockAnalysisHistory(tsCode, analysisType, 50, 0)
      .then((res) => {
        if (res?.code === 200 && res.data) {
          setHistory(res.data.items ?? [])
          setHistoryTotal(res.data.total ?? 0)
        }
      })
      .catch(() => {})
      .finally(() => setHistoryLoading(false))
  }, [open, tsCode, analysisType, refreshKey])

  // 切换记录时退出编辑模式
  useEffect(() => {
    setEditMode(false)
    setDeleteConfirm(false)
    setEditMsg(null)
    setShowRawText(false)
  }, [currentIndex])

  const reloadHistory = async () => {
    const histRes = await apiClient.getStockAnalysisHistory(tsCode, analysisType, 50, 0)
    if (histRes?.code === 200 && histRes.data) {
      setHistory(histRes.data.items ?? [])
      setHistoryTotal(histRes.data.total ?? 0)
      setCurrentIndex(0)
    }
  }

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(promptContent)
    } catch {
      const el = document.createElement('textarea')
      el.value = promptContent
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleGenerate = async () => {
    if (!tsCode || !stockName) return
    setGenerating(true)
    setGenMsg(null)
    try {
      const res = await apiClient.collectStockData(tsCode, stockName)
      if (res?.code === 200 && res.data?.text) {
        setGenMsg({ text: '数据收集完成', type: 'success' })
        await reloadHistory()
        onSaved?.()
      } else {
        setGenMsg({ text: res?.message || '数据收集失败', type: 'error' })
      }
    } catch (e: any) {
      setGenMsg({ text: e?.response?.data?.message || '数据收集失败', type: 'error' })
    } finally {
      setGenerating(false)
    }
  }

  const handleAiGenerate = async () => {
    if (!tsCode || !stockName || !stockCode || !templateKey) return
    setAiGenerating(true)
    setAiGenMsg(null)
    try {
      const res = await apiClient.generateStockAnalysis({
        ts_code: tsCode,
        stock_name: stockName,
        stock_code: stockCode,
        analysis_type: analysisType,
        template_key: templateKey,
      })
      if (res?.code === 200 && res.data?.analysis_text) {
        setAiGenMsg({ text: 'AI 分析完成，已自动保存', type: 'success' })
        await reloadHistory()
        onSaved?.()
      } else {
        setAiGenMsg({ text: res?.message || 'AI 分析失败', type: 'error' })
      }
    } catch (e: any) {
      setAiGenMsg({ text: e?.response?.data?.message || 'AI 分析失败', type: 'error' })
    } finally {
      setAiGenerating(false)
    }
  }

  const handleReview = async (force = false) => {
    if (!currentRecord || !tsCode || !stockName || !stockCode || !reviewType) return
    setReviewing(true)
    setReviewMsg(null)

    // 失败统一处理：若后端返回带"建议..."的时间窗不足提示且非 force，弹 confirm 询问强制重试
    const handleFailure = async (backendMsg: string) => {
      if (backendMsg.includes('建议') && !force) {
        if (window.confirm(`${backendMsg}\n\n是否仍要强制生成复盘？`)) {
          await handleReview(true)
          return
        }
        setReviewMsg({ text: '已取消复盘', type: 'error' })
      } else {
        setReviewMsg({ text: backendMsg, type: 'error' })
      }
    }

    try {
      const res = await apiClient.generateReviewAnalysis({
        ts_code: tsCode,
        stock_name: stockName,
        stock_code: stockCode,
        original_analysis_id: currentRecord.id,
        review_type: reviewType,
        force,
      })
      if (res?.code === 200 && res.data?.analysis_text) {
        setReviewMsg({ text: '复盘完成，已切换到复盘 Tab', type: 'success' })
        onReviewCreated?.(reviewType)
      } else {
        await handleFailure(res?.message || '复盘失败')
      }
    } catch (e: any) {
      await handleFailure(e?.response?.data?.message || '复盘失败')
    } finally {
      setReviewing(false)
    }
  }

  const handleEditStart = () => {
    if (!currentRecord) return
    setEditText(currentRecord.analysis_text)
    setEditScore(currentRecord.score !== null ? String(currentRecord.score) : '')
    setEditMsg(null)
    setEditMode(true)
  }

  const handleEditCancel = () => {
    setEditMode(false)
    setEditMsg(null)
  }

  const handleEditSave = async () => {
    if (!currentRecord) return
    if (!editText.trim()) {
      setEditMsg({ text: '请输入分析内容', type: 'error' })
      return
    }
    const score = editScore.trim() ? parseFloat(editScore) : undefined
    if (score !== undefined && (isNaN(score) || score < 0 || score > 10)) {
      setEditMsg({ text: '评分需在 0-10 之间', type: 'error' })
      return
    }
    setEditSaving(true)
    setEditMsg(null)
    try {
      const res = await apiClient.updateStockAnalysis(currentRecord.id, {
        analysis_text: editText.trim(),
        score,
      })
      if (res?.code === 200) {
        setEditMode(false)
        await reloadHistory()
        onSaved?.()
      } else {
        setEditMsg({ text: res?.message || '修改失败', type: 'error' })
      }
    } catch (e: any) {
      setEditMsg({ text: e?.response?.data?.message || '修改失败', type: 'error' })
    } finally {
      setEditSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!currentRecord) return
    setDeleting(true)
    try {
      const res = await apiClient.deleteStockAnalysis(currentRecord.id)
      if (res?.code === 200) {
        setDeleteConfirm(false)
        await reloadHistory()
        onSaved?.()
      }
    } catch {
      // ignore
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* 历史记录区 */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            已保存分析
            {historyTotal > 0 && (
              <span className="ml-1.5 text-xs text-gray-400">（共 {historyTotal} 条）</span>
            )}
          </span>
          <div className="flex items-center gap-2">
            {analysisType === 'stock_data_collection' && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleGenerate}
                disabled={generating}
                className="gap-1.5 h-7 text-xs"
              >
                <Sparkles className="h-3.5 w-3.5" />
                {generating ? '收集中...' : '生成分析'}
              </Button>
            )}
            {templateKey && (
              <Button
                onClick={handleAiGenerate}
                disabled={aiGenerating}
                size="sm"
                variant="outline"
                className="gap-1.5 h-7 text-xs"
              >
                <Sparkles className="h-3.5 w-3.5" />
                {aiGenerating ? 'AI 分析中...' : 'AI 分析'}
              </Button>
            )}
            {history.length > 1 && (
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setCurrentIndex((i) => Math.min(i + 1, history.length - 1))}
                  disabled={currentIndex >= history.length - 1}
                  className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-30"
                  title="更早版本"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="text-xs text-gray-500 min-w-[60px] text-center">
                  第 {currentIndex + 1} / {history.length} 条
                </span>
                <button
                  onClick={() => setCurrentIndex((i) => Math.max(i - 1, 0))}
                  disabled={currentIndex <= 0}
                  className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-30"
                  title="更新版本"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            )}
          </div>
        </div>
        {genMsg && (
          <p className={`text-xs mb-2 ${genMsg.type === 'success' ? 'text-green-600' : 'text-red-500'}`}>
            {genMsg.text}
          </p>
        )}
        {aiGenMsg && (
          <p className={`text-xs mb-2 ${aiGenMsg.type === 'success' ? 'text-green-600' : 'text-red-500'}`}>
            {aiGenMsg.text}
          </p>
        )}
        {reviewMsg && (
          <p className={`text-xs mb-2 ${reviewMsg.type === 'success' ? 'text-green-600' : 'text-red-500'}`}>
            {reviewMsg.text}
          </p>
        )}

        {historyLoading ? (
          <div className="text-center py-6 text-gray-400 text-sm">加载中...</div>
        ) : currentRecord ? (
          <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 space-y-2">
            {/* 记录头部：版本信息 + 操作按钮 */}
            <div className="flex items-center justify-between text-xs text-gray-400">
              <span>
                版本 {currentRecord.version} · {new Date(currentRecord.created_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}
              </span>
              <div className="flex items-center gap-2">
                {currentRecord.score !== null && !editMode && (
                  <span className={`font-semibold px-2 py-0.5 rounded text-sm ${
                    currentRecord.score >= 8 ? 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400'
                    : currentRecord.score >= 6 ? 'bg-yellow-50 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400'
                    : 'bg-gray-50 text-gray-500 dark:bg-gray-800'
                  }`}>
                    评分 {currentRecord.score}
                  </span>
                )}
                {!editMode && !deleteConfirm && (
                  <>
                    {enableReview && reviewType && (
                      <button
                        onClick={() => handleReview(false)}
                        disabled={reviewing}
                        className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-orange-500 disabled:opacity-40"
                        title={`让${reviewType === 'hot_money' ? '短线' : reviewType === 'midline' ? '中线' : '长线'}专家复盘此报告`}
                      >
                        <RotateCcw className={`h-3.5 w-3.5 ${reviewing ? 'animate-spin' : ''}`} />
                      </button>
                    )}
                    <button
                      onClick={() => setShowRawText(!showRawText)}
                      className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-purple-500"
                      title={showRawText ? '渲染视图' : '源文本'}
                    >
                      {showRawText ? <BookOpen className="h-3.5 w-3.5" /> : <Code className="h-3.5 w-3.5" />}
                    </button>
                    <button
                      onClick={handleEditStart}
                      className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-blue-500"
                      title="编辑"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </button>
                    <button
                      onClick={() => setDeleteConfirm(true)}
                      className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 hover:text-red-500"
                      title="删除"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </>
                )}
              </div>
            </div>

            {/* 删除确认 */}
            {deleteConfirm && !editMode && (
              <div className="flex items-center gap-2 py-1">
                <span className="text-xs text-red-500">确定删除这条记录？</span>
                <button
                  onClick={handleDelete}
                  disabled={deleting}
                  className="text-xs px-2 py-0.5 bg-red-500 text-white rounded hover:bg-red-600 disabled:opacity-50"
                >
                  {deleting ? '删除中...' : '确定'}
                </button>
                <button
                  onClick={() => setDeleteConfirm(false)}
                  className="text-xs px-2 py-0.5 border border-gray-300 dark:border-gray-600 rounded hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  取消
                </button>
              </div>
            )}

            {/* 编辑模式 */}
            {editMode ? (
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400">评分（可选）</span>
                  <input
                    type="number"
                    min={0}
                    max={10}
                    step={0.1}
                    value={editScore}
                    onChange={(e) => setEditScore(e.target.value)}
                    placeholder="0-10"
                    className="w-20 h-7 text-xs border border-gray-200 dark:border-gray-600 rounded px-2 bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200"
                  />
                </div>
                <textarea
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  rows={6}
                  className="w-full text-sm border border-gray-200 dark:border-gray-600 rounded-lg p-3 resize-none bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                {editMsg && (
                  <p className={`text-xs ${editMsg.type === 'success' ? 'text-green-600' : 'text-red-500'}`}>
                    {editMsg.text}
                  </p>
                )}
                <div className="flex items-center gap-2">
                  <Button
                    onClick={handleEditSave}
                    disabled={editSaving || !editText.trim()}
                    size="sm"
                    className="gap-1.5"
                  >
                    <Save className="h-3.5 w-3.5" />
                    {editSaving ? '保存中...' : '保存修改'}
                  </Button>
                  <Button
                    onClick={handleEditCancel}
                    disabled={editSaving}
                    size="sm"
                    variant="outline"
                    className="gap-1.5"
                  >
                    <X className="h-3.5 w-3.5" />
                    取消
                  </Button>
                </div>
              </div>
            ) : showRawText ? (
              <pre className="whitespace-pre-wrap text-sm font-mono break-words text-gray-800 dark:text-gray-200 leading-relaxed">
                {currentRecord.analysis_text}
              </pre>
            ) : (
              <AnalysisContent text={currentRecord.analysis_text} analysisType={analysisType} />
            )}
          </div>
        ) : (
          <div className="text-center py-6 text-gray-400 text-sm border border-dashed border-gray-200 dark:border-gray-700 rounded-lg">
            暂无保存记录，点击上方按钮生成分析
          </div>
        )}
      </div>

      {/* 提示词（可折叠，复制按钮在内） */}
      <div className="border-t border-gray-100 dark:border-gray-700 pt-3">
        <div className="flex items-center justify-between">
          <button
            onClick={() => setPromptExpanded((v) => !v)}
            className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            {promptExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            提示词
          </button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleCopy}
            disabled={promptLoading || !promptContent}
            className="gap-1.5 h-7 text-xs"
          >
            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
            {copied ? '已复制' : '复制提示词'}
          </Button>
        </div>
        {promptExpanded && (
          <div className="mt-2">
            {promptLoading ? (
              <div className="text-center py-4 text-gray-400 text-sm">加载中...</div>
            ) : (
              <pre className="whitespace-pre-wrap text-xs text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-gray-800 rounded-lg p-3 leading-relaxed font-mono max-h-60 overflow-y-auto">
                {promptContent}
              </pre>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

// ── 主弹窗组件 ──────────────────────────────────────────────────

export function HotMoneyViewDialog({
  open, onClose, stockName, stockCode, tsCode,
  promptContent, promptLoading,
  dataCollectionPrompt, dataCollectionPromptLoading,
  midlinePrompt, midlinePromptLoading,
  longtermPrompt, longtermPromptLoading,
  cioPrompt, cioPromptLoading,
  onSaved,
}: HotMoneyViewDialogProps) {
  const [multiGenerating, setMultiGenerating] = useState(false)
  const [multiMsg, setMultiMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [activeTab, setActiveTab] = useState('hot_money')

  // 弹窗关闭时重置状态
  useEffect(() => {
    if (!open) {
      setMultiGenerating(false)
      setMultiMsg(null)
      setActiveTab('hot_money')
    }
  }, [open])

  const handleReviewCreated = useCallback((reviewType: 'hot_money' | 'midline' | 'longterm') => {
    setRefreshKey((k) => k + 1)
    const targetTab = reviewType === 'hot_money' ? 'hot_money_review'
      : reviewType === 'midline' ? 'midline_review'
      : 'longterm_review'
    setActiveTab(targetTab)
    onSaved?.()
  }, [onSaved])

  const handleMultiGenerate = useCallback(async () => {
    if (!tsCode || !stockName || !stockCode) return
    setMultiGenerating(true)
    setMultiMsg(null)
    try {
      const res = await apiClient.generateMultiAnalysis({
        ts_code: tsCode,
        stock_name: stockName,
        stock_code: stockCode,
        analysis_types: ['hot_money_view', 'midline_industry_expert', 'longterm_value_watcher'],
        include_cio: true,
      })
      if (res?.code === 200) {
        const data = res.data
        const count = data?.expert_count ?? 0
        const errors = data?.errors?.length ?? 0
        const time = data?.total_generation_time ?? 0
        setMultiMsg({
          text: `${count} 个专家分析完成（${time}s）` + (errors ? `，${errors} 个失败` : ''),
          type: errors ? 'error' : 'success',
        })
        setRefreshKey((k) => k + 1)
        onSaved?.()
      } else {
        setMultiMsg({ text: res?.message || '一键分析失败', type: 'error' })
      }
    } catch (e: any) {
      setMultiMsg({ text: e?.response?.data?.message || '一键分析失败', type: 'error' })
    } finally {
      setMultiGenerating(false)
    }
  }, [tsCode, stockName, stockCode, onSaved])

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-[720px] max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>AI 分析：{stockName}（{stockCode}）</DialogTitle>
          <DialogDescription>保存并回顾每次 AI 分析结果</DialogDescription>
        </DialogHeader>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col min-h-0">
          <TabsList className="shrink-0 w-full grid grid-cols-8 text-xs">
            <TabsTrigger value="hot_money" className="text-xs px-1">游资</TabsTrigger>
            <TabsTrigger value="hot_money_review" className="text-xs px-1">游资复盘</TabsTrigger>
            <TabsTrigger value="midline" className="text-xs px-1">中线</TabsTrigger>
            <TabsTrigger value="midline_review" className="text-xs px-1">中线复盘</TabsTrigger>
            <TabsTrigger value="longterm" className="text-xs px-1">价值</TabsTrigger>
            <TabsTrigger value="longterm_review" className="text-xs px-1">价值复盘</TabsTrigger>
            <TabsTrigger value="cio" className="text-xs px-1">CIO</TabsTrigger>
            <TabsTrigger value="data_collection" className="text-xs px-1">数据</TabsTrigger>
          </TabsList>

          <div className="flex-1 overflow-y-auto min-h-0 mt-4 pr-1">
            <TabsContent value="hot_money" className="mt-0">
              <AnalysisTab
                tsCode={tsCode}
                stockName={stockName}
                stockCode={stockCode}
                analysisType="hot_money_view"
                templateKey="top_speculative_investor_v1"
                promptContent={promptContent}
                promptLoading={promptLoading}
                open={open}
                refreshKey={refreshKey}
                onSaved={onSaved}
                enableReview
                reviewType="hot_money"
                onReviewCreated={handleReviewCreated}
              />
            </TabsContent>

            <TabsContent value="hot_money_review" className="mt-0">
              <AnalysisTab
                tsCode={tsCode}
                stockName={stockName}
                stockCode={stockCode}
                analysisType="hot_money_review"
                promptContent="复盘提示词随每次请求动态生成（包含原报告 JSON + 最新市场数据）。请在『游资』Tab 点击记录旁的复盘按钮触发。"
                promptLoading={false}
                open={open}
                refreshKey={refreshKey}
                onSaved={onSaved}
              />
            </TabsContent>

            <TabsContent value="midline_review" className="mt-0">
              <AnalysisTab
                tsCode={tsCode}
                stockName={stockName}
                stockCode={stockCode}
                analysisType="midline_review"
                promptContent="复盘提示词随每次请求动态生成（包含原报告 JSON + 最新市场数据）。请在『中线』Tab 点击记录旁的复盘按钮触发。建议原报告发布 ≥20 天后复盘。"
                promptLoading={false}
                open={open}
                refreshKey={refreshKey}
                onSaved={onSaved}
              />
            </TabsContent>

            <TabsContent value="longterm_review" className="mt-0">
              <AnalysisTab
                tsCode={tsCode}
                stockName={stockName}
                stockCode={stockCode}
                analysisType="longterm_review"
                promptContent="复盘提示词随每次请求动态生成（包含原报告 JSON + 最新市场数据）。请在『价值』Tab 点击记录旁的复盘按钮触发。建议原报告发布 ≥90 天后复盘。"
                promptLoading={false}
                open={open}
                refreshKey={refreshKey}
                onSaved={onSaved}
              />
            </TabsContent>

            <TabsContent value="data_collection" className="mt-0">
              <AnalysisTab
                tsCode={tsCode}
                stockName={stockName}
                stockCode={stockCode}
                analysisType="stock_data_collection"
                promptContent={dataCollectionPrompt}
                promptLoading={dataCollectionPromptLoading}
                open={open}
                refreshKey={refreshKey}
                onSaved={onSaved}
              />
            </TabsContent>

            <TabsContent value="midline" className="mt-0">
              <AnalysisTab
                tsCode={tsCode}
                stockName={stockName}
                stockCode={stockCode}
                analysisType="midline_industry_expert"
                templateKey="midline_industry_expert_v1"
                promptContent={midlinePrompt}
                promptLoading={midlinePromptLoading}
                open={open}
                refreshKey={refreshKey}
                onSaved={onSaved}
                enableReview
                reviewType="midline"
                onReviewCreated={handleReviewCreated}
              />
            </TabsContent>

            <TabsContent value="longterm" className="mt-0">
              <AnalysisTab
                tsCode={tsCode}
                stockName={stockName}
                stockCode={stockCode}
                analysisType="longterm_value_watcher"
                templateKey="longterm_value_watcher_v1"
                promptContent={longtermPrompt}
                promptLoading={longtermPromptLoading}
                open={open}
                refreshKey={refreshKey}
                onSaved={onSaved}
                enableReview
                reviewType="longterm"
                onReviewCreated={handleReviewCreated}
              />
            </TabsContent>

            <TabsContent value="cio" className="mt-0">
              <AnalysisTab
                tsCode={tsCode}
                stockName={stockName}
                stockCode={stockCode}
                analysisType="cio_directive"
                templateKey="cio_directive_v1"
                promptContent={cioPrompt}
                promptLoading={cioPromptLoading}
                open={open}
                refreshKey={refreshKey}
                onSaved={onSaved}
              />
            </TabsContent>
          </div>
        </Tabs>

        <DialogFooter className="mt-4">
          {multiMsg && (
            <p className={`text-xs mr-auto self-center ${multiMsg.type === 'success' ? 'text-green-600' : 'text-red-500'}`}>
              {multiMsg.text}
            </p>
          )}
          <Button
            onClick={handleMultiGenerate}
            disabled={multiGenerating}
            size="sm"
            className="gap-1.5"
          >
            <Sparkles className="h-3.5 w-3.5" />
            {multiGenerating ? '分析中...' : '一键分析'}
          </Button>
          <Button variant="outline" onClick={onClose}>关闭</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
