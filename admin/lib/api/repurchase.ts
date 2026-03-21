/**
 * @file lib/api/repurchase.ts
 * @description 股票回购数据 API 客户端
 * @author Claude
 * @created 2026-03-21
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

/**
 * 股票回购查询参数
 */
export interface RepurchaseParams {
  start_date?: string  // 开始日期 YYYY-MM-DD
  end_date?: string    // 结束日期 YYYY-MM-DD
  ts_code?: string     // 股票代码
  proc?: string        // 回购进度
  limit?: number       // 返回记录数限制
}

/**
 * 股票回购数据项
 */
export interface RepurchaseData {
  ts_code: string         // 股票代码
  ann_date: string        // 公告日期
  end_date: string        // 截止日期
  proc: string            // 进度
  exp_date: string        // 过期日期
  vol: number             // 回购数量(股)
  amount: number          // 回购金额(万元)
  high_limit: number      // 回购最高价(元)
  low_limit: number       // 回购最低价(元)
  created_at?: string     // 创建时间
  updated_at?: string     // 更新时间
}

/**
 * 股票回购统计信息
 */
export interface RepurchaseStatistics {
  total_count: number      // 总记录数
  stock_count: number      // 不同股票数量
  total_vol: number        // 回购总数量(万股)
  total_amount: number     // 回购总金额(万元)
  avg_amount: number       // 平均回购金额(万元)
  max_amount: number       // 最大回购金额(万元)
  min_amount: number       // 最小回购金额(万元)
  avg_high_limit: number   // 平均最高价(元)
  avg_low_limit: number    // 平均最低价(元)
}

/**
 * 股票回购 API 客户端
 */
export class RepurchaseApiClient extends BaseApiClient {
  /**
   * 获取股票回购数据
   */
  async getData(params?: RepurchaseParams): Promise<ApiResponse<{
    items: RepurchaseData[]
    total: number
  }>> {
    return this.get('/api/repurchase', { params })
  }

  /**
   * 获取统计信息
   */
  async getStatistics(params?: {
    start_date?: string
    end_date?: string
    ts_code?: string
  }): Promise<ApiResponse<RepurchaseStatistics>> {
    return this.get('/api/repurchase/statistics', { params })
  }

  /**
   * 获取最新数据
   */
  async getLatest(ts_code?: string): Promise<ApiResponse<RepurchaseData>> {
    return this.get('/api/repurchase/latest', { params: { ts_code } })
  }

  /**
   * 异步同步数据
   */
  async syncAsync(params?: {
    ann_date?: string
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/repurchase/sync-async', {}, { params })
  }
}

// 创建单例实例
export const repurchaseApi = new RepurchaseApiClient()
