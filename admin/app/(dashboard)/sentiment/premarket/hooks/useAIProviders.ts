import { useState, useEffect } from 'react'
import { axiosInstance } from '@/lib/api'
import { toast } from 'sonner'
import logger from '@/lib/logger'

export interface AIProvider {
  id: number
  provider: string
  display_name: string
  is_active: boolean
  is_default: boolean
  model_name: string
}

/**
 * AI 提供商管理 Hook
 * 负责加载和管理 AI 提供商配置
 */
export function useAIProviders() {
  const [aiProvider, setAiProvider] = useState<string>("")
  const [aiProviders, setAiProviders] = useState<AIProvider[]>([])
  const [isLoadingProviders, setIsLoadingProviders] = useState(true)

  // 加载AI提供商列表
  const loadProviders = async () => {
    setIsLoadingProviders(true)
    try {
      // Backend 使用 ApiResponse 格式，数据在 response.data 中
      const response = await axiosInstance.get('/api/ai-strategy/providers') as any

      if (response.code !== 200) {
        logger.error('Failed to load AI providers', response)
        toast.error(response.message || "加载AI配置失败")
        setAiProviders([])
        return
      }

      const data = response.data

      if (!Array.isArray(data)) {
        logger.error('AI Providers data is not an array', data)
        toast.error("AI配置数据格式错误")
        setAiProviders([])
        return
      }

      const providers = data.filter((p: AIProvider) => p.is_active)
      setAiProviders(providers)

      const defaultProvider = providers.find((p: AIProvider) => p.is_default)
      if (defaultProvider) {
        setAiProvider(defaultProvider.provider)
      } else if (providers.length > 0) {
        setAiProvider(providers[0].provider)
      }
    } catch (error: any) {
      logger.error('Load AI Providers Error', error)
      toast.error("加载AI配置失败：" + (error.response?.data?.detail || error.message))
      setAiProviders([])
    } finally {
      setIsLoadingProviders(false)
    }
  }

  // 初始加载
  useEffect(() => {
    loadProviders()
  }, [])

  return {
    aiProvider,
    setAiProvider,
    aiProviders,
    isLoadingProviders,
    loadProviders
  }
}
