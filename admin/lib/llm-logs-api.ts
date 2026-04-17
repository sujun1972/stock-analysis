/**
 * LLM调用日志API服务
 * 提供LLM调用记录的查询、统计和分析功能
 */

import { apiClient } from './api-client'

export interface LLMCallLog {
  id: number
  call_id: string
  business_type: string
  business_date: string | null
  business_id: string | null
  provider: string
  model_name: string
  api_base_url: string | null
  call_parameters: Record<string, any>
  prompt_text: string
  prompt_length: number
  prompt_hash: string
  response_text: string | null
  response_length: number | null
  parsed_result: Record<string, any> | null
  tokens_input: number | null
  tokens_output: number | null
  tokens_total: number | null
  cost_estimate: number | null
  duration_ms: number | null
  start_time: string
  end_time: string | null
  status: 'success' | 'failed' | 'timeout' | 'rate_limited'
  error_code: string | null
  error_message: string | null
  http_status_code: number | null
  request_headers: Record<string, any> | null
  response_headers: Record<string, any> | null
  caller_service: string | null
  caller_function: string | null
  user_id: string | null
  is_scheduled: boolean
  retry_count: number
  parent_call_id: string | null
  created_at: string
  updated_at: string
}

export interface LLMCallLogQuery {
  business_type?: 'sentiment_analysis' | 'premarket_analysis' | 'strategy_generation' | 'stock_expert_analysis'
  provider?: string
  status?: 'success' | 'failed' | 'timeout' | 'rate_limited'
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}

export interface LLMCallStatistics {
  stat_date: string
  business_type: string
  provider: string
  model_name: string
  total_calls: number
  success_calls: number
  failed_calls: number
  success_rate: number
  total_tokens: number | null
  avg_tokens_per_call: number | null
  max_tokens: number | null
  total_cost: number | null
  avg_cost_per_call: number | null
  avg_duration_ms: number | null
  min_duration_ms: number | null
  max_duration_ms: number | null
  p95_duration_ms: number | null
  total_retries: number | null
  avg_retry_per_call: number | null
}

export interface LLMSummary {
  period: {
    start_date: string
    end_date: string
    days: number
  }
  overview: {
    total_calls: number
    success_calls: number
    success_rate: number
    total_tokens: number
    total_cost: number
    avg_duration_ms: number
  }
  by_provider: Array<{
    provider: string
    count: number
    cost: number
  }>
  by_business_type: Array<{
    business_type: string
    count: number
    cost: number
  }>
  daily_trend: Array<{
    date: string
    count: number
    cost: number
  }>
}

export interface CostAnalysis {
  group_by: string
  results: Array<{
    name: string
    total_calls: number
    total_tokens: number
    total_cost: number
    avg_cost: number
  }>
}

/**
 * 查询LLM调用日志列表
 *
 * @param params - 查询参数（业务类型、提供商、状态、日期范围、分页等）
 * @returns 包含日志列表和分页信息的响应对象
 *
 * @example
 * ```typescript
 * const result = await getLLMCallLogs({
 *   business_type: 'sentiment_analysis',
 *   provider: 'deepseek',
 *   page: 1,
 *   page_size: 20
 * })
 * console.log(result.data.logs) // LLMCallLog[]
 * ```
 */
export async function getLLMCallLogs(params: LLMCallLogQuery = {}) {
  const queryParams = new URLSearchParams()

  if (params.business_type) queryParams.append('business_type', params.business_type)
  if (params.provider) queryParams.append('provider', params.provider)
  if (params.status) queryParams.append('status', params.status)
  if (params.start_date) queryParams.append('start_date', params.start_date)
  if (params.end_date) queryParams.append('end_date', params.end_date)
  queryParams.append('page', String(params.page || 1))
  queryParams.append('page_size', String(params.page_size || 20))

  // 注意：apiClient.get 返回的已经是 response.data（见 api-client.ts:302）
  // 所以这里的 response 结构是 { success: true, data: { logs: [...], pagination: {...} } }
  const response = await apiClient.get(`/api/llm-logs/list?${queryParams.toString()}`)

  return response as {
    success: boolean
    data: {
      logs: LLMCallLog[]
      pagination: {
        total: number
        page: number
        page_size: number
        total_pages: number
      }
    }
  }
}

