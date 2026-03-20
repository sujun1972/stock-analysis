/**
 * @file lib/api/margin.ts
 * @description 融资融券相关 API（交易汇总、交易明细）
 * @author Claude
 * @created 2024-03-20
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

// ============== 类型定义 ==============

export interface MarginParams {
  start_date?: string   // YYYY-MM-DD
  end_date?: string     // YYYY-MM-DD
  exchange_id?: string  // 交易所代码（SSE/SZSE/BSE）
  page?: number
  page_size?: number
}

export interface MarginStatistics {
  avg_rzrqye: number
  total_rzrqye: number
  max_rzye: number
  max_rqye: number
}

export interface SyncMarginParams {
  trade_date?: string   // YYYY-MM-DD
  start_date?: string   // YYYY-MM-DD
  end_date?: string     // YYYY-MM-DD
  exchange_id?: string  // 交易所代码（SSE/SZSE/BSE）
  ts_code?: string      // 股票代码（明细专用）
}

export interface SyncTaskResponse {
  celery_task_id: string
  task_name: string
  display_name: string
  status: string
}

export interface MarginDetailParams {
  start_date?: string  // YYYY-MM-DD
  end_date?: string    // YYYY-MM-DD
  ts_code?: string     // 股票代码
  page?: number
  page_size?: number
}

export interface MarginDetailStatistics {
  avg_rzrqye: number
  total_rzrqye: number
  max_rzrqye: number
  stock_count: number
}

export interface MarginDetailTopParams {
  trade_date?: string  // YYYY-MM-DD
  limit?: number
}

// ============== API 类 ==============

export class MarginApiClient extends BaseApiClient {
  // ========== 融资融券交易汇总 ==========

  /**
   * 获取融资融券交易汇总数据
   * @param params 查询参数
   * @returns 汇总数据（分页）
   */
  async getMargin(params?: MarginParams): Promise<ApiResponse<{
    data: any[]
    total: number
    page: number
    page_size: number
  }>> {
    return this.get('/api/margin', { params })
  }

  /**
   * 获取融资融券交易汇总统计数据
   * @param params 统计参数（日期范围）
   * @returns 统计数据
   */
  async getMarginStatistics(params?: {
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<MarginStatistics>> {
    return this.get('/api/margin/statistics', { params })
  }

  /**
   * 异步同步融资融券交易汇总数据
   * 通过Celery任务异步执行，立即返回任务ID
   * @param params 同步参数
   * @returns 任务信息
   */
  async syncMarginAsync(params?: SyncMarginParams): Promise<ApiResponse<SyncTaskResponse>> {
    return this.post('/api/margin/sync-async', null, { params })
  }

  // ========== 融资融券交易明细 ==========

  /**
   * 获取融资融券交易明细数据
   * @param params 查询参数
   * @returns 明细数据（分页）
   */
  async getMarginDetail(params: MarginDetailParams): Promise<ApiResponse<{
    data: any[]
    total: number
    page: number
    page_size: number
  }>> {
    return this.get('/api/margin-detail', { params })
  }

  /**
   * 获取融资融券交易明细统计数据
   * @param params 统计参数（日期范围）
   * @returns 统计数据
   */
  async getMarginDetailStatistics(params?: {
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<MarginDetailStatistics>> {
    return this.get('/api/margin-detail/statistics', { params })
  }

  /**
   * 获取融资融券余额TOP股票
   * @param params 查询参数
   * @returns TOP股票列表
   */
  async getMarginDetailTopStocks(params?: MarginDetailTopParams): Promise<ApiResponse<any[]>> {
    return this.get('/api/margin-detail/top-stocks', { params })
  }

  /**
   * 异步同步融资融券交易明细数据
   * 通过Celery任务异步执行，立即返回任务ID
   * @param params 同步参数
   * @returns 任务信息
   */
  async syncMarginDetailAsync(params?: SyncMarginParams): Promise<ApiResponse<SyncTaskResponse>> {
    return this.post('/api/margin-detail/sync-async', null, { params })
  }
}

// ============== 单例导出 ==============

export const marginApi = new MarginApiClient()
