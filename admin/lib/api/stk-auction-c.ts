/**
 * 股票收盘集合竞价 API 客户端
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface StkAuctionCParams {
  ts_code?: string
  trade_date?: string
  start_date?: string
  end_date?: string
  limit?: number
}

export interface StkAuctionCData {
  ts_code: string
  trade_date: string
  close: number
  open: number
  high: number
  low: number
  vol: number
  amount: number
  vwap: number
  created_at?: string
  updated_at?: string
}

export interface StkAuctionCStatistics {
  stock_count: number
  latest_date: string
  total_records: number
  avg_vol: number
  max_vol: number
  avg_amount: number
  max_amount: number
}

export class StkAuctionCApiClient extends BaseApiClient {
  /**
   * 查询收盘集合竞价数据
   */
  async getData(params?: StkAuctionCParams): Promise<ApiResponse<{
    items: StkAuctionCData[]
    statistics: StkAuctionCStatistics
    total: number
  }>> {
    return this.get('/api/stk-auction-c', { params })
  }

  /**
   * 获取统计信息
   */
  async getStatistics(params?: {
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<StkAuctionCStatistics>> {
    return this.get('/api/stk-auction-c/statistics', { params })
  }

  /**
   * 获取最新数据
   */
  async getLatest(): Promise<ApiResponse<{
    latest_date: string
    items: StkAuctionCData[]
    total: number
  }>> {
    return this.get('/api/stk-auction-c/latest')
  }

  /**
   * 异步同步收盘集合竞价数据
   * 通过Celery任务异步执行，立即返回任务ID
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
    return this.post('/api/stk-auction-c/sync-async', null, { params })
  }
}

// 导出单例实例
export const stkAuctionCApi = new StkAuctionCApiClient()
