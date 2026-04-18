import axiosInstance, { apiGet, apiPost, apiPut } from './axios-instance'
import type {
  Strategy,
  CreateStrategyRequest,
  UpdateStrategyRequest,
  StrategyValidationResponse,
  StrategyStatistics,
  StrategyTestResponse,
  StrategyTypeMeta,
  StrategyConfig,
  CreateStrategyConfigRequest,
  UpdateStrategyConfigRequest,
  StrategyConfigValidationResponse,
  StrategyConfigTestResponse,
  DynamicStrategy,
  CreateDynamicStrategyRequest,
  UpdateDynamicStrategyRequest,
  DynamicStrategyCodeResponse,
  DynamicStrategyValidationResponse,
  DynamicStrategyTestResponse,
  DynamicStrategyStatistics,
  ApiResponse,
  PaginatedResponse,
} from '@/types'

// ========== 统一策略相关API (V2.0) ==========

export async function getStrategies(params?: {
  source_type?: 'ai' | 'custom'
  strategy_type?: 'entry' | 'exit' | 'stock_selection'
  category?: string
  is_enabled?: boolean
  publish_status?: 'draft' | 'pending_review' | 'approved' | 'rejected'
  search?: string
  user_id?: number
}): Promise<ApiResponse<Strategy[]>> {
  return apiGet('/api/strategies', { params })
}

export async function getStrategy(id: number): Promise<ApiResponse<Strategy>> {
  return apiGet(`/api/strategies/${id}`)
}

export async function createStrategy(data: CreateStrategyRequest): Promise<ApiResponse<{ strategy_id: number }>> {
  return apiPost('/api/strategies', data)
}

export async function updateStrategy(id: number, data: UpdateStrategyRequest): Promise<ApiResponse<{ strategy_id: number }>> {
  return apiPut(`/api/strategies/${id}`, data)
}

export async function deleteStrategy(id: number): Promise<ApiResponse<void>> {
  const response = await axiosInstance.delete(`/api/strategies/${id}`)
  return response.data
}

export async function validateStrategy(code: string): Promise<ApiResponse<StrategyValidationResponse>> {
  return apiPost('/api/strategies/validate', { code })
}

export async function getStrategyStatistics(): Promise<ApiResponse<StrategyStatistics>> {
  return apiGet('/api/strategies/statistics')
}

export async function getStrategyCode(id: number): Promise<ApiResponse<{ code: string }>> {
  return apiGet(`/api/strategies/${id}/code`)
}

export async function testStrategy(id: number): Promise<ApiResponse<StrategyTestResponse>> {
  return apiPost(`/api/strategies/${id}/test`)
}

// ========== 策略发布 ==========

export async function requestPublishStrategy(strategyId: number): Promise<ApiResponse<unknown>> {
  return apiPost(`/api/strategies/${strategyId}/request-publish`)
}

export async function withdrawPublishRequest(strategyId: number): Promise<ApiResponse<unknown>> {
  return apiPost(`/api/strategies/${strategyId}/withdraw-publish`)
}

export async function getMyStrategies(params?: {
  publish_status?: 'draft' | 'pending_review' | 'approved' | 'rejected'
  page?: number
  page_size?: number
}): Promise<ApiResponse<Strategy[]>> {
  return apiGet('/api/strategies/my-strategies', { params })
}

// ========== 策略配置相关API（旧版，向后兼容）==========

export async function getStrategyTypes(): Promise<ApiResponse<StrategyTypeMeta[]>> {
  return apiGet('/api/strategy-configs/types')
}

export async function createStrategyConfig(data: CreateStrategyConfigRequest): Promise<ApiResponse<{ config_id: number }>> {
  return apiPost('/api/strategy-configs', data)
}

export async function getStrategyConfigs(params?: {
  strategy_type?: string
  is_active?: boolean
  page?: number
  page_size?: number
}): Promise<ApiResponse<PaginatedResponse<StrategyConfig>>> {
  return apiGet('/api/strategy-configs', { params })
}

