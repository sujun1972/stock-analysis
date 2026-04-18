"use client"

import { useState, useEffect, useCallback } from "react"
import { axiosInstance } from "@/lib/api"
import { toast } from "sonner"
import logger from "@/lib/logger"
import { format } from "@/lib/date-utils"

export interface AIProvider {
  id: number
  provider: string
  display_name: string
  is_active: boolean
  is_default: boolean
  model_name: string
}

export interface AIAnalysisResult {
  trade_date: string
  space_analysis?: {
    max_continuous_stock?: {
      code: string
      name: string
      days: number
    }
    theme?: string
    space_level?: string
    analysis?: string
  }
  sentiment_analysis?: {
    money_making_effect?: string
    strategy?: string
    reasoning?: string
  }
  capital_flow_analysis?: {
    hot_money_direction?: {
      themes?: string[]
      stocks?: string[]
      concentration?: string
    }
    institution_direction?: {
      sectors?: string[]
      style?: string
    }
    capital_consensus?: string
    analysis?: string
  }
  tomorrow_tactics?: {
    call_auction_tactics?: {
      participate_conditions?: string
      avoid_conditions?: string
    }
    opening_half_hour_tactics?: {
      low_buy_opportunities?: string
      chase_opportunities?: string
      wait_signals?: string
    }
    buy_conditions?: string[]
    stop_loss_conditions?: string[]
  }
  full_report?: string
  ai_provider?: string
  ai_model?: string
  tokens_used?: number
  generation_time?: number
  status?: string
  created_at?: string
}

/** 格式化日期为 YYYY-MM-DD */
export const formatDateStr = (d: Date) => format(d, "yyyy-MM-dd")

export function useAiAnalysisData() {
  const [date, setDate] = useState<Date>(new Date())
  const [aiProvider, setAiProvider] = useState<string>("")
  const [aiProviders, setAiProviders] = useState<AIProvider[]>([])
  const [analysisData, setAnalysisData] = useState<AIAnalysisResult | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingProviders, setIsLoadingProviders] = useState(true)

  // 加载分析数据
  const loadAnalysis = useCallback(async (targetDate?: Date) => {
    const dateStr = formatDateStr(targetDate || date)
    setIsLoading(true)

    try {
      const response = await axiosInstance.get(`/api/sentiment/ai-analysis/${dateStr}`) as any

      if (response.code === 200 && response.data) {
        setAnalysisData(response.data)
      } else if (response.code === 404) {
        // 暂无数据是正常情况，静默处理，不显示错误提示
        setAnalysisData(null)
      } else {
        setAnalysisData(null)
        // 其他错误静默处理
      }
    } catch (error: any) {
      // 仅对网络错误或服务器异常显示错误提示，404则静默处理
      setAnalysisData(null)
      if (error.response?.status !== 404) {
        toast.error("加载失败：" + (error.response?.data?.detail || error.message))
      }
    } finally {
      setIsLoading(false)
    }
  }, [date])

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

      // 确保是数组
      if (!Array.isArray(data)) {
        logger.error('AI Providers data is not an array', data)
        toast.error("AI配置数据格式错误")
        setAiProviders([])
        return
      }

      const providers = data.filter((p: AIProvider) => p.is_active)

      setAiProviders(providers)

      // 设置默认提供商
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

  // 日期变化时加载
  const handleDateChange = (newDate: Date | undefined) => {
    if (newDate) {
      setDate(newDate)
      loadAnalysis(newDate)
    }
  }

  // 初始加载
  useEffect(() => {
    loadProviders()
    loadAnalysis()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return {
    date,
    aiProvider,
    setAiProvider,
    aiProviders,
    analysisData,
    isLoading,
    isLoadingProviders,
    loadAnalysis,
    handleDateChange,
  }
}
