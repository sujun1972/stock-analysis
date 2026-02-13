/**
 * 回测结果展示组件
 *
 * 功能:
 * - 显示策略信息、回测参数
 * - 展示绩效指标（收益率、夏普率、最大回撤等）
 * - 显示股票K线图表和权益曲线
 *
 * 组件拆分:
 * - BacktestResultView: 主要内容（策略信息、绩效指标、图表）
 * - TradesTable: 独立的交易明细表格（可导出到全屏宽度布局）
 *
 * Note:
 * - 交易明细表格已从主组件中分离，以支持全屏宽度显示
 * - showTradesTable prop 用于向后兼容
 */

'use client'

import { memo, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import dynamic from 'next/dynamic'

// 动态导入图表组件
const PerformanceMetrics = dynamic(() => import('@/components/PerformanceMetrics'), {
  ssr: false
})
const StockChartsCarousel = dynamic(() => import('@/components/backtest/StockChartsCarousel'), {
  ssr: false
})

interface BacktestResultViewProps {
  result: any
  showTradesTable?: boolean  // 是否在这里显示交易表格
}

const BacktestResultView = memo(function BacktestResultView({
  result,
  showTradesTable = false  // 默认不在这里显示，由父组件单独渲染
}: BacktestResultViewProps) {
  if (!result) return null

  return (
    <div className="space-y-6">
      {/* 策略信息卡片 */}
      <Card className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 border-blue-200 dark:border-blue-800">
        <CardHeader>
          <CardTitle>{result.strategy_info?.display_name || result.strategy_name || '回测结果'}</CardTitle>
          <CardDescription>
            {result.backtest_params?.stock_pool && `股票池: ${result.backtest_params.stock_pool.length} 只 | `}
            {result.backtest_params?.start_date && result.backtest_params?.end_date &&
              `周期: ${result.backtest_params.start_date} 至 ${result.backtest_params.end_date}`}
            {result.metrics?.total_trades !== undefined && ` | 交易次数: ${result.metrics.total_trades}`}
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

      {/* 股票K线图表和交易信号（包含权益曲线） */}
      {result.stock_charts && Object.keys(result.stock_charts).length > 0 && (
        <StockChartsCarousel
          stockCharts={result.stock_charts}
          equityCurve={result.equity_curve}
        />
      )}

      {/* 旧版：在这里显示交易明细（向后兼容） */}
      {showTradesTable && result.trades && result.trades.length > 0 && (
        <TradesTable result={result} />
      )}
    </div>
  )
})

BacktestResultView.displayName = 'BacktestResultView'

// 独立的交易明细表格组件，可以放在任何位置
export const TradesTable = memo(function TradesTable({ result }: { result: any }) {
  // 交易明细分页状态
  const [tradesPage, setTradesPage] = useState(1)

  // 翻译原因/策略字段为中文
  const translateReason = (reason?: string, trigger?: string) => {
    if (!reason && !trigger) return '-'

    const reasonMap: Record<string, string> = {
      'rebalance': '调仓',
      'signal': '信号',
      'risk_control': '风险控制',
      'strategy': '策略',
      'reverse_entry': '反向入场'
    }
    const triggerMap: Record<string, string> = {
      'stop_loss': '止损',
      'take_profit': '止盈',
      'trailing_stop': '移动止损',
      'max_holding_period': '持仓时长',
      'rebalance': '调仓'
    }

    const reasonText = reason ? (reasonMap[reason] || reason) : ''
    const triggerText = trigger ? (triggerMap[trigger] || trigger) : ''

    if (reasonText && triggerText) {
      return `${reasonText}/${triggerText}`
    }
    return reasonText || triggerText || '-'
  }

  const tradesPerPage = 20
  const totalTrades = result.trades?.length || 0
  const totalPages = Math.ceil(totalTrades / tradesPerPage)
  const startIndex = (tradesPage - 1) * tradesPerPage
  const endIndex = startIndex + tradesPerPage
  const currentTrades = result.trades?.slice(startIndex, endIndex) || []

  if (!result.trades || result.trades.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>交易明细</CardTitle>
            <CardDescription className="mt-1">
              共 {totalTrades} 笔交易，当前显示第 {startIndex + 1}-{Math.min(endIndex, totalTrades)} 笔
            </CardDescription>
          </div>
          {totalPages > 1 && (
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setTradesPage(p => Math.max(1, p - 1))}
                disabled={tradesPage === 1}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-sm text-muted-foreground min-w-[80px] text-center">
                {tradesPage} / {totalPages}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setTradesPage(p => Math.min(totalPages, p + 1))}
                disabled={tradesPage === totalPages}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </div>
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
                  股票
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
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  原因/策略
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  现金余额
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  持仓市值
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  总资产
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {currentTrades.map((trade: any, idx: number) => {
                // 兼容不同的字段名：type/action, amount/trade_value
                const action = trade.type || trade.action
                const isBuy = action === 'buy'
                const amount = trade.amount || trade.trade_value || (trade.price * trade.shares)

                // 获取股票代码和名称（兼容多种字段名）
                const stockCode = trade.code || trade.symbol || trade.stock_code || '-'
                const stockName = trade.stock_name || trade.name || ''

                // 格式化股票显示：股票名称(代码)
                const formatStock = () => {
                  if (stockName) {
                    return `${stockName}(${stockCode})`
                  }
                  return stockCode
                }

                // 格式化日期：移除时间部分
                const formatDate = (dateStr: string) => {
                  if (!dateStr) return '-'
                  // 如果包含 'T'，只取日期部分
                  if (dateStr.includes('T')) {
                    return dateStr.split('T')[0]
                  }
                  return dateStr
                }

                return (
                  <tr key={idx}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                      {formatDate(trade.date)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                      <span className="font-medium">{formatStock()}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={`px-2 py-1 rounded ${
                        isBuy
                          ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
                          : 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                      }`}>
                        {isBuy ? '买入' : '卖出'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                      ¥{(trade.price || 0).toFixed(2)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                      {trade.shares || 0}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                      ¥{(amount || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                      {isBuy
                        ? translateReason(trade.entry_reason)
                        : translateReason(trade.exit_reason, trade.exit_trigger)
                      }
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100 text-right">
                      {trade.cash_after !== undefined
                        ? `¥${trade.cash_after.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`
                        : '-'
                      }
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100 text-right">
                      {trade.holdings_value_after !== undefined
                        ? `¥${trade.holdings_value_after.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`
                        : '-'
                      }
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100 text-right">
                      {trade.total_value_after !== undefined
                        ? `¥${trade.total_value_after.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`
                        : '-'
                      }
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
})

TradesTable.displayName = 'TradesTable'

export default BacktestResultView
