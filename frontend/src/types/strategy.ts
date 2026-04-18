// ========== 统一策略类型定义 (V2.0) ==========

/**
 * 策略类别定义
 * 与后端 backend/app/schemas/strategy.py 中的验证规则保持一致
 * 共10种预定义类别，防止用户输入无效类别导致验证失败
 */
export const STRATEGY_CATEGORIES = [
  { value: 'momentum', label: '动量策略', description: '基于价格动量的策略' },
  { value: 'reversal', label: '反转策略', description: '基于价格反转的策略' },
  { value: 'mean_reversion', label: '均值回归策略', description: '基于均值回归的策略' },
  { value: 'factor', label: '因子策略', description: '基于多因子的策略' },
  { value: 'ml', label: '机器学习策略', description: '基于机器学习模型的策略' },
  { value: 'arbitrage', label: '套利策略', description: '基于套利机会的策略' },
  { value: 'hybrid', label: '混合策略', description: '结合多种策略类型' },
  { value: 'trend_following', label: '趋势跟踪策略', description: '跟踪市场趋势的策略' },
  { value: 'breakout', label: '突破策略', description: '基于价格突破的策略' },
  { value: 'statistical', label: '统计套利策略', description: '基于统计分析的策略' }
] as const

/**
 * 统一策略接口
 * 所有策略（内置/AI/自定义）都使用这个统一的接口
 */
export interface Strategy {
  // 主键和标识
  id: number
  name: string
  display_name: string

  // 核心代码
  code: string
  code_hash: string
  class_name: string

  // 来源分类
  source_type: 'ai' | 'custom'

  // 策略类型
  strategy_type: 'entry' | 'exit' | 'stock_selection'

  // 策略元信息
  description?: string
  category?: string  // momentum/reversal/factor/ml (entry) | stop_loss/take_profit/trailing_stop/holding_period (exit)
  tags?: string[]

  // 默认参数
  default_params?: Record<string, unknown>

  // 状态和验证
  validation_status: 'pending' | 'passed' | 'failed' | 'validating'
  validation_errors?: Record<string, string | string[]>
  validation_warnings?: Record<string, string | string[]>
  risk_level: 'safe' | 'low' | 'medium' | 'high'
  is_enabled: boolean

  // 发布状态
  publish_status: 'draft' | 'pending_review' | 'approved' | 'rejected'
  publish_requested_at?: string
  publish_reviewed_at?: string
  publish_reviewed_by?: number
  publish_reject_reason?: string

  // 使用统计
  usage_count: number
  backtest_count: number
  avg_sharpe_ratio?: number
  avg_annual_return?: number

  // 版本和审计
  version: number
  parent_strategy_id?: number
  created_by?: string
  created_at: string
  updated_at: string
  last_used_at?: string

  // 用户信息
  user_id?: number
  username?: string
}

/**
 * 策略创建请求
 */
export interface CreateStrategyRequest {
  name: string
  display_name: string
  code: string
  class_name: string
  source_type: 'ai' | 'custom'
  strategy_type: 'entry' | 'exit' | 'stock_selection'
  description?: string
  category?: string
  tags?: string[]
  default_params?: Record<string, unknown>
}

/**
 * 策略更新请求
 */
export interface UpdateStrategyRequest {
  name?: string
  display_name?: string
  class_name?: string
  code?: string
  description?: string
  category?: string
  tags?: string[]
  default_params?: Record<string, unknown>
  is_enabled?: boolean
}

/**
 * 策略验证响应
 */
export interface StrategyValidationResponse {
  is_valid: boolean
  risk_level: 'safe' | 'low' | 'medium' | 'high'
  errors: string[]
  warnings: string[]
}

/**
 * 策略统计信息
 */
export interface StrategyStatistics {
  total: number
  by_source: {
    ai: number
    custom: number
  }
  by_strategy_type: {
    entry: number
    exit: number
    stock_selection: number
  }
  by_category: Record<string, number>
  enabled: number
  validated: number
}

/**
 * 策略测试响应
 */
export interface StrategyTestResponse {
  success: boolean
  message: string
  details?: Record<string, unknown>
}

// ========== 旧类型定义（向后兼容，标记为废弃）==========

/**
 * @deprecated 使用 Strategy 代替
 * 策略类型元数据
 */
export interface StrategyTypeMeta {
  type: string
  name: string
  description: string
  category?: string
  risk_level?: string
  default_params: Record<string, unknown>
  param_schema: {
    [key: string]: {
      type: 'integer' | 'float' | 'boolean' | 'string' | 'select'
      min?: number
      max?: number
      step?: number
      options?: Array<{ value: string | number | boolean; label: string }>
      description?: string
      default: string | number | boolean
    }
  }
}

