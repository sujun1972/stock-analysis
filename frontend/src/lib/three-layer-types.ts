/**
 * 三层架构API类型定义
 * 对应后端 /api/three-layer 接口
 */

/**
 * 参数定义
 */
export interface ParameterDef {
  name: string
  label: string
  type: 'integer' | 'float' | 'boolean' | 'select' | 'string'
  default: any
  min_value?: number
  max_value?: number
  step?: number
  description?: string
  options?: Array<{ value: string; label: string }>
}

/**
 * 选股器信息
 */
export interface SelectorInfo {
  id: string
  name: string
  description: string
  version: string
  parameters: ParameterDef[]
  category?: string
  risk_level?: string
}

/**
 * 入场策略信息
 */
export interface EntryInfo {
  id: string
  name: string
  description: string
  version: string
  parameters: ParameterDef[]
  category?: string
}

/**
 * 退出策略信息
 */
export interface ExitInfo {
  id: string
  name: string
  description: string
  version: string
  parameters: ParameterDef[]
  category?: string
}

/**
 * 策略配置
 */
export interface StrategyConfig {
  selector_id: string
  selector_params: Record<string, any>
  entry_id: string
  entry_params: Record<string, any>
  exit_id: string
  exit_params: Record<string, any>
  stock_codes: string[]
  start_date: string
  end_date: string
  rebalance_freq?: 'D' | 'W' | 'M'
  initial_capital?: number
}

/**
 * 验证结果
 */
export interface ValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
}

/**
 * 交易记录
 */
export interface Trade {
  date: string
  action: 'buy' | 'sell'
  stock_code: string
  price: number
  shares: number
  amount?: number
  reason?: string
}

/**
 * 每日组合价值
 */
export interface DailyPortfolio {
  date: string
  value: number
  cash?: number
  positions_value?: number
}

/**
 * 回测结果数据
 */
export interface BacktestResultData {
  total_return: number
  annualized_return: number
  sharpe_ratio: number
  max_drawdown: number
  win_rate: number
  total_trades: number
  daily_portfolio: DailyPortfolio[]
  trades: Trade[]
  // 可选的额外字段
  sortino_ratio?: number
  calmar_ratio?: number
  volatility?: number
  benchmark_return?: number
  alpha?: number
  beta?: number
}

/**
 * 回测结果
 */
export interface BacktestResult {
  status: 'success' | 'error' | 'running'
  message?: string
  data?: BacktestResultData
  error?: string
}

/**
 * API响应基础结构
 */
export interface ApiResponse<T> {
  status: string
  message?: string
  data?: T
}

/**
 * 三层架构组件列表响应
 */
export interface ComponentListResponse {
  selectors: SelectorInfo[]
  entries: EntryInfo[]
  exits: ExitInfo[]
}
