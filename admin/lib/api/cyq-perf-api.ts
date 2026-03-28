import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface CyqPerfParams {
  ts_code?: string
  trade_date?: string  // YYYY-MM-DD 单日精确查询
  start_date?: string  // YYYY-MM-DD
  end_date?: string    // YYYY-MM-DD
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: string
}

export interface CyqPerfData {
  ts_code: string
  trade_date: string
  his_low: number | null
  his_high: number | null
  cost_5pct: number | null
  cost_15pct: number | null
  cost_50pct: number | null
  cost_85pct: number | null
  cost_95pct: number | null
  weight_avg: number | null
  winner_rate: number | null
  created_at: string | null
  updated_at: string | null
}

export interface CyqPerfStatistics {
  total_count: number
  stock_count: number
  avg_cost: number
  avg_winner_rate: number
  max_winner_rate: number
  min_winner_rate: number
}

export class CyqPerfApiClient extends BaseApiClient {
  async getData(params?: CyqPerfParams): Promise<ApiResponse<{
    items: CyqPerfData[]
    statistics: CyqPerfStatistics
    total: number
    trade_date?: string  // 后端回传的默认日期，供前端回填
  }>> {
    return this.get('/api/cyq-perf', { params })
  }

  async getStatistics(params?: {
    ts_code?: string
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<CyqPerfStatistics>> {
    return this.get('/api/cyq-perf/statistics', { params })
  }

  async getLatest(): Promise<ApiResponse<{
    latest_date: string | null
    data: CyqPerfData[]
  }>> {
    return this.get('/api/cyq-perf/latest')
  }

  async getTopWinner(params?: {
    trade_date?: string
    limit?: number
  }): Promise<ApiResponse<CyqPerfData[]>> {
    return this.get('/api/cyq-perf/top-winner', { params })
  }

  async syncAsync(params: {
    ts_code: string
    trade_date?: string
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/cyq-perf/sync-async', {}, { params })
  }
}

export const cyqPerfApi = new CyqPerfApiClient()
