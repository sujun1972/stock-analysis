import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface StkHoldertradeParams {
  start_date?: string
  end_date?: string
  ts_code?: string
  holder_type?: string
  trade_type?: string
  limit?: number
}

export interface StkHoldertradeData {
  ts_code: string
  ann_date: string
  holder_name: string
  holder_type: string
  in_de: string
  change_vol: number | null
  change_ratio: number | null
  after_share: number | null
  after_ratio: number | null
  avg_price: number | null
  total_share: number | null
  begin_date: string | null
  close_date: string | null
  created_at: string
  updated_at: string
}

export interface StkHoldertradeStatistics {
  total_count: number
  stock_count: number
  increase_count: number
  decrease_count: number
  total_increase_vol: number
  total_decrease_vol: number
  avg_increase_ratio: number
  avg_decrease_ratio: number
}

export interface StkHoldertradeListResponse {
  items: StkHoldertradeData[]
  statistics: StkHoldertradeStatistics
  total: number
}

export interface SyncStkHoldertradeParams {
  ts_code?: string
  ann_date?: string
  start_date?: string
  end_date?: string
  trade_type?: string
  holder_type?: string
}

export class StkHoldertradeApiClient extends BaseApiClient {
  /**
   * 查询股东增减持数据
   */
  async getStkHoldertrade(params?: StkHoldertradeParams): Promise<ApiResponse<StkHoldertradeListResponse>> {
    return this.get('/api/stk-holdertrade', { params })
  }

  /**
   * 获取股东增减持统计信息
   */
  async getStatistics(params?: {
    start_date?: string
    end_date?: string
    ts_code?: string
  }): Promise<ApiResponse<StkHoldertradeStatistics>> {
    return this.get('/api/stk-holdertrade/statistics', { params })
  }

  /**
   * 获取最新数据信息
   */
  async getLatest(): Promise<ApiResponse<{
    latest_date: string | null
    record_count: number
  }>> {
    return this.get('/api/stk-holdertrade/latest')
  }

  /**
   * 异步同步股东增减持数据
   * 通过Celery任务异步执行，立即返回任务ID
   */
  async syncAsync(params?: SyncStkHoldertradeParams): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/stk-holdertrade/sync-async', null, { params })
  }
}

export const stkHoldertradeApi = new StkHoldertradeApiClient()
