/**
 * 股票AI分析结果 API 客户端
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

/**
 * 查询参数
 */
export interface StockAiAnalysisParams {
  ts_code?: string
  analysis_type?: string
  ai_provider?: string
  trade_date?: string
  sort_by?: string
  sort_order?: string
  limit?: number
  offset?: number
}

/**
 * 分析记录
 */
export interface StockAiAnalysisData {
  id: number
  ts_code: string
  analysis_type: string
  analysis_text: string
  score: number | null
  prompt_text: string | null
  ai_provider: string | null
  ai_model: string | null
  version: number
  created_by: number | null
  created_at: string
  updated_at: string
  trade_date: string | null
}

/**
 * 股票AI分析结果 API 客户端
 */
export class StockAiAnalysisApiClient extends BaseApiClient {
  /**
   * 查询分析记录列表（分页）
   */
  async getList(params?: StockAiAnalysisParams): Promise<ApiResponse<{
    items: StockAiAnalysisData[]
    total: number
  }>> {
    return this.get('/api/stock-ai-analysis/list', { params })
  }

  /** 删除单条分析记录 */
  async deleteRecord(recordId: number): Promise<ApiResponse<null>> {
    return this.delete(`/api/stock-ai-analysis/${recordId}`)
  }

  /** 清空全部分析记录 */
  async clearAll(): Promise<ApiResponse<any>> {
    return this.post('/api/data/clear/stock_ai_analysis')
  }
}

// 导出单例实例
export const stockAiAnalysisApi = new StockAiAnalysisApiClient()
