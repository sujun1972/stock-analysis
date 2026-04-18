import axiosInstance, { apiGet, apiPost } from './axios-instance'
import type { BacktestRequest, ApiResponse } from '@/types'

// ========== 统一回测API ==========

export async function runBacktestV2(params: BacktestRequest): Promise<ApiResponse<unknown>> {
  return apiPost('/api/backtest/run-v3', params)
}

export async function runUnifiedBacktest(params: BacktestRequest): Promise<ApiResponse<unknown>> {
  return apiPost('/api/backtest', params)
}

export async function runAsyncBacktest(params: BacktestRequest): Promise<{
  task_id: string
  execution_id: number
  status: string
  message: string
}> {
  const response = await axiosInstance.post('/api/backtest/async', params)
  return response.data
}

export async function getBacktestStatus(taskId: string): Promise<{
  task_id: string
  status: 'PENDING' | 'PROGRESS' | 'SUCCESS' | 'FAILURE'
  execution_id?: number
  result?: unknown
  error?: string
  progress?: { current: number; total: number; status: string }
  message?: string
}> {
  const response = await axiosInstance.get(`/api/backtest/status/${taskId}`)
  return response.data
}

export async function cancelBacktest(taskId: string): Promise<{ message: string; task_id: string }> {
  const response = await axiosInstance.delete(`/api/backtest/cancel/${taskId}`)
  return response.data
}

export async function getBacktestResult(taskId: string): Promise<ApiResponse<unknown>> {
  return apiGet(`/api/backtest/result/${taskId}`)
}

// ========== 回测相关API（旧版，向后兼容）==========

export async function runBacktest(params: {
  symbols: string | string[]
  start_date: string
  end_date: string
  initial_cash?: number
  strategy_id?: string
  strategy_params?: Record<string, unknown>
}): Promise<ApiResponse<unknown>> {
  return runUnifiedBacktest({
    strategy_id: 0,
    strategy_type: 'predefined',
    strategy_name: params.strategy_id || 'momentum',
    strategy_config: params.strategy_params || {},
    stock_pool: Array.isArray(params.symbols) ? params.symbols : [params.symbols],
    start_date: params.start_date,
    end_date: params.end_date,
    initial_capital: params.initial_cash
  })
}

export async function getStrategyList(): Promise<ApiResponse<unknown[]>> {
  return apiGet('/api/strategy/list')
}

export async function getStrategyMetadata(strategyId: string = 'complex_indicator'): Promise<ApiResponse<unknown>> {
  return apiGet('/api/strategy/metadata', { params: { strategy_id: strategyId } })
}
