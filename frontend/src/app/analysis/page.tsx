'use client'

import { useEffect, useState, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { apiClient } from '@/lib/api-client'
import type { StockInfo, FeatureData } from '@/types'
import EChartsStockChart from '@/components/EChartsStockChart'

function AnalysisContent() {
  const searchParams = useSearchParams()
  const code = searchParams.get('code')

  const [stockInfo, setStockInfo] = useState<StockInfo | null>(null)
  const [features, setFeatures] = useState<FeatureData[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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

      // 获取股票基本信息
      const stockInfoData = await apiClient.getStock(code)
      setStockInfo(stockInfoData)

      // 获取技术指标数据（包含OHLCV和技术指标，支持懒加载）
      const response = await apiClient.getFeatures(code, { limit: 500 })
      setFeatures(response.data || [])
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
          K线图表（支持懒加载）
        </h2>
        {features.length > 0 ? (
          <EChartsStockChart data={features} stockCode={code} />
        ) : (
          <div className="text-center py-12">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            <p className="mt-4 text-gray-600 dark:text-gray-400">暂无数据</p>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-500">
              请先在数据同步页面同步该股票的历史数据
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