export async function getStrategyConfig(id: number): Promise<ApiResponse<StrategyConfig>> {
  return apiGet(`/api/strategy-configs/${id}`)
}

export async function updateStrategyConfig(id: number, data: UpdateStrategyConfigRequest): Promise<ApiResponse<{ config_id: number }>> {
  return apiPut(`/api/strategy-configs/${id}`, data)
}

export async function deleteStrategyConfig(id: number): Promise<ApiResponse<void>> {
  const response = await axiosInstance.delete(`/api/strategy-configs/${id}`)
  return response.data
}

export async function testStrategyConfig(id: number): Promise<ApiResponse<StrategyConfigTestResponse>> {
  return apiPost(`/api/strategy-configs/${id}/test`)
}

export async function validateStrategyConfig(data: {
  strategy_type: string
  config: Record<string, unknown>
}): Promise<ApiResponse<StrategyConfigValidationResponse>> {
  return apiPost('/api/strategy-configs/validate', data)
}

// ========== 动态策略相关API ==========

export async function createDynamicStrategy(data: CreateDynamicStrategyRequest): Promise<ApiResponse<{ strategy_id: number }>> {
  return apiPost('/api/dynamic-strategies', data)
}

export async function getDynamicStrategies(params?: {
  validation_status?: string
  is_enabled?: boolean
  page?: number
  page_size?: number
}): Promise<ApiResponse<PaginatedResponse<DynamicStrategy>>> {
  return apiGet('/api/dynamic-strategies', { params })
}

export async function getDynamicStrategy(id: number): Promise<ApiResponse<DynamicStrategy>> {
  return apiGet(`/api/dynamic-strategies/${id}`)
}

export async function getDynamicStrategyCode(id: number): Promise<ApiResponse<DynamicStrategyCodeResponse>> {
  return apiGet(`/api/dynamic-strategies/${id}/code`)
}

export async function updateDynamicStrategy(id: number, data: UpdateDynamicStrategyRequest): Promise<ApiResponse<{ strategy_id: number }>> {
  return apiPut(`/api/dynamic-strategies/${id}`, data)
}

export async function deleteDynamicStrategy(id: number): Promise<ApiResponse<void>> {
  const response = await axiosInstance.delete(`/api/dynamic-strategies/${id}`)
  return response.data
}

export async function testDynamicStrategy(id: number): Promise<ApiResponse<DynamicStrategyTestResponse>> {
  return apiPost(`/api/dynamic-strategies/${id}/test`)
}

export async function validateDynamicStrategy(id: number): Promise<ApiResponse<DynamicStrategyValidationResponse>> {
  return apiPost(`/api/dynamic-strategies/${id}/validate`)
}

export async function getDynamicStrategyStatistics(): Promise<ApiResponse<DynamicStrategyStatistics>> {
  return apiGet('/api/dynamic-strategies/statistics')
}

// ========== AI策略生成异步API ==========

export async function generateStrategyAsync(params: {
  strategy_requirement: string
  strategy_type?: 'entry' | 'exit' | 'stock_selection'
  provider?: string
  use_custom_prompt?: boolean
  custom_prompt_template?: string
}): Promise<{
  task_id: string
  status: string
  message: string
  provider_used: string
}> {
  const response = await axiosInstance.post('/api/ai-strategy/async-generate', params)
  return response.data.data
}

export async function getAIGenerationStatus(taskId: string): Promise<{
  task_id: string
  status: 'PENDING' | 'PROGRESS' | 'SUCCESS' | 'FAILURE'
  message: string
  strategy_code?: string
  strategy_metadata?: Record<string, unknown>
  tokens_used?: number
  generation_time?: number
  provider_used?: string
  error?: string
}> {
  const response = await axiosInstance.get(`/api/ai-strategy/status/${taskId}`)
  return response.data.data
}

export async function cancelAIGeneration(taskId: string): Promise<{
  message: string
  task_id: string
}> {
  const response = await axiosInstance.delete(`/api/ai-strategy/cancel/${taskId}`)
  return response.data
}
