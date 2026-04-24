// 概念板块类型
export interface Concept {
  id: number
  code: string
  name: string
  source: string
  description?: string
  stock_count: number
  created_at?: string
  updated_at?: string
}

// 股票信息类型
export interface StockInfo {
  code: string
  name: string
  market: string
  list_date?: string
  delist_date?: string
  industry?: string
  area?: string
  status?: string
  // Tushare 扩展字段
  ts_code?: string
  fullname?: string
  enname?: string
  cnspell?: string
  exchange?: string
  curr_type?: string
  list_status?: string
  is_hs?: string
  act_name?: string
  act_ent_type?: string
  // 实时行情信息
  latest_price?: number
  pct_change?: number
  change_amount?: number
  volume?: number
  amount?: number
  turnover?: number
  trade_time?: string
  // 概念标签
  concepts?: Concept[]
  // AI分析摘要（include_analysis=true 时由后端注入）
  /** @deprecated 旧字段，由 latest_analysis_hot_money 替代 */
  latest_analysis?: {
    id: number
    score: number | null
    version: number
    created_at: string
  } | null
  latest_analysis_hot_money?: {
    id: number
    score: number | null
    version: number
    created_at: string
  } | null
  latest_analysis_midline?: {
    id: number
    score: number | null
    version: number
    created_at: string
  } | null
  latest_analysis_longterm?: {
    id: number
    score: number | null
    version: number
    created_at: string
  } | null
  latest_analysis_cio?: {
    id: number
    score: number | null
    version: number
    created_at: string
    followup_triggers?: CioFollowupTriggers | null
  } | null
  // 价值度量（魔法公式 ROC/EY + 格雷厄姆内在价值）；数据不足时字段为 null
  value_metrics?: {
    roc?: number | null                 // 资本收益率（小数，0.25 = 25%）
    earnings_yield?: number | null      // 收益率（小数）
    intrinsic_value?: number | null     // 格雷厄姆内在价值（元/股）
    intrinsic_margin?: number | null    // 安全边际 = 内在价值/当前价 - 1
    g_rate?: number | null              // 用于 IV 的年化增长率（封顶 15%）
    g_source?: 'analyst' | 'history' | 'na' | null
  } | null
}

// CIO 复查触发器：由 CIO 综合分析输出，驱动事件/价位触发下一轮复查
export interface CioTimeTrigger {
  type?: 'event' | 'fixed_date'
  event_ref?: string        // 事件类型关键词（如 quarterly_earnings / lockup_expiry / announcement）
  expected_date?: string    // YYYY-MM-DD
  days_from_today?: number
  reason?: string           // 为什么要等这个事件
  priority?: 'high' | 'medium' | 'low'
}

export interface CioPriceTrigger {
  direction: 'break_up' | 'break_down'
  price?: number            // 触发价位（数字；无有效价位时省略）
  price_basis?: string      // 锚定依据（MA/布林/前高前低/缺口等）
  action_hint?: string      // 触发后建议动作
  valid_until?: string      // YYYY-MM-DD
  priority?: 'high' | 'medium' | 'low'
}

export interface CioFollowupTriggers {
  time_triggers?: CioTimeTrigger[]
  price_triggers?: CioPriceTrigger[]
  review_horizon_days?: number | null
}

// 行情面板数据类型（stock_realtime + daily_basic 合并）
export interface StockQuotePanel {
  // 实时行情
  latest_price?: number
  open?: number
  high?: number
  low?: number
  pre_close?: number
  pct_change?: number
  change_amount?: number
  volume?: number
  amount?: number
  amplitude?: number
  turnover?: number
  trade_time?: string
  // 每日估值（daily_basic，收盘后更新）
  daily_date?: string
  pe?: number
  pe_ttm?: number
  pb?: number
  ps?: number
  ps_ttm?: number
  volume_ratio?: number
  turnover_rate?: number
  turnover_rate_f?: number
  dv_ratio?: number
  dv_ttm?: number
  total_share?: number   // 万股
  float_share?: number   // 万股
  free_share?: number    // 万股
  total_mv?: number      // 亿元
  circ_mv?: number       // 亿元
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

// 分时数据类型
export interface MinuteData {
  trade_time: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount?: number
  pct_change?: number
  change_amount?: number
}

// 技术指标数据类型
export interface TechnicalIndicator {
  date: string
  [key: string]: number | string
}

// 特征数据类型（包含OHLCV和技术指标）
export interface FeatureData {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  // 技术指标（可选）
  MA5?: number | null
  MA20?: number | null
  MA60?: number | null
  MACD?: number | null
  MACD_SIGNAL?: number | null
  MACD_HIST?: number | null
  KDJ_K?: number | null
  KDJ_D?: number | null
  KDJ_J?: number | null
  RSI6?: number | null
  RSI12?: number | null
  RSI24?: number | null
  BOLL_UPPER?: number | null
  BOLL_MIDDLE?: number | null
  BOLL_LOWER?: number | null
  [key: string]: number | string | null | undefined
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

// 用户股票列表（自选股）
export interface StockList {
  id: number
  name: string
  description?: string | null
  stock_count: number
  created_at: string
  updated_at: string
}

export interface StockListItem {
  ts_code: string
  code: string
  name: string
  market: string
  industry: string
  latest_price: number | null
  pct_change: number | null
  change_amount: number | null
  added_at: string
}

// API响应类型（匹配后端实际格式）
export interface ApiResponse<T = unknown> {
  code: number
  data: T
  message?: string
  error?: string
  // 兼容旧代码中使用 success 的写法
  success?: boolean
}

// AI分析记录类型
export interface StockAnalysisRecord {
  id: number
  ts_code: string
  analysis_type: string
  analysis_text: string
  score: number | null
  prompt_text: string | null
  ai_provider: string | null
  ai_model: string | null
  version: number
  created_at: string
}

// 分页响应类型（匹配后端 v2.0 格式）
export interface PaginatedResponse<T> {
  items: T[]           // 数据列表
  total: number        // 总记录数
  page: number         // 当前页码
  page_size: number    // 每页大小
  total_pages: number  // 总页数
}
