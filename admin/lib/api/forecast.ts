/**
 * @file lib/api/forecast.ts
 * @description 业绩预告数据 API 客户端
 * @author Claude
 * @created 2026-03-22
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

/**
 * 业绩预告查询参数
 */
export interface ForecastParams {
  start_date?: string  // 开始日期 YYYY-MM-DD
  end_date?: string    // 结束日期 YYYY-MM-DD
  ts_code?: string     // 股票代码
  period?: string      // 报告期 YYYY-MM-DD
  type?: string        // 预告类型
  limit?: number       // 返回记录数限制
  offset?: number      // 分页偏移量
}

/**
 * 业绩预告数据项
 */
export interface ForecastData {
  ts_code: string              // 股票代码
  ann_date: string             // 公告日期
  end_date: string             // 报告期
  type: string                 // 业绩预告类型
  p_change_min: number | null  // 预告净利润变动幅度下限（%）
  p_change_max: number | null  // 预告净利润变动幅度上限（%）
  net_profit_min: number | null // 预告净利润下限（万元）
  net_profit_max: number | null // 预告净利润上限（万元）
  last_parent_net: number | null // 上年同期归属母公司净利润（万元）
  first_ann_date: string | null  // 首次公告日
  summary: string | null         // 业绩预告摘要
  change_reason: string | null   // 业绩变动原因
  created_at?: string           // 创建时间
  updated_at?: string           // 更新时间
}

/**
 * 业绩预告统计信息
 */
export interface ForecastStatistics {
  total_count: number          // 总记录数
  stock_count: number          // 不同股票数量
  avg_p_change_min: number     // 平均变动幅度下限
  avg_p_change_max: number     // 平均变动幅度上限
  avg_net_profit_min: number   // 平均净利润下限
  avg_net_profit_max: number   // 平均净利润上限
  positive_count: number       // 正面预告数量
  negative_count: number       // 负面预告数量
  positive_ratio: number       // 正面预告比例
  negative_ratio: number       // 负面预告比例
}

/**
 * 业绩预告 API 客户端
 */
export class ForecastApiClient extends BaseApiClient {
  /**
   * 获取业绩预告数据
   */
  async getData(params?: ForecastParams): Promise<ApiResponse<{
    items: ForecastData[]
    total: number
  }>> {
    return this.get('/api/forecast', { params })
  }

  /**
   * 获取统计信息
   */
  async getStatistics(params?: {
    start_date?: string
    end_date?: string
    ts_code?: string
    type?: string
  }): Promise<ApiResponse<ForecastStatistics>> {
    return this.get('/api/forecast/statistics', { params })
  }

  /**
   * 获取最新数据
   */
  async getLatest(ts_code?: string): Promise<ApiResponse<ForecastData>> {
    return this.get('/api/forecast/latest', { params: { ts_code } })
  }

  /**
   * 异步同步数据
   */
  async syncAsync(params?: {
    ann_date?: string
    start_date?: string
    end_date?: string
    period?: string
    type?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/forecast/sync-async', {}, { params })
  }

  /**
   * 全量同步历史数据
   */
  async syncFullHistoryAsync(params?: {
    start_date?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/forecast/sync-full-history-async', {}, { params })
  }
}

// 创建单例实例
export const forecastApi = new ForecastApiClient()
