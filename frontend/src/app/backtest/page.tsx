'use client'

import { useState, useEffect } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'
import { apiClient } from '@/lib/api-client'
import type {
  StrategyTypeMeta,
  StrategyConfig,
  DynamicStrategy,
  BacktestRequest
} from '@/types/strategy'
import StrategyConfigEditor from '@/components/strategies/StrategyConfigEditor'
import StockPoolSelector from '@/components/backtest/StockPoolSelector'
import DateRangeSelector from '@/components/backtest/DateRangeSelector'
import BacktestResultView from '@/components/backtest/BacktestResultView'
import { Loader2, TrendingUp, Settings, Code } from 'lucide-react'

export default function BacktestPage() {
  // 策略来源类型
  const [strategySource, setStrategySource] = useState<'predefined' | 'config' | 'dynamic'>('predefined')

  // 预定义策略相关
  const [strategyTypes, setStrategyTypes] = useState<StrategyTypeMeta[]>([])
  const [selectedStrategyType, setSelectedStrategyType] = useState<string>('')
  const [strategyConfig, setStrategyConfig] = useState<Record<string, any>>({})

  // 策略配置相关
  const [strategyConfigs, setStrategyConfigs] = useState<StrategyConfig[]>([])
  const [selectedConfigId, setSelectedConfigId] = useState<number | undefined>()

  // 动态策略相关
  const [dynamicStrategies, setDynamicStrategies] = useState<DynamicStrategy[]>([])
  const [selectedDynamicId, setSelectedDynamicId] = useState<number | undefined>()

  // 回测参数
  const [stockPool, setStockPool] = useState<string[]>([])
  const [dateRange, setDateRange] = useState({
    start: new Date(new Date().setFullYear(new Date().getFullYear() - 1)).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0]
  })
  const [initialCapital, setInitialCapital] = useState(1000000)
  const [rebalanceFreq, setRebalanceFreq] = useState<'D' | 'W' | 'M'>('W')

  // 回测状态
  const [isRunning, setIsRunning] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(false)

  const { toast } = useToast()

  // 加载策略类型列表
  useEffect(() => {
    loadStrategyTypes()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 根据策略来源加载对应数据
  useEffect(() => {
    if (strategySource === 'config') {
      loadStrategyConfigs()
    } else if (strategySource === 'dynamic') {
      loadDynamicStrategies()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [strategySource])

  // 当选择的策略类型变化时，更新默认配置
  useEffect(() => {
    if (selectedStrategyType && (strategyTypes || []).length > 0) {
      const strategyType = (strategyTypes || []).find(t => t.type === selectedStrategyType)
      if (strategyType) {
        setStrategyConfig(strategyType.default_params)
      }
    }
  }, [selectedStrategyType, strategyTypes])

  const loadStrategyTypes = async () => {
    setIsLoading(true)
    try {
      const response = await apiClient.getStrategyTypes()
      if (response.success && response.data) {
        const types = Array.isArray(response.data) ? response.data : []
        setStrategyTypes(types)
        if (types.length > 0) {
          setSelectedStrategyType(types[0].type)
          setStrategyConfig(types[0].default_params)
        }
      } else {
        toast({
          title: '加载失败',
          description: response.error || '无法加载策略类型列表',
          variant: 'destructive'
        })
      }
    } catch (error: any) {
      toast({
        title: '加载失败',
        description: error.message || '无法加载策略类型列表',
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }

  const loadStrategyConfigs = async () => {
    setIsLoading(true)
    try {
      const response = await apiClient.getStrategyConfigs({ is_active: true })
      if (response.success && response.data) {
        const items = response.data.items || []
        setStrategyConfigs(items)
        if (items.length > 0 && !selectedConfigId) {
          setSelectedConfigId(items[0].id)
        }
      } else {
        toast({
          title: '加载失败',
          description: response.error || '无法加载策略配置列表',
          variant: 'destructive'
        })
      }
    } catch (error: any) {
      toast({
        title: '加载失败',
        description: error.message || '无法加载策略配置列表',
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }

  const loadDynamicStrategies = async () => {
    setIsLoading(true)
    try {
      const response = await apiClient.getDynamicStrategies({
        is_enabled: true,
        validation_status: 'passed'
      })
      if (response.success && response.data) {
        const items = response.data.items || []
        setDynamicStrategies(items)
        if (items.length > 0 && !selectedDynamicId) {
          setSelectedDynamicId(items[0].id)
        }
      } else {
        toast({
          title: '加载失败',
          description: response.error || '无法加载动态策略列表',
          variant: 'destructive'
        })
      }
    } catch (error: any) {
      toast({
        title: '加载失败',
        description: error.message || '无法加载动态策略列表',
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }

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

    // 验证策略选择
    if (strategySource === 'predefined' && !selectedStrategyType) {
      toast({
        title: '参数错误',
        description: '请选择预定义策略',
        variant: 'destructive'
      })
      return
    }

    if (strategySource === 'config' && !selectedConfigId) {
      toast({
        title: '参数错误',
        description: '请选择策略配置',
        variant: 'destructive'
      })
      return
    }

    if (strategySource === 'dynamic' && !selectedDynamicId) {
      toast({
        title: '参数错误',
        description: '请选择动态策略',
        variant: 'destructive'
      })
      return
    }

    // 构建请求参数
    const request: BacktestRequest = {
      strategy_type: strategySource,
      stock_pool: stockPool,
      start_date: dateRange.start,
      end_date: dateRange.end,
      initial_capital: initialCapital,
      rebalance_freq: rebalanceFreq
    }

    if (strategySource === 'predefined') {
      request.strategy_name = selectedStrategyType
      request.strategy_config = strategyConfig
    } else if (strategySource === 'config') {
      request.strategy_id = selectedConfigId
    } else if (strategySource === 'dynamic') {
      request.strategy_id = selectedDynamicId
    }

    // 运行回测
    setIsRunning(true)
    setResult(null)
    try {
      const response = await apiClient.runUnifiedBacktest(request)
      if (response.success && response.data) {
        setResult(response.data)
        toast({
          title: '回测完成',
          description: '策略回测已完成，请查看结果'
        })
      } else {
        toast({
          title: '回测失败',
          description: response.error || '未知错误',
          variant: 'destructive'
        })
      }
    } catch (error: any) {
      toast({
        title: '回测失败',
        description: error.response?.data?.detail || error.message || '网络错误',
        variant: 'destructive'
      })
    } finally {
      setIsRunning(false)
    }
  }

  const currentStrategyType = (strategyTypes || []).find(t => t.type === selectedStrategyType)
  const selectedConfig = (strategyConfigs || []).find(c => c.id === selectedConfigId)
  const selectedDynamic = (dynamicStrategies || []).find(s => s.id === selectedDynamicId)

  return (
    <div className="container mx-auto py-6 px-4 max-w-7xl">
      <div className="space-y-6">
        {/* 页面标题 */}
        <div>
          <h1 className="text-3xl font-bold tracking-tight">策略回测</h1>
          <p className="text-muted-foreground mt-2">
            选择策略类型，配置参数，运行回测分析
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 左侧: 配置面板 */}
          <div className="lg:col-span-1 space-y-6">
            {/* 策略选择卡片 */}
            <Card>
              <CardHeader>
                <CardTitle>策略选择</CardTitle>
                <CardDescription>
                  选择策略类型并配置参数
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Tabs value={strategySource} onValueChange={(v: any) => setStrategySource(v)}>
                  <TabsList className="grid w-full grid-cols-3">
                    <TabsTrigger value="predefined" className="text-xs">
                      <TrendingUp className="h-3 w-3 mr-1" />
                      预定义
                    </TabsTrigger>
                    <TabsTrigger value="config" className="text-xs">
                      <Settings className="h-3 w-3 mr-1" />
                      配置
                    </TabsTrigger>
                    <TabsTrigger value="dynamic" className="text-xs">
                      <Code className="h-3 w-3 mr-1" />
                      动态
                    </TabsTrigger>
                  </TabsList>

                  {/* 预定义策略 */}
                  <TabsContent value="predefined" className="space-y-4 mt-4">
                    {isLoading ? (
                      <div className="flex justify-center py-8">
                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                      </div>
                    ) : (
                      <>
                        <div className="space-y-2">
                          <Label>策略类型</Label>
                          <Select value={selectedStrategyType} onValueChange={setSelectedStrategyType}>
                            <SelectTrigger>
                              <SelectValue placeholder="选择策略" />
                            </SelectTrigger>
                            <SelectContent>
                              {(strategyTypes || []).map(type => (
                                <SelectItem key={type.type} value={type.type}>
                                  {type.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        {currentStrategyType && (
                          <>
                            <div className="p-3 bg-muted rounded-lg">
                              <p className="text-sm text-muted-foreground">
                                {currentStrategyType.description}
                              </p>
                              {currentStrategyType.category && (
                                <p className="text-xs text-muted-foreground mt-1">
                                  类别: {currentStrategyType.category}
                                </p>
                              )}
                            </div>

                            <div className="space-y-3">
                              <Label className="text-sm font-semibold">策略参数</Label>
                              <StrategyConfigEditor
                                strategyType={selectedStrategyType}
                                config={strategyConfig}
                                schema={currentStrategyType.param_schema}
                                onChange={setStrategyConfig}
                              />
                            </div>
                          </>
                        )}
                      </>
                    )}
                  </TabsContent>

                  {/* 策略配置 */}
                  <TabsContent value="config" className="space-y-4 mt-4">
                    {isLoading ? (
                      <div className="flex justify-center py-8">
                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                      </div>
                    ) : (strategyConfigs || []).length === 0 ? (
                      <div className="text-center py-8">
                        <p className="text-sm text-muted-foreground mb-4">
                          暂无可用的策略配置
                        </p>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => window.location.href = '/strategies/configs'}
                        >
                          前往创建
                        </Button>
                      </div>
                    ) : (
                      <>
                        <div className="space-y-2">
                          <Label>选择配置</Label>
                          <Select
                            value={selectedConfigId?.toString()}
                            onValueChange={(v) => setSelectedConfigId(parseInt(v))}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="选择配置" />
                            </SelectTrigger>
                            <SelectContent>
                              {(strategyConfigs || []).map(config => (
                                <SelectItem key={config.id} value={config.id.toString()}>
                                  {config.name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        {selectedConfig && (
                          <div className="p-3 bg-muted rounded-lg space-y-2">
                            <div>
                              <p className="text-xs text-muted-foreground">策略类型</p>
                              <p className="text-sm font-medium">{selectedConfig.strategy_type}</p>
                            </div>
                            {selectedConfig.description && (
                              <div>
                                <p className="text-xs text-muted-foreground">描述</p>
                                <p className="text-sm">{selectedConfig.description}</p>
                              </div>
                            )}
                            <div>
                              <p className="text-xs text-muted-foreground">配置参数</p>
                              <div className="text-xs font-mono mt-1 p-2 bg-background rounded">
                                {JSON.stringify(selectedConfig.config, null, 2)}
                              </div>
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </TabsContent>

                  {/* 动态策略 */}
                  <TabsContent value="dynamic" className="space-y-4 mt-4">
                    {isLoading ? (
                      <div className="flex justify-center py-8">
                        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                      </div>
                    ) : (dynamicStrategies || []).length === 0 ? (
                      <div className="text-center py-8">
                        <p className="text-sm text-muted-foreground mb-4">
                          暂无可用的动态策略
                        </p>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => window.location.href = '/strategies/dynamic'}
                        >
                          前往创建
                        </Button>
                      </div>
                    ) : (
                      <>
                        <div className="space-y-2">
                          <Label>选择策略</Label>
                          <Select
                            value={selectedDynamicId?.toString()}
                            onValueChange={(v) => setSelectedDynamicId(parseInt(v))}
                          >
                            <SelectTrigger>
                              <SelectValue placeholder="选择策略" />
                            </SelectTrigger>
                            <SelectContent>
                              {(dynamicStrategies || []).map(strategy => (
                                <SelectItem key={strategy.id} value={strategy.id.toString()}>
                                  {strategy.display_name}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        {selectedDynamic && (
                          <div className="p-3 bg-muted rounded-lg space-y-2">
                            <div>
                              <p className="text-xs text-muted-foreground">策略名称</p>
                              <p className="text-sm font-medium">{selectedDynamic.strategy_name}</p>
                            </div>
                            {selectedDynamic.description && (
                              <div>
                                <p className="text-xs text-muted-foreground">描述</p>
                                <p className="text-sm">{selectedDynamic.description}</p>
                              </div>
                            )}
                            <div>
                              <p className="text-xs text-muted-foreground">验证状态</p>
                              <p className="text-sm font-medium text-green-600">
                                {selectedDynamic.validation_status === 'passed' ? '✓ 验证通过' : selectedDynamic.validation_status}
                              </p>
                            </div>
                            {selectedDynamic.version && (
                              <div>
                                <p className="text-xs text-muted-foreground">版本</p>
                                <p className="text-sm">v{selectedDynamic.version}</p>
                              </div>
                            )}
                          </div>
                        )}
                      </>
                    )}
                  </TabsContent>
                </Tabs>
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

            {/* 运行回测按钮 */}
            <Button
              onClick={handleRunBacktest}
              disabled={isRunning || isLoading}
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
                    请稍候，正在计算策略回测结果
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
                  在左侧配置策略和回测参数，点击&ldquo;运行回测&rdquo;按钮开始
                </CardDescription>
              </Card>
            ) : (
              <BacktestResultView result={result} />
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
