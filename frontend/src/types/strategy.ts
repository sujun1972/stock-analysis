// ========== 策略类型定义 ==========

/**
 * 策略类型元数据
 */
export interface StrategyTypeMeta {
  type: string
  name: string
  description: string
  category?: string
  risk_level?: string
  default_params: Record<string, any>
  param_schema: {
    [key: string]: {
      type: 'integer' | 'float' | 'boolean' | 'string' | 'select'
      min?: number
      max?: number
      step?: number
      options?: Array<{ value: any; label: string }>
      description?: string
      default: any
    }
  }
}

/**
 * 策略配置
 */
export interface StrategyConfig {
  id: number
  strategy_type: string
  name: string
  description?: string
  config: Record<string, any>
  is_active: boolean
  created_at: string
  updated_at: string
  created_by?: string
  tags?: string[]
}

/**
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
  test_results?: any
  is_enabled: boolean
  created_at: string
  updated_at: string
  created_by?: string
  version?: number
  parent_id?: number
}

/**
 * 统一回测请求
 */
export interface BacktestRequest {
  strategy_type: 'predefined' | 'config' | 'dynamic'
  strategy_name?: string
  strategy_id?: number
  strategy_config?: Record<string, any>
  stock_pool: string[]
  start_date: string
  end_date: string
  initial_capital?: number
  rebalance_freq?: 'D' | 'W' | 'M'
}

/**
 * 策略执行记录
 */
export interface StrategyExecution {
  id: number
  strategy_id: number
  execution_type: 'backtest' | 'live_trading' | 'paper_trading'
  execution_params: any
  status: 'pending' | 'running' | 'completed' | 'failed'
  result?: any
  metrics?: any
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
  config: Record<string, any>
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
