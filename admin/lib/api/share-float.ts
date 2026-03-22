/**
 * 限售股解禁 API 客户端
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface ShareFloatParams {
  start_date?: string  // YYYY-MM-DD
  end_date?: string    // YYYY-MM-DD
  ts_code?: string
  ann_date?: string    // YYYY-MM-DD
  float_date?: string  // YYYY-MM-DD
  limit?: number
}

export interface ShareFloatData {
  ts_code: string
  ann_date: string
  float_date: string
  float_share: number | null
  float_ratio: number | null
  holder_name: string
  share_type: string
  created_at: string
  updated_at: string
}

export interface ShareFloatStatistics {
  total_records: number
  total_stocks: number
  total_float_share: number
  total_float_share_yi: number  // 亿股
  avg_float_ratio: number
  avg_float_ratio_percent: number  // 百分比
  max_float_share: number
  max_float_ratio: number
  max_float_ratio_percent: number  // 百分比
}

export class ShareFloatApiClient extends BaseApiClient {
  /**
   * 查询限售股解禁数据
   */
  async getData(params?: ShareFloatParams): Promise<ApiResponse<{
    items: ShareFloatData[]
    total: number
  }>> {
    return this.get('/api/share-float', { params })
  }

  /**
   * 获取限售股解禁统计信息
   */
  async getStatistics(params?: {
    start_date?: string
    end_date?: string
    ts_code?: string
  }): Promise<ApiResponse<ShareFloatStatistics>> {
    return this.get('/api/share-float/statistics', { params })
  }

  /**
   * 获取最新的限售股解禁数据
   */
  async getLatest(params?: {
    ts_code?: string
  }): Promise<ApiResponse<{
    latest_date: string | null
    items: ShareFloatData[]
  }>> {
    return this.get('/api/share-float/latest', { params })
  }

  /**
   * 异步同步限售股解禁数据
   * 通过Celery任务异步执行，立即返回任务ID
   */
  async syncAsync(params?: {
    ts_code?: string
    ann_date?: string
    float_date?: string
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/share-float/sync-async', null, { params })
  }
}

export const shareFloatApi = new ShareFloatApiClient()
