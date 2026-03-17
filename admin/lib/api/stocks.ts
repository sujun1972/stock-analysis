/**
 * @file lib/api/stocks.ts
 * @description 股票相关 API
 * @author Claude
 * @created 2024-03-16
 * @updated 2024-03-16
 */

import { BaseApiClient } from './base'
import { ApiResponse, PaginatedResponse, PaginatedData } from '@/types/api'
import { StockInfo, StockDaily, MinuteData, Concept } from '@/types'

export interface StockListParams {
  market?: string
  industry?: string
  status?: string
  skip?: number
  limit?: number
  search?: string
  concepts?: string
  sort_by?: string
  sort_order?: string
}

export interface UpdateStockRequest {
  name?: string
  market?: string
  industry?: string
  status?: string
  list_date?: string
  concepts?: number[]
}

export interface StockConceptRequest {
  stock_code: string
  concept_ids: number[]
}

/**
 * 股票 API 客户端
 */
export class StockApiClient extends BaseApiClient {
  /**
   * 获取股票列表
   */
  async getStockList(params?: StockListParams): Promise<PaginatedResponse<StockInfo>> {
    const response = await this.get<ApiResponse<PaginatedData<StockInfo>>>('/api/stocks', { params })
    return response || { code: 200, message: 'OK', data: { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 } }
  }

  /**
   * 获取单个股票信息
   */
  async getStock(code: string): Promise<StockInfo> {
    const response = await this.get<ApiResponse<PaginatedData<StockInfo>>>('/api/stocks', {
      params: { search: code, limit: 1 }
    })

    if (!response.data?.items?.[0]) {
      throw new Error(`未找到股票 ${code}`)
    }

    return response.data.items[0]
  }

  /**
   * 更新股票信息
   */
  async updateStock(code: string, data: UpdateStockRequest): Promise<ApiResponse<StockInfo>> {
    return this.patch(`/api/stocks/${code}`, data)
  }

  /**
   * 更新股票列表
   */
  async updateStockList(): Promise<ApiResponse<{ total: number }>> {
    return this.post('/api/stocks/sync')
  }

  /**
   * 获取股票概念列表
   */
  async getStockConcepts(code: string): Promise<ApiResponse<Concept[]>> {
    return this.get(`/api/stocks/${code}/concepts`)
  }

  /**
   * 更新股票概念
   */
  async updateStockConcepts(code: string, conceptIds: number[]): Promise<ApiResponse<{ message: string }>> {
    return this.post(`/api/stocks/${code}/concepts`, { concept_ids: conceptIds })
  }

  /**
   * 批量更新股票概念
   */
  async batchUpdateStockConcepts(updates: StockConceptRequest[]): Promise<ApiResponse<{
    success: number
    failed: number
    errors: string[]
  }>> {
    return this.post('/api/stocks/concepts/batch', { updates })
  }

  /**
   * 获取股票日K线数据
   */
  async getStockDaily(code: string, params?: {
    start_date?: string
    end_date?: string
    limit?: number
  }): Promise<ApiResponse<StockDaily[]>> {
    return this.get(`/api/stocks/${code}/daily`, { params })
  }

  /**
   * 获取股票分钟线数据
   */
  async getStockMinute(code: string, params?: {
    date?: string
    interval?: string
  }): Promise<ApiResponse<MinuteData[]>> {
    return this.get(`/api/stocks/${code}/minute`, { params })
  }

  /**
   * 同步股票数据
   */
  async syncStockData(code: string, dataType: 'daily' | 'minute' | 'features'): Promise<ApiResponse<{
    message: string
    count?: number
  }>> {
    return this.post(`/api/stocks/${code}/sync/${dataType}`)
  }

  /**
   * 批量同步股票数据
   */
  async batchSyncStockData(codes: string[], dataType: 'daily' | 'minute' | 'features'): Promise<ApiResponse<{
    success: string[]
    failed: string[]
    total: number
  }>> {
    return this.post('/api/stocks/sync/batch', {
      codes,
      data_type: dataType
    })
  }

  /**
   * 获取股票行业分类
   */
  async getIndustries(): Promise<ApiResponse<string[]>> {
    return this.get('/api/stocks/industries')
  }

  /**
   * 获取股票市场列表
   */
  async getMarkets(): Promise<ApiResponse<string[]>> {
    return this.get('/api/stocks/markets')
  }

  /**
   * 搜索股票
   */
  async searchStocks(keyword: string, limit: number = 10): Promise<ApiResponse<StockInfo[]>> {
    return this.get('/api/stocks/search', {
      params: { keyword, limit }
    })
  }
}

export const stockApi = new StockApiClient()