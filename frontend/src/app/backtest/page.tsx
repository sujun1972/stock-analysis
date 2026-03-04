'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'
import { apiClient } from '@/lib/api-client'
import { extractApiError } from '@/lib/error-formatter'
import type {
  StrategyTypeMeta,
  StrategyConfig,
  DynamicStrategy,
  Strategy
} from '@/types/strategy'
import StrategyConfigEditor from '@/components/strategies/StrategyConfigEditor'
import StockPoolSelector from '@/components/backtest/StockPoolSelector'
import DateRangeSelector from '@/components/backtest/DateRangeSelector'
import BacktestResultView, { TradesTable } from '@/components/backtest/BacktestResultView'
import ExitStrategySelector from '@/components/backtest/ExitStrategySelector'
import { Loader2, AlertCircle } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'

/**
 * 策略来源类型
 * - predefined: 预定义策略 (如动量策略、均值回归等)
 * - config: 策略配置 (V1.0兼容)
 * - dynamic: 动态策略 (V1.0兼容)
 * - unified: 统一策略 (V2.0)
 * - ml: ML模型策略
 */
type StrategySourceType = 'predefined' | 'config' | 'dynamic' | 'unified' | 'ml'

function BacktestContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { toast } = useToast()

  // URL参数: type(策略类型) 和 id(策略/模型ID)
  const strategyType = searchParams.get('type') as StrategySourceType | null
  const strategyId = searchParams.get('id')

  // 策略数据状态
  const [strategyData, setStrategyData] = useState<any>(null)
  const [strategyConfig, setStrategyConfig] = useState<Record<string, any>>({})
  const [isLoadingStrategy, setIsLoadingStrategy] = useState(true)
  const [strategyError, setStrategyError] = useState<string | null>(null)

  // 回测参数
  const [stockPool, setStockPool] = useState<string[]>([])
  const [dateRange, setDateRange] = useState({
    start: new Date(new Date().setFullYear(new Date().getFullYear() - 1)).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0]
  })
  const [initialCapital, setInitialCapital] = useState(1000000)
  const [rebalanceFreq, setRebalanceFreq] = useState<'D' | 'W' | 'M'>('W')
  const [exitStrategyIds, setExitStrategyIds] = useState<number[]>([])

  // 回测状态
  const [isRunning, setIsRunning] = useState(false)
  const [result, setResult] = useState<any>(null)

  // 异步回测状态
  const [isAsync, setIsAsync] = useState(false)  // 是否使用异步模式
  const [taskId, setTaskId] = useState<string | null>(null)  // Celery任务ID
  const [taskStatus, setTaskStatus] = useState<string>('idle')  // 任务状态
  const [progress, setProgress] = useState({ current: 0, total: 100, status: '' })  // 进度信息
  const [executionId, setExecutionId] = useState<number | null>(null)  // 执行记录ID，用于跳转结果页面

  // ML策略ID（从数据库查询）
  const [mlStrategyId, setMlStrategyId] = useState<number | null>(null)

  // 加载ML策略ID
  useEffect(() => {
    const loadMLStrategyId = async () => {
      try {
        const response = await apiClient.getStrategies({ source_type: 'builtin' })
        if (response.success && response.data) {
          const mlStrategy = response.data.find((s: any) => s.name === 'ml_model')
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
        let data: any = null

        switch (strategyType) {
          case 'predefined': {
            // 获取预定义策略类型列表
            const typesResponse = await apiClient.getStrategyTypes()
            if (typesResponse.success && typesResponse.data) {
              const types = Array.isArray(typesResponse.data) ? typesResponse.data : []
              const strategyType = types.find((t: StrategyTypeMeta) => t.type === strategyId)
              if (strategyType) {
                data = strategyType
                setStrategyConfig(strategyType.default_params || {})
              } else {
                setStrategyError(`未找到预定义策略: ${strategyId}`)
              }
            } else {
              setStrategyError(typesResponse.error || '无法加载预定义策略')
            }
            break
          }

          case 'ml': {
            // ML模型策略类型
            // 首先获取ml_model策略的定义
            const typesResponse = await apiClient.getStrategyTypes()
            if (typesResponse.success && typesResponse.data) {
              const types = Array.isArray(typesResponse.data) ? typesResponse.data : []
              const mlStrategy = types.find((t: StrategyTypeMeta) => t.type === 'ml_model')
              if (mlStrategy) {
                // 使用ml_model策略的元数据,但设置model_id
                data = {
                  ...mlStrategy,
                  name: `机器学习模型策略 (${strategyId})`,
                  description: `使用ML模型 ${strategyId} 进行预测和交易`
                }
                setStrategyConfig({
                  ...mlStrategy.default_params,
                  model_id: strategyId // 使用URL中的id作为model_id
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
            // 获取策略配置
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
            // 获取动态策略
            const response = await apiClient.getDynamicStrategy(parseInt(strategyId))
            if (response.success && response.data) {
              data = response.data
            } else {
              setStrategyError(response.error || '无法加载动态策略')
            }
            break
          }

          case 'unified': {
            // 获取统一策略
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
      } catch (error: any) {
        console.error('加载策略失败:', error)
        setStrategyError(error.message || '加载策略时发生错误')
      } finally {
        setIsLoadingStrategy(false)
      }
    }

    loadStrategyData()
  }, [strategyType, strategyId])

  // 轮询任务状态 (后台轮询，不影响用户导航)
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

          // 提取execution_id用于跳转
          const execId = statusData.execution_id || statusData.result?.execution_id
          if (execId) {
            setExecutionId(execId)
          }

          // 显示可点击的toast，跳转到结果页面
          toast({
            title: '✅ 回测完成',
            description: '点击查看详细结果',
            action: execId ? (
              <Button
                size="sm"
                onClick={() => router.push(`/backtest-results?id=${execId}`)}
              >
                查看结果
              </Button>
            ) : undefined,
          })
        } else if (statusData.status === 'FAILURE') {
          setIsRunning(false)
          clearInterval(pollInterval)
          toast({
            title: '❌ 回测失败',
            description: statusData.error || '任务执行失败',
            variant: 'destructive'
          })
        }
      } catch (error: any) {
        console.error('轮询任务状态失败:', error)
      }
    }, 2000) // 每2秒轮询一次

    return () => clearInterval(pollInterval)
  }, [taskId, taskStatus, router, toast])

  // 取消异步回测任务
  const handleCancelBacktest = async () => {
    if (!taskId) return

    try {
      await apiClient.cancelBacktest(taskId)
      setIsRunning(false)
      setTaskStatus('CANCELLED')
      toast({
        title: '已取消',
        description: '回测任务已取消'
      })
    } catch (error: any) {
      toast({
        title: '取消失败',
        description: extractApiError(error, '取消任务失败'),
        variant: 'destructive'
      })
    }
  }

  const handleRunBacktest = async () => {
    // 检查是否有未完成的任务
    if (isRunning && taskId) {
      toast({
        title: '⚠️ 有正在执行的回测',
        description: '请等待当前回测完成或取消后再开始新的回测',
        variant: 'destructive',
        action: (
          <Button size="sm" variant="outline" onClick={handleCancelBacktest}>
            取消当前任务
          </Button>
        )
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

    // ⚠️ 验证离场策略（必选）
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
    const request: any = {
      stock_pool: stockPool,
      start_date: dateRange.start,
      end_date: dateRange.end,
      initial_capital: initialCapital,
      rebalance_freq: rebalanceFreq,
      // 添加离场策略IDs（如果有选择）
      exit_strategy_ids: exitStrategyIds.length > 0 ? exitStrategyIds : undefined
    }

    // 根据策略类型设置不同的参数
    setIsRunning(true)
    setResult(null)
    setTaskId(null)
    setTaskStatus('idle')
    setProgress({ current: 0, total: 100, status: '' })

    try {
      // 根据策略类型构建请求
      if (strategyType === 'ml') {
        // ML模型回测：使用内置的ml_model策略
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
        // 使用异步模式
        const asyncResponse = await apiClient.runAsyncBacktest(request)
        setTaskId(asyncResponse.task_id)
        setExecutionId(asyncResponse.execution_id)  // 保存execution_id
        setTaskStatus('PENDING')
        setIsAsync(true)
        toast({
          title: '🚀 任务已提交',
          description: `回测任务已在后台运行，您可以自由导航到其他页面。完成后会提示您查看结果。`,
        })
      } else {
        // 使用同步模式
        const response = await apiClient.runUnifiedBacktest(request)
        if (response.success && response.data) {
          // 同步模式：保存execution_id并跳转到结果页面
          const execId = response.data.execution_id
          if (execId) {
            toast({
              title: '✅ 回测完成',
              description: '正在跳转到结果页面...',
            })
            router.push(`/backtest-results?id=${execId}`)
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
    } catch (error: any) {
      // 格式化错误信息，处理 Pydantic 验证错误等复杂对象
      toast({
        title: '回测失败',
        description: extractApiError(error, '网络错误'),
        variant: 'destructive'
      })
      setIsRunning(false)
    }
  }

  // 渲染策略信息卡片
  const renderStrategyInfo = () => {
    if (!strategyData) return null

    switch (strategyType) {
      case 'predefined': {
        const strategy = strategyData as StrategyTypeMeta
        return (
          <div className="space-y-3">
            <div>
              <p className="text-sm font-medium text-muted-foreground">策略名称</p>
              <p className="text-lg font-semibold">{strategy.name}</p>
            </div>
            {strategy.description && (
              <div>
                <p className="text-sm font-medium text-muted-foreground">描述</p>
                <p className="text-sm">{strategy.description}</p>
              </div>
            )}
            {strategy.category && (
              <div>
                <p className="text-sm font-medium text-muted-foreground">类别</p>
                <p className="text-sm">{strategy.category}</p>
              </div>
            )}
            {strategy.param_schema && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-muted-foreground">策略参数</p>
                <StrategyConfigEditor
                  strategyType={strategyId!}
                  config={strategyConfig}
                  schema={strategy.param_schema}
                  onChange={setStrategyConfig}
                />
              </div>
            )}
          </div>
        )
      }

      case 'config': {
        const config = strategyData as StrategyConfig
        return (
          <div className="space-y-3">
            <div>
              <p className="text-sm font-medium text-muted-foreground">配置名称</p>
              <p className="text-lg font-semibold">{config.name}</p>
            </div>
            {config.description && (
              <div>
                <p className="text-sm font-medium text-muted-foreground">描述</p>
                <p className="text-sm">{config.description}</p>
              </div>
            )}
            <div>
              <p className="text-sm font-medium text-muted-foreground">策略类型</p>
              <p className="text-sm">{config.strategy_type}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">配置参数</p>
              <div className="text-xs font-mono mt-1 p-2 bg-muted rounded max-h-40 overflow-auto">
                {JSON.stringify(config.config, null, 2)}
              </div>
            </div>
          </div>
        )
      }

      case 'dynamic': {
        const strategy = strategyData as DynamicStrategy
        return (
          <div className="space-y-3">
            <div>
              <p className="text-sm font-medium text-muted-foreground">策略名称</p>
              <p className="text-lg font-semibold">{strategy.display_name}</p>
            </div>
            {strategy.description && (
              <div>
                <p className="text-sm font-medium text-muted-foreground">描述</p>
                <p className="text-sm">{strategy.description}</p>
              </div>
            )}
            <div>
              <p className="text-sm font-medium text-muted-foreground">验证状态</p>
              <p className={`text-sm font-medium ${
                strategy.validation_status === 'passed' ? 'text-green-600' : 'text-yellow-600'
              }`}>
                {strategy.validation_status === 'passed' ? '✓ 验证通过' : strategy.validation_status}
              </p>
            </div>
            {strategy.version && (
              <div>
                <p className="text-sm font-medium text-muted-foreground">版本</p>
                <p className="text-sm">v{strategy.version}</p>
              </div>
            )}
          </div>
        )
      }

      case 'unified': {
        const strategy = strategyData as Strategy
        return (
          <div className="space-y-3">
            <div>
              <p className="text-sm font-medium text-muted-foreground">策略名称</p>
              <p className="text-lg font-semibold">{strategy.name}</p>
            </div>
            {strategy.description && (
              <div>
                <p className="text-sm font-medium text-muted-foreground">描述</p>
                <p className="text-sm">{strategy.description}</p>
              </div>
            )}
            <div>
              <p className="text-sm font-medium text-muted-foreground">来源类型</p>
              <p className="text-sm">{strategy.source_type}</p>
            </div>
            {strategy.category && (
              <div>
                <p className="text-sm font-medium text-muted-foreground">类别</p>
                <p className="text-sm">{strategy.category}</p>
              </div>
            )}
          </div>
        )
      }

      case 'ml': {
        const strategy = strategyData as StrategyTypeMeta
        return (
          <div className="space-y-3">
            <div>
              <p className="text-sm font-medium text-muted-foreground">策略类型</p>
              <p className="text-lg font-semibold">机器学习模型策略</p>
            </div>
            <div>
              <p className="text-sm font-medium text-muted-foreground">模型ID</p>
              <p className="text-sm font-mono">{strategyId}</p>
            </div>
            {strategy.description && (
              <div>
                <p className="text-sm font-medium text-muted-foreground">描述</p>
                <p className="text-sm">{strategy.description}</p>
              </div>
            )}
            {strategy.param_schema && (
              <div className="space-y-2">
                <p className="text-sm font-medium text-muted-foreground">策略参数</p>
                <StrategyConfigEditor
                  strategyType="ml_model"
                  config={strategyConfig}
                  schema={strategy.param_schema}
                  onChange={setStrategyConfig}
                />
              </div>
            )}
          </div>
        )
      }

      default:
        return null
    }
  }

  // 显示错误状态
  if (!isLoadingStrategy && strategyError) {
    return (
      <div className="container mx-auto py-6 px-4 max-w-7xl">
        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">策略回测</h1>
            <p className="text-muted-foreground mt-2">
              配置参数,运行回测分析
            </p>
          </div>

          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertTitle>加载失败</AlertTitle>
            <AlertDescription>{strategyError}</AlertDescription>
          </Alert>

          <div className="flex gap-4">
            <Button onClick={() => router.back()} variant="outline">
              返回上一页
            </Button>
            <Button onClick={() => router.push('/strategies')} variant="default">
              前往策略管理
            </Button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-6 px-4 max-w-7xl">
      <div className="space-y-6">
        {/* 页面标题 */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">策略回测</h1>
          <p className="text-muted-foreground mt-2">
            配置参数,运行回测分析
          </p>
        </div>

        {/* 1. 策略信息 */}
        <Card>
          <CardHeader>
            <CardTitle>策略信息</CardTitle>
            <CardDescription>
              当前选择的策略详情
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoadingStrategy ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : (
              renderStrategyInfo()
            )}
          </CardContent>
        </Card>

        {/* 2. 回测参数 */}
        <Card>
          <CardHeader>
            <CardTitle>回测参数</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* 股票池选择 */}
              <div className="md:col-span-2">
                <StockPoolSelector value={stockPool} onChange={setStockPool} maxStocks={500} />
              </div>

              {/* 日期范围选择 */}
              <div className="md:col-span-2">
                <DateRangeSelector value={dateRange} onChange={setDateRange} />
              </div>

              {/* 初始资金 */}
              <div className="space-y-2">
                <Label htmlFor="initial-capital">初始资金（元）</Label>
                <Input
                  id="initial-capital"
                  type="number"
                  value={initialCapital}
                  onChange={(e) => setInitialCapital(parseInt(e.target.value) || 1000000)}
                  min={10000}
                  step={10000}
                />
              </div>

              {/* 调仓频率 */}
              <div className="space-y-2">
                <Label htmlFor="rebalance-freq">调仓频率</Label>
                <Select value={rebalanceFreq} onValueChange={(v: any) => setRebalanceFreq(v)}>
                  <SelectTrigger id="rebalance-freq">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="D">每日</SelectItem>
                    <SelectItem value="W">每周</SelectItem>
                    <SelectItem value="M">每月</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 3. 离场策略 */}
        <ExitStrategySelector
          selectedIds={exitStrategyIds}
          onChange={setExitStrategyIds}
        />

        {/* 运行回测按钮 */}
        <div className="flex justify-center gap-4">
          <Button
            onClick={handleRunBacktest}
            disabled={isRunning || isLoadingStrategy || !!strategyError}
            className="w-full md:w-auto min-w-[200px]"
            size="lg"
          >
            {isRunning && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {isRunning ? '回测中...' : '运行回测'}
          </Button>
          {isRunning && taskId && (
            <Button
              onClick={handleCancelBacktest}
              variant="destructive"
              size="lg"
            >
              取消任务
            </Button>
          )}
        </div>

        {/* 4. 回测状态提示 */}
        {isRunning ? (
          <Card className="p-12 text-center">
            <div className="flex flex-col items-center justify-center space-y-4">
              <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-primary"></div>
              <div>
                <CardTitle className="text-2xl">
                  {taskStatus === 'PENDING' ? '任务排队中...' : '正在运行回测...'}
                </CardTitle>
                <CardDescription className="mt-2 text-base">
                  {taskStatus === 'PROGRESS' && progress.status
                    ? progress.status
                    : '正在计算策略回测结果，这可能需要几分钟时间'}
                </CardDescription>
                {isAsync && (
                  <CardDescription className="mt-2 text-sm text-blue-600">
                    💡 您可以自由导航到其他页面，任务将在后台继续执行
                  </CardDescription>
                )}
              </div>
              {taskStatus === 'PROGRESS' && progress.total > 0 && (
                <div className="w-full max-w-md">
                  <div className="w-full bg-gray-200 rounded-full h-2.5 dark:bg-gray-700">
                    <div
                      className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                      style={{ width: `${(progress.current / progress.total) * 100}%` }}
                    ></div>
                  </div>
                  <p className="text-sm text-muted-foreground mt-2">
                    {progress.current} / {progress.total}
                  </p>
                </div>
              )}
              {!isAsync && (
                <div className="text-sm text-muted-foreground mt-4">
                  <p>• 正在加载历史数据</p>
                  <p>• 正在执行策略信号</p>
                  <p>• 正在计算绩效指标</p>
                </div>
              )}
            </div>
          </Card>
        ) : executionId ? (
          // 回测完成，显示跳转按钮
          <Card className="p-12 text-center">
            <div className="flex flex-col items-center justify-center space-y-4">
              <div className="rounded-full bg-green-100 p-3">
                <svg className="h-16 w-16 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div>
                <CardTitle className="text-2xl text-green-600">回测完成</CardTitle>
                <CardDescription className="mt-2 text-base">
                  回测任务已成功完成，点击下方按钮查看详细结果
                </CardDescription>
              </div>
              <Button
                size="lg"
                onClick={() => router.push(`/backtest-results?id=${executionId}`)}
                className="mt-4"
              >
                查看回测结果
              </Button>
            </div>
          </Card>
        ) : (
          <Card className="p-12 text-center">
            <svg
              className="mx-auto h-24 w-24 text-muted-foreground"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
            <CardTitle className="mt-4">等待回测结果</CardTitle>
            <CardDescription className="mt-2">
              配置上方参数后，点击&ldquo;运行回测&rdquo;按钮开始
            </CardDescription>
          </Card>
        )}
      </div>
    </div>
  )
}

export default function BacktestPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    }>
      <BacktestContent />
    </Suspense>
  )
}
