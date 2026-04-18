'use client'

import { useState, useEffect, useCallback } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useToast } from '@/hooks/use-toast'
import { apiClient } from '@/lib/api-client'
import { extractApiError } from '@/lib/error-formatter'
import { useBacktestTask } from '@/contexts/BacktestTaskContext'
import type { StrategyTypeMeta } from '@/types/strategy'

/**
 * 策略来源类型
 * - predefined: 预定义策略 (如动量策略、均值回归等)
 * - config: 策略配置 (V1.0兼容)
 * - dynamic: 动态策略 (V1.0兼容)
 * - unified: 统一策略 (V2.0)
 * - ml: ML模型策略
 */
export type StrategySourceType = 'predefined' | 'config' | 'dynamic' | 'unified' | 'ml'

export interface BacktestProgress {
  current: number
  total: number
  status: string
}

export interface DateRange {
  start: string
  end: string
}

export interface UseBacktestFormReturn {
  // URL params
  strategyType: StrategySourceType | null
  strategyId: string | null

  // Strategy data state
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- 策略数据来自多种 API，结构各异
  strategyData: any
  strategyConfig: Record<string, unknown>
  setStrategyConfig: React.Dispatch<React.SetStateAction<Record<string, unknown>>>
  isLoadingStrategy: boolean
  strategyError: string | null

  // Backtest params
  stockPool: string[]
  setStockPool: React.Dispatch<React.SetStateAction<string[]>>
  dateRange: DateRange
  setDateRange: React.Dispatch<React.SetStateAction<DateRange>>
  initialCapital: number
  setInitialCapital: React.Dispatch<React.SetStateAction<number>>
  rebalanceFreq: 'D' | 'W' | 'M'
  setRebalanceFreq: React.Dispatch<React.SetStateAction<'D' | 'W' | 'M'>>
  exitStrategyIds: number[]
  setExitStrategyIds: React.Dispatch<React.SetStateAction<number[]>>

  // Backtest execution state
  isRunning: boolean
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  result: any
  isAsync: boolean
  taskId: string | null
  taskStatus: string
  progress: BacktestProgress
  executionId: number | null

  // Handlers
  handleRunBacktest: () => Promise<void>
  handleCancelBacktest: () => Promise<void>

  // Router (for navigation in the page)
  router: ReturnType<typeof useRouter>
}

const DEFAULT_DATE_RANGE: DateRange = {
  start: new Date(new Date().setFullYear(new Date().getFullYear() - 1)).toISOString().split('T')[0],
  end: new Date().toISOString().split('T')[0],
}

