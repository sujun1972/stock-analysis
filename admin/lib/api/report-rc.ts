/**
 * 卖方盈利预测数据 API 客户端
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

/**
 * 查询参数
 */
export interface ReportRcParams {
  ts_code?: string
  trade_date?: string  // YYYY-MM-DD 单日精确查询
  start_date?: string  // YYYY-MM-DD
  end_date?: string    // YYYY-MM-DD
  org_name?: string
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: string
}

/**
 * 卖方盈利预测数据
 */
export interface ReportRcData {
  ts_code: string
  name: string
  report_date: string
  report_title: string
  report_type: string
  classify: string
  org_name: string
  author_name: string
  quarter: string
  op_rt: number | null        // 预测营业收入（万元）
  op_pr: number | null        // 预测营业利润（万元）
  tp: number | null           // 预测利润总额（万元）
  np: number | null           // 预测净利润（万元）
  eps: number | null          // 预测每股收益（元）
  pe: number | null           // 预测市盈率
  rd: number | null           // 预测股息率
  roe: number | null          // 预测净资产收益率
  ev_ebitda: number | null    // 预测EV/EBITDA
  rating: string | null       // 卖方评级
  max_price: number | null    // 预测最高目标价
  min_price: number | null    // 预测最低目标价
  imp_dg: string | null       // 机构关注度
  create_time: string | null
  created_at: string
  updated_at: string
}

/**
 * 统计信息
 */
export interface ReportRcStatistics {
  total_count: number
  stock_count: number
  org_count: number
  avg_eps: number
  avg_pe: number
  avg_roe: number
}

/**
 * 高评级股票
 */
export interface TopRatedStock {
  ts_code: string
  name: string
  org_count: number
  avg_eps: number | null
  avg_pe: number | null
  avg_target_price: number | null
}

/**
 * 卖方盈利预测数据 API 客户端
 */
export class ReportRcApiClient extends BaseApiClient {
  /**
   * 查询卖方盈利预测数据
   */
  async getData(params?: ReportRcParams): Promise<ApiResponse<{
    items: ReportRcData[]
    statistics: ReportRcStatistics
    total: number
    report_date?: string  // 后端回传的默认日期，供前端回填
  }>> {
    return this.get('/api/report-rc', { params })
  }

  /**
   * 获取统计信息
   */
  async getStatistics(params?: {
    start_date?: string
    end_date?: string
    ts_code?: string
  }): Promise<ApiResponse<ReportRcStatistics>> {
    return this.get('/api/report-rc/statistics', { params })
  }

  /**
   * 获取最新数据
   */
  async getLatest(): Promise<ApiResponse<{
    latest_date: string | null
    data: ReportRcData[]
  }>> {
    return this.get('/api/report-rc/latest')
  }

  /**
   * 获取高评级股票
   */
  async getTopRated(params?: {
    report_date?: string  // YYYY-MM-DD
    limit?: number
  }): Promise<ApiResponse<TopRatedStock[]>> {
    return this.get('/api/report-rc/top-rated', { params })
  }

  /**
   * 异步同步卖方盈利预测数据
   * 通过Celery任务异步执行，立即返回任务ID
   */
  async syncAsync(params?: {
    ts_code?: string
    report_date?: string  // YYYY-MM-DD
    start_date?: string   // YYYY-MM-DD
    end_date?: string     // YYYY-MM-DD
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/report-rc/sync-async', null, { params })
  }
}

// 导出单例实例
export const reportRcApi = new ReportRcApiClient()
