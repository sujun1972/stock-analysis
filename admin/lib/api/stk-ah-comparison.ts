import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface StkAhComparisonParams {
  hk_code?: string
  ts_code?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
  limit?: number
}

export interface StkAhComparisonData {
  hk_code: string
  ts_code: string
  trade_date: string
  hk_name: string
  hk_pct_chg: number | null
  hk_close: number | null
  name: string
  close: number | null
  pct_chg: number | null
  ah_comparison: number | null
  ah_premium: number | null
}

export interface StkAhComparisonStatistics {
  stock_count: number
  avg_premium: number
  max_premium: number
  min_premium: number
  avg_comparison: number
}

export interface TopPremiumParams {
  trade_date?: string
  limit?: number
}

export interface SyncAsyncParams {
  hk_code?: string
  ts_code?: string
  trade_date?: string
  start_date?: string
  end_date?: string
}

export class StkAhComparisonApiClient extends BaseApiClient {
  /**
   * 获取AH股比价数据
   */
  async getData(params?: StkAhComparisonParams): Promise<ApiResponse<{
    items: StkAhComparisonData[]
    statistics: StkAhComparisonStatistics
    total: number
    resolved_date?: string
  }>> {
    return this.get('/api/stk-ah-comparison', { params })
  }

  /**
   * 获取统计信息
   */
  async getStatistics(params?: { start_date?: string; end_date?: string }): Promise<ApiResponse<StkAhComparisonStatistics>> {
    return this.get('/api/stk-ah-comparison/statistics', { params })
  }

  /**
   * 获取最新交易日期
   */
  async getLatest(): Promise<ApiResponse<{ latest_trade_date: string }>> {
    return this.get('/api/stk-ah-comparison/latest')
  }

  /**
   * 获取溢价率最高的股票
   */
  async getTopPremium(params?: TopPremiumParams): Promise<ApiResponse<{
    items: StkAhComparisonData[]
    total: number
  }>> {
    return this.get('/api/stk-ah-comparison/top-premium', { params })
  }

  /**
   * 异步同步AH股比价数据
   * 通过Celery任务异步执行，立即返回任务ID
   */
  async syncAsync(params?: SyncAsyncParams): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/stk-ah-comparison/sync-async', null, { params })
  }
}

export const stkAhComparisonApi = new StkAhComparisonApiClient()
