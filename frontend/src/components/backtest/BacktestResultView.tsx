/**
 * 回测结果展示组件
 * 展示回测的关键指标和结果
 */

'use client'

import { memo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import dynamic from 'next/dynamic'

// 动态导入图表组件
const PerformanceMetrics = dynamic(() => import('@/components/PerformanceMetrics'), {
  ssr: false
})

interface BacktestResultViewProps {
  result: any
}

const BacktestResultView = memo(function BacktestResultView({
  result
}: BacktestResultViewProps) {
  if (!result) return null

  return (
    <div className="space-y-6">
      {/* 策略信息卡片 */}
      <Card className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 border-blue-200 dark:border-blue-800">
        <CardHeader>
          <CardTitle>{result.strategy_name || '回测结果'}</CardTitle>
          <CardDescription>
            {result.symbol && `股票: ${result.symbol} | `}
            {result.symbols && `股票池: ${result.symbols.length} 只 | `}
            周期: {result.start_date} 至 {result.end_date}
            {result.total_trades !== undefined && ` | 交易次数: ${result.total_trades}`}
          </CardDescription>
        </CardHeader>
      </Card>

      {/* 绩效指标 */}
      {result.metrics && (
        <PerformanceMetrics
          metrics={result.metrics}
          mode={result.mode || 'single'}
        />
      )}

      {/* 基本统计信息 */}
      <Card>
        <CardHeader>
          <CardTitle>回测统计</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {result.metrics?.total_return !== undefined && (
              <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                <div className="text-sm text-gray-600 dark:text-gray-400">总收益率</div>
                <div className={`text-2xl font-bold mt-1 ${
                  result.metrics.total_return > 0
                    ? 'text-green-600 dark:text-green-400'
                    : 'text-red-600 dark:text-red-400'
                }`}>
                  {(result.metrics.total_return * 100).toFixed(2)}%
                </div>
              </div>
            )}
            {result.metrics?.sharpe_ratio !== undefined && (
              <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                <div className="text-sm text-gray-600 dark:text-gray-400">夏普比率</div>
                <div className="text-2xl font-bold text-purple-600 dark:text-purple-400 mt-1">
                  {result.metrics.sharpe_ratio.toFixed(2)}
                </div>
              </div>
            )}
            {result.metrics?.max_drawdown !== undefined && (
              <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4">
                <div className="text-sm text-gray-600 dark:text-gray-400">最大回撤</div>
                <div className="text-2xl font-bold text-red-600 dark:text-red-400 mt-1">
                  {(result.metrics.max_drawdown * 100).toFixed(2)}%
                </div>
              </div>
            )}
            {result.metrics?.win_rate !== undefined && (
              <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                <div className="text-sm text-gray-600 dark:text-gray-400">胜率</div>
                <div className="text-2xl font-bold text-green-600 dark:text-green-400 mt-1">
                  {(result.metrics.win_rate * 100).toFixed(2)}%
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 交易明细（如果有） */}
      {result.trades && result.trades.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>交易明细 (最近 {Math.min(result.trades.length, 20)} 笔)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                      日期
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                      操作
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                      价格
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                      数量
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                      金额
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {result.trades.slice(0, 20).map((trade: any, idx: number) => (
                    <tr key={idx}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                        {trade.date}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className={`px-2 py-1 rounded ${
                          trade.type === 'buy'
                            ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
                            : 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                        }`}>
                          {trade.type === 'buy' ? '买入' : '卖出'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                        ¥{trade.price.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                        {trade.shares}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                        ¥{trade.amount.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {result.total_trades > 20 && (
              <p className="mt-4 text-sm text-muted-foreground text-center">
                共 {result.total_trades} 笔交易，显示最近 20 笔
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
})

BacktestResultView.displayName = 'BacktestResultView'

export default BacktestResultView
