import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

/**
 * 股票列表数据
 */
export interface StockListData {
  code: string
  name: string
  ts_code: string
  fullname?: string
  enname?: string
  cnspell?: string
  market: string
  exchange: string
  area?: string
  industry?: string
  curr_type?: string
  list_status: string
  list_date?: string
  delist_date?: string
  is_hs?: string
  act_name?: string
  act_ent_type?: string
  status: string
}

/**
 * 股票列表统计信息
 */
export interface StockListStatistics {
  total_count: number
  listed_count: number
  delisted_count: number
  suspended_count: number
  hs_count: number
  market_distribution: { [key: string]: number }
  exchange_distribution: { [key: string]: number }
}

/**
 * 查询参数
 */
export interface StockListParams {
  list_status?: string  // L上市/D退市/P暂停上市/G过会未交易
  market?: string
  exchange?: string
  is_hs?: string
  limit?: number
  offset?: number
}

/**
 * 股票列表API客户端
 */
export class StockListApiClient extends BaseApiClient {
  /**
   * 获取股票列表数据
   */
  async getData(params?: StockListParams): Promise<ApiResponse<{ items: StockListData[], total: number }>> {
    return this.get('/api/stocks/list', { params })
  }

  /**
   * 获取统计信息
   */
  async getStatistics(): Promise<ApiResponse<StockListStatistics>> {
    return this.get('/api/stocks/list/statistics')
  }

  /**
   * 异步同步数据（使用Celery）
   */
  async syncAsync(params?: { list_status?: string }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/stocks/list/sync-async', {}, { params })
  }
}

export const stockListApi = new StockListApiClient()
