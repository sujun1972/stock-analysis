'use client'

import { useEffect, useState, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { apiClient } from '@/lib/api-client'
import type { StockInfo, StockDaily, FeatureData } from '@/types'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { format } from 'date-fns'

function AnalysisContent() {
  const searchParams = useSearchParams()
  const code = searchParams.get('code')

  const [stockInfo, setStockInfo] = useState<StockInfo | null>(null)
  const [dailyData, setDailyData] = useState<StockDaily[]>([])
  const [features, setFeatures] = useState<FeatureData[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dataError, setDataError] = useState<string | null>(null)

  useEffect(() => {
    if (code) {
      loadStockData()
    } else {
      setIsLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code])

  const loadStockData = async () => {
    if (!code) return

    try {
      setIsLoading(true)
      setError(null)
      setDataError(null)

      // 获取股票基本信息
      const stockInfoData = await apiClient.getStock(code)
      setStockInfo(stockInfoData)

      // 计算180天前的日期
      const endDate = new Date()
      const startDate = new Date()
      startDate.setDate(startDate.getDate() - 180)

      const startDateStr = format(startDate, 'yyyy-MM-dd')
      const endDateStr = format(endDate, 'yyyy-MM-dd')

      // 获取日线数据
      try {
        const dailyDataResponse = await apiClient.getDailyData(code, {
          start_date: startDateStr,
          end_date: endDateStr,
        })
        setDailyData(dailyDataResponse || [])
      } catch (err: any) {
        console.error('Failed to load daily data:', err)
        setDataError('日线数据加载失败，可能尚未同步数据')
      }

      // 获取技术指标数据
      try {
        const featuresData = await apiClient.getFeatures(code)
        setFeatures(featuresData || [])
      } catch (err: any) {
        console.error('Failed to load features:', err)
        // 技术指标失败不影响主流程
      }
    } catch (err: any) {
      setError(err.message || '加载股票数据失败')
      console.error('Failed to load stock data:', err)
    } finally {
      setIsLoading(false)
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
  if (error) {
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

      {/* 数据错误提示 */}
      {dataError && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mr-2" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            <span className="text-yellow-800 dark:text-yellow-200">{dataError}</span>
          </div>
        </div>
      )}

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

      {/* K线图表 */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          价格走势图（最近180天）
        </h2>
        {dailyData.length > 0 ? (
          <div className="w-full h-96">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={dailyData}
                margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
              >
                <CartesianGrid strokeDasharray="3 3" className="stroke-gray-300 dark:stroke-gray-700" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(value) => {
                    try {
                      return format(new Date(value), 'MM/dd')
                    } catch {
                      return value
                    }
                  }}
                  className="text-gray-600 dark:text-gray-400"
                />
                <YAxis
                  domain={['auto', 'auto']}
                  className="text-gray-600 dark:text-gray-400"
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    border: '1px solid #ccc',
                    borderRadius: '4px',
                  }}
                  labelFormatter={(value) => {
                    try {
                      return format(new Date(value), 'yyyy-MM-dd')
                    } catch {
                      return value
                    }
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="close"
                  name="收盘价"
                  stroke="#3b82f6"
                  strokeWidth={2}
                  dot={false}
                />
                <Line
                  type="monotone"
                  dataKey="high"
                  name="最高价"
                  stroke="#ef4444"
                  strokeWidth={1}
                  dot={false}
                  strokeDasharray="5 5"
                />
                <Line
                  type="monotone"
                  dataKey="low"
                  name="最低价"
                  stroke="#22c55e"
                  strokeWidth={1}
                  dot={false}
                  strokeDasharray="5 5"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
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
        )}
      </div>

      {/* 技术指标展示 */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          技术指标
        </h2>
        {features.length > 0 ? (
          <div className="space-y-4">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      日期
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      指标类型
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      指标值
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                  {features.slice(0, 10).map((feature, idx) => (
                    <tr key={idx} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        {feature.date}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                        {feature.feature_type}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-900 dark:text-white">
                        <div className="max-w-md truncate">
                          {JSON.stringify(feature.feature_data)}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {features.length > 10 && (
              <p className="text-sm text-gray-500 dark:text-gray-400 text-center">
                显示最近10条记录，共{features.length}条
              </p>
            )}
          </div>
        ) : (
          <div className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
            </svg>
            <p className="mt-4 text-gray-600 dark:text-gray-400">暂无技术指标数据</p>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-500">
              可以在特征计算页面计算该股票的技术指标
            </p>
          </div>
        )}
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
