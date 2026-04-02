/**
 * @file lib/api/stk-alert.ts
 * @description 交易所重点提示证券 API 客户端
 * @author Claude
 * @created 2026-03-21
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

/**
 * 交易所重点提示证券查询参数
 */
export interface StkAlertParams {
  start_date?: string  // 开始日期 YYYY-MM-DD
  end_date?: string    // 结束日期 YYYY-MM-DD
  ts_code?: string     // 股票代码
  limit?: number       // 返回记录数限制
}

/**
 * 交易所重点提示证券数据项
 */
export interface StkAlertData {
  ts_code: string         // 股票代码
  name: string            // 股票名称
  start_date: string      // 交易所重点提示起始日期
  end_date: string        // 交易所重点提示参考截至日期
  type: string            // 提示类型
  created_at?: string     // 创建时间
  updated_at?: string     // 更新时间
}

/**
 * 交易所重点提示证券统计信息
 */
export interface StkAlertStatistics {
  total_count: number      // 总记录数
  stock_count: number      // 不同股票数量
  type_count: number       // 不同提示类型数量
}

/**
 * 交易所重点提示证券 API 客户端
 */
export class StkAlertApiClient extends BaseApiClient {
  /**
   * 获取交易所重点提示证券数据
   */
  async getData(params?: StkAlertParams): Promise<ApiResponse<{
    items: StkAlertData[]
    total: number
    trade_date?: string
  }>> {
    return this.get('/api/stk-alert', { params })
  }

  /**
   * 获取统计信息
   */
  async getStatistics(params?: {
    start_date?: string
    end_date?: string
    trade_date?: string
  }): Promise<ApiResponse<StkAlertStatistics>> {
    return this.get('/api/stk-alert/statistics', { params })
  }

  /**
   * 获取最新数据
   */
  async getLatest(limit?: number): Promise<ApiResponse<{
    items: StkAlertData[]
    total: number
  }>> {
    return this.get('/api/stk-alert/latest', { params: { limit } })
  }

  /**
   * 获取当前有效的重点提示证券
   */
  async getActive(params?: {
    current_date?: string
    limit?: number
  }): Promise<ApiResponse<{
    items: StkAlertData[]
    total: number
  }>> {
    return this.get('/api/stk-alert/active', { params })
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
    return this.post('/api/stk-alert/sync-async', {}, { params })
  }
}

// 创建单例实例
export const stkAlertApi = new StkAlertApiClient()
