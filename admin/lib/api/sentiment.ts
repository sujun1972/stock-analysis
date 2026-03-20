/**
 * @file lib/api/sentiment.ts
 * @description 市场情绪相关 API
 * @author Claude
 * @created 2024-03-20
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'
import type {
  MarketSentiment,
  LimitUpPool,
  DragonTigerRecord,
  TradingCalendar,
  SentimentStatistics,
} from '@/types/sentiment'

// ============== 类型定义 ==============

export interface SentimentListParams {
  page?: number
  limit?: number
  start_date?: string
  end_date?: string
}

export interface SyncSentimentBatchParams {
  start_date: string
  end_date: string
}

export interface DragonTigerListParams {
  date?: string
  stock_code?: string
  has_institution?: boolean
  page?: number
  limit?: number
}

export interface TradingCalendarParams {
  year?: number
  month?: number
}

// ============== API 类 ==============

export class SentimentApiClient extends BaseApiClient {
  /**
   * 获取情绪数据列表
   * @param params 查询参数
   * @returns 情绪数据列表
   */
  async getSentimentList(params?: SentimentListParams): Promise<ApiResponse<any>> {
    return this.get('/api/sentiment/list', { params })
  }

  /**
   * 获取指定日期情绪数据
   * @param date 日期 (YYYY-MM-DD)，不传则返回最新日期
   * @returns 情绪数据
   */
  async getSentimentDaily(date?: string): Promise<ApiResponse<any>> {
    return this.get('/api/sentiment/daily', { params: { date } })
  }

  /**
   * 手动触发同步情绪数据
   * @param date 日期 (YYYY-MM-DD)，不传则同步最新日期
   * @returns 同步结果
   */
  async syncSentimentData(date?: string): Promise<ApiResponse<any>> {
    return this.post('/api/sentiment/sync', null, { params: { date } })
  }

  /**
   * 批量同步情绪数据
   * @param params 批量同步参数（日期范围）
   * @returns 同步结果
   */
  async syncSentimentBatch(params: SyncSentimentBatchParams): Promise<ApiResponse<any>> {
    return this.post('/api/sentiment/sync/batch', null, { params })
  }

  /**
   * 查询同步任务状态
   * @param taskId 任务ID
   * @returns 任务状态
   */
  async getSyncTaskStatus(taskId: string): Promise<ApiResponse<any>> {
    return this.get(`/api/sentiment/sync/status/${taskId}`)
  }

  /**
   * 获取涨停板池
   * @param date 日期 (YYYY-MM-DD)，不传则返回最新日期
   * @returns 涨停板池数据
   */
  async getLimitUpPool(date?: string): Promise<ApiResponse<any>> {
    return this.get('/api/sentiment/limit-up', { params: { date } })
  }

  /**
   * 获取涨停趋势
   * @param days 天数，默认30天
   * @returns 涨停趋势数据
   */
  async getLimitUpTrend(days: number = 30): Promise<ApiResponse<any>> {
    return this.get('/api/sentiment/limit-up/trend', { params: { days } })
  }

  /**
   * 获取龙虎榜
   * @param params 查询参数
   * @returns 龙虎榜数据
   */
  async getDragonTigerList(params?: DragonTigerListParams): Promise<ApiResponse<any>> {
    return this.get('/api/sentiment/dragon-tiger', { params })
  }

  /**
   * 获取个股龙虎榜历史
   * @param stockCode 股票代码
   * @param days 查询天数，默认90天
   * @returns 个股龙虎榜历史数据
   */
  async getStockDragonTigerHistory(
    stockCode: string,
    days: number = 90
  ): Promise<ApiResponse<any>> {
    return this.get(`/api/sentiment/dragon-tiger/stock/${stockCode}`, { params: { days } })
  }

  /**
   * 获取交易日历
   * @param params 查询参数（年份、月份）
   * @returns 交易日历数据
   */
  async getTradingCalendar(params?: TradingCalendarParams): Promise<ApiResponse<any>> {
    return this.get('/api/sentiment/calendar', { params })
  }

  /**
   * 同步交易日历
   * @param years 年份数组
   * @returns 同步结果
   */
  async syncTradingCalendar(years: number[]): Promise<ApiResponse<any>> {
    return this.post('/api/sentiment/calendar/sync', null, {
      params: { years: years.join(',') }
    })
  }

  /**
   * 获取情绪统计分析
   * @param startDate 开始日期 (YYYY-MM-DD)
   * @param endDate 结束日期 (YYYY-MM-DD)
   * @returns 统计分析数据
   */
  async getSentimentStatistics(
    startDate: string,
    endDate: string
  ): Promise<ApiResponse<any>> {
    return this.get('/api/sentiment/statistics', {
      params: { start_date: startDate, end_date: endDate }
    })
  }
}

// ============== 单例导出 ==============

export const sentimentApi = new SentimentApiClient()
