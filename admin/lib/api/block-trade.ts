/**
 * @file lib/api/block-trade.ts
 * @description 大宗交易数据 API 客户端
 * @author Claude
 * @created 2026-03-22
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

/**
 * 大宗交易查询参数
 */
export interface BlockTradeParams {
  trade_date?: string  // 交易日期 YYYY-MM-DD
  start_date?: string  // 开始日期 YYYY-MM-DD
  end_date?: string    // 结束日期 YYYY-MM-DD
  ts_code?: string     // 股票代码
  limit?: number       // 返回记录数限制
}

/**
 * 大宗交易数据项
 */
export interface BlockTradeData {
  ts_code: string         // 股票代码
  trade_date: string      // 交易日期
  price: number           // 成交价(元)
  vol: number             // 成交量(万股)
  amount: number          // 成交金额(万元)
  buyer: string           // 买方营业部
  seller: string          // 卖方营业部
  created_at?: string     // 创建时间
  updated_at?: string     // 更新时间
}

/**
 * 大宗交易统计信息
 */
export interface BlockTradeStatistics {
  stock_count: number      // 不同股票数量
  latest_date: string      // 最新交易日期
  total_records: number    // 总记录数
  total_amount: number     // 总成交金额(万元)
  avg_amount: number       // 平均成交金额(万元)
  max_amount: number       // 最大成交金额(万元)
  trading_days: number     // 交易天数
  total_vol: number        // 总成交量(万股)
  avg_price: number        // 平均成交价(元)
}

/**
 * 大宗交易 API 客户端
 */
export class BlockTradeApiClient extends BaseApiClient {
  /**
   * 获取大宗交易数据
   */
  async getData(params?: BlockTradeParams): Promise<ApiResponse<{
    items: BlockTradeData[]
    count: number
  }>> {
    return this.get('/api/block-trade', { params })
  }

  /**
   * 获取统计信息
   */
  async getStatistics(params?: {
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<BlockTradeStatistics>> {
    return this.get('/api/block-trade/statistics', { params })
  }

  /**
   * 获取最新数据
   */
  async getLatest(): Promise<ApiResponse<BlockTradeData>> {
    return this.get('/api/block-trade/latest')
  }

  /**
   * 异步同步数据
   */
  async syncAsync(params?: {
    trade_date?: string
    start_date?: string
    end_date?: string
    ts_code?: string
  }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/block-trade/sync-async', {}, { params })
  }
}

// 创建单例实例
export const blockTradeApi = new BlockTradeApiClient()
