import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

/**
 * 龙虎榜机构明细查询参数
 */
export interface TopInstParams {
  trade_date?: string
  start_date?: string
  end_date?: string
  ts_code?: string
  side?: string  // 0：买入，1：卖出
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: string
}

/**
 * 龙虎榜机构明细数据项
 */
export interface TopInstItem {
  trade_date: string
  ts_code: string
  exalter: string  // 营业部名称
  side: string  // 买卖类型（0：买入，1：卖出）
  buy: number | null  // 买入额（万元）
  buy_rate: number | null  // 买入占总成交比例
  sell: number | null  // 卖出额（万元）
  sell_rate: number | null  // 卖出占总成交比例
  net_buy: number | null  // 净成交额（万元）
  reason: string | null  // 上榜理由
  name: string | null  // 股票名称（行情缓存注入）
}

/**
 * 龙虎榜机构明细统计信息
 */
export interface TopInstStatistics {
  total_records: number  // 总记录数
  trading_days: number  // 交易天数
  stock_count: number  // 股票数量
  exalter_count: number  // 营业部数量
  avg_net_buy: number  // 平均净买入额（万元）
  max_net_buy: number  // 最大净买入额（万元）
  min_net_buy: number  // 最小净卖出额（万元）
  total_net_buy: number  // 累计净买入额（万元）
  total_net_sell: number  // 累计净卖出额（万元）
}

/**
 * 龙虎榜机构明细 API 客户端
 */
export class TopInstApiClient extends BaseApiClient {
  /**
   * 查询龙虎榜机构明细数据（支持分页和排序）
   */
  async getTopInst(params?: TopInstParams): Promise<ApiResponse<{
    items: TopInstItem[]
    total: number
    trade_date: string | null
  }>> {
    return this.get('/api/top-inst', { params })
  }

  /**
   * 获取龙虎榜机构明细统计信息
   */
  async getStatistics(params?: {
    trade_date?: string
    start_date?: string
    end_date?: string
    ts_code?: string
  }): Promise<ApiResponse<TopInstStatistics>> {
    return this.get('/api/top-inst/statistics', { params })
  }

  /**
   * 获取最新交易日的龙虎榜机构明细数据
   */
  async getLatest(): Promise<ApiResponse<{
    latest_date: string | null
    items: TopInstItem[]
    total: number
  }>> {
    return this.get('/api/top-inst/latest')
  }

  /**
   * 异步同步龙虎榜机构明细数据
   */
  async syncAsync(params: {
    trade_date?: string
    ts_code?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/top-inst/sync-async', {}, { params })
  }
}

export const topInstApi = new TopInstApiClient()
