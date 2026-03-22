/**
 * 股东人数 API 客户端
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

/**
 * 股东人数查询参数
 */
export interface StkHolderNumberParams {
  ts_code?: string      // 股票代码
  start_date?: string   // 开始日期 YYYY-MM-DD
  end_date?: string     // 结束日期 YYYY-MM-DD
  limit?: number        // 返回记录数限制
}

/**
 * 股东人数数据
 */
export interface StkHolderNumberData {
  ts_code: string       // 股票代码
  ann_date: string      // 公告日期
  end_date: string      // 截止日期
  holder_num: number    // 股东户数
  created_at: string    // 创建时间
  updated_at: string    // 更新时间
}

/**
 * 股东人数统计信息
 */
export interface StkHolderNumberStatistics {
  record_count: number     // 记录数
  avg_holder_num: number   // 平均股东户数
  max_holder_num: number   // 最大股东户数
  min_holder_num: number   // 最小股东户数
  stock_count: number      // 统计股票数
}

/**
 * 股东人数 API 客户端
 */
export class StkHolderNumberApiClient extends BaseApiClient {
  /**
   * 获取股东人数数据
   */
  async getData(params?: StkHolderNumberParams): Promise<ApiResponse<{
    items: StkHolderNumberData[]
    total: number
  }>> {
    return this.get('/api/stk-holdernumber', { params })
  }

  /**
   * 获取统计信息
   */
  async getStatistics(params?: {
    ts_code?: string
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<StkHolderNumberStatistics>> {
    return this.get('/api/stk-holdernumber/statistics', { params })
  }

  /**
   * 获取指定股票的最新数据
   */
  async getLatest(
    ts_code: string,
    limit: number = 10
  ): Promise<ApiResponse<{
    items: StkHolderNumberData[]
    total: number
  }>> {
    return this.get(`/api/stk-holdernumber/latest/${ts_code}`, {
      params: { limit }
    })
  }

  /**
   * 异步同步数据
   */
  async syncAsync(params?: {
    ts_code?: string
    ann_date?: string
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/stk-holdernumber/sync-async', null, { params })
  }
}

// 导出单例实例
export const stkHolderNumberApi = new StkHolderNumberApiClient()
