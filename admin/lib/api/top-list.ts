import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

/**
 * 龙虎榜查询参数
 */
export interface TopListParams {
  start_date?: string
  end_date?: string
  ts_code?: string
  limit?: number
}

/**
 * 龙虎榜数据项
 */
export interface TopListItem {
  trade_date: string
  ts_code: string
  name: string
  close: number | null
  pct_change: number | null
  turnover_rate: number | null
  amount: number | null
  l_sell: number | null
  l_buy: number | null
  l_amount: number | null
  net_amount: number | null
  net_rate: number | null
  amount_rate: number | null
  float_values: number | null
  reason: string | null
}

/**
 * 龙虎榜统计信息
 */
export interface TopListStatistics {
  stock_count: number
  total_records: number
  avg_net_amount: number
  total_net_amount: number
  max_net_amount: number
  min_net_amount: number
  avg_amount: number
  avg_pct_change: number
}

/**
 * 龙虎榜 API 客户端
 */
export class TopListApiClient extends BaseApiClient {
  /**
   * 查询龙虎榜数据
   */
  async getTopList(params?: TopListParams): Promise<ApiResponse<{
    items: TopListItem[]
    total: number
  }>> {
    return this.get('/api/top-list', { params })
  }

  /**
   * 获取龙虎榜统计信息
   */
  async getStatistics(params?: {
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<TopListStatistics>> {
    return this.get('/api/top-list/statistics', { params })
  }

  /**
   * 获取最新交易日的龙虎榜数据
   */
  async getLatest(): Promise<ApiResponse<{
    latest_date: string | null
    items: TopListItem[]
    total: number
  }>> {
    return this.get('/api/top-list/latest')
  }

  /**
   * 获取净买入额排名TOP数据
   */
  async getTopRank(params?: {
    trade_date?: string
    limit?: number
  }): Promise<ApiResponse<TopListItem[]>> {
    return this.get('/api/top-list/top-rank', { params })
  }

  /**
   * 异步同步龙虎榜数据
   */
  async syncAsync(params: {
    trade_date: string
    ts_code?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/top-list/sync-async', {}, { params })
  }
}

export const topListApi = new TopListApiClient()
