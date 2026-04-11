/**
 * 提示词模板管理 API 客户端
 */

import { apiClient } from './api-client'
import type {
  PromptTemplate,
  PromptTemplateCreate,
  PromptTemplateUpdate,
  PromptTemplateVersionCreate,
  PromptTemplatePreviewRequest,
  PromptTemplatePreviewResponse,
  PromptTemplateStatistics,
  PromptTemplateHistory,
  PromptTemplateListResponse,
} from '@/types/prompt-template'

/**
 * 提示词模板API客户端
 * 使用 apiClient 确保所有请求都带有认证 token
 */
export const promptTemplateApi = {
  /**
   * 获取提示词模板列表
   */
  list: async (params?: {
    business_type?: string
    is_active?: boolean
    skip?: number
    limit?: number
  }): Promise<PromptTemplateListResponse> => {
    const response = await apiClient.get('/api/prompt-templates/', { params })
    // apiClient.get 返回 ApiResponse<T> 格式: { code, message, data }
    // 实际的模板列表数据在 response.data 中
    return response.data as PromptTemplateListResponse
  },

  /**
   * 获取模板详情
   */
  get: async (id: number): Promise<PromptTemplate> => {
    const response = await apiClient.get(`/api/prompt-templates/${id}`)
    return response.data
  },

  /**
   * 创建新模板
   */
  create: async (data: PromptTemplateCreate): Promise<PromptTemplate> => {
    const response = await apiClient.post('/api/prompt-templates/', data)
    return response.data
  },

  /**
   * 更新模板
   */
  update: async (id: number, data: PromptTemplateUpdate): Promise<PromptTemplate> => {
    const response = await apiClient.put(`/api/prompt-templates/${id}`, data)
    return response.data
  },

  /**
   * 删除模板
   */
  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/prompt-templates/${id}`)
  },

  /**
   * 基于现有模板创建新版本
   */
  createVersion: async (
    id: number,
    data: PromptTemplateVersionCreate
  ): Promise<PromptTemplate> => {
    const response = await apiClient.post(`/api/prompt-templates/${id}/versions`, data)
    return response.data
  },

  /**
   * 激活模板
   */
  activate: async (id: number, setAsDefault: boolean = false): Promise<PromptTemplate> => {
    const response = await apiClient.post(
      `/api/prompt-templates/${id}/activate`,
      null,
      { params: { set_as_default: setAsDefault } }
    )
    return response.data
  },

  /**
   * 停用模板
   */
  deactivate: async (id: number): Promise<PromptTemplate> => {
    const response = await apiClient.post(`/api/prompt-templates/${id}/deactivate`)
    return response.data
  },

  /**
   * 预览渲染后的提示词
   */
  preview: async (
    id: number,
    variables: Record<string, any>
  ): Promise<PromptTemplatePreviewResponse> => {
    const response = await apiClient.post(`/api/prompt-templates/${id}/preview`, { variables })
    return response.data
  },

  /**
   * 获取模板的性能统计
   */
  getStatistics: async (id: number): Promise<PromptTemplateStatistics> => {
    const response = await apiClient.get(`/api/prompt-templates/${id}/statistics`)
    return response.data
  },

  /**
   * 获取模板的修改历史
   */
  getHistory: async (id: number, limit: number = 50): Promise<PromptTemplateHistory[]> => {
    const response = await apiClient.get(`/api/prompt-templates/${id}/history`, {
      params: { limit }
    })
    return response.data
  },

  /**
   * 获取所有业务类型
   */
  getBusinessTypes: async (): Promise<string[]> => {
    const response = await apiClient.get('/api/prompt-templates/business-types/all/')
    return response.data
  },

  // ── by-key 方法（通过 template_key 操作，稳定引用系统内置模板）────────

  /**
   * 通过 template_key 获取模板详情
   */
  getByKey: async (key: string): Promise<PromptTemplate> => {
    const response = await apiClient.get(`/api/prompt-templates/by-key/${key}`)
    return response.data
  },

  /**
   * 通过 template_key 更新模板
   */
  updateByKey: async (key: string, data: PromptTemplateUpdate): Promise<PromptTemplate> => {
    const response = await apiClient.put(`/api/prompt-templates/by-key/${key}`, data)
    return response.data
  },

  /**
   * 通过 template_key 删除模板
   */
  deleteByKey: async (key: string): Promise<void> => {
    await apiClient.delete(`/api/prompt-templates/by-key/${key}`)
  },

  /**
   * 通过 template_key 激活模板
   */
  activateByKey: async (key: string, setAsDefault: boolean = false): Promise<PromptTemplate> => {
    const response = await apiClient.post(
      `/api/prompt-templates/by-key/${key}/activate`,
      null,
      { params: { set_as_default: setAsDefault } }
    )
    return response.data
  },

  /**
   * 通过 template_key 停用模板
   */
  deactivateByKey: async (key: string): Promise<PromptTemplate> => {
    const response = await apiClient.post(`/api/prompt-templates/by-key/${key}/deactivate`)
    return response.data
  },

  /**
   * 通过 template_key 创建新版本
   */
  createVersionByKey: async (
    key: string,
    data: PromptTemplateVersionCreate
  ): Promise<PromptTemplate> => {
    const response = await apiClient.post(`/api/prompt-templates/by-key/${key}/versions`, data)
    return response.data
  },

  /**
   * 通过 template_key 预览渲染后的提示词
   */
  previewByKey: async (
    key: string,
    variables: Record<string, any>
  ): Promise<PromptTemplatePreviewResponse> => {
    const response = await apiClient.post(`/api/prompt-templates/by-key/${key}/preview`, { variables })
    return response.data
  },

  /**
   * 通过 template_key 获取模板的性能统计
   */
  getStatisticsByKey: async (key: string): Promise<PromptTemplateStatistics> => {
    const response = await apiClient.get(`/api/prompt-templates/by-key/${key}/statistics`)
    return response.data
  },

  /**
   * 通过 template_key 获取模板的修改历史
   */
  getHistoryByKey: async (key: string, limit: number = 50): Promise<PromptTemplateHistory[]> => {
    const response = await apiClient.get(`/api/prompt-templates/by-key/${key}/history`, {
      params: { limit }
    })
    return response.data
  },
}
