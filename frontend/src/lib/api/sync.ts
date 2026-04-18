import { apiGet, apiPost } from './axios-instance'
import type { ApiResponse } from '@/types'

export async function getSyncStatus(): Promise<ApiResponse<{
  status: string
  last_sync_date: string
  progress: number
  total: number
  completed: number
}>> {
  return apiGet('/api/sync/status')
}

export async function syncStockList(): Promise<ApiResponse<{ total: number }>> {
  return apiPost('/api/sync/stock-list')
}

export async function syncNewStocks(days: number = 30): Promise<ApiResponse<{ total: number }>> {
  return apiPost('/api/sync/new-stocks', { days })
}

export async function syncDelistedStocks(): Promise<ApiResponse<{ total: number }>> {
  return apiPost('/api/sync/delisted-stocks')
}

export async function syncDailyBatch(params: {
  codes?: string[]
  start_date?: string
  end_date?: string
  years?: number
  max_stocks?: number
}): Promise<ApiResponse<{
  success: number
  failed: number
  skipped: number
  total: number
  aborted: boolean
}>> {
  return apiPost('/api/sync/daily/batch', params)
}

export async function syncDailyStock(code: string, years: number = 5): Promise<ApiResponse<{
  code: string
  records: number
}>> {
  return apiPost(`/api/sync/daily/${code}`, { years })
}

export async function abortSync(): Promise<ApiResponse<unknown>> {
  return apiPost('/api/sync/abort')
}

export async function syncMinuteData(code: string, params: {
  period?: string
  days?: number
}): Promise<ApiResponse<unknown>> {
  return apiPost(`/api/sync/minute/${code}`, params)
}

export async function syncRealtimeQuotes(params?: {
  codes?: string[]
  batch_size?: number
  update_oldest?: boolean
}): Promise<ApiResponse<{
  total: number
  batch_size: number | string
  update_mode: string
  updated_at: string
}>> {
  return apiPost('/api/sync/realtime', params || {})
}

export async function getSyncHistory(params?: {
  limit?: number
  offset?: number
}): Promise<ApiResponse<unknown[]>> {
  return apiGet('/api/sync/history', { params })
}

export async function getModuleSyncStatus(module: string): Promise<ApiResponse<{
  status: string
  total: number
  success: number
  failed: number
  progress: number
  error_message: string
  started_at: string
  completed_at: string
}>> {
  return apiGet(`/api/sync/status/${module}`)
}
