/**
 * 复权因子 API 客户端
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface AdjFactorParams {
  ts_code?: string
  start_date?: string  // YYYY-MM-DD
  end_date?: string    // YYYY-MM-DD
  limit?: number
}

export interface AdjFactorData {
  ts_code: string
  trade_date: string
  adj_factor: number | null
  created_at?: string
  updated_at?: string
}

export interface AdjFactorStatistics {
  total_records: number
  stock_count: number
  min_factor: number | null
  max_factor: number | null
  avg_factor: number | null
  latest_date: string | null
}

export class AdjFactorApiClient extends BaseApiClient {
  /**
   * 查询复权因子数据
   */
  async getData(params?: AdjFactorParams): Promise<ApiResponse<{
    items: AdjFactorData[]
    total: number
  }>> {
    return this.get('/api/adj-factor', { params })
  }

  /**
   * 获取最新复权因子数据
   */
  async getLatest(ts_code?: string): Promise<ApiResponse<AdjFactorData | {
    latest_date: string
    items: AdjFactorData[]
    total: number
  }>> {
    return this.get('/api/adj-factor/latest', { params: { ts_code } })
  }

  /**
   * 获取复权因子统计信息
   */
  async getStatistics(params?: Omit<AdjFactorParams, 'limit'>): Promise<ApiResponse<AdjFactorStatistics>> {
    return this.get('/api/adj-factor/statistics', { params })
  }

  /**
   * 异步同步复权因子数据
   * 通过Celery任务异步执行，立即返回任务ID
   */
  async syncAsync(params?: AdjFactorParams & { trade_date?: string }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/adj-factor/sync-async', null, { params })
  }
}

// 导出单例实例
export const adjFactorApi = new AdjFactorApiClient()
