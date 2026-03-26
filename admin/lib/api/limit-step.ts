import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface LimitStepParams {
  trade_date?: string
  start_date?: string
  end_date?: string
  ts_code?: string
  nums?: string
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}

export interface LimitStepData {
  trade_date: string
  ts_code: string
  name: string
  nums: string
}

export interface LimitStepStatistics {
  stock_count: number
  total_records: number
  max_nums: number
  avg_nums: number
  min_nums: number
  trade_date_count: number
}

export class LimitStepApiClient extends BaseApiClient {
  /**
   * 获取连板天梯数据
   */
  async getData(params?: LimitStepParams): Promise<ApiResponse<{
    items: LimitStepData[]
    statistics: LimitStepStatistics
    total: number
    trade_date: string | null
  }>> {
    return this.get('/api/limit-step', { params })
  }

  /**
   * 获取连板天梯统计信息
   */
  async getStatistics(params?: Omit<LimitStepParams, 'page' | 'page_size' | 'sort_by' | 'sort_order'>): Promise<ApiResponse<{
    statistics: LimitStepStatistics
  }>> {
    return this.get('/api/limit-step/statistics', { params })
  }

  /**
   * 获取最新连板天梯数据
   */
  async getLatest(params?: {
    nums?: string
    limit?: number
  }): Promise<ApiResponse<{
    items: LimitStepData[]
    statistics: LimitStepStatistics
    latest_date: string | null
    total: number
  }>> {
    return this.get('/api/limit-step/latest', { params })
  }

  /**
   * 获取连板次数排行榜
   */
  async getTop(params?: {
    trade_date?: string
    limit?: number
    ascending?: boolean
  }): Promise<ApiResponse<{
    items: LimitStepData[]
    total: number
  }>> {
    return this.get('/api/limit-step/top', { params })
  }

  /**
   * 异步同步连板天梯数据
   * 通过Celery任务异步执行，立即返回任务ID
   */
  async syncAsync(params?: {
    trade_date?: string
    start_date?: string
    end_date?: string
    ts_code?: string
    nums?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/limit-step/sync-async', null, { params })
  }
}

export const limitStepApi = new LimitStepApiClient()
