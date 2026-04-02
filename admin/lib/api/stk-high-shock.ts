/**
 * @file lib/api/stk-high-shock.ts
 * @description 个股严重异常波动 API 客户端
 * @author Claude
 * @created 2026-03-21
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

/**
 * 个股严重异常波动查询参数
 */
export interface StkHighShockParams {
  start_date?: string      // 开始日期 YYYY-MM-DD
  end_date?: string        // 结束日期 YYYY-MM-DD
  ts_code?: string         // 股票代码
  trade_market?: string    // 交易所
  limit?: number           // 返回记录数限制
}

/**
 * 个股严重异常波动数据项
 */
export interface StkHighShockData {
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
 * 个股严重异常波动统计信息
 */
export interface StkHighShockStatistics {
  total_count: number      // 总记录数
  stock_count: number      // 不同股票数量
  market_count: number     // 不同交易所数量
}

/**
 * 个股严重异常波动 API 客户端
 */
export class StkHighShockApiClient extends BaseApiClient {
  /**
   * 获取个股严重异常波动数据
   */
  async getData(params?: StkHighShockParams): Promise<ApiResponse<{
    items: StkHighShockData[]
    total: number
    trade_date?: string
  }>> {
    return this.get('/api/stk-high-shock', { params })
  }

  /**
   * 获取统计信息
   */
  async getStatistics(params?: {
    start_date?: string
    end_date?: string
    trade_date?: string
  }): Promise<ApiResponse<StkHighShockStatistics>> {
    return this.get('/api/stk-high-shock/statistics', { params })
  }

  /**
   * 获取最新数据
   */
  async getLatest(limit?: number): Promise<ApiResponse<{
    items: StkHighShockData[]
    total: number
  }>> {
    return this.get('/api/stk-high-shock/latest', { params: { limit } })
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
    return this.post('/api/stk-high-shock/sync-async', {}, { params })
  }
}

// 创建单例实例
export const stkHighShockApi = new StkHighShockApiClient()
