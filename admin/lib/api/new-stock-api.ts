import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface NewStockParams {
  days?: number
  start_date?: string
  end_date?: string
  market?: string
  limit?: number
  offset?: number
}

export interface NewStockData {
  code: string
  name: string
  market: string
  industry: string | null
  area: string | null
  list_date: string
  status: string
  data_source: string
}

export interface NewStockStatistics {
  total_count: number
  market_distribution: Record<string, number>
  industry_distribution: Record<string, number>
  recent_7_days: number
  recent_30_days: number
  recent_90_days: number
}

export class NewStockApiClient extends BaseApiClient {
  /**
   * 查询新股列表
   */
  async getData(params?: NewStockParams): Promise<ApiResponse<{
    items: NewStockData[]
    total: number
  }>> {
    return this.get('/api/new-stocks', { params })
  }

  /**
   * 获取新股统计信息
   */
  async getStatistics(params?: NewStockParams): Promise<ApiResponse<NewStockStatistics>> {
    return this.get('/api/new-stocks/statistics', { params })
  }

  /**
   * 异步同步新股数据
   */
  async syncAsync(params?: { days?: number }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/sync/new-stocks', params || { days: 30 })
  }
}

export const newStockApi = new NewStockApiClient()
