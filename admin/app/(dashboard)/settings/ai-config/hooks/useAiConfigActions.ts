'use client'

import { useState } from 'react'
import { useToast } from '@/hooks/use-toast'
import { configApi } from '@/lib/api'
import logger from '@/lib/logger'
import type { AIProvider } from './useAiConfigData'

export interface AIProviderFormData {
  provider: string
  display_name: string
  api_key: string
  api_base_url: string
  model_name: string
  max_tokens: number
  temperature: number
  is_active: boolean
  is_default: boolean
  priority: number
  rate_limit: number
  timeout: number
  description: string
}

const DEFAULT_FORM_DATA: AIProviderFormData = {
  provider: '',
  display_name: '',
  api_key: '',
  api_base_url: '',
  model_name: '',
  max_tokens: 8000,
  temperature: 0.7,
  is_active: true,
  is_default: false,
  priority: 50,
  rate_limit: 10,
  timeout: 60,
  description: ''
}

const PROVIDER_PRESETS: Record<string, Partial<AIProviderFormData>> = {
  deepseek: {
    display_name: 'DeepSeek',
    api_base_url: 'https://api.deepseek.com/v1',
    model_name: 'deepseek-chat',
    description: 'DeepSeek AI - 高性价比的中文AI模型'
  },
  gemini: {
    display_name: 'Google Gemini',
    api_base_url: 'https://generativelanguage.googleapis.com/v1beta',
    model_name: 'gemini-1.5-flash',
    description: 'Google Gemini - 支持免费额度'
  },
  openai: {
    display_name: 'OpenAI',
    api_base_url: 'https://api.openai.com/v1',
    model_name: 'gpt-4o',
    description: 'OpenAI GPT-4 - 性能优秀'
  }
}

interface UseAiConfigActionsOptions {
  fetchProviders: () => Promise<void>
}

export function useAiConfigActions({ fetchProviders }: UseAiConfigActionsOptions) {
  const { toast } = useToast()
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingProvider, setEditingProvider] = useState<AIProvider | null>(null)
  const [formData, setFormData] = useState<AIProviderFormData>({ ...DEFAULT_FORM_DATA })

  const handleCreate = () => {
    setEditingProvider(null)
    setFormData({ ...DEFAULT_FORM_DATA })
    setIsDialogOpen(true)
  }

  const handleEdit = (provider: AIProvider) => {
    setEditingProvider(provider)
    setFormData({
      provider: provider.provider,
      display_name: provider.display_name,
      api_key: provider.api_key.includes('*') ? '' : provider.api_key,
      api_base_url: provider.api_base_url,
      model_name: provider.model_name,
      max_tokens: provider.max_tokens,
      temperature: provider.temperature,
      is_active: provider.is_active,
      is_default: provider.is_default,
      priority: provider.priority,
      rate_limit: provider.rate_limit,
      timeout: provider.timeout,
      description: provider.description
    })
    setIsDialogOpen(true)
  }

  const handleSave = async () => {
    try {
      if (editingProvider) {
        const updateData: any = {}
        if (formData.api_key) updateData.api_key = formData.api_key
        if (formData.display_name) updateData.display_name = formData.display_name
        if (formData.api_base_url) updateData.api_base_url = formData.api_base_url
        if (formData.model_name) updateData.model_name = formData.model_name
        updateData.max_tokens = formData.max_tokens
        updateData.temperature = formData.temperature
        updateData.is_active = formData.is_active
        updateData.is_default = formData.is_default
        updateData.priority = formData.priority
        updateData.rate_limit = formData.rate_limit
        updateData.timeout = formData.timeout
        if (formData.description) updateData.description = formData.description

        await configApi.updateAIProvider(editingProvider.provider, updateData)

        toast({
          title: '更新成功',
          description: `AI提供商 ${formData.display_name} 已更新`
        })
      } else {
        await configApi.createAIProvider(formData)

        toast({
          title: '创建成功',
          description: `AI提供商 ${formData.display_name} 已创建`
        })
      }

      setIsDialogOpen(false)
      fetchProviders()
    } catch (error: any) {
      logger.error('保存AI提供商失败', error)
      toast({
        title: '操作失败',
        description: error.response?.data?.detail || error.message || '未知错误',
        variant: 'destructive'
      })
    }
  }

  const handleDelete = async (provider: string) => {
    if (!confirm(`确定要删除 ${provider} 吗？`)) return

    try {
      await configApi.deleteAIProvider(provider)

      toast({
        title: '删除成功',
        description: `AI提供商 ${provider} 已删除`
      })

      fetchProviders()
    } catch (error: any) {
      logger.error('删除AI提供商失败', error)
      toast({
        title: '删除失败',
        description: error.response?.data?.detail || error.message || '未知错误',
        variant: 'destructive'
      })
    }
  }

  const handleProviderChange = (value: string) => {
    const preset = PROVIDER_PRESETS[value] || {}
    setFormData({
      ...formData,
      provider: value,
      ...preset
    })
  }

  return {
    isDialogOpen,
    setIsDialogOpen,
    editingProvider,
    formData,
    setFormData,
    handleCreate,
    handleEdit,
    handleSave,
    handleDelete,
    handleProviderChange,
  }
}
