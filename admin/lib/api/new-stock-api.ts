import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface NewStockParams {
  start_date?: string
  end_date?: string
  limit?: number
  offset?: number
}

/** new_stocks 表字段（对应 Tushare new_share 接口） */
export interface NewStockData {
  ts_code:       string
  sub_code:      string | null
  name:          string
  ipo_date:      string | null   // 上网发行日期 YYYYMMDD
  issue_date:    string | null   // 上市日期 YYYYMMDD
  amount:        number | null   // 发行总量（万股）
  market_amount: number | null   // 上网发行量（万股）
  price:         number | null   // 发行价格
  pe:            number | null   // 发行市盈率
  limit_amount:  number | null   // 个人申购上限（万股）
  funds:         number | null   // 募集资金（亿元）
  ballot:        number | null   // 中签率
}

export interface NewStockStatistics {
  total_count:    number
  recent_7_days:  number
  recent_30_days: number
  recent_90_days: number
}

export class NewStockApiClient extends BaseApiClient {
  async getData(params?: NewStockParams): Promise<ApiResponse<{
    items: NewStockData[]
    total: number
  }>> {
    return this.get('/api/new-stocks', { params })
  }

  async getStatistics(): Promise<ApiResponse<NewStockStatistics>> {
    return this.get('/api/new-stocks/statistics')
  }

  async syncAsync(params?: { days?: number; start_date?: string; end_date?: string }): Promise<ApiResponse<{
    celery_task_id: string
    task_name: string
    display_name: string
    status: string
  }>> {
    return this.post('/api/new-stocks/sync-async', null, { params })
  }
}

export const newStockApi = new NewStockApiClient()
