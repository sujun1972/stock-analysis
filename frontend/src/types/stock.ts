// 股票信息类型
export interface StockInfo {
  code: string
  name: string
  market: string
  list_date?: string
  industry?: string
  area?: string
  status?: string
  // 实时行情信息
  latest_price?: number
  pct_change?: number
  change_amount?: number
  volume?: number
  amount?: number
  turnover?: number
  trade_time?: string
}

// 股票日线数据类型
export interface StockDaily {
  code: string
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount?: number
  change?: number
  pct_change?: number
}

// 技术指标数据类型
export interface TechnicalIndicator {
  date: string
  [key: string]: number | string
}

// 特征数据类型
export interface FeatureData {
  code: string
  date: string
  feature_type: string
  feature_data: Record<string, number>
}

// 模型预测结果类型
export interface Prediction {
  code: string
  date: string
  model_name: string
  predicted_return: number
  confidence?: number
}

// 回测结果类型
export interface BacktestResult {
  task_id: string
  strategy: string
  start_date: string
  end_date: string
  metrics: {
    total_return: number
    annual_return: number
    sharpe_ratio: number
    max_drawdown: number
    win_rate: number
    total_trades: number
  }
  equity_curve: Array<{
    date: string
    value: number
  }>
}

// API响应类型
export interface ApiResponse<T> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

// 分页响应类型
export interface PaginatedResponse<T> {
  total: number
  skip: number
  limit: number
  data: T[]
}
