/**
 * 停复牌信息 API 客户端
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface SuspendData {
  ts_code: string
  trade_date: string
  suspend_timing: string | null
  suspend_type: string
  created_at: string
  updated_at: string
}

export interface SuspendStatistics {
  total_count: number
  stock_count: number
  trade_date_count: number
  suspend_count: number
  resume_count: number
}

export interface SuspendListParams {
  start_date?: string  // YYYY-MM-DD
  end_date?: string    // YYYY-MM-DD
  ts_code?: string
  suspend_type?: string
  page?: number        // 页码，从1开始
  page_size?: number   // 每页记录数
}

export interface SuspendSyncParams {
  ts_code?: string
  trade_date?: string    // YYYY-MM-DD
  start_date?: string    // YYYY-MM-DD
  end_date?: string      // YYYY-MM-DD
  suspend_type?: string
}

export class SuspendApiClient extends BaseApiClient {
  /**
   * 查询停复牌数据（支持分页）
   */
  async getData(params?: SuspendListParams): Promise<ApiResponse<{
    items: SuspendData[]
    total: number
    page: number
    page_size: number
    total_pages: number
  }>> {
    return this.get('/api/suspend', { params })
  }

  /**
   * 获取停复牌统计信息
   */
  async getStatistics(params?: { start_date?: string, end_date?: string }): Promise<ApiResponse<SuspendStatistics>> {
    return this.get('/api/suspend/statistics', { params })
  }

  /**
   * 获取最新交易日期
   */
  async getLatest(): Promise<ApiResponse<{ latest_trade_date: string }>> {
    return this.get('/api/suspend/latest')
  }

  /**
   * 异步同步停复牌数据（通过Celery任务）
   */
  async syncAsync(params?: SuspendSyncParams): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/suspend/sync-async', null, { params })
  }

  /**
   * 全量历史同步（逐只股票，支持中断续继）
   */
  async syncFullHistoryAsync(): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/suspend/sync-full-history', null)
  }
}

export const suspendApi = new SuspendApiClient()
