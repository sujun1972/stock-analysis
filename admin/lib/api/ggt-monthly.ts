import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface GgtMonthlyData {
  month: string  // YYYY-MM
  day_buy_amt: number  // 当月日均买入成交金额(亿元)
  day_buy_vol: number  // 当月日均买入成交笔数(万笔)
  day_sell_amt: number  // 当月日均卖出成交金额(亿元)
  day_sell_vol: number  // 当月日均卖出成交笔数(万笔)
  total_buy_amt: number  // 总买入成交金额(亿元)
  total_buy_vol: number  // 总买入成交笔数(万笔)
  total_sell_amt: number  // 总卖出成交金额(亿元)
  total_sell_vol: number  // 总卖出成交笔数(万笔)
  created_at: string
  updated_at: string
}

export interface GgtMonthlyStatistics {
  total_count: number
  avg_day_buy_amt: number
  avg_day_sell_amt: number
  sum_total_buy_amt: number
  sum_total_sell_amt: number
  max_total_buy_amt: number
  max_total_sell_amt: number
  min_total_buy_amt: number
  min_total_sell_amt: number
}

export interface GgtMonthlyParams {
  start_month?: string  // YYYY-MM
  end_month?: string    // YYYY-MM
  limit?: number
}

export class GgtMonthlyApiClient extends BaseApiClient {
  /**
   * 获取港股通每月成交统计数据
   */
  async getData(params?: GgtMonthlyParams): Promise<ApiResponse<{
    items: GgtMonthlyData[]
    total: number
    statistics: GgtMonthlyStatistics
  }>> {
    return this.get('/api/ggt-monthly', { params })
  }

  /**
   * 获取港股通每月成交统计信息
   */
  async getStatistics(params?: {
    start_month?: string  // YYYY-MM
    end_month?: string    // YYYY-MM
  }): Promise<ApiResponse<GgtMonthlyStatistics>> {
    return this.get('/api/ggt-monthly/statistics', { params })
  }

  /**
   * 获取最新港股通每月成交统计数据
   */
  async getLatest(): Promise<ApiResponse<{
    items: GgtMonthlyData[]
    total: number
    latest_month: string
    statistics: GgtMonthlyStatistics
  }>> {
    return this.get('/api/ggt-monthly/latest')
  }

  /**
   * 异步同步港股通每月成交统计数据
   * 通过Celery任务异步执行,立即返回任务ID
   */
  async syncAsync(params?: {
    month?: string         // YYYY-MM,支持多月逗号分隔
    start_month?: string   // YYYY-MM
    end_month?: string     // YYYY-MM
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/ggt-monthly/sync-async', null, { params })
  }
}

export const ggtMonthlyApi = new GgtMonthlyApiClient()
