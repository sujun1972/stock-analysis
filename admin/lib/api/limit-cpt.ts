import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface LimitCptParams {
  start_date?: string
  end_date?: string
  ts_code?: string
  limit?: number
}

export interface LimitCptData {
  trade_date: string
  ts_code: string
  name: string
  days: number
  up_stat: string
  cons_nums: number
  up_nums: number
  pct_chg: number
  rank: number
}

export interface LimitCptStatistics {
  trading_days: number
  concept_count: number
  avg_up_nums: number
  max_up_nums: number
  avg_cons_nums: number
  max_cons_nums: number
  avg_pct_chg: number
  max_pct_chg: number
}

export class LimitCptApiClient extends BaseApiClient {
  /**
   * 获取最强板块统计数据
   */
  async getData(params?: LimitCptParams): Promise<ApiResponse<{
    items: LimitCptData[]
    total: number
  }>> {
    return this.get('/api/limit-cpt', { params })
  }

  /**
   * 获取最强板块统计信息
   */
  async getStatistics(params?: Omit<LimitCptParams, 'limit' | 'ts_code'>): Promise<ApiResponse<LimitCptStatistics>> {
    return this.get('/api/limit-cpt/statistics', { params })
  }

  /**
   * 获取最新最强板块数据
   */
  async getLatest(): Promise<ApiResponse<{
    items: LimitCptData[]
    total: number
    latest_date: string
  }>> {
    return this.get('/api/limit-cpt/latest')
  }

  /**
   * 获取涨停家数排行榜
   */
  async getTopRank(params?: {
    trade_date?: string
    limit?: number
  }): Promise<ApiResponse<LimitCptData[]>> {
    return this.get('/api/limit-cpt/top-rank', { params })
  }

  /**
   * 异步同步最强板块统计数据
   * 通过Celery任务异步执行，立即返回任务ID
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
    return this.post('/api/limit-cpt/sync-async', null, { params })
  }
}

export const limitCptApi = new LimitCptApiClient()
