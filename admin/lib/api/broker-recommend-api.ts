import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface BrokerRecommendParams {
  month?: string
  start_month?: string
  end_month?: string
  broker?: string
  ts_code?: string
  page?: number
  page_size?: number
  limit?: number
}

export interface BrokerRecommendData {
  month: string
  broker: string
  ts_code: string
  name: string
  created_at: string | null
  updated_at: string | null
}

export interface BrokerRecommendStatistics {
  month_count: number
  broker_count: number
  stock_count: number
  total_records: number
}

export class BrokerRecommendApiClient extends BaseApiClient {
  async getData(params?: BrokerRecommendParams): Promise<ApiResponse<{
    items: BrokerRecommendData[]
    statistics: BrokerRecommendStatistics
    total: number
  }>> {
    return this.get('/api/broker-recommend', { params })
  }

  async getStatistics(params?: {
    start_month?: string
    end_month?: string
  }): Promise<ApiResponse<BrokerRecommendStatistics>> {
    return this.get('/api/broker-recommend/statistics', { params })
  }

  async getLatest(): Promise<ApiResponse<{
    latest_month: string | null
    items: BrokerRecommendData[]
    total: number
  }>> {
    return this.get('/api/broker-recommend/latest')
  }

  async getBrokers(params?: { month?: string }): Promise<ApiResponse<{ brokers: string[] }>> {
    return this.get('/api/broker-recommend/brokers', { params })
  }

  async getTopStocks(params: { month: string; limit?: number }): Promise<ApiResponse<{
    stocks: { ts_code: string; name: string; recommend_count: number }[]
  }>> {
    return this.get('/api/broker-recommend/top-stocks', { params })
  }

  async syncAsync(params?: { month?: string }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/broker-recommend/sync-async', {}, { params })
  }
}

export const brokerRecommendApi = new BrokerRecommendApiClient()
