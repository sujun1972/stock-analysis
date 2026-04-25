// 4 个专家的展示元信息（图标 / 中文名 / 副标题 / 身份色 token / analysis_type / 模板 key）
// 任何新增/变更都改这一个数组——卡 ②/③/④ 自动同步。

import { Brain, Flame, TrendingUp, Gem, type LucideIcon } from 'lucide-react'

export interface ExpertMeta {
  /** 内部 key（与父组件 Tab value 对齐） */
  key: 'cio' | 'hot_money' | 'midline' | 'longterm'
  /** 后端 stock_ai_analysis.analysis_type 值 */
  analysisType: 'cio_directive' | 'hot_money_view' | 'midline_industry_expert' | 'longterm_value_watcher'
  /** Prompt 模板 key（用于 build_stock_prompt） */
  templateKey: string
  /** 中文名（卡片头） */
  label: string
  /** 副标题（时间窗 / 风格） */
  subtitle: string
  /** 图标 */
  icon: LucideIcon
  /** 身份色 token 名（与 globals.css `--expert-*` 一一对应） */
  colorVar: string
  /** Tailwind border 类（用于左 border 色条） */
  borderClass: string
}

export const EXPERTS: ExpertMeta[] = [
  {
    key: 'cio',
    analysisType: 'cio_directive',
    templateKey: 'cio_directive_v1',
    label: 'CIO 综合',
    subtitle: '首席投资官',
    icon: Brain,
    colorVar: '--expert-cio',
    borderClass: 'border-l-expert-cio',
  },
  {
    key: 'hot_money',
    analysisType: 'hot_money_view',
    templateKey: 'top_speculative_investor_v1',
    label: '游资',
    subtitle: '短线 1-5 日',
    icon: Flame,
    colorVar: '--expert-hot-money',
    borderClass: 'border-l-expert-hot-money',
  },
  {
    key: 'midline',
    analysisType: 'midline_industry_expert',
    templateKey: 'midline_industry_expert_v1',
    label: '中线',
    subtitle: '产业 1-3 月',
    icon: TrendingUp,
    colorVar: '--expert-midline',
    borderClass: 'border-l-expert-midline',
  },
  {
    key: 'longterm',
    analysisType: 'longterm_value_watcher',
    templateKey: 'longterm_value_watcher_v1',
    label: '价值',
    subtitle: '长线 3-5 年',
    icon: Gem,
    colorVar: '--expert-longterm',
    borderClass: 'border-l-expert-longterm',
  },
]

export const EXPERT_BY_KEY: Record<ExpertMeta['key'], ExpertMeta> = Object.fromEntries(
  EXPERTS.map((e) => [e.key, e]),
) as Record<ExpertMeta['key'], ExpertMeta>

export const EXPERT_BY_ANALYSIS_TYPE: Record<string, ExpertMeta> = Object.fromEntries(
  EXPERTS.map((e) => [e.analysisType, e]),
)

/** 评分文本色阶：≥8 紫 / ≥6 金 / ≥4 蓝 / 其余灰，对应 globals.css 的 score-* token。
 *  禁止借用 positive/negative（行情红绿）—— 评分高低不是涨跌，会与 K 线红涨绿跌冲突。*/
export function scoreToneClass(s?: number | null): string {
  if (s == null) return 'text-gray-400 dark:text-gray-500'
  if (s >= 8) return 'text-score-high'
  if (s >= 6) return 'text-score-mid'
  if (s >= 4) return 'text-score-low'
  return 'text-muted-foreground'
}

/** 安全 JSON 解析：失败返回 null（不抛错） */
export function safeParseJSON(text?: string | null): Record<string, any> | null {
  if (!text || typeof text !== 'string') return null
  try {
    const d = JSON.parse(text)
    if (d && typeof d === 'object' && !Array.isArray(d)) return d
  } catch {
    // ignore
  }
  return null
}

/** 提取 final_score.score（兜底 comprehensive_score / score） */
export function extractScore(parsed: Record<string, any> | null): number | null {
  if (!parsed) return null
  const fs = parsed.final_score
  const raw = fs?.score ?? parsed.comprehensive_score ?? parsed.score
  if (raw == null) return null
  const n = Number(raw)
  return Number.isFinite(n) ? n : null
}

export function extractKeyQuote(parsed: Record<string, any> | null): string | null {
  const q = parsed?.final_score?.key_quote
  return typeof q === 'string' && q.trim() ? q.trim() : null
}

export function extractRating(parsed: Record<string, any> | null): string | null {
  const r = parsed?.final_score?.rating ?? parsed?.rating_and_action?.rating
  return typeof r === 'string' && r.trim() ? r.trim() : null
}

export function extractBullBearCount(parsed: Record<string, any> | null): { bull: number; bear: number } {
  const fs = parsed?.final_score
  const bull = Array.isArray(fs?.bull_factors) ? fs.bull_factors.length
    : Array.isArray(fs?.pros) ? fs.pros.length
    : 0
  const bear = Array.isArray(fs?.bear_factors) ? fs.bear_factors.length
    : Array.isArray(fs?.cons) ? fs.cons.length
    : 0
  return { bull, bear }
}
