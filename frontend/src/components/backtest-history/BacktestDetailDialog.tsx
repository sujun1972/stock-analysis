'use client'

import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import BacktestResultView, { TradesTable } from '@/components/backtest/BacktestResultView'

interface BacktestDetailDialogProps {
  record: any
  open: boolean
  onOpenChange: (open: boolean) => void
}

export default function BacktestDetailDialog({ record, open, onOpenChange }: BacktestDetailDialogProps) {
  if (!record) return null

  const formatPercent = (value: number) => {
    return `${(value * 100).toFixed(2)}%`
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>回测详情</DialogTitle>
          <DialogDescription>
            {record.strategy?.display_name || record.strategy?.name} -
            {record.execution_params?.start_date} ~ {record.execution_params?.end_date}
          </DialogDescription>
        </DialogHeader>

        <Tabs defaultValue="overview" className="w-full">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="overview">概览</TabsTrigger>
            <TabsTrigger value="trades">交易明细</TabsTrigger>
            <TabsTrigger value="chart">图表</TabsTrigger>
          </TabsList>

          {/* 概览标签页 */}
          <TabsContent value="overview" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>绩效指标</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-3 gap-6">
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">总收益率</p>
                    <p className={`text-2xl font-bold ${
                      record.metrics?.total_return >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {formatPercent(record.metrics?.total_return || 0)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">年化收益率</p>
                    <p className="text-2xl font-bold">
                      {formatPercent(record.metrics?.annual_return || 0)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">夏普比率</p>
                    <p className="text-2xl font-bold">
                      {record.metrics?.sharpe_ratio?.toFixed(2) || '0.00'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">最大回撤</p>
                    <p className="text-2xl font-bold text-red-600">
                      {formatPercent(record.metrics?.max_drawdown || 0)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">索提诺比率</p>
                    <p className="text-2xl font-bold">
                      {record.metrics?.sortino_ratio?.toFixed(2) || '0.00'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">卡玛比率</p>
                    <p className="text-2xl font-bold">
                      {record.metrics?.calmar_ratio?.toFixed(2) || '0.00'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">胜率</p>
                    <p className="text-2xl font-bold">
                      {formatPercent(record.metrics?.win_rate || 0)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">盈亏比</p>
                    <p className="text-2xl font-bold">
                      {record.metrics?.profit_factor?.toFixed(2) || '0.00'}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">交易次数</p>
                    <p className="text-2xl font-bold">
                      {record.metrics?.total_trades || 0}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>回测参数</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">股票池:</span>
                    <span className="ml-2 font-medium">
                      {record.execution_params?.stock_pool?.length || 0} 只股票
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">初始资金:</span>
                    <span className="ml-2 font-medium">
                      ¥{(record.execution_params?.initial_capital || 0).toLocaleString()}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">回测区间:</span>
                    <span className="ml-2 font-medium">
                      {record.execution_params?.start_date} ~ {record.execution_params?.end_date}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-500 dark:text-gray-400">执行时长:</span>
                    <span className="ml-2 font-medium">
                      {record.execution_duration_ms ?
                        `${(record.execution_duration_ms / 1000).toFixed(2)}秒` :
                        '-'}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* 交易明细标签页 */}
          <TabsContent value="trades">
            <Card>
              <CardHeader>
                <CardTitle>交易记录</CardTitle>
                <CardDescription>
                  共 {record.result?.trades?.length || 0} 笔交易
                </CardDescription>
              </CardHeader>
              <CardContent>
                {record.result?.trades && record.result.trades.length > 0 ? (
                  <TradesTable result={record.result} />
                ) : (
                  <p className="text-center py-8 text-gray-500">暂无交易记录</p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* 图表标签页 */}
          <TabsContent value="chart">
            {record.result?.equity_curve && record.result.equity_curve.length > 0 ? (
              <BacktestResultView
                metrics={record.metrics}
                equityCurve={record.result.equity_curve}
                trades={record.result.trades || []}
                stockCharts={record.result.stock_charts || {}}
              />
            ) : (
              <Card>
                <CardContent className="py-12">
                  <p className="text-center text-gray-500">暂无图表数据</p>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  )
}
