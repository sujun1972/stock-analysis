/**
 * @file lib/api/config.ts
 * @description 系统配置相关 API
 * @author Claude
 * @created 2024-03-20
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

// ============== 类型定义 ==============

export interface DataSourceConfig {
  tushare_token: string
  earliest_history_date?: string
}

export interface UpdateDataSourceConfigRequest {
  tushare_token?: string
  earliest_history_date?: string
}

export interface AIProviderConfig {
  provider: string
  display_name: string
  api_key: string
  api_base_url?: string
  model_name?: string
  max_tokens?: number
  temperature?: number
  is_active?: boolean
  is_default?: boolean
  priority?: number
  rate_limit?: number
  timeout?: number
  description?: string
}

// ============== API 类 ==============

export class ConfigApiClient extends BaseApiClient {
  // ========== 数据源配置 ==========

  /**
   * 获取数据源配置
   * @returns 数据源配置
   */
  async getDataSourceConfig(): Promise<ApiResponse<DataSourceConfig>> {
    return this.get('/api/config/source')
  }

  /**
   * 更新数据源配置
   * @param params 配置参数
   * @returns 更新结果
   */
  async updateDataSourceConfig(params: UpdateDataSourceConfigRequest): Promise<ApiResponse<any>> {
    return this.post('/api/config/source', params)
  }

  /**
   * 获取所有系统配置
   * @returns 系统配置
   */
  async getAllConfigs(): Promise<ApiResponse<Record<string, any>>> {
    return this.get('/api/config/all')
  }

  // ========== AI 提供商配置 ==========

  /**
   * 获取 AI 提供商列表
   * @returns AI 提供商列表
   */
  async getAIProviders(): Promise<ApiResponse<any[]>> {
    return this.get('/api/ai-strategy/providers')
  }

  /**
   * 获取单个 AI 提供商详情
   * @param provider 提供商标识
   * @returns 提供商详情
   */
  async getAIProvider(provider: string): Promise<ApiResponse<any>> {
    return this.get(`/api/ai-strategy/providers/${provider}`)
  }

  /**
   * 创建 AI 提供商
   * @param data 提供商配置
   * @returns 创建结果
   */
  async createAIProvider(data: AIProviderConfig): Promise<ApiResponse<{ id: number }>> {
    return this.post('/api/ai-strategy/providers', data)
  }

  /**
   * 更新 AI 提供商
   * @param provider 提供商标识
   * @param data 更新数据
   * @returns 更新结果
   */
  async updateAIProvider(provider: string, data: Partial<AIProviderConfig>): Promise<ApiResponse<any>> {
    return this.put(`/api/ai-strategy/providers/${provider}`, data)
  }

  /**
   * 删除 AI 提供商
   * @param provider 提供商标识
   * @returns 删除结果
   */
  async deleteAIProvider(provider: string): Promise<ApiResponse<{ message: string }>> {
    return this.delete(`/api/ai-strategy/providers/${provider}`)
  }

  /**
   * 测试 AI 提供商连接
   * @param provider 提供商标识
   * @returns 测试结果
   */
  async testAIProvider(provider: string): Promise<ApiResponse<{
    success: boolean
    message: string
    response_time?: number
  }>> {
    return this.post(`/api/ai-strategy/providers/${provider}/test`)
  }

  /**
   * 设置默认 AI 提供商
   * @param provider 提供商标识
   * @returns 设置结果
   */
  async setDefaultAIProvider(provider: string): Promise<ApiResponse<any>> {
    return this.post(`/api/ai-strategy/providers/${provider}/set-default`)
  }
}

// ============== 单例导出 ==============

export const configApi = new ConfigApiClient()
