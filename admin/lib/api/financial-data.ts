/**
 * 财务数据API客户端
 * 包括：利润表、资产负债表、现金流量表、业绩预告、业绩快报、分红送股等
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

// ============================================
// 财务指标数据类型定义
// ============================================
export interface FinaIndicatorData {
  ts_code: string
  ann_date: string
  end_date: string
  // 每股指标
  eps?: number
  dt_eps?: number
  bps?: number
  revenue_ps?: number
  capital_rese_ps?: number
  // 收益率指标
  roe?: number
  roe_waa?: number
  roe_dt?: number
  roa?: number
  roic?: number
  // 资产负债结构
  debt_to_assets?: number
  assets_to_eqt?: number
  current_ratio?: number
  quick_ratio?: number
  // 利润率指标
  netprofit_margin?: number
  grossprofit_margin?: number
  // 营运能力
  ar_turn?: number
  inv_turn?: number
  assets_turn?: number
  // 成长能力
  basic_eps_yoy?: number
  netprofit_yoy?: number
  or_yoy?: number
  roe_yoy?: number
}

export interface FinaIndicatorStatistics {
  total_count: number
  stock_count: number
  avg_eps: number
  avg_roe: number
  avg_debt_ratio: number
  avg_netprofit_margin: number
  max_roe: number
  min_debt_ratio: number
}

export interface FinaIndicatorParams {
  ts_code?: string
  start_date?: string  // YYYY-MM-DD
  end_date?: string    // YYYY-MM-DD
  period?: string      // YYYY-MM-DD
  limit?: number
}

export interface FinaIndicatorSyncParams {
  ts_code?: string
  ann_date?: string     // YYYY-MM-DD
  start_date?: string   // YYYY-MM-DD
  end_date?: string     // YYYY-MM-DD
  period?: string       // YYYY-MM-DD
}

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
  // 财务指标数据 API
  // ============================================

  /**
   * 获取财务指标数据
   */
  async getFinaIndicator(params?: FinaIndicatorParams): Promise<ApiResponse<{
    items: FinaIndicatorData[]
    statistics: FinaIndicatorStatistics
    total: number
  }>> {
    return this.get('/api/fina-indicator', { params })
  }

  /**
   * 获取财务指标统计信息
   */
  async getFinaIndicatorStatistics(params?: {
    ts_code?: string
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<FinaIndicatorStatistics>> {
    return this.get('/api/fina-indicator/statistics', { params })
  }

  /**
   * 异步同步财务指标数据
   * 通过Celery任务异步执行，立即返回任务ID
   */
  async syncFinaIndicatorAsync(params?: FinaIndicatorSyncParams): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/fina-indicator/sync-async', null, { params })
  }

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