/**
 * @deprecated 使用 Strategy 代替
 * 策略配置
 */
export interface StrategyConfig {
  id: number
  strategy_type: string
  name: string
  description?: string
  config: Record<string, unknown>
  is_active: boolean
  created_at: string
  updated_at: string
  created_by?: string
  tags?: string[]
}

/**
 * @deprecated 使用 Strategy 代替
 * 动态策略
 */
export interface DynamicStrategy {
  id: number
  strategy_name: string
  display_name: string
  class_name: string
  description?: string
  generated_code: string
  code_hash?: string
  validation_status: 'pending' | 'passed' | 'failed' | 'warning'
  validation_errors?: Array<{ type: string; message: string }>
  validation_warnings?: Array<{ type: string; message: string }>
  test_status?: 'untested' | 'passed' | 'failed'
  test_results?: Record<string, unknown>
  is_enabled: boolean
  created_at: string
  updated_at: string
  created_by?: string
  version?: number
  parent_id?: number
}

/**
 * 统一回测请求 (V2.0)
 */
export interface BacktestRequest {
  // V2.0: 只需要 strategy_id
  strategy_id: number
  stock_pool: string[]
  start_date: string
  end_date: string
  initial_capital?: number
  rebalance_freq?: 'D' | 'W' | 'M'

  // 策略参数（用于覆盖默认参数，例如 ML 模型 ID）
  strategy_params?: Record<string, unknown>

  // 离场策略（可选，支持多个）
  exit_strategy_ids?: number[]

  // V1.0 兼容字段（废弃）
  /** @deprecated */
  strategy_type?: 'predefined' | 'config' | 'dynamic'
  /** @deprecated */
  strategy_name?: string
  /** @deprecated */
  strategy_config?: Record<string, unknown>
}

/**
 * 策略执行记录
 */
export interface StrategyExecution {
  id: number
  strategy_id: number
  execution_type: 'backtest' | 'live_trading' | 'paper_trading'
  execution_params: Record<string, unknown>
  status: 'pending' | 'running' | 'completed' | 'failed'
  result?: Record<string, unknown>
  metrics?: Record<string, number>
  error_message?: string
  execution_duration_ms?: number
  started_at?: string
  completed_at?: string
  created_at: string
}

/**
 * 策略配置创建请求
 */
export interface CreateStrategyConfigRequest {
  strategy_type: string
  name: string
  config: Record<string, unknown>
  description?: string
}

/**
 * 策略配置更新请求
 */
export interface UpdateStrategyConfigRequest {
  name?: string
  config?: Record<string, any>
  description?: string
  is_active?: boolean
}

/**
 * 策略配置验证响应
 */
export interface StrategyConfigValidationResponse {
  is_valid: boolean
  errors: string[]
  warnings: string[]
}

/**
 * 策略配置测试响应
 */
export interface StrategyConfigTestResponse {
  success: boolean
  message: string
}

/**
 * 动态策略创建请求
 */
export interface CreateDynamicStrategyRequest {
  strategy_name: string
  display_name: string
  class_name: string
  generated_code: string
  description?: string
}

/**
 * 动态策略更新请求
 */
export interface UpdateDynamicStrategyRequest {
  display_name?: string
  generated_code?: string
  description?: string
  is_enabled?: boolean
}

/**
 * 动态策略代码响应
 */
export interface DynamicStrategyCodeResponse {
  strategy_name: string
  code: string
}

/**
 * 动态策略验证响应
 */
export interface DynamicStrategyValidationResponse {
  is_valid: boolean
  errors: string[]
  warnings: string[]
}

/**
 * 动态策略测试响应
 */
export interface DynamicStrategyTestResponse {
  success: boolean
  message: string
}

/**
 * 动态策略统计信息
 */
export interface DynamicStrategyStatistics {
  total_strategies: number
  enabled_strategies: number
  validation_passed: number
  validation_failed: number
  validation_warnings: number
  recent_strategies: DynamicStrategy[]
}

// ========== 发布审核相关类型 (V2.1) ==========

/**
 * 发布审核记录
 */
export interface PublishReview {
  id: number
  strategy_id: number
  reviewer_id: number
  reviewer_username?: string
  action: 'approve' | 'reject' | 'withdraw' | 'request_publish'
  previous_status: string
  new_status: string
  comment?: string
  created_at: string
  metadata?: Record<string, unknown>
}

/**
 * 批准策略请求
 */
export interface ApproveStrategyRequest {
  comment?: string
  auto_enable?: boolean
}

/**
 * 拒绝策略请求
 */
export interface RejectStrategyRequest {
  reason: string
}
