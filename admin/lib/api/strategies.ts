/**
 * @file lib/api/strategies.ts
 * @description 策略相关 API
 * @author Claude
 * @created 2024-03-16
 * @updated 2024-03-16
 */

import { BaseApiClient } from './base'
import { ApiResponse, PaginatedResponse } from '@/types/api'
import {
  Strategy,
  CreateStrategyRequest,
  UpdateStrategyRequest,
  StrategyValidationResponse,
  StrategyTestResponse,
  BacktestResult,
  BacktestRequest,
  StrategyStatistics
} from '@/types'

export interface StrategyListParams {
  page?: number
  page_size?: number
  search?: string
  strategy_type?: string
  source_type?: string
  is_enabled?: boolean
  is_published?: boolean
  user_id?: number
  sort_by?: string
  sort_order?: string
}

export interface AssignStrategyRequest {
  user_id: number
  strategy_ids: number[]
}

/**
 * 策略 API 客户端
 */
export class StrategyApiClient extends BaseApiClient {
  /**
   * 获取策略列表
   */
  async getStrategies(params?: StrategyListParams): Promise<ApiResponse<PaginatedResponse<Strategy>>> {
    return this.get('/api/strategies', { params })
  }

  /**
   * 获取单个策略详情
   */
  async getStrategy(id: number): Promise<ApiResponse<Strategy>> {
    return this.get(`/api/strategies/${id}`)
  }

  /**
   * 创建策略
   */
  async createStrategy(data: CreateStrategyRequest): Promise<ApiResponse<Strategy>> {
    return this.post('/api/strategies', data)
  }

  /**
   * 更新策略
   */
  async updateStrategy(id: number, data: UpdateStrategyRequest): Promise<ApiResponse<Strategy>> {
    return this.patch(`/api/strategies/${id}`, data)
  }

  /**
   * 删除策略
   */
  async deleteStrategy(id: number): Promise<ApiResponse<{ message: string }>> {
    return this.delete(`/api/strategies/${id}`)
  }

  /**
   * 批量删除策略
   */
  async batchDeleteStrategies(ids: number[]): Promise<ApiResponse<{
    deleted_count: number
    failed_ids: number[]
  }>> {
    return this.post('/api/strategies/batch-delete', { ids })
  }

  /**
   * 验证策略代码
   */
  async validateStrategy(code: string): Promise<ApiResponse<StrategyValidationResponse>> {
    return this.post('/api/strategies/validate', { code })
  }

  /**
   * 测试策略
   */
  async testStrategy(id: number, params?: {
    stock_codes?: string[]
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<StrategyTestResponse>> {
    return this.post(`/api/strategies/${id}/test`, params)
  }

  /**
   * 运行策略回测
   */
  async runBacktest(data: BacktestRequest): Promise<ApiResponse<BacktestResult>> {
    return this.post('/api/strategies/backtest', data)
  }

  /**
   * 启用/禁用策略
   */
  async toggleStrategy(id: number, enabled: boolean): Promise<ApiResponse<Strategy>> {
    return this.patch(`/api/strategies/${id}`, { is_enabled: enabled })
  }

  /**
   * 发布/取消发布策略
   */
  async togglePublish(id: number, published: boolean): Promise<ApiResponse<Strategy>> {
    return this.patch(`/api/strategies/${id}`, { is_published: published })
  }

  /**
   * 复制策略
   */
  async cloneStrategy(id: number, newName: string): Promise<ApiResponse<Strategy>> {
    return this.post(`/api/strategies/${id}/clone`, { name: newName })
  }

  /**
   * 获取策略统计信息
   */
  async getStrategyStatistics(id: number): Promise<ApiResponse<StrategyStatistics>> {
    return this.get(`/api/strategies/${id}/statistics`)
  }

  /**
   * 获取用户策略列表
   */
  async getUserStrategies(userId: number, params?: {
    page?: number
    page_size?: number
  }): Promise<ApiResponse<PaginatedResponse<Strategy>>> {
    return this.get(`/api/users/${userId}/strategies`, { params })
  }

  /**
   * 分配策略给用户
   */
  async assignStrategiesToUser(data: AssignStrategyRequest): Promise<ApiResponse<{
    assigned_count: number
    failed_ids: number[]
  }>> {
    return this.post('/api/strategies/assign', data)
  }

  /**
   * 移除用户策略
   */
  async removeUserStrategy(userId: number, strategyId: number): Promise<ApiResponse<{ message: string }>> {
    return this.delete(`/api/users/${userId}/strategies/${strategyId}`)
  }

  /**
   * 获取策略类型列表
   */
  async getStrategyTypes(): Promise<ApiResponse<Array<{
    value: string
    label: string
    description?: string
  }>>> {
    return this.get('/api/strategies/types')
  }

  /**
   * 导出策略
   */
  async exportStrategy(id: number, format: 'json' | 'python' = 'json'): Promise<ApiResponse<{
    filename: string
    content: string
  }>> {
    return this.get(`/api/strategies/${id}/export`, {
      params: { format }
    })
  }

  /**
   * 导入策略
   */
  async importStrategy(file: File): Promise<ApiResponse<Strategy>> {
    const formData = new FormData()
    formData.append('file', file)

    return this.post('/api/strategies/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  }

  /**
   * 获取策略执行日志
   */
  async getStrategyLogs(id: number, params?: {
    page?: number
    page_size?: number
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<PaginatedResponse<{
    id: number
    strategy_id: number
    execution_time: string
    status: 'success' | 'failed' | 'error'
    message?: string
    result?: any
    duration_ms?: number
  }>>> {
    return this.get(`/api/strategies/${id}/logs`, { params })
  }

  /**
   * 清理策略执行日志
   */
  async clearStrategyLogs(id: number, beforeDate?: string): Promise<ApiResponse<{
    deleted_count: number
  }>> {
    return this.delete(`/api/strategies/${id}/logs`, {
      params: { before_date: beforeDate }
    })
  }
}

export const strategyApi = new StrategyApiClient()