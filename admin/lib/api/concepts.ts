/**
 * @file lib/api/concepts.ts
 * @description 概念板块相关 API
 * @author Claude
 * @created 2024-03-20
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'
import type { Concept } from '@/types'

// ============== 类型定义 ==============

export interface ConceptListParams {
  page?: number
  limit?: number
  search?: string
}

export interface ConceptStocksParams {
  page?: number
  limit?: number
}

export interface UpdateConceptRequest {
  name?: string
  description?: string
  stock_codes?: string[]
}

// ============== API 类 ==============

export class ConceptsApiClient extends BaseApiClient {
  /**
   * 获取概念列表
   * @param params 查询参数
   * @returns 概念列表
   */
  async getConcepts(params?: ConceptListParams): Promise<ApiResponse<Concept[]>> {
    return this.get('/api/concepts', { params })
  }

  /**
   * 获取概念详情
   * @param conceptId 概念ID
   * @returns 概念详情
   */
  async getConcept(conceptId: number): Promise<ApiResponse<Concept>> {
    return this.get(`/api/concepts/${conceptId}`)
  }

  /**
   * 获取概念下的股票列表
   * @param conceptId 概念ID
   * @param params 查询参数
   * @returns 股票列表
   */
  async getConceptStocks(conceptId: number, params?: ConceptStocksParams): Promise<ApiResponse<any[]>> {
    return this.get(`/api/concepts/${conceptId}/stocks`, { params })
  }

  /**
   * 同步概念数据
   * @returns 同步结果
   */
  async syncConcepts(): Promise<ApiResponse<{ total: number }>> {
    return this.post('/api/concepts/sync')
  }

  /**
   * 更新概念信息
   * @param conceptId 概念ID
   * @param data 更新数据
   * @returns 更新结果
   */
  async updateConcept(conceptId: number, data: UpdateConceptRequest): Promise<ApiResponse<any>> {
    return this.put(`/api/concepts/${conceptId}`, data)
  }

  /**
   * 删除概念
   * @param conceptId 概念ID
   * @returns 删除结果
   */
  async deleteConcept(conceptId: number): Promise<ApiResponse<any>> {
    return this.delete(`/api/concepts/${conceptId}`)
  }
}

// ============== 单例导出 ==============

export const conceptsApi = new ConceptsApiClient()
