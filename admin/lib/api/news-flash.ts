/**
 * 财经快讯 API 客户端（news_anns Phase 2）
 * 数据源：AkShare 财新要闻精选（stock_news_main_cx）+ 东财个股新闻（stock_news_em）
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'


export interface NewsFlashItem {
  id: number
  publish_time: string          // ISO 8601
  source: string                // caixin / eastmoney
  title: string
  summary: string | null
  url: string | null
  tags: string[]
  related_ts_codes: string[]
  created_at: string | null
  // 舆情打分字段（未打分时全部为 null）
  sentiment_score?: number | null
  sentiment_impact?: 'bullish' | 'bearish' | 'neutral' | null
  sentiment_tags?: string[] | null
  scoring_reason?: string | null
  score_model?: string | null
  scored_at?: string | null
}


export interface NewsFlashSourceStat {
  source: string
  count: number
  last_publish_time: string | null
}


export interface NewsFlashQueryParams {
  source?: string
  start_time?: string
  end_time?: string
  ts_code?: string
  keyword?: string
  tag?: string
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}


export interface NewsFlashListResponse {
  items: NewsFlashItem[]
  total: number
  sources: NewsFlashSourceStat[]
  page: number
  page_size: number
}


export class NewsFlashApiClient extends BaseApiClient {
  /** 分页查询快讯列表 */
  async getData(params?: NewsFlashQueryParams): Promise<ApiResponse<NewsFlashListResponse>> {
    return this.get('/api/news-flash', { params })
  }

  /** 单只股票近 N 天关联快讯 */
  async getByStock(ts_code: string, days: number = 7, limit: number = 50): Promise<ApiResponse<{
    ts_code: string
    days: number
    items: NewsFlashItem[]
    total: number
  }>> {
    return this.get(`/api/news-flash/stock/${encodeURIComponent(ts_code)}`, {
      params: { days, limit },
    })
  }

  /** 增量同步（财新要闻） */
  async syncAsync(_params?: Record<string, unknown>): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
  }>> {
    return this.post('/api/news-flash/sync-async', null)
  }

  /** 全量（快讯接口无历史参数，退化为一次增量） */
  async syncFullHistory(params?: {
    concurrency?: number
  }): Promise<ApiResponse<{ celery_task_id: string }>> {
    return this.post('/api/news-flash/sync-full-history', null, { params })
  }

  /** 被动同步单只（东财个股新闻） */
  async syncByStock(ts_code: string, days: number = 7): Promise<ApiResponse<{
    celery_task_id: string
  }>> {
    return this.post(`/api/news-flash/sync/${encodeURIComponent(ts_code)}`, null, {
      params: { days },
    })
  }
}


export const newsFlashApi = new NewsFlashApiClient()
