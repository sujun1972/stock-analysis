'use client'

import { Suspense } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type {
  StrategyTypeMeta,
  StrategyConfig,
  DynamicStrategy,
  Strategy
} from '@/types/strategy'
import StrategyConfigEditor from '@/components/strategies/StrategyConfigEditor'
import StockPoolSelector from '@/components/backtest/StockPoolSelector'
import DateRangeSelector from '@/components/backtest/DateRangeSelector'
import ExitStrategySelector from '@/components/backtest/ExitStrategySelector'
import { Loader2, AlertCircle } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useBacktestForm } from './hooks/useBacktestForm'
import type { StrategySourceType } from './hooks/useBacktestForm'

function BacktestContent() {
  const {
    strategyType,
    strategyId,
    strategyData,
    strategyConfig,
    setStrategyConfig,
    isLoadingStrategy,
    strategyError,
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
    isRunning,
    isAsync,
    taskId,
    taskStatus,
    progress,
    executionId,
    handleRunBacktest,
    handleCancelBacktest,
    router,
  } = useBacktestForm()

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
                onClick={() => router.push(`/backtest-results/${executionId}`)}
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
