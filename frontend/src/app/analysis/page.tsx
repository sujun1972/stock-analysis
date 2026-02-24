'use client'

import { useEffect, useState, Suspense, useMemo } from 'react'
import dynamic from 'next/dynamic'
import { useSearchParams } from 'next/navigation'
import { apiClient } from '@/lib/api-client'
import type { StockInfo, Concept } from '@/types'

// 动态导入StockPriceCard组件（统一的图表组件）
const StockPriceCard = dynamic(() => import('@/components/StockPriceCard'), {
  ssr: false,
  loading: () => <div className="flex items-center justify-center h-[600px] bg-gray-50 dark:bg-gray-900 rounded-lg">加载图表中...</div>
})
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { useSmartRefresh } from '@/hooks/useMarketStatus'

function AnalysisContent() {
  const searchParams = useSearchParams()
  const code = searchParams.get('code')

  // 原有状态
  const [stockInfo, setStockInfo] = useState<StockInfo | null>(null)

  // 概念相关状态
  const [stockConcepts, setStockConcepts] = useState<Concept[]>([])
  const [allConcepts, setAllConcepts] = useState<Concept[]>([])
  const [isEditingConcepts, setIsEditingConcepts] = useState(false)
  const [selectedConceptIds, setSelectedConceptIds] = useState<number[]>([])

  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (code) {
      loadStockInfo()
      loadConceptsData()
    } else {
      setIsLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code])

  const loadConceptsData = async () => {
    if (!code) return

    try {
      // 加载股票的概念
      const concepts = await apiClient.getStockConcepts(code)
      setStockConcepts(concepts)
      setSelectedConceptIds(concepts.map(c => c.id))

      // 加载所有可用的概念
      const allConceptsResult = await apiClient.getConceptsList({ limit: 100 })
      setAllConcepts(allConceptsResult.items || [])
    } catch (err) {
      console.error('Failed to load concepts:', err)
    }
  }

  const handleSaveConcepts = async () => {
    if (!code) return

    try {
      await apiClient.updateStockConcepts(code, selectedConceptIds)
      // 重新加载概念数据
      await loadConceptsData()
      setIsEditingConcepts(false)
    } catch (err: any) {
      alert(`保存失败: ${err.message}`)
    }
  }

  const toggleConceptSelection = (conceptId: number) => {
    setSelectedConceptIds(prev => {
      if (prev.includes(conceptId)) {
        return prev.filter(id => id !== conceptId)
      } else {
        return [...prev, conceptId]
      }
    })
  }

  const loadStockInfo = async () => {
    if (!code) return

    try {
      setIsLoading(true)
      setError(null)

      // 获取股票基本信息
      const stockInfoData = await apiClient.getStock(code)
      setStockInfo(stockInfoData)
    } catch (err: any) {
      setError(err.message || '加载股票数据失败')
      console.error('Failed to load stock data:', err)
    } finally {
      setIsLoading(false)
    }
  }

  // 使用 useMemo 稳定 codes 数组引用，避免重复触发刷新
  const codes = useMemo(() => code ? [code] : undefined, [code])

  // 使用智能刷新Hook - 刷新股票实时数据（自动后台刷新）
  useSmartRefresh(
    async () => {
      if (!code) return

      // 先同步最新的实时数据（从数据源获取）
      await apiClient.syncRealtimeQuotes({
        codes: [code],
        batch_size: 1
      })

      // 然后重新获取股票信息（从数据库读取已更新的数据）
      const stockInfoData = await apiClient.getStock(code)
      setStockInfo(stockInfoData)
    },
    codes,  // 使用稳定的引用
    true    // 启用自动刷新
  )


  // 如果没有code参数
  if (!code) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          股票分析
        </h1>
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
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
          </CardContent>
        </Card>
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
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-300 border-t-blue-600"></div>
              <p className="mt-4 text-gray-600 dark:text-gray-400">加载中...</p>
            </div>
          </CardContent>
        </Card>
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
        <Card>
          <CardContent className="p-0">
            <Alert className="bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 rounded-none">
              <AlertDescription className="text-red-800 dark:text-red-200">
                {error}
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
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
      <Card>
        <CardHeader>
          <CardTitle>基本信息</CardTitle>
        </CardHeader>
        <CardContent>
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

        {/* 概念标签 */}
        <div className="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-900 dark:text-white">概念标签</h3>
            {!isEditingConcepts ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsEditingConcepts(true)}
              >
                编辑
              </Button>
            ) : (
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setIsEditingConcepts(false)
                    setSelectedConceptIds(stockConcepts.map(c => c.id))
                  }}
                >
                  取消
                </Button>
                <Button
                  size="sm"
                  onClick={handleSaveConcepts}
                >
                  保存
                </Button>
              </div>
            )}
          </div>

          {!isEditingConcepts ? (
            <div className="flex flex-wrap gap-2">
              {stockConcepts.length > 0 ? (
                stockConcepts.map((concept) => (
                  <span
                    key={concept.id}
                    className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200"
                  >
                    {concept.name}
                  </span>
                ))
              ) : (
                <p className="text-sm text-gray-500 dark:text-gray-400">暂无概念标签</p>
              )}
            </div>
          ) : (
            <div className="max-h-60 overflow-y-auto border border-gray-200 dark:border-gray-700 rounded-lg p-3">
              <div className="flex flex-wrap gap-2">
                {allConcepts.map((concept) => (
                  <button
                    key={concept.id}
                    onClick={() => toggleConceptSelection(concept.id)}
                    className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                      selectedConceptIds.includes(concept.id)
                        ? 'bg-blue-600 text-white dark:bg-blue-500'
                        : 'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-700'
                    }`}
                  >
                    {concept.name} ({concept.stock_count})
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </CardContent>
      </Card>

      {/* 图表区域 - 使用统一的 StockPriceCard 组件 */}
      <StockPriceCard
        stockCode={code}
        stockName={stockInfo?.name}
        defaultChartType="daily"
        showHeader={true}
      />
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
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-300 border-t-blue-600"></div>
              <p className="mt-4 text-gray-600 dark:text-gray-400">加载中...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    }>
      <AnalysisContent />
    </Suspense>
  )
}
