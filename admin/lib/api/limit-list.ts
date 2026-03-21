import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface LimitListParams {
  start_date?: string
  end_date?: string
  ts_code?: string
  limit_type?: string  // U涨停D跌停Z炸板
  limit?: number
}

export interface LimitListData {
  trade_date: string
  ts_code: string
  industry: string | null
  name: string | null
  close: number | null
  pct_chg: number | null
  amount: number | null
  limit_amount: number | null
  float_mv: number | null
  total_mv: number | null
  turnover_ratio: number | null
  fd_amount: number | null
  first_time: string | null
  last_time: string | null
  open_times: number | null
  up_stat: string | null
  limit_times: number | null
  limit_type: string | null
}

export interface LimitListStatistics {
  total_count: number
  trade_days: number
  stock_count: number
  avg_pct_chg: number
  max_pct_chg: number
  avg_limit_times: number
  max_limit_times: number
}

export class LimitListApiClient extends BaseApiClient {
  /**
   * 查询涨跌停列表数据
   */
  async getData(params?: LimitListParams): Promise<ApiResponse<{
    items: LimitListData[]
    statistics: LimitListStatistics
    total: number
  }>> {
    return this.get('/api/limit-list', { params })
  }

  /**
   * 获取统计信息
   */
  async getStatistics(params?: Omit<LimitListParams, 'limit'>): Promise<ApiResponse<{
    statistics: LimitListStatistics
  }>> {
    return this.get('/api/limit-list/statistics', { params })
  }

  /**
   * 获取最新涨跌停列表数据
   */
  async getLatest(params?: { limit_type?: string }): Promise<ApiResponse<{
    items: LimitListData[]
    statistics: LimitListStatistics
    total: number
    trade_date: string | null
  }>> {
    return this.get('/api/limit-list/latest', { params })
  }

  /**
   * 获取涨停股票排行
   */
  async getTopLimitUp(params?: {
    trade_date?: string
    limit?: number
  }): Promise<ApiResponse<{
    items: LimitListData[]
    total: number
  }>> {
    return this.get('/api/limit-list/top-limit-up', { params })
  }

  /**
   * 异步同步涨跌停列表数据（使用Celery）
   */
  async syncAsync(params?: {
    trade_date?: string
    start_date?: string
    end_date?: string
    ts_code?: string
    limit_type?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/limit-list/sync-async', {}, { params })
  }
}

export const limitListApi = new LimitListApiClient()
