import { useState } from 'react'
import { axiosInstance } from '@/lib/api'
import { toast } from 'sonner'
import type { ApiResponse } from '@/types'
import type { SyncResult } from '@/types/premarket'

/**
 * 盘前操作管理 Hook
 * 负责同步数据和生成碰撞分析
 */
export function usePremarketActions(
  formatDate: (d: Date) => string,
  onSuccess?: () => Promise<void>
) {
  const [isSyncing, setIsSyncing] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)

  // 同步盘前数据
  const handleSync = async (date: Date) => {
    const dateStr = formatDate(date)
    setIsSyncing(true)

    // 显示加载提示并保存 ID，用于后续关闭避免 toast 重叠
    const loadingToastId = toast.info("正在同步盘前数据...")

    try {
      const res = await axiosInstance.post<ApiResponse<SyncResult>>(
        `/api/premarket/sync?date=${dateStr}`
      ) as any

      // 先关闭加载提示，再显示结果，确保 toast 顺序展示不重叠
      toast.dismiss(loadingToastId)

      if (res.code === 200) {
        toast.success(res.message || "同步成功")
        // 重新加载数据
        if (onSuccess) {
          await onSuccess()
        }
      } else {
        toast.error(res.message || "同步失败")
      }
    } catch (error: any) {
      toast.dismiss(loadingToastId)
      toast.error("同步失败：" + (error.response?.data?.detail || error.message))
    } finally {
      setIsSyncing(false)
    }
  }

  // 生成碰撞分析
  const handleGenerate = async (date: Date, aiProvider: string) => {
    const dateStr = formatDate(date)
    setIsGenerating(true)

    // 显示加载提示并保存 ID，用于后续关闭避免 toast 重叠
    const loadingToastId = toast.info("正在调用AI生成碰撞分析，请稍候...")

    try {
      const res = await axiosInstance.post<ApiResponse<any>>(
        `/api/premarket/collision-analysis/generate?date=${dateStr}&provider=${aiProvider}`
      ) as any

      // 先关闭加载提示，再显示结果，确保 toast 顺序展示不重叠
      toast.dismiss(loadingToastId)

      if (res.code === 200) {
        toast.success("碰撞分析生成成功")
        if (onSuccess) {
          await onSuccess()
        }
      } else {
        toast.error(res.message || "生成失败")
      }
    } catch (error: any) {
      toast.dismiss(loadingToastId)
      toast.error("生成失败：" + (error.response?.data?.detail || error.message))
    } finally {
      setIsGenerating(false)
    }
  }

  return {
    isSyncing,
    isGenerating,
    handleSync,
    handleGenerate
  }
}
