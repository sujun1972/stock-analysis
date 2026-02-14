'use client'

import { useState, useEffect } from 'react'
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

export default function BacktestPage() {
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

  const handleRunBacktest = async () => {
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
    try {
      let response: any

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

        // 使用统一回测接口，传递ml_model策略ID和模型ID
        // strategyId 是 URL 中的 ML 模型 ID
        response = await apiClient.runUnifiedBacktest({
          strategy_id: mlStrategyId,  // ml_model 策略的数据库 ID
          stock_pool: stockPool,
          start_date: dateRange.start,
          end_date: dateRange.end,
          initial_capital: initialCapital,
          rebalance_freq: rebalanceFreq,
          // 通过 strategy_params 传递模型 ID
          strategy_params: {
            model_id: strategyId  // ML 模型的 ID (来自 URL 参数)
          },
          // 添加离场策略IDs（如果有选择）
          exit_strategy_ids: exitStrategyIds.length > 0 ? exitStrategyIds : undefined
        })
      } else {
        // 其他类型的策略回测：使用统一回测API
        if (strategyType === 'predefined') {
          request.strategy_type = 'predefined'
          request.strategy_name = strategyId!
          request.strategy_config = strategyConfig
        } else if (strategyType === 'unified') {
          // 统一策略使用新的 API (V2.0)
          request.strategy_id = parseInt(strategyId!)
        } else {
          // config 和 dynamic 类型使用旧的 API (V1.0)
          request.strategy_type = strategyType
          request.strategy_id = parseInt(strategyId!)
        }

        response = await apiClient.runUnifiedBacktest(request)
      }
      if (response.success && response.data) {
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
    } catch (error: any) {
      // 格式化错误信息，处理 Pydantic 验证错误等复杂对象
      toast({
        title: '回测失败',
        description: extractApiError(error, '网络错误'),
        variant: 'destructive'
      })
    } finally {
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
    <>
      <div className="container mx-auto py-6 px-4 max-w-7xl">
        <div className="space-y-6">
          {/* 页面标题 */}
          <div>
            <h1 className="text-3xl font-bold tracking-tight">策略回测</h1>
            <p className="text-muted-foreground mt-2">
              配置参数,运行回测分析
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* 左侧: 配置面板 */}
            <div className="lg:col-span-1 space-y-6">
              {/* 策略信息卡片 */}
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

            {/* 回测参数卡片 */}
            <Card>
              <CardHeader>
                <CardTitle>回测参数</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* 股票池选择 */}
                <StockPoolSelector value={stockPool} onChange={setStockPool} maxStocks={50} />

                {/* 日期范围选择 */}
                <DateRangeSelector value={dateRange} onChange={setDateRange} />

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
              </CardContent>
            </Card>

            {/* 离场策略选择器 */}
            <ExitStrategySelector
              selectedIds={exitStrategyIds}
              onChange={setExitStrategyIds}
            />

            {/* 运行回测按钮 */}
            <Button
              onClick={handleRunBacktest}
              disabled={isRunning || isLoadingStrategy || !!strategyError}
              className="w-full"
              size="lg"
            >
              {isRunning && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {isRunning ? '回测中...' : '运行回测'}
            </Button>
          </div>

          {/* 右侧: 结果展示 */}
          <div className="lg:col-span-2">
            {isRunning ? (
              <Card className="p-12 text-center">
                <div className="flex flex-col items-center justify-center">
                  <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-primary"></div>
                  <CardTitle className="mt-4">正在运行回测...</CardTitle>
                  <CardDescription className="mt-2">
                    请稍候,正在计算策略回测结果
                  </CardDescription>
                </div>
              </Card>
            ) : !result ? (
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
                  在左侧配置回测参数,点击&ldquo;运行回测&rdquo;按钮开始
                </CardDescription>
              </Card>
            ) : (
              <BacktestResultView result={result} />
            )}
            </div>
          </div>
        </div>
      </div>

      {/* 交易明细表格 - 占据全屏宽度 */}
      {result && result.trades && result.trades.length > 0 && (
        <div className="w-full bg-gray-50 dark:bg-gray-900 py-6">
          <div className="container-custom">
            <TradesTable result={result} />
          </div>
        </div>
      )}
    </>
  )
}
