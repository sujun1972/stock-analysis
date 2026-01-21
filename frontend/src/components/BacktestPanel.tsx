'use client'

import { useState, useEffect } from 'react'
import { apiClient } from '@/lib/api-client'
import StrategyParamsPanel from './StrategyParamsPanel'

interface BacktestPanelProps {
  onBacktestComplete?: (result: any) => void
}

interface Strategy {
  id: string
  name: string
  description: string
  version: string
  parameter_count: number
}

export default function BacktestPanel({ onBacktestComplete }: BacktestPanelProps) {
  // 表单状态
  const [symbols, setSymbols] = useState<string>('600000')
  const [startDate, setStartDate] = useState<string>('2024-01-01')
  const [endDate, setEndDate] = useState<string>('2024-12-31')
  const [initialCash, setInitialCash] = useState<number>(1000000)

  // 策略相关状态
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [selectedStrategyId, setSelectedStrategyId] = useState<string>('complex_indicator')
  const [strategyParams, setStrategyParams] = useState<Record<string, any>>({})
  const [showParams, setShowParams] = useState<boolean>(false)

  // 加载状态
  const [isLoading, setIsLoading] = useState(false)
  const [progress, setProgress] = useState<string>('')
  const [error, setError] = useState<string>('')

  // 加载策略列表
  useEffect(() => {
    const fetchStrategies = async () => {
      try {
        const response = await apiClient.getStrategyList()
        if (response.data) {
          setStrategies(response.data)
        }
      } catch (error) {
        console.error('获取策略列表失败:', error)
      }
    }

    fetchStrategies()
  }, [])

  // 自动添加交易所后缀
  const normalizeSymbol = (code: string): string => {
    const cleanCode = code.trim()

    // 如果已经有后缀,直接返回
    if (cleanCode.includes('.')) {
      return cleanCode
    }

    // 根据股票代码规则自动添加后缀
    if (cleanCode.startsWith('6') || cleanCode.startsWith('688')) {
      return `${cleanCode}.SH`
    } else if (cleanCode.startsWith('0') || cleanCode.startsWith('3')) {
      return `${cleanCode}.SZ`
    } else if (cleanCode.startsWith('8') || cleanCode.startsWith('4')) {
      return `${cleanCode}.BJ`
    }

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
        strategy_id: selectedStrategyId,
        strategy_params: Object.keys(strategyParams).length > 0 ? strategyParams : undefined
      })

      setProgress('正在计算绩效指标...')

      if (response.data) {
        setProgress('回测完成！')
        // 将结果传递给父组件
        if (onBacktestComplete) {
          onBacktestComplete(response.data)
        }
      } else {
        throw new Error('回测失败')
      }
    } catch (err: any) {
      console.error('回测错误:', err)
      setError(err.response?.data?.detail || err.message || '回测失败，请检查参数')
    } finally {
      setIsLoading(false)
      setTimeout(() => setProgress(''), 3000)
    }
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <h2 className="text-xl font-bold text-gray-900 dark:text-white mb-4">
        回测配置
      </h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* 基础配置 */}
        <div className="space-y-4 pb-4 border-b border-gray-200 dark:border-gray-700">
          {/* 股票代码 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              股票代码
            </label>
            <input
              type="text"
              value={symbols}
              onChange={(e) => setSymbols(e.target.value)}
              placeholder="600000 或 000031,600519"
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
              required
            />
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              支持单股或多股（逗号分隔），无需添加交易所后缀
            </p>
          </div>

          {/* 日期范围 */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                开始日期
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                结束日期
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                required
              />
            </div>
          </div>

          {/* 初始资金 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              初始资金: ¥{initialCash.toLocaleString()}
            </label>
            <input
              type="range"
              min="100000"
              max="10000000"
              step="100000"
              value={initialCash}
              onChange={(e) => setInitialCash(Number(e.target.value))}
              className="w-full h-2 bg-gray-200 dark:bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
            />
            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
              <span>10万</span>
              <span>1000万</span>
            </div>
          </div>
        </div>

        {/* 策略选择 */}
        <div className="space-y-3">
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
            回测策略
          </label>

          <div className="space-y-2">
            {strategies.map(strategy => (
              <div
                key={strategy.id}
                className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                  selectedStrategyId === strategy.id
                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-gray-300 dark:border-gray-600 hover:border-gray-400 dark:hover:border-gray-500'
                }`}
                onClick={() => setSelectedStrategyId(strategy.id)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <input
                        type="radio"
                        checked={selectedStrategyId === strategy.id}
                        onChange={() => setSelectedStrategyId(strategy.id)}
                        className="text-blue-600"
                      />
                      <span className="font-medium text-gray-900 dark:text-white">
                        {strategy.name}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        v{strategy.version}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 ml-6">
                      {strategy.description}
                    </p>
                  </div>
                  {strategy.parameter_count > 0 && (
                    <span className="ml-2 px-2 py-1 bg-gray-100 dark:bg-gray-700 text-xs text-gray-600 dark:text-gray-400 rounded">
                      {strategy.parameter_count} 个参数
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* 参数配置按钮 */}
          {(strategies.find(s => s.id === selectedStrategyId)?.parameter_count || 0) > 0 && (
            <button
              type="button"
              onClick={() => setShowParams(!showParams)}
              className="w-full px-4 py-2 text-sm text-blue-600 dark:text-blue-400 border border-blue-600 dark:border-blue-400 rounded-lg hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
            >
              {showParams ? '收起' : '展开'}策略参数配置
            </button>
          )}
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          </div>
        )}

        {/* 运行按钮 */}
        <button
          type="submit"
          disabled={isLoading}
          className={`w-full py-3 rounded-lg font-medium transition-colors ${
            isLoading
              ? 'bg-gray-400 cursor-not-allowed'
              : 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white'
          }`}
        >
          {isLoading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {progress || '运行中...'}
            </span>
          ) : (
            '运行回测'
          )}
        </button>
      </form>

      {/* 参数配置面板（弹出式） */}
      {showParams && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <StrategyParamsPanel
            strategyId={selectedStrategyId}
            onParamsChange={setStrategyParams}
          />
        </div>
      )}
    </div>
  )
}
