/**
 * 提示词模板管理 API 客户端
 */

import axios from 'axios'
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

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * 提示词模板API客户端
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
    const response = await axios.get(`${API_BASE_URL}/api/prompt-templates`, {
      params,
      withCredentials: true,
    })
    return response.data
  },

  /**
   * 获取模板详情
   */
  get: async (id: number): Promise<PromptTemplate> => {
    const response = await axios.get(`${API_BASE_URL}/api/prompt-templates/${id}`, {
      withCredentials: true,
    })
    return response.data
  },

  /**
   * 创建新模板
   */
  create: async (data: PromptTemplateCreate): Promise<PromptTemplate> => {
    const response = await axios.post(`${API_BASE_URL}/api/prompt-templates`, data, {
      withCredentials: true,
    })
    return response.data
  },

  /**
   * 更新模板
   */
  update: async (id: number, data: PromptTemplateUpdate): Promise<PromptTemplate> => {
    const response = await axios.put(`${API_BASE_URL}/api/prompt-templates/${id}`, data, {
      withCredentials: true,
    })
    return response.data
  },

  /**
   * 删除模板
   */
  delete: async (id: number): Promise<void> => {
    await axios.delete(`${API_BASE_URL}/api/prompt-templates/${id}`, {
      withCredentials: true,
    })
  },

  /**
   * 基于现有模板创建新版本
   */
  createVersion: async (
    id: number,
    data: PromptTemplateVersionCreate
  ): Promise<PromptTemplate> => {
    const response = await axios.post(
      `${API_BASE_URL}/api/prompt-templates/${id}/versions`,
      data,
      {
        withCredentials: true,
      }
    )
    return response.data
  },

  /**
   * 激活模板
   */
  activate: async (id: number, setAsDefault: boolean = false): Promise<PromptTemplate> => {
    const response = await axios.post(
      `${API_BASE_URL}/api/prompt-templates/${id}/activate`,
      null,
      {
        params: { set_as_default: setAsDefault },
        withCredentials: true,
      }
    )
    return response.data
  },

  /**
   * 停用模板
   */
  deactivate: async (id: number): Promise<PromptTemplate> => {
    const response = await axios.post(
      `${API_BASE_URL}/api/prompt-templates/${id}/deactivate`,
      null,
      {
        withCredentials: true,
      }
    )
    return response.data
  },

  /**
   * 预览渲染后的提示词
   */
  preview: async (
    id: number,
    variables: Record<string, any>
  ): Promise<PromptTemplatePreviewResponse> => {
    const response = await axios.post(
      `${API_BASE_URL}/api/prompt-templates/${id}/preview`,
      { variables },
      {
        withCredentials: true,
      }
    )
    return response.data
  },

  /**
   * 获取模板的性能统计
   */
  getStatistics: async (id: number): Promise<PromptTemplateStatistics> => {
    const response = await axios.get(
      `${API_BASE_URL}/api/prompt-templates/${id}/statistics`,
      {
        withCredentials: true,
      }
    )
    return response.data
  },

  /**
   * 获取模板的修改历史
   */
  getHistory: async (id: number, limit: number = 50): Promise<PromptTemplateHistory[]> => {
    const response = await axios.get(
      `${API_BASE_URL}/api/prompt-templates/${id}/history`,
      {
        params: { limit },
        withCredentials: true,
      }
    )
    return response.data
  },

  /**
   * 获取所有业务类型
   */
  getBusinessTypes: async (): Promise<string[]> => {
    const response = await axios.get(
      `${API_BASE_URL}/api/prompt-templates/business-types/all`,
      {
        withCredentials: true,
      }
    )
    return response.data
  },
}
