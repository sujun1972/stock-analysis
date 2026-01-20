'use client'

import { useState } from 'react'
import { apiClient } from '@/lib/api-client'

interface BacktestPanelProps {
  onBacktestComplete?: (result: any) => void
}

export default function BacktestPanel({ onBacktestComplete }: BacktestPanelProps) {
  // 表单状态
  const [symbols, setSymbols] = useState<string>('600000')
  const [startDate, setStartDate] = useState<string>('2023-01-01')
  const [endDate, setEndDate] = useState<string>('2023-12-31')
  const [initialCash, setInitialCash] = useState<number>(1000000)
  const [topN, setTopN] = useState<number>(10)
  const [holdingPeriod, setHoldingPeriod] = useState<number>(5)
  const [rebalanceFreq, setRebalanceFreq] = useState<string>('W')

  // 加载状态
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState<string>('')
  const [error, setError] = useState<string>('')

  // 自动添加交易所后缀
  const normalizeSymbol = (code: string): string => {
    const cleanCode = code.trim()

    // 如果已经有后缀,直接返回
    if (cleanCode.includes('.')) {
      return cleanCode
    }

    // 根据股票代码规则自动添加后缀
    // 6开头 = 上交所 (SH)
    // 0/3开头 = 深交所 (SZ)
    // 688开头 = 科创板 (SH)
    // 300开头 = 创业板 (SZ)
    // 8/4开头 = 北交所 (BJ)
    if (cleanCode.startsWith('6') || cleanCode.startsWith('688')) {
      return `${cleanCode}.SH`
    } else if (cleanCode.startsWith('0') || cleanCode.startsWith('3')) {
      return `${cleanCode}.SZ`
    } else if (cleanCode.startsWith('8') || cleanCode.startsWith('4')) {
      return `${cleanCode}.BJ`
    }

    // 默认返回原值
    return cleanCode
  }

  // 处理回测提交
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setProgress('正在初始化回测引擎...')
    setError('')

    try {
      // 解析股票代码(支持逗号分隔)并自动添加交易所后缀
      const symbolList = symbols
        .split(',')
        .map(s => s.trim())
        .filter(s => s.length > 0)
        .map(s => normalizeSymbol(s))

      setProgress('正在获取历史数据...')

      // 调用回测API
      const response = await apiClient.runBacktest({
        symbols: symbolList.length === 1 ? symbolList[0] : symbolList,
        start_date: startDate,
        end_date: endDate,
        initial_cash: initialCash,
        strategy_params: {
          top_n: topN,
          holding_period: holdingPeriod,
          rebalance_freq: rebalanceFreq
        }
      })

      setProgress('回测完成!')

      // 回调父组件
      if (onBacktestComplete) {
        onBacktestComplete(response.data)
      }

    } catch (err: any) {
      console.error('回测失败:', err)
      setError(err.response?.data?.detail || err.message || '回测失败')
    } finally {
      setIsLoading(false)
      setTimeout(() => setProgress(''), 3000)
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
        回测配置
      </h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* 股票代码 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            股票代码
          </label>
          <input
            type="text"
            value={symbols}
            onChange={(e) => setSymbols(e.target.value)}
            placeholder="600000 或 600000,000001,000002 (多股用逗号分隔)"
            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                     focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
            required
          />
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            自动识别交易所后缀 (6/688开头=SH, 0/3开头=SZ)
          </p>
        </div>

        {/* 日期范围 */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              开始日期
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                       focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              结束日期
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg
                       focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              required
            />
          </div>
        </div>

        {/* 初始资金 */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            初始资金 (元)
          </label>
          <input
            type="range"
            min="100000"
            max="10000000"
            step="100000"
            value={initialCash}
            onChange={(e) => setInitialCash(Number(e.target.value))}
            className="w-full"
          />
          <div className="flex justify-between text-sm text-gray-600 dark:text-gray-400">
            <span>10万</span>
            <span className="font-semibold text-blue-600 dark:text-blue-400">
              {(initialCash / 10000).toFixed(0)}万
            </span>
            <span>1000万</span>
          </div>
        </div>

        {/* 策略参数 */}
        <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
            策略参数 (多股模式)
          </h3>

          <div className="grid grid-cols-3 gap-4">
            {/* 选股数量 */}
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                选股数量
              </label>
              <input
                type="number"
                min="1"
                max="50"
                value={topN}
                onChange={(e) => setTopN(Number(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded
                         focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white text-sm"
              />
            </div>

            {/* 持仓期 */}
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                持仓期(天)
              </label>
              <input
                type="number"
                min="1"
                max="60"
                value={holdingPeriod}
                onChange={(e) => setHoldingPeriod(Number(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded
                         focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white text-sm"
              />
            </div>

            {/* 调仓频率 */}
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">
                调仓频率
              </label>
              <select
                value={rebalanceFreq}
                onChange={(e) => setRebalanceFreq(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded
                         focus:ring-2 focus:ring-blue-500 dark:bg-gray-700 dark:text-white text-sm"
              >
                <option value="D">每日</option>
                <option value="W">每周</option>
                <option value="M">每月</option>
              </select>
            </div>
          </div>
        </div>

        {/* 提交按钮 */}
        <button
          type="submit"
          disabled={isLoading}
          className={`w-full py-3 px-4 rounded-lg font-semibold text-white transition-colors
            ${isLoading
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-blue-600 hover:bg-blue-700 active:bg-blue-800'
            }`}
        >
          {isLoading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              运行中...
            </span>
          ) : (
            '运行回测'
          )}
        </button>

        {/* 进度提示 */}
        {progress && (
          <div className="p-3 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-700 rounded-lg">
            <p className="text-sm text-blue-700 dark:text-blue-300">{progress}</p>
          </div>
        )}

        {/* 错误提示 */}
        {error && (
          <div className="p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-lg">
            <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
          </div>
        )}
      </form>
    </div>
  )
}
