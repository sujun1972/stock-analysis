/**
 * 股票开盘集合竞价 API 客户端
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface StkAuctionOParams {
  ts_code?: string
  trade_date?: string
  start_date?: string
  end_date?: string
  limit?: number
}

export interface StkAuctionOData {
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

export interface StkAuctionOStatistics {
  stock_count: number
  latest_date: string
  total_records: number
  avg_vol: number
  max_vol: number
  avg_amount: number
  max_amount: number
}

export class StkAuctionOApiClient extends BaseApiClient {
  /**
   * 查询开盘集合竞价数据
   */
  async getData(params?: StkAuctionOParams): Promise<ApiResponse<{
    items: StkAuctionOData[]
    statistics: StkAuctionOStatistics
    total: number
  }>> {
    return this.get('/api/stk-auction-o', { params })
  }

  /**
   * 获取统计信息
   */
  async getStatistics(params?: {
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<StkAuctionOStatistics>> {
    return this.get('/api/stk-auction-o/statistics', { params })
  }

  /**
   * 获取最新数据
   */
  async getLatest(): Promise<ApiResponse<{
    latest_date: string
    items: StkAuctionOData[]
    total: number
  }>> {
    return this.get('/api/stk-auction-o/latest')
  }

  /**
   * 异步同步开盘集合竞价数据
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
    return this.post('/api/stk-auction-o/sync-async', null, { params })
  }
}

// 导出单例实例
export const stkAuctionOApi = new StkAuctionOApiClient()
