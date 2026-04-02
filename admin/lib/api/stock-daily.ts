/**
 * @file lib/api/stock-daily.ts
 * @description 股票日线数据 API
 * @created 2026-03-25
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

// ============== 类型定义 ==============

export interface StockDailyData {
  code: string
  name: string
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount: number
  amplitude: number
  pct_change: number
  change: number
  turnover: number
}

export interface StockDailyStatistics {
  stock_count: number
  record_count: number
  avg_pct_change: number
  latest_date: string | null
  earliest_date: string | null
}

export interface StockDailyParams {
  code?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}

export interface SyncDailyParams {
  code?: string  // 可选：留空则同步全市场
  start_date?: string
  end_date?: string
  years?: number
}

export interface FullHistoryProgressData {
  completed: number
  total: number
  is_in_progress: boolean
  percent: number
}

// ============== API 类 ==============

export class StockDailyApiClient extends BaseApiClient {
  /**
   * 查询日线数据
   * @param params 查询参数
   * @returns 日线数据
   */
  async getData(params?: StockDailyParams): Promise<ApiResponse<{
    items: StockDailyData[]
    total: number
    page: number
    page_size: number
    total_pages: number
  }>> {
    return this.get('/api/stock-daily', { params })
  }

  /**
   * 获取统计信息
   * @param code 股票代码（可选）
   * @param start_date 开始日期
   * @param end_date 结束日期
   * @returns 统计信息
   */
  async getStatistics(code?: string, start_date?: string, end_date?: string): Promise<ApiResponse<StockDailyStatistics>> {
    return this.get('/api/stock-daily/statistics', {
      params: { code, start_date, end_date }
    })
  }

  /**
   * 同步单只股票日线数据（同步执行）
   * @param params 同步参数
   * @returns 同步结果
   */
  async sync(params: SyncDailyParams): Promise<ApiResponse<any>> {
    return this.post('/api/stock-daily/sync', params)
  }

  /**
   * 异步同步日线数据（Celery任务）
   *
   * 支持两种模式：
   * - 单只股票：指定 code 参数，同步历史数据（默认 5 年）
   * - 全市场：不指定 code，同步最近交易日的所有股票数据
   *
   * @param params 同步参数
   * @returns 任务信息
   */
  async syncAsync(params: SyncDailyParams): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
  }>> {
    return this.post('/api/stock-daily/sync-async', params)
  }

  /**
   * 触发全量历史日线同步（2021年起，可中断续继）
   */
  async syncFullHistory(): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
  }>> {
    return this.post('/api/stock-daily/sync-full-history', {})
  }

  /**
   * 查询全量历史同步进度
   */
  async getFullHistoryProgress(): Promise<ApiResponse<FullHistoryProgressData>> {
    return this.get('/api/stock-daily/full-history-progress')
  }
}

// ============== 单例导出 ==============

export const stockDailyApi = new StockDailyApiClient()
