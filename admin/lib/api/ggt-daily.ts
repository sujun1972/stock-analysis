/**
 * 港股通每日成交统计 API 客户端
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

/**
 * 港股通每日成交统计数据接口
 */
export interface GgtDailyData {
  trade_date: string
  buy_amount: number       // 买入成交金额（亿元）
  buy_volume: number       // 买入成交笔数（万笔）
  sell_amount: number      // 卖出成交金额（亿元）
  sell_volume: number      // 卖出成交笔数（万笔）
}

/**
 * 港股通每日成交统计查询参数
 */
export interface GgtDailyParams {
  start_date?: string   // YYYY-MM-DD
  end_date?: string     // YYYY-MM-DD
  limit?: number
  offset?: number
}

/**
 * 统计数据接口
 */
export interface GgtDailyStatistics {
  total_count: number
  avg_buy_amount: number
  avg_sell_amount: number
  total_buy_amount: number
  total_sell_amount: number
  max_buy_amount: number
  max_sell_amount: number
  min_buy_amount: number
  min_sell_amount: number
}

/**
 * 港股通每日成交统计 API 客户端
 */
export class GgtDailyApiClient extends BaseApiClient {
  /**
   * 查询港股通每日成交统计数据
   */
  async getGgtDaily(params?: GgtDailyParams): Promise<ApiResponse<{
    items: GgtDailyData[]
    total: number
    statistics: GgtDailyStatistics
  }>> {
    return this.get('/api/ggt-daily', { params })
  }

  /**
   * 获取统计信息
   */
  async getStatistics(params?: {
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<GgtDailyStatistics>> {
    return this.get('/api/ggt-daily/statistics', { params })
  }

  /**
   * 获取最新数据
   */
  async getLatest(): Promise<ApiResponse<{
    items: GgtDailyData[]
    total: number
    latest_date: string
    statistics: GgtDailyStatistics
  }>> {
    return this.get('/api/ggt-daily/latest')
  }

  /**
   * 异步同步港股通每日成交统计数据
   * 通过Celery任务异步执行，立即返回任务ID
   */
  async syncAsync(params?: {
    trade_date?: string   // YYYY-MM-DD，支持多日逗号分隔
    start_date?: string   // YYYY-MM-DD
    end_date?: string     // YYYY-MM-DD
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/ggt-daily/sync-async', null, { params })
  }

  async syncFullHistory(params?: { start_date?: string }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/ggt-daily/sync-full-history', null, { params })
  }
}

// 导出单例实例
export const ggtDailyApi = new GgtDailyApiClient()
