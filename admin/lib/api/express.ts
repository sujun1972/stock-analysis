/**
 * @file lib/api/express.ts
 * @description 业绩快报数据 API 客户端
 * @author Claude
 * @created 2026-03-22
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

/**
 * 业绩快报查询参数
 */
export interface ExpressParams {
  start_date?: string  // 开始日期 YYYY-MM-DD
  end_date?: string    // 结束日期 YYYY-MM-DD
  ts_code?: string     // 股票代码
  period?: string      // 报告期 YYYY-MM-DD
  limit?: number       // 返回记录数限制
}

/**
 * 业绩快报数据项
 */
export interface ExpressData {
  ts_code: string              // 股票代码
  ann_date: string             // 公告日期
  end_date: string             // 报告期
  revenue: number | null       // 营业收入(亿元)
  operate_profit: number | null // 营业利润(亿元)
  total_profit: number | null  // 利润总额(亿元)
  n_income: number | null      // 净利润(亿元)
  total_assets: number | null  // 总资产(亿元)
  total_hldr_eqy_exc_min_int: number | null // 股东权益合计(亿元)
  diluted_eps: number | null   // 每股收益(摊薄)(元)
  diluted_roe: number | null   // 净资产收益率(摊薄)(%)
  yoy_net_profit: number | null // 去年同期修正后净利润
  bps: number | null           // 每股净资产
  yoy_sales: number | null     // 同比增长率:营业收入
  yoy_op: number | null        // 同比增长率:营业利润
  yoy_tp: number | null        // 同比增长率:利润总额
  yoy_dedu_np: number | null   // 同比增长率:归属母公司股东的净利润
  yoy_eps: number | null       // 同比增长率:基本每股收益
  yoy_roe: number | null       // 同比增减:加权平均净资产收益率
  growth_assets: number | null // 比年初增长率:总资产
  yoy_equity: number | null    // 比年初增长率:归属母公司的股东权益
  growth_bps: number | null    // 比年初增长率:归属于母公司股东的每股净资产
  or_last_year: number | null  // 去年同期营业收入
  op_last_year: number | null  // 去年同期营业利润
  tp_last_year: number | null  // 去年同期利润总额
  np_last_year: number | null  // 去年同期净利润
  eps_last_year: number | null // 去年同期每股收益
  open_net_assets: number | null // 期初净资产
  open_bps: number | null      // 期初每股净资产
  perf_summary: string | null  // 业绩简要说明
  is_audit: number | null      // 是否审计：1是 0否
  remark: string | null        // 备注
  created_at?: string          // 创建时间
  updated_at?: string          // 更新时间
}

/**
 * 业绩快报统计信息
 */
export interface ExpressStatistics {
  total_count: number        // 总记录数
  stock_count: number        // 不同股票数量
  avg_revenue: number        // 平均营业收入(亿元)
  avg_n_income: number       // 平均净利润(亿元)
  avg_eps: number            // 平均每股收益
  avg_roe: number            // 平均净资产收益率
  max_revenue: number        // 最大营业收入(亿元)
  min_revenue: number        // 最小营业收入(亿元)
}

/**
 * 业绩快报 API 客户端
 */
export class ExpressApiClient extends BaseApiClient {
  /**
   * 获取业绩快报数据
   */
  async getData(params?: ExpressParams): Promise<ApiResponse<{
    items: ExpressData[]
    total: number
  }>> {
    return this.get('/api/express', { params })
  }

  /**
   * 获取统计信息
   */
  async getStatistics(params?: {
    start_date?: string
    end_date?: string
    ts_code?: string
  }): Promise<ApiResponse<ExpressStatistics>> {
    return this.get('/api/express/statistics', { params })
  }

  /**
   * 异步同步数据
   */
  async syncAsync(params?: {
    ann_date?: string
    start_date?: string
    end_date?: string
    period?: string
    ts_code?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/express/sync-async', {}, { params })
  }
}

// 创建单例实例
export const expressApi = new ExpressApiClient()
