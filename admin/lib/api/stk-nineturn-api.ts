import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface StkNineturnParams {
  ts_code?: string
  start_date?: string
  end_date?: string
  freq?: string
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface StkNineturnData {
  ts_code: string
  name: string
  trade_date: string
  freq: string
  open: number | null
  high: number | null
  low: number | null
  close: number | null
  vol: number | null
  amount: number | null
  up_count: number | null
  down_count: number | null
  nine_up_turn: string | null
  nine_down_turn: string | null
}

export interface StkNineturnStatistics {
  total_records: number
  stock_count: number
  up_turn_count: number
  down_turn_count: number
  avg_up_count: number
  avg_down_count: number
  max_up_count: number
  max_down_count: number
}

export interface TurnSignal {
  ts_code: string
  trade_date: string
  close: number | null
  up_count: number | null
  down_count: number | null
  nine_up_turn: string | null
  nine_down_turn: string | null
}

export class StkNineturnApiClient extends BaseApiClient {
  async getData(params?: StkNineturnParams): Promise<ApiResponse<{
    items: StkNineturnData[]
    statistics: StkNineturnStatistics
    total: number
    start_date: string | null
    end_date: string | null
  }>> {
    return this.get('/api/stk-nineturn', { params })
  }

  async getStatistics(params?: {
    ts_code?: string
    start_date?: string
    end_date?: string
    freq?: string
  }): Promise<ApiResponse<StkNineturnStatistics>> {
    return this.get('/api/stk-nineturn/statistics', { params })
  }

  async getLatest(params?: {
    ts_code?: string
  }): Promise<ApiResponse<{
    latest_date: string | null
  }>> {
    return this.get('/api/stk-nineturn/latest', { params })
  }

  async getSignals(params?: {
    start_date?: string
    end_date?: string
    signal_type?: 'up' | 'down' | 'all'
    limit?: number
  }): Promise<ApiResponse<{
    items: TurnSignal[]
    total: number
  }>> {
    return this.get('/api/stk-nineturn/signals', { params })
  }

  async syncAsync(params?: {
    ts_code?: string
    trade_date?: string
    freq?: string
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/stk-nineturn/sync-async', {}, { params })
  }
}

export const stkNineturnApi = new StkNineturnApiClient()
