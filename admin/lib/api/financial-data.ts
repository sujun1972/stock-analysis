/**
 * 财务数据API客户端
 * 包括：利润表、资产负债表、现金流量表、业绩预告、业绩快报、分红送股等
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

// ============================================
// 分红送股数据类型定义
// ============================================
export interface DividendData {
  ts_code: string
  end_date: string
  ann_date: string
  div_proc?: string
  stk_div?: number
  stk_bo_rate?: number
  stk_co_rate?: number
  cash_div?: number
  cash_div_tax?: number
  record_date?: string
  ex_date?: string
  pay_date?: string
  div_listdate?: string
  imp_ann_date?: string
  base_date?: string
  base_share?: number
}

export interface DividendStatistics {
  total_records: number
  stock_count: number
  avg_cash_div: number
  max_cash_div: number
  avg_stk_div: number
  max_stk_div: number
}

export interface DividendParams {
  ts_code?: string
  start_date?: string  // YYYY-MM-DD
  end_date?: string    // YYYY-MM-DD
  limit?: number
}

export interface DividendSyncParams {
  ts_code?: string
  ann_date?: string       // YYYY-MM-DD
  record_date?: string    // YYYY-MM-DD
  ex_date?: string        // YYYY-MM-DD
  imp_ann_date?: string   // YYYY-MM-DD
}

export class FinancialDataApiClient extends BaseApiClient {
  // ============================================
  // 分红送股数据 API
  // ============================================

  /**
   * 获取分红送股数据
   */
  async getDividend(params?: DividendParams): Promise<ApiResponse<{
    items: DividendData[]
    statistics: DividendStatistics
    total: number
  }>> {
    return this.get('/api/dividend', { params })
  }

  /**
   * 获取分红送股统计信息
   */
  async getDividendStatistics(params?: {
    ts_code?: string
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<DividendStatistics>> {
    return this.get('/api/dividend/statistics', { params })
  }

  /**
   * 异步同步分红送股数据
   * 通过Celery任务异步执行，立即返回任务ID
   */
  async syncDividendAsync(params?: DividendSyncParams): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/dividend/sync-async', null, { params })
  }
}

export const financialDataApi = new FinancialDataApiClient()
