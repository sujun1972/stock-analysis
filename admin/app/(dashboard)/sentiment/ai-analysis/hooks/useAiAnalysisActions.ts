"use client"

import { useState } from "react"
import { axiosInstance } from "@/lib/api"
import { toast } from "sonner"
import { addTaskToQueue } from "@/hooks/use-task-polling"
import logger from "@/lib/logger"
import { formatDateStr, type AIProvider } from "./useAiAnalysisData"

interface UseAiAnalysisActionsParams {
  date: Date
  aiProvider: string
  aiProviders: AIProvider[]
  loadAnalysis: () => Promise<void>
}

export function useAiAnalysisActions({
  date,
  aiProvider,
  aiProviders,
  loadAnalysis,
}: UseAiAnalysisActionsParams) {
  const [isGenerating, setIsGenerating] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [promptDialogOpen, setPromptDialogOpen] = useState(false)
  const [promptText, setPromptText] = useState<string>("")
  const [promptDate, setPromptDate] = useState<string>("")
  const [isLoadingPrompt, setIsLoadingPrompt] = useState(false)

  // 预览提示词
  const handlePreviewPrompt = async () => {
    setIsLoadingPrompt(true)
    setPromptDialogOpen(true)
    try {
      const dateStr = formatDateStr(date)
      const response = await axiosInstance.get(`/api/sentiment/ai-analysis/preview-prompt`, {
        params: { date: dateStr }
      }) as any
      if (response.code === 200 && response.data) {
        setPromptText(response.data.prompt)
        setPromptDate(response.data.trade_date)
      } else {
        toast.error(response.message || "获取提示词失败")
        setPromptDialogOpen(false)
      }
    } catch (error: any) {
      toast.error("获取提示词失败：" + (error.response?.data?.detail || error.message))
      setPromptDialogOpen(false)
    } finally {
      setIsLoadingPrompt(false)
    }
  }

  // 轮询任务状态（页面内实时反馈）
  const pollTaskStatus = async (pollTaskId: string, dateStr: string) => {
    const maxAttempts = 200 // 最多轮询10分钟（200次 x 3秒）
    let attempts = 0

    const intervalId = setInterval(async () => {
      attempts++

      try {
        const statusRes = await axiosInstance.get(`/api/sentiment/sync/status/${pollTaskId}`) as any

        if (statusRes.code === 200 && statusRes.data) {
          const { status, result, message, progress } = statusRes.data

          // 更新进度信息（可选：在UI中显示进度）
          if (status === 'PROGRESS' || status === 'STARTED') {
            logger.info(`AI分析任务进度: ${progress || 0}% - ${message || '执行中'}`)
          }

          if (status === 'SUCCESS') {
            clearInterval(intervalId)

            // 任务成功，自动刷新数据
            if (result?.success) {
              await loadAnalysis()
              toast.success("AI分析完成", {
                description: `${dateStr} 的分析报告已生成，数据已刷新`,
                duration: 4000,
              })
            } else if (result?.status === 'skipped') {
              toast.info("任务已跳过", {
                description: result.reason || "非交易日或数据缺失",
                duration: 4000,
              })
            }

            setTaskId(null)
          } else if (status === 'FAILURE') {
            clearInterval(intervalId)
            setTaskId(null)
            // 错误 toast 由全局轮询处理，这里只做清理
            logger.error('AI分析任务失败', statusRes.data.error || message)
          }
        }

        // 超时停止轮询
        if (attempts >= maxAttempts) {
          clearInterval(intervalId)
          setTaskId(null)
          toast.warning("轮询超时", {
            description: "任务可能仍在执行，请稍后刷新页面或查看异步任务管理",
            duration: 5000,
          })
        }
      } catch (error) {
        logger.error('轮询任务状态失败', error)

        // 连续失败多次后停止轮询
        if (attempts > 5) {
          clearInterval(intervalId)
          setTaskId(null)
          toast.error("轮询失败", {
            description: "无法获取任务状态，请检查网络连接或查看异步任务管理",
            duration: 5000,
          })
        }
      }
    }, 3000) // 每3秒轮询一次
  }

  // 生成AI分析（异步提交）
  const handleGenerate = async () => {
    const dateStr = formatDateStr(date)
    setIsGenerating(true)

    try {
      const response = await axiosInstance.post("/api/sentiment/ai-analysis/generate", null, {
        params: { date: dateStr, provider: aiProvider }
      }) as any

      if (response.code === 200 && response.data?.task_id) {
        const newTaskId = response.data.task_id
        setTaskId(newTaskId)

        // 获取AI提供商显示名称
        const providerDisplay = aiProviders.find(p => p.provider === aiProvider)?.display_name || aiProvider

        // 加入全局轮询队列（项目级轮询，跨页面）
        addTaskToQueue(
          newTaskId,
          `sentiment.ai_analysis_18_00`,
          `AI分析生成（${dateStr} - ${providerDisplay}）`,
          'ai_analysis'
        )

        toast.success("AI分析任务已提交", {
          description: `正在生成 ${dateStr} 的分析报告，可在异步任务管理中查看进度`,
          duration: 5000,
        })

        // 开始轮询任务状态（仅用于当前页面实时反馈）
        pollTaskStatus(newTaskId, dateStr)
      } else if (response.code === 409) {
        toast.warning("分析任务正在执行中", {
          description: "已有AI分析任务正在执行，请等待完成或查看异步任务管理",
          duration: 4000,
        })
      } else {
        toast.error(response.message || "提交失败")
      }
    } catch (error: any) {
      logger.error("提交AI分析任务失败", error)
      toast.error("提交失败：" + (error.response?.data?.detail || error.message))
    } finally {
      setIsGenerating(false)
    }
  }

  return {
    isGenerating,
    taskId,
    promptDialogOpen,
    setPromptDialogOpen,
    promptText,
    promptDate,
    isLoadingPrompt,
    handlePreviewPrompt,
    handleGenerate,
  }
}
