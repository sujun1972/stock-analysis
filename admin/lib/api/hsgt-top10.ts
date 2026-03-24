/**
 * 沪深股通十大成交股 API 客户端
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

/**
 * 沪深股通十大成交股数据接口
 */
export interface HsgtTop10Data {
  trade_date: string
  ts_code: string
  name: string
  close: number
  change: number
  rank: number
  market_type: string
  amount: number
  net_amount: number
  buy: number
  sell: number
}

/**
 * 沪深股通十大成交股查询参数
 */
export interface HsgtTop10Params {
  start_date?: string   // YYYY-MM-DD
  end_date?: string     // YYYY-MM-DD
  ts_code?: string
  market_type?: string  // 1:沪市 3:深市
  limit?: number
}

/**
 * 统计数据接口
 */
export interface HsgtTop10Statistics {
  total_records: number
  trading_days: number
  stock_count: number
  avg_amount: number
  avg_net_amount: number
  max_amount: number
  min_amount: number
  total_net_amount: number
  avg_amount_yi: number
  avg_net_amount_yi: number
  max_amount_yi: number
  total_net_amount_yi: number
}

/**
 * 沪深股通十大成交股 API 客户端
 */
export class HsgtTop10ApiClient extends BaseApiClient {
  /**
   * 查询沪深股通十大成交股数据
   */
  async getHsgtTop10(params?: HsgtTop10Params): Promise<ApiResponse<{
    items: HsgtTop10Data[]
    total: number
  }>> {
    return this.get('/api/hsgt-top10', { params })
  }

  /**
   * 获取统计信息
   */
  async getStatistics(params?: {
    start_date?: string
    end_date?: string
    market_type?: string
  }): Promise<ApiResponse<HsgtTop10Statistics>> {
    return this.get('/api/hsgt-top10/statistics', { params })
  }

  /**
   * 获取最新数据
   */
  async getLatest(params?: {
    market_type?: string
    limit?: number
  }): Promise<ApiResponse<{
    items: HsgtTop10Data[]
    total: number
    latest_date: string
  }>> {
    return this.get('/api/hsgt-top10/latest', { params })
  }

  /**
   * 获取指定日期净成交金额排名前N的股票
   */
  async getTopByNetAmount(params: {
    trade_date: string
    market_type?: string
    limit?: number
  }): Promise<ApiResponse<{
    items: HsgtTop10Data[]
    total: number
  }>> {
    return this.get('/api/hsgt-top10/top', { params })
  }

  /**
   * 异步同步沪深股通十大成交股数据
   * 通过Celery任务异步执行，立即返回任务ID
   */
  async syncAsync(params?: {
    ts_code?: string
    trade_date?: string   // YYYY-MM-DD
    start_date?: string   // YYYY-MM-DD
    end_date?: string     // YYYY-MM-DD
    market_type?: string  // 1:沪市 3:深市
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/hsgt-top10/sync-async', null, { params })
  }
}

// 导出单例实例
export const hsgtTop10Api = new HsgtTop10ApiClient()
