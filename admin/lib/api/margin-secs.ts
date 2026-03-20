/**
 * @file lib/api/margin-secs.ts
 * @description 融资融券标的（盘前更新）API
 * @author Claude
 * @created 2026-03-20
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

// ============== 类型定义 ==============

export interface MarginSecsParams {
  start_date?: string   // YYYY-MM-DD
  end_date?: string     // YYYY-MM-DD
  ts_code?: string      // 标的代码
  exchange?: string     // 交易所代码（SSE/SZSE/BSE）
  limit?: number        // 返回记录数限制
}

export interface MarginSecsItem {
  trade_date: string
  ts_code: string
  name: string
  exchange: string
  created_at?: string
  updated_at?: string
}

export interface MarginSecsStatistics {
  total_count: number
  unique_stocks: number
  trading_days: number
  exchange_count: number
}

export interface MarginSecsData {
  items: MarginSecsItem[]
  statistics: MarginSecsStatistics
  total: number
}

export interface LatestMarginSecsData {
  items: MarginSecsItem[]
  statistics: {
    total_count: number
    trade_date: string
    exchange_distribution: Array<{
      exchange: string
      count: number
    }>
  }
  trade_date: string
}

export interface SyncMarginSecsParams {
  trade_date?: string   // YYYYMMDD
  exchange?: string     // 交易所代码（SSE/SZSE/BSE）
  start_date?: string   // YYYYMMDD
  end_date?: string     // YYYYMMDD
}

export interface SyncTaskResponse {
  celery_task_id: string
  task_name: string
  display_name: string
  status: string
  task_type: string
}

// ============== API 类 ==============

/**
 * 融资融券标的 API 客户端
 */
export class MarginSecsApi extends BaseApiClient {
  /**
   * 获取融资融券标的数据
   */
  async getMarginSecs(params?: MarginSecsParams): Promise<ApiResponse<MarginSecsData>> {
    return this.get<MarginSecsData>('/api/margin-secs', { params })
  }

  /**
   * 获取最新交易日的融资融券标的数据
   */
  async getLatestMarginSecs(exchange?: string): Promise<ApiResponse<LatestMarginSecsData>> {
    return this.get<LatestMarginSecsData>('/api/margin-secs/latest', {
      params: exchange ? { exchange } : undefined
    })
  }

  /**
   * 异步同步融资融券标的数据
   */
  async syncMarginSecsAsync(params?: SyncMarginSecsParams): Promise<ApiResponse<SyncTaskResponse>> {
    return this.post<SyncTaskResponse>('/api/margin-secs/sync-async', params)
  }

  /**
   * 获取融资融券标的统计信息
   */
  async getMarginSecsStatistics(params?: {
    start_date?: string
    end_date?: string
    exchange?: string
  }): Promise<ApiResponse<MarginSecsStatistics>> {
    return this.get<MarginSecsStatistics>('/api/margin-secs/statistics', { params })
  }
}

// ============== 导出单例 ==============

export const marginSecsApi = new MarginSecsApi()
