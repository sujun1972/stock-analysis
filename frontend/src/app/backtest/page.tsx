'use client'

import { useState } from 'react'
import BacktestPanel from '@/components/BacktestPanel'
import BacktestKLineChart from '@/components/BacktestKLineChart'
import EquityCurveChart from '@/components/EquityCurveChart'
import PerformanceMetrics from '@/components/PerformanceMetrics'

interface BacktestHistory {
  id: string
  timestamp: number
  strategy_name: string
  symbol: string
  result: any
}

export default function BacktestPage() {
  const [backtestResult, setBacktestResult] = useState<any>(null)
  const [backtestHistory, setBacktestHistory] = useState<BacktestHistory[]>([])
  const [selectedHistoryIds, setSelectedHistoryIds] = useState<Set<string>>(new Set())

  const handleBacktestComplete = (result: any) => {
    console.log('回测完成:', result)
    setBacktestResult(result)

    // 保存到历史记录
    const historyItem: BacktestHistory = {
      id: `backtest_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: Date.now(),
      strategy_name: result.strategy_name || '未知策略',
      symbol: result.symbol || result.symbols?.[0] || '未知股票',
      result: result
    }

    setBacktestHistory(prev => [historyItem, ...prev].slice(0, 10)) // 最多保留10个
  }

  const toggleHistorySelection = (id: string) => {
    const newSelection = new Set(selectedHistoryIds)
    if (newSelection.has(id)) {
      newSelection.delete(id)
    } else {
      if (newSelection.size >= 3) {
        // 最多选择3个进行对比
        return
      }
      newSelection.add(id)
    }
    setSelectedHistoryIds(newSelection)
  }

  const getSelectedResults = () => {
    return backtestHistory
      .filter(item => selectedHistoryIds.has(item.id))
      .map(item => item.result)
  }

  const renderSingleStockResults = () => {
    if (!backtestResult || backtestResult.mode !== 'single') return null

    return (
      <div className="space-y-6">
        {/* 策略信息卡片 */}
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                {backtestResult.strategy_name || '回测策略'}
              </h3>
              <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                股票: {backtestResult.symbol} |
                周期: {backtestResult.start_date} 至 {backtestResult.end_date} |
                交易次数: {backtestResult.total_trades || 0}
              </p>
            </div>
            <button
              onClick={() => {
                // 自动选中当前结果用于对比
                const currentId = backtestHistory[0]?.id
                if (currentId) {
                  toggleHistorySelection(currentId)
                }
              }}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors"
            >
              添加到对比
            </button>
          </div>
        </div>

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
          title={`${backtestResult.strategy_name} vs 沪深300`}
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
        {/* 策略信息卡片 */}
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-lg p-4 border border-blue-200 dark:border-blue-800">
          <h3 className="text-lg font-bold text-gray-900 dark:text-white">
            {backtestResult.strategy_name || '组合回测策略'}
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
            股票组合: {backtestResult.symbols?.length || 0} 只 |
            周期: {backtestResult.start_date} 至 {backtestResult.end_date}
          </p>
        </div>

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

  const renderComparisonView = () => {
    const selectedResults = getSelectedResults()
    if (selectedResults.length < 2) return null

    return (
      <div className="mt-6 p-6 bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-900/20 dark:to-orange-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
        <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
          多策略对比分析 ({selectedResults.length}个策略)
        </h2>

        {/* 对比图表 - 使用多条曲线 */}
        <EquityCurveChart
          strategies={selectedResults.map((result, idx) => ({
            name: result.strategy_name || `策略${idx + 1}`,
            data: result.equity_curve,
            color: ['#3b82f6', '#8b5cf6', '#10b981'][idx] || '#6b7280'
          }))}
          benchmarkData={selectedResults[0].benchmark_curve}
          title="策略对比 vs 沪深300"
        />

        {/* 对比表格 */}
        <div className="mt-6 overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-700">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  策略
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  总收益率
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  夏普比率
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  最大回撤
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                  胜率
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
              {selectedResults.map((result, idx) => (
                <tr key={idx}>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white">
                    {result.strategy_name}
                  </td>
                  <td className={`px-4 py-3 text-sm text-right font-semibold ${
                    (result.metrics.total_return || 0) > 0
                      ? 'text-green-600 dark:text-green-400'
                      : 'text-red-600 dark:text-red-400'
                  }`}>
                    {((result.metrics.total_return || 0) * 100).toFixed(2)}%
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-gray-900 dark:text-gray-100">
                    {(result.metrics.sharpe_ratio || 0).toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-red-600 dark:text-red-400 font-semibold">
                    {((result.metrics.max_drawdown || 0) * 100).toFixed(2)}%
                  </td>
                  <td className="px-4 py-3 text-sm text-right text-gray-900 dark:text-gray-100">
                    {((result.metrics.win_rate || 0) * 100).toFixed(2)}%
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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
            支持单股K线回测和多股组合回测，动态参数配置，多策略对比分析
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 左侧: 配置面板 */}
          <div className="lg:col-span-1 space-y-6">
            <BacktestPanel onBacktestComplete={handleBacktestComplete} />

            {/* 历史记录面板 */}
            {backtestHistory.length > 0 && (
              <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-sm font-bold text-gray-900 dark:text-white">
                    回测历史
                  </h3>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    选择2-3个对比
                  </span>
                </div>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {backtestHistory.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => toggleHistorySelection(item.id)}
                      className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                        selectedHistoryIds.has(item.id)
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-gray-200 dark:border-gray-700 hover:border-gray-300'
                      }`}
                    >
                      <div className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={selectedHistoryIds.has(item.id)}
                          onChange={() => {}}
                          className="text-blue-600"
                        />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                            {item.strategy_name}
                          </p>
                          <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                            {item.symbol} | {new Date(item.timestamp).toLocaleTimeString('zh-CN', {
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
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
            ) : (
              <>
                {backtestResult.mode === 'single' ? renderSingleStockResults() : renderMultiStockResults()}
                {renderComparisonView()}
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
