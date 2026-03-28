import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface CcassHoldDetailParams {
  ts_code?: string
  col_participant_id?: string
  trade_date?: string   // YYYY-MM-DD 单日精确查询
  start_date?: string   // YYYY-MM-DD
  end_date?: string     // YYYY-MM-DD
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: string
}

export interface CcassHoldDetailData {
  trade_date: string
  ts_code: string
  name: string | null
  col_participant_id: string
  col_participant_name: string | null
  col_shareholding: number | null
  col_shareholding_percent: number | null
  created_at: string | null
  updated_at: string | null
}

export interface CcassHoldDetailStatistics {
  total_records: number
  trading_days: number
  stock_count: number
  participant_count: number
  total_shareholding: number
  avg_shareholding_percent: number
}

export class CcassHoldDetailApiClient extends BaseApiClient {
  async getData(params?: CcassHoldDetailParams): Promise<ApiResponse<{
    items: CcassHoldDetailData[]
    statistics: CcassHoldDetailStatistics
    total: number
    trade_date?: string  // 后端回传的默认日期，供前端回填
  }>> {
    return this.get('/api/ccass-hold-detail', { params })
  }

  async getStatistics(params?: {
    ts_code?: string
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<CcassHoldDetailStatistics>> {
    return this.get('/api/ccass-hold-detail/statistics', { params })
  }

  async getLatest(params?: {
    ts_code?: string
    limit?: number
  }): Promise<ApiResponse<CcassHoldDetailData[]>> {
    return this.get('/api/ccass-hold-detail/latest', { params })
  }

  async getTopParticipants(params: {
    trade_date: string
    ts_code?: string
    limit?: number
  }): Promise<ApiResponse<CcassHoldDetailData[]>> {
    return this.get('/api/ccass-hold-detail/top-participants', { params })
  }

  async syncAsync(params?: {
    ts_code?: string
    hk_code?: string
    trade_date?: string
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/ccass-hold-detail/sync-async', {}, { params })
  }
}

export const ccassHoldDetailApi = new CcassHoldDetailApiClient()
