/**
 * 盘前预期管理系统类型定义
 *
 * 包含所有前端需要的数据类型
 */

// ========== 隔夜外盘数据 ==========

export interface MarketIndicator {
  close: number
  change: number
}

export interface OvernightData {
  trade_date: string
  a50: MarketIndicator
  china_concept: MarketIndicator
  wti_crude: MarketIndicator
  comex_gold: MarketIndicator
  lme_copper: MarketIndicator
  usdcnh: MarketIndicator
  sp500: MarketIndicator
  nasdaq: MarketIndicator
  dow: MarketIndicator
  fetch_time: string | null
}

// ========== 盘前核心新闻 ==========

export type NewsImportanceLevel = 'critical' | 'high' | 'medium'

export interface PremarketNews {
  id: number
  trade_date: string
  news_time: string
  source: string
  title: string
  content: string
  keywords: string[]
  importance_level: NewsImportanceLevel
  created_at: string | null
}

export interface NewsListResponse {
  count: number
  news: PremarketNews[]
}

// ========== AI碰撞分析结果 ==========

export interface MacroTone {
  direction: string  // '高开', '低开', '平开'
  confidence: string  // 置信度百分比
  a50_impact: string  // A50的具体影响分析
  reasoning: string  // 综合外盘判断
}

export interface AffectedStock {
  code: string
  name: string
  reason: string
}

export interface HoldingsAlert {
  has_risk: boolean
  affected_sectors: string[]
  affected_stocks: AffectedStock[]
  actions: string
}

export interface PlanAdjustmentItem {
  stock: string
  reason: string
}

export interface PlanAdjustment {
  cancel_buy: PlanAdjustmentItem[]
  early_stop_loss: PlanAdjustmentItem[]
  keep_plan: string
  reasoning: string
}

export interface FocusStock {
  code: string
  name: string
  reason: string
}

export interface AuctionConditions {
  participate_conditions: string
  avoid_conditions: string
}

export interface AuctionFocus {
  stocks: FocusStock[]
  conditions: AuctionConditions
  actions: string
}

export interface CollisionAnalysis {
  trade_date: string
  macro_tone: MacroTone | null
  holdings_alert: HoldingsAlert | null
  plan_adjustment: PlanAdjustment | null
  auction_focus: AuctionFocus | null
  action_command: string
  ai_provider: string
  ai_model: string
  tokens_used: number
  generation_time: number
  status: 'success' | 'failed'
  created_at: string | null
}

// ========== 历史记录 ==========

export interface AnalysisHistory {
  trade_date: string
  action_command: string
  status: 'success' | 'failed'
  ai_provider: string
  ai_model: string
  tokens_used: number
  generation_time: number
  created_at: string | null
}

// ========== API响应类型 ==========

export interface ApiResponse<T> {
  code: number
  message: string
  data: T | null
}

export interface SyncResult {
  trade_date: string
  is_trading_day: boolean
  synced_tables: string[]
  details: {
    overnight_data?: {
      a50_change: number
      china_concept_change: number
      wti_crude_change: number
    }
    news?: {
      count: number
      critical_count: number
    }
  }
}

export interface GenerateAnalysisResult {
  success: boolean
  trade_date: string
  analysis_result?: CollisionAnalysis
  action_command?: string
  ai_provider?: string
  ai_model?: string
  tokens_used?: number
  generation_time?: number
  error?: string
}