/**
 * 获取单条日志详情
 *
 * @param callId - 调用ID（UUID格式）
 * @returns LLM调用日志详情
 */
export async function getLLMCallLogDetail(callId: string) {
  const response = await apiClient.get(`/api/llm-logs/detail/${callId}`)
  return response.data as LLMCallLog
}

/**
 * 获取LLM调用统计数据
 *
 * @param startDate - 开始日期（YYYY-MM-DD格式，可选）
 * @param endDate - 结束日期（YYYY-MM-DD格式，可选）
 * @returns 按日期/业务类型/提供商分组的统计数据数组
 */
export async function getLLMStatistics(startDate?: string, endDate?: string) {
  const queryParams = new URLSearchParams()
  if (startDate) queryParams.append('start_date', startDate)
  if (endDate) queryParams.append('end_date', endDate)

  const response = await apiClient.get(`/api/llm-logs/statistics?${queryParams.toString()}`)
  return response.data as LLMCallStatistics[]
}

/**
 * 获取LLM调用概览数据（用于Dashboard展示）
 *
 * @param days - 统计最近N天的数据（默认7天）
 * @returns 包含总调用次数、成功率、Token消耗、成本等概览数据
 *
 * @example
 * ```typescript
 * const summary = await getLLMSummary(7)
 * console.log(summary.overview.total_calls) // 总调用次数
 * console.log(summary.overview.success_rate) // 成功率
 * ```
 */
export async function getLLMSummary(days: number = 7) {
  const response = await apiClient.get(`/api/llm-logs/summary?days=${days}`)
  return response.data as LLMSummary
}

/**
 * 获取最近的LLM调用记录
 *
 * @param limit - 返回记录数量限制（默认10条）
 * @returns 最近的LLM调用日志列表（按时间倒序）
 */
export async function getRecentLLMCalls(limit: number = 10) {
  const response = await apiClient.get(`/api/llm-logs/recent?limit=${limit}`)
  return response.data as LLMCallLog[]
}

/**
 * 获取LLM调用成本分析
 *
 * @param params - 分析参数
 * @param params.start_date - 开始日期（可选）
 * @param params.end_date - 结束日期（可选）
 * @param params.group_by - 分组维度（provider/business_type/model，默认provider）
 * @returns 按指定维度分组的成本分析数据
 *
 * @example
 * ```typescript
 * const analysis = await getCostAnalysis({
 *   group_by: 'provider',
 *   start_date: '2024-01-01',
 *   end_date: '2024-01-31'
 * })
 * ```
 */
export async function getCostAnalysis(params: {
  start_date?: string
  end_date?: string
  group_by?: 'provider' | 'business_type' | 'model'
}) {
  const queryParams = new URLSearchParams()
  if (params.start_date) queryParams.append('start_date', params.start_date)
  if (params.end_date) queryParams.append('end_date', params.end_date)
  queryParams.append('group_by', params.group_by || 'provider')

  const response = await apiClient.get(`/api/llm-logs/cost-analysis?${queryParams.toString()}`)
  return response.data as CostAnalysis
}

/**
 * 业务类型映射
 */
export const businessTypeMap: Record<string, string> = {
  sentiment_analysis: '市场情绪分析',
  premarket_analysis: '盘前碰撞分析',
  strategy_generation: '策略代码生成',
  stock_expert_analysis: '个股专家分析'
}

/**
 * 状态映射
 */
export const statusMap: Record<string, { text: string; color: string }> = {
  success: { text: '成功', color: 'green' },
  failed: { text: '失败', color: 'red' },
  timeout: { text: '超时', color: 'orange' },
  rate_limited: { text: '限流', color: 'yellow' }
}

/**
 * 提供商映射
 */
export const providerMap: Record<string, string> = {
  deepseek: 'DeepSeek',
  gemini: 'Google Gemini',
  openai: 'OpenAI'
}
