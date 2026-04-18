'use client'

import { useState, useEffect, useCallback } from 'react'
import { useToast } from '@/hooks/use-toast'
import { configApi } from '@/lib/api'
import logger from '@/lib/logger'

export interface AIProvider {
  id: number
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
  created_at: string
  updated_at: string
}

export function useAiConfigData() {
  const { toast } = useToast()
  const [providers, setProviders] = useState<AIProvider[]>([])
  const [loading, setLoading] = useState(true)

  const fetchProviders = useCallback(async () => {
    try {
      const response = await configApi.getAIProviders()
      setProviders(response.data || response as any)
    } catch (error) {
      logger.error('获取AI提供商列表失败', error)
      toast({
        title: '加载失败',
        description: error instanceof Error ? error.message : '未知错误',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }, [toast])

  useEffect(() => {
    fetchProviders()
  }, [fetchProviders])

  return {
    providers,
    loading,
    fetchProviders,
  }
}
