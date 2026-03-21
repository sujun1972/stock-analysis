/**
 * @file lib/api/stk-shock.ts
 * @description 个股异常波动 API 客户端
 * @author Claude
 * @created 2026-03-21
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

/**
 * 个股异常波动查询参数
 */
export interface StkShockParams {
  start_date?: string  // 开始日期 YYYY-MM-DD
  end_date?: string    // 结束日期 YYYY-MM-DD
  ts_code?: string     // 股票代码
  limit?: number       // 返回记录数限制
}

/**
 * 个股异常波动数据项
 */
export interface StkShockData {
  ts_code: string         // 股票代码
  trade_date: string      // 公告日期
  name: string            // 股票名称
  trade_market: string    // 交易所
  reason: string          // 异常说明
  period: string          // 异常期间
  created_at?: string     // 创建时间
  updated_at?: string     // 更新时间
}

/**
 * 个股异常波动统计信息
 */
export interface StkShockStatistics {
  total_records: number      // 总记录数
  unique_stocks: number      // 不同股票数量
  unique_dates: number       // 不同交易日数量
  earliest_date: string | null  // 最早日期
  latest_date: string | null    // 最新日期
}

/**
 * 个股异常波动 API 客户端
 */
export class StkShockApiClient extends BaseApiClient {
  /**
   * 获取个股异常波动数据
   */
  async getData(params?: StkShockParams): Promise<ApiResponse<{
    items: StkShockData[]
    total: number
  }>> {
    return this.get('/api/stk-shock', { params })
  }

  /**
   * 获取统计信息
   */
  async getStatistics(params?: {
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<StkShockStatistics>> {
    return this.get('/api/stk-shock/statistics', { params })
  }

  /**
   * 获取最新数据
   */
  async getLatest(limit?: number): Promise<ApiResponse<{
    items: StkShockData[]
    total: number
  }>> {
    return this.get('/api/stk-shock/latest', { params: { limit } })
  }

  /**
   * 异步同步数据
   */
  async syncAsync(params?: {
    trade_date?: string
    start_date?: string
    end_date?: string
    ts_code?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/stk-shock/sync-async', {}, { params })
  }
}

// 创建单例实例
export const stkShockApi = new StkShockApiClient()
