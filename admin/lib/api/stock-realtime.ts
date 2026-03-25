/**
 * 实时行情 API 客户端
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface StockRealtimeData {
  code: string
  name: string
  latest_price: number | null
  open: number | null
  high: number | null
  low: number | null
  pre_close: number | null
  volume: number | null
  amount: number | null
  pct_change: number | null
  change_amount: number | null
  turnover: number | null
  amplitude: number | null
  trade_time: string | null
  data_source: string
  updated_at: string | null
}

export interface StockRealtimeStatistics {
  total_count: number
  rising_count: number
  falling_count: number
  unchanged_count: number
  avg_pct_change: number
  max_pct_change: number
  min_pct_change: number
  total_volume: number
  total_amount: number
  last_updated: string | null
}

export interface RealtimeSyncParams {
  batch_size?: number
  update_oldest?: boolean
  data_source?: string  // 'akshare' | 'tushare'
}

export class StockRealtimeApiClient extends BaseApiClient {
  /**
   * 查询实时行情数据（所有股票，支持分页）
   */
  async getData(page?: number, pageSize?: number): Promise<ApiResponse<{
    items: StockRealtimeData[]
    total: number
    page: number
    page_size: number
    total_pages: number
  }>> {
    return this.get('/api/stock-realtime', {
      params: {
        page: page || 1,
        page_size: pageSize || 30
      }
    })
  }

  /**
   * 根据股票代码查询实时行情
   */
  async getByCode(code: string): Promise<ApiResponse<StockRealtimeData>> {
    return this.get(`/api/stock-realtime/code/${code}`)
  }

  /**
   * 获取涨幅榜前N名
   */
  async getTopGainers(limit?: number): Promise<ApiResponse<{
    items: StockRealtimeData[]
    total: number
  }>> {
    return this.get('/api/stock-realtime/top-gainers', { params: { limit } })
  }

  /**
   * 获取跌幅榜前N名
   */
  async getTopLosers(limit?: number): Promise<ApiResponse<{
    items: StockRealtimeData[]
    total: number
  }>> {
    return this.get('/api/stock-realtime/top-losers', { params: { limit } })
  }

  /**
   * 获取实时行情统计信息
   */
  async getStatistics(): Promise<ApiResponse<StockRealtimeStatistics>> {
    return this.get('/api/stock-realtime/statistics')
  }

  /**
   * 异步同步实时行情数据（通过Celery任务）
   */
  async syncAsync(params?: RealtimeSyncParams): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/stock-realtime/sync-async', null, { params })
  }
}

export const stockRealtimeApi = new StockRealtimeApiClient()
