/**
 * 每日涨跌停价格 API 客户端
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface StkLimitDParams {
  ts_code?: string
  start_date?: string  // YYYY-MM-DD
  end_date?: string    // YYYY-MM-DD
  page?: number
  page_size?: number
}

export interface StkLimitDData {
  trade_date: string
  ts_code: string
  pre_close: number | null
  up_limit: number | null
  down_limit: number | null
}

export interface StkLimitDStatistics {
  total_records: number
  trading_days: number
  stock_count: number
  avg_up_range: number
  avg_down_range: number
}

export class StkLimitDApiClient extends BaseApiClient {
  /**
   * 查询每日涨跌停价格数据
   */
  async getData(params?: StkLimitDParams): Promise<ApiResponse<{
    items: StkLimitDData[]
    statistics: StkLimitDStatistics
    total: number
  }>> {
    return this.get('/api/stk-limit-d', { params })
  }

  /**
   * 获取最新的每日涨跌停价格数据
   */
  async getLatest(limit?: number): Promise<ApiResponse<{
    items: StkLimitDData[]
    latest_date: string | null
    total: number
  }>> {
    return this.get('/api/stk-limit-d/latest', { params: { limit } })
  }

  /**
   * 获取每日涨跌停价格统计信息
   */
  async getStatistics(params?: Omit<StkLimitDParams, 'limit'>): Promise<ApiResponse<StkLimitDStatistics>> {
    return this.get('/api/stk-limit-d/statistics', { params })
  }

  /**
   * 增量同步每日涨跌停价格数据
   * 不传日期参数，由后端从 sync_configs 自动计算
   */
  async syncAsync(): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/stk-limit-d/sync-async')
  }

  /**
   * 全量历史同步：逐只股票同步每日涨跌停价格，8并发，支持Redis中断续继
   */
  async syncFullHistory(params?: { start_date?: string }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/stk-limit-d/sync-full-history', null, { params })
  }
}

// 导出单例实例
export const stkLimitDApi = new StkLimitDApiClient()
