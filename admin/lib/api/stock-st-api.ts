import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface StockStParams {
  ts_code?: string
  st_type?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}

export interface StockStData {
  ts_code: string
  trade_date: string
  name: string
  type: string
  type_name: string
  created_at?: string
  updated_at?: string
}

export interface StockStStatistics {
  total_records: number
  unique_stocks: number
  trading_days: number
  st_types: number
  latest_date: string | null
  earliest_date: string | null
}

export interface StockStResponse {
  items: StockStData[]
  total: number
  page: number
  page_size: number
  statistics?: StockStStatistics
}

export interface StockStTypeDistribution {
  type: string
  type_name: string
  count: number
}

export class StockStApiClient extends BaseApiClient {
  /**
   * 获取ST股票列表数据
   */
  async getData(params?: StockStParams): Promise<ApiResponse<StockStResponse>> {
    return this.get('/api/stock-st', { params })
  }

  /**
   * 获取ST股票统计信息
   */
  async getStatistics(params?: { start_date?: string; end_date?: string }): Promise<ApiResponse<StockStStatistics>> {
    return this.get('/api/stock-st/statistics', { params })
  }

  /**
   * 获取最新的ST股票数据
   */
  async getLatest(): Promise<ApiResponse<{ items: StockStData[]; trade_date: string | null; total: number }>> {
    return this.get('/api/stock-st/latest')
  }

  /**
   * 异步同步ST股票数据
   * 通过Celery任务异步执行，立即返回任务ID
   *
   * 注意：st_type参数仅用于前端查询筛选，同步时会获取所有ST类型的股票
   */
  async syncAsync(params?: {
    ts_code?: string
    trade_date?: string
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/stock-st/sync-async', null, { params })
  }
}

export const stockStApi = new StockStApiClient()
