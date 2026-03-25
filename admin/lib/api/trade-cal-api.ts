import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface TradeCalParams {
  exchange?: string
  start_date?: string
  end_date?: string
  is_open?: string
  page?: number
  page_size?: number
}

export interface TradeCalData {
  exchange: string
  cal_date: string
  is_open: number
  pretrade_date: string | null
}

export interface TradeCalStatistics {
  year: number
  total_days: number
  trading_days: number
  non_trading_days: number
  trading_day_ratio: number
}

export interface TradeCalSyncParams {
  exchange?: string
  start_date?: string
  end_date?: string
}

export class TradeCalApiClient extends BaseApiClient {
  async getData(params?: TradeCalParams): Promise<ApiResponse<{
    items: TradeCalData[]
    total: number
    page: number
    page_size: number
  }>> {
    return this.get('/api/trade-cal', { params })
  }

  async getStatistics(params?: {
    year?: number
    exchange?: string
  }): Promise<ApiResponse<TradeCalStatistics>> {
    return this.get('/api/trade-cal/statistics', { params })
  }

  async getLatest(params?: { exchange?: string }): Promise<ApiResponse<{
    latest_trading_day: string | null
    exchange: string
  }>> {
    return this.get('/api/trade-cal/latest', { params })
  }

  async syncAsync(params?: TradeCalSyncParams): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/trade-cal/sync-async', {}, { params })
  }
}

export const tradeCalApi = new TradeCalApiClient()
