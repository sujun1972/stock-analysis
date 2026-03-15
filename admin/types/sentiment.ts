/**
 * 市场情绪数据类型定义
 */

// 交易日历
export interface TradingCalendar {
  trade_date: string
  is_trading_day: boolean
  exchange: string
  day_type?: string
  holiday_name?: string
  created_at?: string
}

// 大盘情绪
export interface MarketSentiment {
  id: number
  trade_date: string

  // 上证指数
  sh_index_code: string
  sh_index_close: number
  sh_index_change: number
  sh_index_amplitude?: number
  sh_index_volume?: number
  sh_index_amount?: number

  // 深成指数
  sz_index_code: string
  sz_index_close: number
  sz_index_change: number
  sz_index_amplitude?: number
  sz_index_volume?: number
  sz_index_amount?: number

  // 创业板指数
  cyb_index_code: string
  cyb_index_close: number
  cyb_index_change: number
  cyb_index_amplitude?: number
  cyb_index_volume?: number
  cyb_index_amount?: number

  // 市场汇总
  total_volume: number
  total_amount: number

  // 涨停板数据（来自联表查询）
  limit_up_count?: number
  limit_down_count?: number
  blast_rate?: number
  max_continuous_days?: number

  created_at?: string
  updated_at?: string
}

// 涨停股票
export interface LimitUpStock {
  code: string
  name: string
  days: number  // 连板天数
  reason?: string
  first_limit_time?: string
}

// 炸板股票
export interface BlastStock {
  code: string
  name: string
  blast_times: number
  final_change?: number
}

// 涨停板池
export interface LimitUpPool {
  id: number
  trade_date: string

  // 涨跌停统计
  limit_up_count: number
  limit_down_count: number

  // 炸板数据
  blast_count: number
  blast_rate: number

  // 连板数据
  max_continuous_days: number
  max_continuous_count: number
  continuous_ladder: Record<string, number>  // {"2连板": 15, "3连板": 8, ...}

  // 股票列表
  limit_up_stocks: LimitUpStock[]
  blast_stocks: BlastStock[]

  // 市场统计
  total_stocks?: number
  rise_count?: number
  fall_count?: number
  rise_fall_ratio?: number

  created_at?: string
  updated_at?: string
}

// 龙虎榜席位
export interface Seat {
  rank: number
  name: string
  amount: number
}

// 龙虎榜记录
export interface DragonTigerRecord {
  id: number
  trade_date: string
  stock_code: string
  stock_name: string

  // 上榜原因
  reason: string
  reason_type: string

  // 股票行情
  close_price: number
  price_change: number
  turnover_rate: number

  // 买卖数据
  buy_amount: number
  sell_amount: number
  net_amount: number

  // 席位信息
  top_buyers: Seat[]
  top_sellers: Seat[]

  // 机构信息
  has_institution: boolean
  institution_count: number

  // 营业部统计
  dept_buy_count: number
  dept_sell_count: number

  created_at?: string
  updated_at?: string
}

// 分页响应
export interface PaginatedSentimentResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// 情绪统计
export interface SentimentStatistics {
  period: {
    start_date: string
    end_date: string
  }
  limit_up_stats: {
    avg_blast_rate: number
    avg_limit_up: number
    max_continuous: number
  }
  dragon_tiger_stats: {
    total_records: number
    unique_stocks: number
    institution_records: number
  }
  trend: {
    date: string
    limit_up: number
    limit_down: number
    blast_rate: number
  }[]
}

// ==================== 情绪周期类型（新增）====================
// 注意: ApiResponse 类型已移至 types/api.ts，请从 '@/types' 导入

// 情绪周期数据
export interface SentimentCycle {
  trade_date: string
  cycle_stage: 'freezing' | 'starting' | 'fermenting' | 'retreating'
  cycle_stage_cn: '冰点' | '启动' | '发酵' | '退潮'
  confidence_score: number

  // 计算指标
  limit_up_count: number
  limit_down_count: number
  limit_ratio: number
  blast_count: number
  blast_rate: number
  max_continuous_days: number
  max_continuous_count: number
  continuous_growth_rate: number

  // 核心指数
  money_making_index: number  // 0-100
  sentiment_score: number  // 0-100

  // 阶段统计
  stage_duration_days: number
  previous_stage?: string
  stage_change_date?: string

  // 市场统计
  total_stocks: number
  rise_count: number
  fall_count: number
  rise_fall_ratio: number
  total_amount: number
  amount_change_rate: number

  // 详细分析
  analysis_result?: {
    stage_reason?: string
    key_indicators?: {
      limit_up_strength?: string
      continuous_height?: string
      blast_pressure?: string
      money_making_effect?: string
    }
    market_characteristics?: string[]
    risk_warning?: string
  }
}

// 情绪周期趋势点
export interface SentimentCycleTrendPoint {
  date: string
  stage: string
  money_making_index: number
  sentiment_score: number
  limit_up_count: number
  max_continuous_days: number
}

// 情绪周期统计
export interface SentimentCycleStatistics {
  stage_distribution: Array<{
    stage: string
    days: number
    avg_money_making_index: number
    avg_sentiment_score: number
  }>
  overall_stats: {
    avg_money_making_index: number
    avg_sentiment_score: number
    avg_limit_up_count: number
    avg_continuous_days: number
  }
}

// ==================== 游资相关类型（新增）====================

// 游资席位
export interface HotMoneySeat {
  seat_name: string
  seat_type: 'top_tier' | 'famous' | 'retail_base' | 'institution' | 'unknown'
  seat_label: string
  city?: string
  broker?: string
  branch_office?: string

  // 统计信息
  appearance_count: number
  total_buy_amount: number
  total_sell_amount: number
  net_amount: number
  win_rate?: number
  avg_hold_days?: number

  // 席位特征
  trade_style?: string
  specialty_sectors?: string[]
  tags?: string[]
  last_appearance_date?: string
  description?: string

  // 活跃度（排行用）
  activity_score?: number
  rank?: number
}

// 机构净买入个股
export interface InstitutionTopStock {
  stock_code: string
  stock_name: string
  close_price: number
  price_change: number
  net_buy_amount: number
  institution_count: number
  institution_seats: Array<{
    seat_name: string
    buy_amount: number
    rank: number
  }>
  reason: string
}

// 游资打板个股
export interface HotMoneyLimitUpStock {
  stock_code: string
  stock_name: string
  close_price: number
  price_change: number
  is_limit_up: boolean
  hot_money_count: number
  total_buy_amount: number
  hot_money_seats: Array<{
    seat_name: string
    seat_label: string
    buy_amount: number
    rank: number
  }>
  reason: string
}

// 每日综合分析报告
export interface DailySentimentAnalysis {
  trade_date: string
  summary: {
    cycle_stage: string
    money_making_index: number
    sentiment_score: number
    confidence: number
    stage_duration: number
  }
  institution: {
    top_stocks: InstitutionTopStock[]
    net_buy: number
    stock_count: number
  }
  hot_money: {
    top_tier_stocks: HotMoneyLimitUpStock[]
    total_buy: number
    appearance_count: number
  }
  retail_base: {
    stocks: HotMoneyLimitUpStock[]
    total_buy: number
  }
  activity: {
    top_tier_count: number
    top_tier_buy_amount: number
    institution_count: number
    institution_buy_amount: number
    retail_base_count: number
    famous_count: number
    total_records: number
  }
  characteristics: {
    cycle_stage: string
    money_making_index: number
    sentiment_score: number
    confidence: number
    features: string[]
  }
  analysis_detail: any
}
