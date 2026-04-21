/**
 * 宏观经济指标 API 客户端
 * 数据源：AkShare 免费宏观接口（CPI / PPI / PMI / M2 / 社融 / GDP / Shibor）
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'


export interface MacroIndicatorItem {
  indicator_code: string
  period_date: string         // YYYY-MM-DD
  value: number | null
  yoy: number | null
  mom: number | null
  publish_date: string | null
  source: string
  raw?: Record<string, unknown> | null
  created_at?: string | null
  updated_at?: string | null
}


export interface MacroIndicatorSummary {
  indicator_code: string
  count: number
  earliest: string | null
  latest: string | null
  last_updated: string | null
}


export interface MacroIndicatorQueryParams {
  indicator_code?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
  sort_by?: 'period_date' | 'publish_date' | 'indicator_code'
  sort_order?: 'asc' | 'desc'
}


export interface MacroIndicatorListResponse {
  items: MacroIndicatorItem[]
  total: number
  summary: MacroIndicatorSummary[]
  page: number
  page_size: number
}


export interface MacroIndicatorSeriesResponse {
  indicator_code: string
  items: MacroIndicatorItem[]
  total: number
}


export interface MacroSnapshotLatest {
  indicator_code: string
  period_date: string
  value: number | null
  yoy: number | null
  mom: number | null
  publish_date: string | null
  lag_days: number | null
  raw?: Record<string, unknown> | null
}


export interface MacroSnapshotResponse {
  latest: Record<string, MacroSnapshotLatest>
  series: Record<string, MacroIndicatorItem[]>
  indicators: string[]
  lookback_months: number
}


/** 前端展示用：中文标签 + 单位（与后端 INDICATOR_FETCHERS 对齐） */
export const MACRO_INDICATOR_LABELS: Record<string, { label: string; unit: string; desc: string; frequency: string }> = {
  cpi_yoy:           { label: 'CPI 同比',     unit: '%',   desc: '消费者物价指数月度同比',   frequency: 'monthly' },
  ppi_yoy:           { label: 'PPI 同比',     unit: '%',   desc: '生产者物价指数月度同比',   frequency: 'monthly' },
  pmi_manu:          { label: 'PMI 制造业',   unit: '',    desc: '制造业采购经理指数（50 为荣枯线）', frequency: 'monthly' },
  pmi_nonmanu:       { label: 'PMI 非制造业', unit: '',    desc: '非制造业采购经理指数',      frequency: 'monthly' },
  m2_yoy:            { label: 'M2 同比',      unit: '%',   desc: '货币供应 M2 月度同比',      frequency: 'monthly' },
  new_credit_month:  { label: '新增社融',     unit: '亿元', desc: '新增社会融资当月值',        frequency: 'monthly' },
  gdp_yoy:           { label: 'GDP 同比',     unit: '%',   desc: 'GDP 季度同比',              frequency: 'quarterly' },
  shibor_on:         { label: 'Shibor O/N',   unit: '%',   desc: '隔夜 Shibor 利率',          frequency: 'daily' },
  shibor_1w:         { label: 'Shibor 1W',    unit: '%',   desc: '1 周 Shibor 利率',          frequency: 'daily' },
  shibor_1m:         { label: 'Shibor 1M',    unit: '%',   desc: '1 月 Shibor 利率',          frequency: 'daily' },
}


export class MacroIndicatorsApiClient extends BaseApiClient {
  async getData(params?: MacroIndicatorQueryParams): Promise<ApiResponse<MacroIndicatorListResponse>> {
    return this.get('/api/macro-indicators', { params })
  }

  async getSeries(
    indicatorCode: string,
    params?: { start_date?: string; end_date?: string; limit?: number }
  ): Promise<ApiResponse<MacroIndicatorSeriesResponse>> {
    return this.get(`/api/macro-indicators/series/${encodeURIComponent(indicatorCode)}`, { params })
  }

  async getSnapshot(lookbackMonths: number = 12): Promise<ApiResponse<MacroSnapshotResponse>> {
    return this.get('/api/macro-indicators/snapshot', {
      params: { lookback_months: lookbackMonths },
    })
  }

  async syncAsync(_params?: Record<string, unknown>): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
  }>> {
    return this.post('/api/macro-indicators/sync-async', null)
  }

  async syncFullHistory(params?: {
    concurrency?: number
    start_date?: string
  }): Promise<ApiResponse<{ celery_task_id: string }>> {
    return this.post('/api/macro-indicators/sync-full-history', null, { params })
  }
}


export const macroIndicatorsApi = new MacroIndicatorsApiClient()
