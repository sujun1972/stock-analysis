/**
 * 公司公告 API 客户端（news_anns Phase 1）
 * 数据源：AkShare 东方财富聚合（免费，替代 Tushare anns_d）
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'


export interface StockAnnsItem {
  ts_code: string
  ann_date: string        // YYYY-MM-DD
  title: string
  anno_type: string | null
  stock_name: string | null
  url: string | null
  source: string
  has_content: boolean
  content_fetched_at: string | null
  created_at?: string | null
}


export interface AnnoTypeStat {
  anno_type: string
  count: number
}


export interface StockAnnsQueryParams {
  ts_code?: string
  start_date?: string  // YYYY-MM-DD
  end_date?: string    // YYYY-MM-DD
  anno_type?: string
  keyword?: string
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: 'asc' | 'desc'
}


export interface StockAnnsListResponse {
  items: StockAnnsItem[]
  total: number
  anno_types: AnnoTypeStat[]
  page: number
  page_size: number
}


export interface StockAnnsContent {
  ts_code: string
  ann_date: string
  title: string
  content: string | null
  content_fetched_at: string | null
  url: string | null
  anno_type: string | null
}


export interface FetchContentEntry {
  ts_code?: string
  ann_date?: string
  title?: string
  url: string
}


export class StockAnnsApiClient extends BaseApiClient {
  /** 分页查询公告列表（支持筛选 + 排序） */
  async getData(params?: StockAnnsQueryParams): Promise<ApiResponse<StockAnnsListResponse>> {
    return this.get('/api/stock-anns', { params })
  }

  /** 近 N 天出现过的公告类型 + 计数（下拉筛选用） */
  async getAnnoTypes(days: number = 90, limit: number = 200): Promise<ApiResponse<{
    items: AnnoTypeStat[]
    days: number
  }>> {
    return this.get('/api/stock-anns/anno-types', { params: { days, limit } })
  }

  /** 单只股票近 N 天公告 */
  async getByStock(ts_code: string, days: number = 30, limit: number = 50): Promise<ApiResponse<{
    ts_code: string
    days: number
    items: StockAnnsItem[]
    total: number
  }>> {
    return this.get(`/api/stock-anns/stock/${encodeURIComponent(ts_code)}`, {
      params: { days, limit },
    })
  }

  /** 读取已抓取的公告正文 */
  async getContent(ts_code: string, ann_date: string, title: string): Promise<ApiResponse<StockAnnsContent>> {
    return this.get('/api/stock-anns/content', {
      params: { ts_code, ann_date, title },
    })
  }

  /** 增量同步（盘后统一）— 对应 useDataPage 的 syncFn 签名 */
  async syncAsync(_params?: Record<string, unknown>): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
  }>> {
    return this.post('/api/stock-anns/sync-async', null)
  }

  /** 全量历史同步（可指定起始日期缩短覆盖） */
  async syncFullHistory(params?: {
    concurrency?: number
    start_date?: string  // YYYY-MM-DD（覆盖默认 20200101）
  }): Promise<ApiResponse<{ celery_task_id: string }>> {
    return this.post('/api/stock-anns/sync-full-history', null, { params })
  }

  /** 被动同步单只股票（前端点击"刷新"按钮，或 AI 分析弹窗前静默触发） */
  async syncByStock(ts_code: string, days: number = 90): Promise<ApiResponse<{
    celery_task_id: string
  }>> {
    return this.post(`/api/stock-anns/sync/${encodeURIComponent(ts_code)}`, null, {
      params: { days },
    })
  }

  /** 按需抓取公告正文（限流：单次 5 个 URL，间隔 2 秒） */
  async fetchContent(entries: FetchContentEntry[], write_back: boolean = true): Promise<ApiResponse<{
    requested: number
    processed: number
    succeeded: number
    results: Array<{
      ts_code: string | null
      ann_date: string | null
      title: string | null
      url: string
      content: string | null
      ok: boolean
    }>
  }>> {
    return this.post('/api/stock-anns/fetch-content', { entries, write_back })
  }
}


export const stockAnnsApi = new StockAnnsApiClient()
