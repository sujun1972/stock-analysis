/**
 * 提示词模板类型定义
 */

export interface PromptTemplate {
  id: number
  business_type: string
  template_name: string
  template_key: string
  system_prompt?: string
  user_prompt_template: string
  output_format?: string
  required_variables?: Record<string, string>
  optional_variables?: Record<string, string>
  version: string
  parent_template_id?: number
  is_active: boolean
  is_default: boolean
  recommended_provider?: string
  recommended_model?: string
  recommended_temperature?: number
  recommended_max_tokens?: number
  description?: string
  changelog?: string
  tags?: string[]
  avg_tokens_used?: number
  avg_generation_time?: number
  success_rate?: number
  usage_count: number
  created_by?: string
  updated_by?: string
  created_at: string
  updated_at: string
}

export interface PromptTemplateCreate {
  business_type: string
  template_name: string
  template_key: string
  system_prompt?: string
  user_prompt_template: string
  output_format?: string
  required_variables?: Record<string, string>
  optional_variables?: Record<string, string>
  version: string
  parent_template_id?: number
  is_active?: boolean
  is_default?: boolean
  recommended_provider?: string
  recommended_model?: string
  recommended_temperature?: number
  recommended_max_tokens?: number
  description?: string
  changelog?: string
  tags?: string[]
  created_by?: string
}

export interface PromptTemplateUpdate {
  template_name?: string
  system_prompt?: string
  user_prompt_template?: string
  output_format?: string
  required_variables?: Record<string, string>
  optional_variables?: Record<string, string>
  is_active?: boolean
  is_default?: boolean
  recommended_provider?: string
  recommended_model?: string
  recommended_temperature?: number
  recommended_max_tokens?: number
  description?: string
  changelog?: string
  tags?: string[]
  updated_by?: string
}

export interface PromptTemplateVersionCreate {
  version: string
  changelog: string
  template_name?: string
  system_prompt?: string
  user_prompt_template?: string
  output_format?: string
  required_variables?: Record<string, string>
  optional_variables?: Record<string, string>
  recommended_provider?: string
  recommended_model?: string
  recommended_temperature?: number
  recommended_max_tokens?: number
  description?: string
  tags?: string[]
  created_by?: string
}

export interface PromptTemplatePreviewRequest {
  variables: Record<string, any>
}

export interface PromptTemplatePreviewResponse {
  system_prompt?: string
  user_prompt: string
  full_prompt: string
  missing_variables: string[]
  extra_variables: string[]
  success?: boolean
  error?: string
}

export interface PromptTemplateStatistics {
  template_id: number
  template_name: string
  template_key: string
  version: string
  total_calls: number
  successful_calls: number
  failed_calls: number
  success_rate: number
  avg_tokens_used?: number
  avg_duration_sec?: number
  total_cost?: number
  last_used_at?: string
  created_at: string
}

export interface PromptTemplateHistory {
  id: number
  template_id: number
  change_type: string
  old_content?: Record<string, any>
  new_content?: Record<string, any>
  change_summary?: string
  changed_by?: string
  changed_at: string
  reason?: string
}

export interface PromptTemplateListResponse {
  total: number
  items: PromptTemplate[]
}

export const BUSINESS_TYPES = {
  SENTIMENT_ANALYSIS: 'sentiment_analysis',
  PREMARKET_ANALYSIS: 'premarket_analysis',
  STRATEGY_GENERATION: 'strategy_generation',
  STRATEGY_GENERATION_ENTRY: 'strategy_generation_entry',
  STRATEGY_GENERATION_EXIT: 'strategy_generation_exit',
  STRATEGY_GENERATION_STOCK_SELECTION: 'strategy_generation_stock_selection',
  STOCK_ANALYSIS: 'stock_analysis',
  STOCK_DATA_COLLECTION: 'stock_data_collection',
  HOT_MONEY_VIEW: 'hot_money_view',
  MIDLINE_INDUSTRY_EXPERT: 'midline_industry_expert',
  LONGTERM_VALUE_WATCHER: 'longterm_value_watcher',
  CIO_DIRECTIVE: 'cio_directive',
} as const

export const BUSINESS_TYPE_LABELS: Record<string, string> = {
  sentiment_analysis: '市场情绪分析',
  premarket_analysis: '盘前预期分析',
  strategy_generation: '策略生成（通用）',
  strategy_generation_entry: '策略生成 - 入场策略',
  strategy_generation_exit: '策略生成 - 离场策略',
  strategy_generation_stock_selection: '策略生成 - 选股策略',
  stock_analysis: '个股分析',
  stock_data_collection: '个股数据收集',
  hot_money_view: '顶级游资观点',
  midline_industry_expert: '中线产业趋势专家观点',
  longterm_value_watcher: '长线价值守望者观点',
  cio_directive: '首席投资官（CIO）指令',
}
