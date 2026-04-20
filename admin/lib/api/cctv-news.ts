/**
 * 新闻联播 API 客户端（news_anns Phase 2）
 * 数据源：AkShare news_cctv（按自然日）
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'


export interface CctvNewsItem {
  news_date: string    // YYYY-MM-DD
  seq_no: number
  title: string
  content: string | null
  created_at: string | null
}


export interface CctvNewsDateStat {
  news_date: string
  count: number
}


export interface CctvNewsQueryParams {
  start_date?: string
  end_date?: string
  keyword?: string
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}


export interface CctvNewsListResponse {
  items: CctvNewsItem[]
  total: number
  dates: CctvNewsDateStat[]
  page: number
  page_size: number
}


export class CctvNewsApiClient extends BaseApiClient {
  async getData(params?: CctvNewsQueryParams): Promise<ApiResponse<CctvNewsListResponse>> {
    return this.get('/api/cctv-news', { params })
  }

  async getByDate(news_date: string, limit: number = 50): Promise<ApiResponse<{
    news_date: string
    items: CctvNewsItem[]
    total: number
  }>> {
    return this.get(`/api/cctv-news/by-date/${encodeURIComponent(news_date)}`, {
      params: { limit },
    })
  }

  async syncAsync(_params?: Record<string, unknown>): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
  }>> {
    return this.post('/api/cctv-news/sync-async', null)
  }

  async syncFullHistory(params?: {
    concurrency?: number
    start_date?: string  // YYYY-MM-DD
  }): Promise<ApiResponse<{ celery_task_id: string }>> {
    return this.post('/api/cctv-news/sync-full-history', null, { params })
  }
}


export const cctvNewsApi = new CctvNewsApiClient()
