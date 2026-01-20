'use client'

import { useState } from 'react'
import BacktestPanel from '@/components/BacktestPanel'
import BacktestKLineChart from '@/components/BacktestKLineChart'
import EquityCurveChart from '@/components/EquityCurveChart'
import PerformanceMetrics from '@/components/PerformanceMetrics'

export default function BacktestPage() {
  const [backtestResult, setBacktestResult] = useState<any>(null)

  const handleBacktestComplete = (result: any) => {
    console.log('回测完成:', result)
    setBacktestResult(result)
  }

  const renderSingleStockResults = () => {
    if (!backtestResult || backtestResult.mode !== 'single') return null

    return (
      <div className="space-y-6">
        {/* K线图 + 买卖信号 */}
        <BacktestKLineChart
          data={backtestResult.kline_data}
          signalPoints={backtestResult.signal_points}
          stockCode={backtestResult.symbol}
        />

        {/* 资金曲线对比 */}
        <EquityCurveChart
          strategyData={backtestResult.equity_curve}
          benchmarkData={backtestResult.benchmark_curve}
          title="策略净值 vs 沪深300"
        />

        {/* 绩效报告 */}
        <PerformanceMetrics
          metrics={backtestResult.metrics}
          mode="single"
        />

        {/* 交易明细 */}
        {backtestResult.trades && backtestResult.trades.length > 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
              交易明细 (最近{backtestResult.trades.length}笔)
            </h2>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      日期
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      操作
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      价格
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      数量
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      金额
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {backtestResult.trades.map((trade: any, idx: number) => (
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
            {backtestResult.total_trades > backtestResult.trades.length && (
              <p className="mt-4 text-sm text-gray-500 dark:text-gray-400 text-center">
                共{backtestResult.total_trades}笔交易,显示最近{backtestResult.trades.length}笔
              </p>
            )}
          </div>
        )}
      </div>
    )
  }

  const renderMultiStockResults = () => {
    if (!backtestResult || backtestResult.mode !== 'multi') return null

    return (
      <div className="space-y-6">
        {/* 资金曲线对比 */}
        <EquityCurveChart
          strategyData={backtestResult.equity_curve}
          benchmarkData={backtestResult.benchmark_curve}
          title="组合净值 vs 沪深300"
        />

        {/* 绩效报告 */}
        <PerformanceMetrics
          metrics={backtestResult.metrics}
          mode="multi"
        />

        {/* 组合信息 */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
            组合信息
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
              <div className="text-sm text-gray-600 dark:text-gray-400">股票数量</div>
              <div className="text-2xl font-bold text-blue-600 dark:text-blue-400 mt-1">
                {backtestResult.symbols.length}
              </div>
            </div>
            <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
              <div className="text-sm text-gray-600 dark:text-gray-400">数据点数</div>
              <div className="text-2xl font-bold text-purple-600 dark:text-purple-400 mt-1">
                {backtestResult.equity_curve.length}
              </div>
            </div>
            <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
              <div className="text-sm text-gray-600 dark:text-gray-400">持仓记录</div>
              <div className="text-2xl font-bold text-green-600 dark:text-green-400 mt-1">
                {backtestResult.positions_count}
              </div>
            </div>
          </div>

          {/* 股票列表 */}
          <div className="mt-6">
            <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
              回测股票池 ({backtestResult.symbols.length}只)
            </h3>
            <div className="flex flex-wrap gap-2">
              {backtestResult.symbols.map((symbol: string, idx: number) => (
                <span
                  key={idx}
                  className="px-3 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-full text-sm"
                >
                  {symbol}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* 页面标题 */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            策略回测系统
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            支持单股K线回测和多股组合回测,自动对比沪深300基准
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 左侧: 配置面板 */}
          <div className="lg:col-span-1">
            <BacktestPanel onBacktestComplete={handleBacktestComplete} />
          </div>

          {/* 右侧: 结果展示 */}
          <div className="lg:col-span-2">
            {!backtestResult ? (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-12 text-center">
                <svg
                  className="mx-auto h-24 w-24 text-gray-400"
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
                <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-white">
                  等待回测结果
                </h3>
                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                  在左侧配置回测参数并点击&ldquo;运行回测&rdquo;按钮
                </p>
              </div>
            ) : backtestResult.mode === 'single' ? (
              renderSingleStockResults()
            ) : (
              renderMultiStockResults()
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