export function useBacktestForm(): UseBacktestFormReturn {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { toast } = useToast()
  const { addTask, hasActiveTasks } = useBacktestTask()

  // URL参数: type(策略类型) 和 id(策略/模型ID)
  const strategyType = searchParams.get('type') as StrategySourceType | null
  const strategyId = searchParams.get('id')

  // 策略数据状态
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- 策略数据结构因 strategyType 而异
  const [strategyData, setStrategyData] = useState<any>(null)
  const [strategyConfig, setStrategyConfig] = useState<Record<string, unknown>>({})
  const [isLoadingStrategy, setIsLoadingStrategy] = useState(true)
  const [strategyError, setStrategyError] = useState<string | null>(null)

  // 回测参数
  const [stockPool, setStockPool] = useState<string[]>([])
  const [dateRange, setDateRange] = useState<DateRange>(DEFAULT_DATE_RANGE)
  const [initialCapital, setInitialCapital] = useState(1000000)
  const [rebalanceFreq, setRebalanceFreq] = useState<'D' | 'W' | 'M'>('W')
  const [exitStrategyIds, setExitStrategyIds] = useState<number[]>([])

  // 回测状态
  const [isRunning, setIsRunning] = useState(false)
  const [result, setResult] = useState<any>(null)

  // 异步回测状态
  const [isAsync, setIsAsync] = useState(false)
  const [taskId, setTaskId] = useState<string | null>(null)
  const [taskStatus, setTaskStatus] = useState<string>('idle')
  const [progress, setProgress] = useState<BacktestProgress>({ current: 0, total: 100, status: '' })
  const [executionId, setExecutionId] = useState<number | null>(null)

  // ML策略ID（从数据库查询）
  const [mlStrategyId, setMlStrategyId] = useState<number | null>(null)

  // 加载ML策略ID
  useEffect(() => {
    const loadMLStrategyId = async () => {
      try {
        const response = await apiClient.getStrategies({})
        if (response.success && response.data) {
          const mlStrategy = (response.data as Array<{ id: number; name: string }>).find(s => s.name === 'ml_model')
          if (mlStrategy) {
            setMlStrategyId(mlStrategy.id)
          }
        }
      } catch (error) {
        console.error('加载ML策略ID失败:', error)
      }
    }
    loadMLStrategyId()
  }, [])

  // 加载策略数据
  useEffect(() => {
    const loadStrategyData = async () => {
      // 验证URL参数
      if (!strategyType || !strategyId) {
        setStrategyError('缺少必需的URL参数：type 和 id')
        setIsLoadingStrategy(false)
        return
      }

      // 验证策略类型
      if (!['predefined', 'config', 'dynamic', 'unified', 'ml'].includes(strategyType)) {
        setStrategyError(`无效的策略类型: ${strategyType}`)
        setIsLoadingStrategy(false)
        return
      }

      setIsLoadingStrategy(true)
      setStrategyError(null)

      try {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any -- 多种策略类型，运行时确定
        let data: any = null

        switch (strategyType) {
          case 'predefined': {
            const typesResponse = await apiClient.getStrategyTypes()
            if (typesResponse.success && typesResponse.data) {
              const types = Array.isArray(typesResponse.data) ? typesResponse.data : []
              const foundType = types.find((t: StrategyTypeMeta) => t.type === strategyId)
              if (foundType) {
                data = foundType
                setStrategyConfig(foundType.default_params || {})
              } else {
                setStrategyError(`未找到预定义策略: ${strategyId}`)
              }
            } else {
              setStrategyError(typesResponse.error || '无法加载预定义策略')
            }
            break
          }

          case 'ml': {
            const typesResponse = await apiClient.getStrategyTypes()
            if (typesResponse.success && typesResponse.data) {
              const types = Array.isArray(typesResponse.data) ? typesResponse.data : []
              const mlStrategy = types.find((t: StrategyTypeMeta) => t.type === 'ml_model')
              if (mlStrategy) {
                data = {
                  ...mlStrategy,
                  name: `机器学习模型策略 (${strategyId})`,
                  description: `使用ML模型 ${strategyId} 进行预测和交易`
                }
                setStrategyConfig({
                  ...mlStrategy.default_params,
                  model_id: strategyId
                })
              } else {
                setStrategyError('未找到ML模型策略定义')
              }
            } else {
              setStrategyError(typesResponse.error || '无法加载ML策略')
            }
            break
          }

          case 'config': {
            const response = await apiClient.getStrategyConfig(parseInt(strategyId))
            if (response.success && response.data) {
              data = response.data
              setStrategyConfig(data.config || {})
            } else {
              setStrategyError(response.error || '无法加载策略配置')
            }
            break
          }

          case 'dynamic': {
            const response = await apiClient.getDynamicStrategy(parseInt(strategyId))
            if (response.success && response.data) {
              data = response.data
            } else {
              setStrategyError(response.error || '无法加载动态策略')
            }
            break
          }

          case 'unified': {
            const response = await apiClient.getStrategy(parseInt(strategyId))
            if (response.success && response.data) {
              data = response.data
              setStrategyConfig(data.parameters || {})
            } else {
              setStrategyError(response.error || '无法加载统一策略')
            }
            break
          }
        }

        setStrategyData(data)
      } catch (error) {
        console.error('加载策略失败:', error)
        setStrategyError(error instanceof Error ? error.message : '加载策略时发生错误')
      } finally {
        setIsLoadingStrategy(false)
      }
    }

    loadStrategyData()
  }, [strategyType, strategyId])

  // 本地轮询任务状态（仅在当前页面显示实时进度）
  useEffect(() => {
    if (!taskId || taskStatus === 'SUCCESS' || taskStatus === 'FAILURE') {
      return
    }

    const pollInterval = setInterval(async () => {
      try {
        const statusData = await apiClient.getBacktestStatus(taskId)

        setTaskStatus(statusData.status)

        if (statusData.status === 'PROGRESS' && statusData.progress) {
          setProgress(statusData.progress)
        }

        if (statusData.status === 'SUCCESS') {
          setIsRunning(false)
          clearInterval(pollInterval)

          const execId = statusData.execution_id || (statusData.result as Record<string, unknown>)?.execution_id as number | undefined
          if (execId) {
            setExecutionId(execId)
          }
        } else if (statusData.status === 'FAILURE') {
          setIsRunning(false)
          clearInterval(pollInterval)
        }
      } catch (error) {
        console.error('轮询任务状态失败:', error)
      }
    }, 2000)

    return () => clearInterval(pollInterval)
  }, [taskId, taskStatus])

  // 取消异步回测任务
  const handleCancelBacktest = useCallback(async () => {
    if (!taskId) return

    try {
      await apiClient.cancelBacktest(taskId)
      setIsRunning(false)
      setTaskStatus('CANCELLED')
      toast({
        title: '已取消',
        description: '回测任务已取消'
      })
    } catch (error) {
      toast({
        title: '取消失败',
        description: extractApiError(error, '取消任务失败'),
        variant: 'destructive'
      })
    }
  }, [taskId, toast])

  const handleRunBacktest = useCallback(async () => {
    // 检查是否有未完成的任务（包括全局后台任务）
    if (hasActiveTasks()) {
      toast({
        title: '⚠️ 有正在执行的回测任务',
        description: '您有正在后台运行的回测任务，请等待完成后再开始新的回测',
        variant: 'destructive',
        duration: 5000,
      })
      return
    }

    // 额外检查当前页面的任务状态
    if (isRunning && taskId) {
      toast({
        title: '⚠️ 有正在执行的回测',
        description: '请等待当前回测完成或取消后再开始新的回测',
        variant: 'destructive',
      })
      return
    }

    // 验证参数
    if (stockPool.length === 0) {
      toast({
        title: '参数错误',
        description: '请至少选择一只股票',
        variant: 'destructive'
      })
      return
    }

    if (!dateRange.start || !dateRange.end) {
      toast({
        title: '参数错误',
        description: '请选择回测日期范围',
        variant: 'destructive'
      })
      return
    }

    if (!strategyData) {
      toast({
        title: '策略错误',
        description: '策略数据未加载',
        variant: 'destructive'
      })
      return
    }

    if (!exitStrategyIds || exitStrategyIds.length === 0) {
      toast({
        title: '请选择离场策略',
        description: '离场策略是必选项，用于控制何时卖出股票（止损/止盈/持仓时长等）。如果不选择离场策略，系统将永远不会卖出持仓，可能导致巨大亏损。',
        variant: 'destructive'
      })
      return
    }

    // 判断是否使用异步模式（股票数量 > 10 或时间跨度 > 1年）
    const daysDiff = Math.floor(
      (new Date(dateRange.end).getTime() - new Date(dateRange.start).getTime()) / (1000 * 60 * 60 * 24)
    )
    const shouldUseAsync = stockPool.length > 10 || daysDiff > 365

    // 构建请求参数
    // eslint-disable-next-line @typescript-eslint/no-explicit-any -- 动态构建请求，字段因策略类型而异
    const request: any = {
      stock_pool: stockPool,
      start_date: dateRange.start,
      end_date: dateRange.end,
      initial_capital: initialCapital,
      rebalance_freq: rebalanceFreq,
      exit_strategy_ids: exitStrategyIds.length > 0 ? exitStrategyIds : undefined
    }

    // 重置状态
    setIsRunning(true)
    setResult(null)
    setTaskId(null)
    setTaskStatus('idle')
    setProgress({ current: 0, total: 100, status: '' })

    try {
      // 根据策略类型构建请求
      if (strategyType === 'ml') {
        if (!mlStrategyId) {
          toast({
            title: '策略错误',
            description: 'ML策略未加载，请刷新页面重试',
            variant: 'destructive'
          })
          setIsRunning(false)
          return
        }

        request.strategy_id = mlStrategyId
        request.strategy_params = { model_id: strategyId }
      } else if (strategyType === 'predefined') {
        request.strategy_type = 'predefined'
        request.strategy_name = strategyId!
        request.strategy_config = strategyConfig
      } else if (strategyType === 'unified') {
        request.strategy_id = parseInt(strategyId!)
      } else {
        request.strategy_type = strategyType
        request.strategy_id = parseInt(strategyId!)
      }

      // 选择同步或异步模式
      if (shouldUseAsync || isAsync) {
        const asyncResponse = await apiClient.runAsyncBacktest(request)
        setTaskId(asyncResponse.task_id)
        setExecutionId(asyncResponse.execution_id)
        setTaskStatus('PENDING')
        setIsAsync(true)

        // 注册到全局任务监控
        addTask(asyncResponse.task_id, asyncResponse.execution_id)

        toast({
          title: '🚀 任务已提交',
          description: '回测任务已在后台运行，您可以自由导航到其他页面。完成后会提示您查看结果。',
        })
      } else {
        const response = await apiClient.runUnifiedBacktest(request)
        if (response.success && response.data) {
          const execId = response.data.execution_id
          if (execId) {
            toast({
              title: '✅ 回测完成',
              description: '正在跳转到结果页面...',
            })
            router.push(`/backtest-results/${execId}`)
            return
          }
          // 降级：如果没有execution_id，显示在当前页面
          setResult(response.data)
          toast({
            title: '回测完成',
            description: '策略回测已完成,请查看结果'
          })
        } else {
          toast({
            title: '回测失败',
            description: response.error || '未知错误',
            variant: 'destructive'
          })
        }
        setIsRunning(false)
      }
    } catch (error) {
      toast({
        title: '回测失败',
        description: extractApiError(error, '网络错误'),
        variant: 'destructive'
      })
      setIsRunning(false)
    }
  }, [
    hasActiveTasks, isRunning, taskId, stockPool, dateRange,
    strategyData, exitStrategyIds, initialCapital, rebalanceFreq,
    strategyType, strategyId, strategyConfig, mlStrategyId, isAsync,
    toast, addTask, router,
  ])

  return {
    // URL params
    strategyType,
    strategyId,

    // Strategy data state
    strategyData,
    strategyConfig,
    setStrategyConfig,
    isLoadingStrategy,
    strategyError,

    // Backtest params
    stockPool,
    setStockPool,
    dateRange,
    setDateRange,
    initialCapital,
    setInitialCapital,
    rebalanceFreq,
    setRebalanceFreq,
    exitStrategyIds,
    setExitStrategyIds,

    // Backtest execution state
    isRunning,
    result,
    isAsync,
    taskId,
    taskStatus,
    progress,
    executionId,

    // Handlers
    handleRunBacktest,
    handleCancelBacktest,

    // Router
    router,
  }
}
