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

// API响应
export interface ApiResponse<T = any> {
  code: number
  message: string
  data?: T
}
