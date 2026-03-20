import { useState, useCallback } from 'react'
import { apiClient } from '@/lib/api-client'
import { toast } from 'sonner'
import logger from '@/lib/logger'
import type { ApiResponse } from '@/types'
import type {
  OvernightData,
  CollisionAnalysis,
  PremarketNews,
  AnalysisHistory
} from '@/types/premarket'

/**
 * 盘前数据管理 Hook
 * 负责加载外盘数据、碰撞分析、新闻列表和历史记录
 */
export function usePremarketData(formatDate: (d: Date) => string) {
  const [overnightData, setOvernightData] = useState<OvernightData | null>(null)
  const [collisionAnalysis, setCollisionAnalysis] = useState<CollisionAnalysis | null>(null)
  const [newsList, setNewsList] = useState<PremarketNews[]>([])
  const [history, setHistory] = useState<AnalysisHistory[]>([])
  const [isLoading, setIsLoading] = useState(false)

  // 加载所有数据
  const loadAllData = useCallback(async (date: Date) => {
    const dateStr = formatDate(date)
    setIsLoading(true)

    try {
      // 并行加载所有数据，使用 Promise.allSettled 确保单个请求失败不影响其他请求
      // 404 错误会被 axios 拦截器静默处理，不会在控制台显示
      const [overnightRes, analysisRes, newsRes] = await Promise.allSettled([
        apiClient.get(`/api/premarket/overnight-data/${dateStr}`),
        apiClient.get(`/api/premarket/collision-analysis/${dateStr}`),
        apiClient.get(`/api/premarket/news/${dateStr}`)
      ])

      // 处理外盘数据
      if (overnightRes.status === 'fulfilled' && (overnightRes.value as any)?.code === 200) {
        setOvernightData((overnightRes.value as any).data)
      } else {
        setOvernightData(null)
      }

      // 处理碰撞分析
      if (analysisRes.status === 'fulfilled' && (analysisRes.value as any)?.code === 200) {
        setCollisionAnalysis((analysisRes.value as any).data)
      } else {
        setCollisionAnalysis(null)
      }

      // 处理新闻列表
      if (newsRes.status === 'fulfilled' && (newsRes.value as any)?.code === 200) {
        setNewsList((newsRes.value as any).data?.news || [])
      } else {
        setNewsList([])
      }
    } catch (error: any) {
      logger.error('Load data error', error)
      toast.error("加载数据失败")
    } finally {
      setIsLoading(false)
    }
  }, [formatDate])

  // 加载历史记录
  const loadHistory = useCallback(async () => {
    try {
      const response = await apiClient.get<ApiResponse<AnalysisHistory[]>>('/api/premarket/history?limit=10') as any
      if (response.code === 200 && response.data) {
        setHistory(response.data)
      }
    } catch (error: any) {
      logger.error('Load history error', error)
    }
  }, [])

  return {
    overnightData,
    collisionAnalysis,
    newsList,
    history,
    isLoading,
    loadAllData,
    loadHistory
  }
}
