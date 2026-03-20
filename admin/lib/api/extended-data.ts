/**
 * @file lib/api/extended-data.ts
 * @description 扩展数据相关 API（daily_basic, hk_hold, block_trade等）
 * @author Claude
 * @created 2024-03-20
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

// ============== 类型定义 ==============

export interface DateRangeParams {
  start_date?: string
  end_date?: string
  limit?: number
}

export interface DailyBasicParams extends DateRangeParams {
  ts_code: string
}

export interface HkHoldParams {
  ts_code?: string
  start_date?: string
  end_date?: string
  limit?: number
  offset?: number
}

export interface LimitPricesParams {
  trade_date?: string
  ts_code?: string
  limit?: number
}

export interface BlockTradeParams {
  trade_date?: string
  ts_code?: string
  start_date?: string
  end_date?: string
  limit?: number
}

export interface ExtendedDataSummary {
  daily_basic: {
    total: number
    latest_date: string
  }
  hk_hold: {
    total: number
    latest_date: string
  }
  limit_prices: {
    total: number
    latest_date: string
  }
  block_trade: {
    total: number
    latest_date: string
  }
}

// ============== API 类 ==============

export class ExtendedDataApiClient extends BaseApiClient {
  // ========== 每日指标 (daily_basic) ==========

  /**
   * 获取每日指标数据
   * @param tsCode 股票代码
   * @param params 查询参数
   * @returns 每日指标数据
   */
  async getDailyBasic(tsCode: string, params?: DateRangeParams): Promise<ApiResponse<any>> {
    return this.get(`/api/extended-data/daily-basic/${tsCode}`, { params })
  }

  /**
   * 同步每日指标数据
   * @param date 日期 (YYYY-MM-DD)
   * @returns 同步结果
   */
  async syncDailyBasic(date: string): Promise<ApiResponse<{ count: number }>> {
    return this.post('/api/extended-data/daily-basic/sync', { date })
  }

  // ========== 北向资金持股 (hk_hold) ==========

  /**
   * 获取北向资金持股数据
   * @param params 查询参数
   * @returns 持股数据
   */
  async getHkHold(params?: HkHoldParams): Promise<ApiResponse<any>> {
    return this.get('/api/extended-data/hk-hold', { params })
  }

  /**
   * 同步北向资金持股数据
   * @param date 日期 (YYYY-MM-DD)
   * @returns 同步结果
   */
  async syncHkHold(date: string): Promise<ApiResponse<{ count: number }>> {
    return this.post('/api/extended-data/hk-hold/sync', { date })
  }

  // ========== 涨跌停价格 (stk_limit) ==========

  /**
   * 获取涨跌停价格数据
   * @param params 查询参数
   * @returns 涨跌停价格数据
   */
  async getLimitPrices(params?: LimitPricesParams): Promise<ApiResponse<any>> {
    return this.get('/api/extended-data/limit-prices', { params })
  }

  /**
   * 同步涨跌停价格数据
   * @param date 日期 (YYYY-MM-DD)
   * @returns 同步结果
   */
  async syncLimitPrices(date: string): Promise<ApiResponse<{ count: number }>> {
    return this.post('/api/extended-data/limit-prices/sync', { date })
  }

  // ========== 大宗交易 (block_trade) ==========

  /**
   * 获取大宗交易数据
   * @param params 查询参数
   * @returns 大宗交易数据
   */
  async getBlockTrade(params?: BlockTradeParams): Promise<ApiResponse<any>> {
    return this.get('/api/extended-data/block-trade', { params })
  }

  /**
   * 同步大宗交易数据
   * @param date 日期 (YYYY-MM-DD)
   * @returns 同步结果
   */
  async syncBlockTrade(date: string): Promise<ApiResponse<{ count: number }>> {
    return this.post('/api/extended-data/block-trade/sync', { date })
  }

  // ========== 复权因子 (adj_factor) ==========

  /**
   * 获取复权因子数据
   * @param tsCode 股票代码
   * @param params 查询参数
   * @returns 复权因子数据
   */
  async getAdjFactor(tsCode: string, params?: DateRangeParams): Promise<ApiResponse<any>> {
    return this.get(`/api/extended-data/adj-factor/${tsCode}`, { params })
  }

  /**
   * 同步复权因子数据
   * @param date 日期 (YYYY-MM-DD)
   * @returns 同步结果
   */
  async syncAdjFactor(date: string): Promise<ApiResponse<{ count: number }>> {
    return this.post('/api/extended-data/adj-factor/sync', { date })
  }

  // ========== 停复牌信息 ==========

  /**
   * 获取停复牌信息
   * @param params 查询参数
   * @returns 停复牌信息
   */
  async getSuspendInfo(params?: {
    ts_code?: string
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<any>> {
    return this.get('/api/extended-data/suspend', { params })
  }

  // ========== 综合统计 ==========

  /**
   * 获取扩展数据综合统计
   * @returns 统计信息
   */
  async getExtendedDataSummary(): Promise<ApiResponse<ExtendedDataSummary>> {
    return this.get('/api/extended-data/summary')
  }
}

// ============== 单例导出 ==============

export const extendedDataApi = new ExtendedDataApiClient()
