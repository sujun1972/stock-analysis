/**
 * @file lib/api/sentiment.ts
 * @description 市场情绪相关 API
 * @author Claude
 * @created 2024-03-20
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'
import type {
  TradingCalendar,
} from '@/types/sentiment'

// ============== 类型定义 ==============

export interface SyncSentimentBatchParams {
  start_date: string
  end_date: string
}

export interface TradingCalendarParams {
  year?: number
  month?: number
}

// ============== API 类 ==============

export class SentimentApiClient extends BaseApiClient {
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
}

// ============== 单例导出 ==============

export const sentimentApi = new SentimentApiClient()
