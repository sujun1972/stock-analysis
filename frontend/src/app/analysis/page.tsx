'use client'

import { useEffect, useState, Suspense, useMemo } from 'react'
import { useSearchParams } from 'next/navigation'
import { apiClient } from '@/lib/api-client'
import type { StockInfo, FeatureData, MinuteData } from '@/types'
import { aggregateMinuteData, type MinutePeriod } from '@/lib/minute-data-aggregator'
import EChartsStockChart from '@/components/EChartsStockChart'
import MinuteChart from '@/components/MinuteChart'

type ChartType = 'daily' | 'minute'

function AnalysisContent() {
  const searchParams = useSearchParams()
  const code = searchParams.get('code')

  // 原有状态
  const [stockInfo, setStockInfo] = useState<StockInfo | null>(null)
  const [features, setFeatures] = useState<FeatureData[]>([])

  // 新增状态
  const [chartType, setChartType] = useState<ChartType>('daily')
  const [minutePeriod, setMinutePeriod] = useState<MinutePeriod>('5')
  const [rawMinuteData, setRawMinuteData] = useState<MinuteData[]>([]) // 存储1分钟原始数据
  const [minuteDate, setMinuteDate] = useState<string>(
    new Date().toISOString().split('T')[0]
  )

  const [isLoading, setIsLoading] = useState(true)
  const [isLoadingMinute, setIsLoadingMinute] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fromCache, setFromCache] = useState<boolean>(false)

  // 根据选择的周期聚合数据
  const aggregatedMinuteData = useMemo(() => {
    if (!rawMinuteData || rawMinuteData.length === 0) return []
    return aggregateMinuteData(rawMinuteData, minutePeriod)
  }, [rawMinuteData, minutePeriod])

  useEffect(() => {
    if (code) {
      loadStockData()
    } else {
      setIsLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code])

  // 当切换到分时图或更换日期时，加载1分钟数据
  // 注意：切换周期时不需要重新加载，只需重新聚合
  useEffect(() => {
    if (code && chartType === 'minute') {
      loadMinuteData()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code, chartType, minuteDate])

  const loadStockData = async () => {
    if (!code) return

    try {
      setIsLoading(true)
      setError(null)

      // 获取股票基本信息
      const stockInfoData = await apiClient.getStock(code)
      setStockInfo(stockInfoData)

      // 获取日线数据
      const response = await apiClient.getFeatures(code, { limit: 500 })
      setFeatures(response.data || [])
    } catch (err: any) {
      setError(err.message || '加载股票数据失败')
      console.error('Failed to load stock data:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const loadMinuteData = async () => {
    if (!code) return

    try {
      setIsLoadingMinute(true)
      setError(null)

      // 只请求1分钟数据
      const response = await apiClient.getMinuteData(
        code,
        minuteDate
      )

      if (response.data) {
        // 保存原始的1分钟数据
        setRawMinuteData(response.data.records)
        setFromCache(response.data.from_cache)

        // 如果是从缓存加载，显示提示
        if (response.data.from_cache) {
          console.log(`✓ 从缓存加载1分钟数据 (完整度: ${response.data.completeness}%)`)
        } else {
          console.log(`✓ 从数据源获取1分钟数据 (${response.data.record_count}条记录)`)
        }
      }
    } catch (err: any) {
      const statusCode = err.response?.status
      const errorDetail = err.response?.data?.detail || err.message

      let errorMsg = '加载分时数据失败'

      if (statusCode === 404) {
        // 404表示无数据
        const dateObj = new Date(minuteDate)
        const dayOfWeek = dateObj.getDay()

        // 判断是否为周末
        if (dayOfWeek === 0 || dayOfWeek === 6) {
          errorMsg = `${minuteDate} 是周末，非交易日`
        } else {
          errorMsg = `${minuteDate} 暂无分时数据（可能是非交易日或数据源未提供）`
        }
      } else {
        errorMsg = errorDetail || '加载分时数据失败'
      }

      setError(errorMsg)
      setRawMinuteData([]) // 清空数据
      console.warn('无法加载分时数据:', errorMsg, err)
    } finally {
      setIsLoadingMinute(false)
    }
  }

  // 如果没有code参数
  if (!code) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          股票分析
        </h1>
        <div className="card">
          <div className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <p className="mt-4 text-gray-600 dark:text-gray-400">请从股票列表选择股票</p>
            <a
              href="/stocks"
              className="mt-4 inline-block text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
            >
              前往股票列表
            </a>
          </div>
        </div>
      </div>
    )
  }

  // 加载中状态
  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          股票分析
        </h1>
        <div className="card">
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-300 border-t-blue-600"></div>
            <p className="mt-4 text-gray-600 dark:text-gray-400">加载中...</p>
          </div>
        </div>
      </div>
    )
  }

  // 错误状态
  if (error && !rawMinuteData.length && chartType === 'daily') {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          股票分析
        </h1>
        <div className="card">
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <div className="flex items-center">
              <svg className="w-5 h-5 text-red-600 dark:text-red-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
              <span className="text-red-800 dark:text-red-200">{error}</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          {stockInfo?.name}({stockInfo?.code})
        </h1>
      </div>

      {/* 股票基本信息卡片 */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          基本信息
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">股票代码</p>
            <p className="text-lg font-medium text-gray-900 dark:text-white">{stockInfo?.code}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">股票名称</p>
            <p className="text-lg font-medium text-gray-900 dark:text-white">{stockInfo?.name}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">市场</p>
            <p className="text-lg font-medium text-gray-900 dark:text-white">{stockInfo?.market || '-'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">上市日期</p>
            <p className="text-lg font-medium text-gray-900 dark:text-white">{stockInfo?.list_date || '-'}</p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">最新价</p>
            <p className={`text-lg font-medium ${
              stockInfo?.pct_change !== null && stockInfo?.pct_change !== undefined
                ? stockInfo.pct_change > 0
                  ? 'text-red-600 dark:text-red-400'
                  : stockInfo.pct_change < 0
                    ? 'text-green-600 dark:text-green-400'
                    : 'text-gray-900 dark:text-white'
                : 'text-gray-900 dark:text-white'
            }`}>
              {stockInfo?.latest_price ? stockInfo.latest_price.toFixed(2) : '-'}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">涨跌幅</p>
            <p className={`text-lg font-medium ${
              stockInfo?.pct_change !== null && stockInfo?.pct_change !== undefined
                ? stockInfo.pct_change > 0
                  ? 'text-red-600 dark:text-red-400'
                  : stockInfo.pct_change < 0
                    ? 'text-green-600 dark:text-green-400'
                    : 'text-gray-900 dark:text-white'
                : 'text-gray-900 dark:text-white'
            }`}>
              {stockInfo?.pct_change !== null && stockInfo?.pct_change !== undefined
                ? `${stockInfo.pct_change > 0 ? '+' : ''}${stockInfo.pct_change.toFixed(2)}%`
                : '-'
              }
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">成交量</p>
            <p className="text-lg font-medium text-gray-900 dark:text-white">
              {stockInfo?.volume ? (stockInfo.volume / 10000).toFixed(2) + '万' : '-'}
            </p>
          </div>
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">换手率</p>
            <p className="text-lg font-medium text-gray-900 dark:text-white">
              {stockInfo?.turnover !== null && stockInfo?.turnover !== undefined
                ? stockInfo.turnover.toFixed(2) + '%'
                : '-'
              }
            </p>
          </div>
        </div>
      </div>

      {/* 图表区域 */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          股价走势
        </h2>

        {/* Tab 导航栏 */}
        <div className="border-b border-gray-200 dark:border-gray-700 mb-4">
          <div className="flex items-center justify-between">
            {/* Tab 标签 */}
            <div className="flex -mb-px">
              <button
                onClick={() => setChartType('daily')}
                className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  chartType === 'daily'
                    ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                日线图
              </button>
              <button
                onClick={() => setChartType('minute')}
                className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  chartType === 'minute'
                    ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
                }`}
              >
                分时图
              </button>
            </div>

            {/* Tab 控制项 */}
            <div className="flex items-center gap-3 pb-3">
              {/* 日线图控制项：指标设置（预留） */}
              {chartType === 'daily' && (
                <div className="flex items-center gap-2">
                  {/* TODO: 添加指标设置 */}
                  {/*
                  <button className="btn-secondary text-sm">
                    <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                    </svg>
                    指标设置
                  </button>
                  */}
                </div>
              )}

              {/* 分时图控制项：周期和日期选择 */}
              {chartType === 'minute' && (
                <div className="flex items-center gap-2">
                  <select
                    value={minutePeriod}
                    onChange={(e) => setMinutePeriod(e.target.value as MinutePeriod)}
                    className="input-field py-2 px-3 text-sm min-w-[100px]"
                  >
                    <option value="1">1分钟</option>
                    <option value="5">5分钟</option>
                    <option value="15">15分钟</option>
                    <option value="30">30分钟</option>
                    <option value="60">60分钟</option>
                  </select>

                  <input
                    type="date"
                    value={minuteDate}
                    onChange={(e) => setMinuteDate(e.target.value)}
                    max={new Date().toISOString().split('T')[0]}
                    className="input-field py-2 px-3 text-sm min-w-[140px]"
                  />
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 错误提示（仅在分时图模式下显示） */}
        {error && chartType === 'minute' && (
          <div className="mb-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
            <div className="flex items-start">
              <svg className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
              <div className="flex-1">
                <p className="text-yellow-800 dark:text-yellow-200 font-medium">{error}</p>
                {error.includes('非交易日') && (
                  <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-2">
                    💡 提示：请选择工作日日期，或查看日线图了解历史走势
                  </p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* 图表容器 */}
        <div className="relative">
          {isLoadingMinute && chartType === 'minute' && (
            <div className="absolute inset-0 bg-white/50 dark:bg-gray-900/50 flex items-center justify-center z-10">
              <div className="flex items-center gap-2">
                <div className="inline-block animate-spin rounded-full h-6 w-6 border-2 border-gray-300 border-t-blue-600"></div>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  加载分时数据...
                </span>
              </div>
            </div>
          )}

          {chartType === 'daily' ? (
            features.length > 0 ? (
              <EChartsStockChart data={features} stockCode={code} />
            ) : (
              <div className="text-center py-12">
                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <p className="mt-4 text-gray-600 dark:text-gray-400">暂无日线数据</p>
                <p className="mt-2 text-sm text-gray-500 dark:text-gray-500">
                  请先在数据同步页面同步该股票的历史数据
                </p>
              </div>
            )
          ) : (
            <MinuteChart
              data={aggregatedMinuteData}
              period={minutePeriod}
              stockCode={code || ''}
              stockName={stockInfo?.name || ''}
            />
          )}
        </div>
      </div>
    </div>
  )
}

export default function AnalysisPage() {
  return (
    <Suspense fallback={
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          股票分析
        </h1>
        <div className="card">
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-300 border-t-blue-600"></div>
            <p className="mt-4 text-gray-600 dark:text-gray-400">加载中...</p>
          </div>
        </div>
      </div>
    }>
      <AnalysisContent />
    </Suspense>
  )
}
