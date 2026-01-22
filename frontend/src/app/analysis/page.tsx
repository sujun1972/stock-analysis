'use client'

import { useEffect, useState, Suspense, useMemo } from 'react'
import { useSearchParams } from 'next/navigation'
import { apiClient } from '@/lib/api-client'
import type { StockInfo, FeatureData, MinuteData } from '@/types'
import { aggregateMinuteData, type MinutePeriod } from '@/lib/minute-data-aggregator'
import EChartsStockChart from '@/components/EChartsStockChart'
import MinuteChart from '@/components/MinuteChart'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Calendar } from '@/components/ui/calendar'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { CalendarIcon } from 'lucide-react'
import { format } from 'date-fns'
import { zhCN } from 'date-fns/locale'
import { cn } from '@/lib/utils'
import { useSmartRefresh } from '@/hooks/useMarketStatus'

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
  if (error && !rawMinuteData.length && chartType === 'daily') {
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
      </CardContent>
      </Card>

      {/* 图表区域 */}
      <Card>
        <CardHeader>
          <CardTitle>股价走势</CardTitle>
        </CardHeader>
        <CardContent>
          {/* Tab 导航栏 */}
          <div className="mb-4">
            <div className="flex items-center justify-between">
              {/* Tab 标签 */}
              <Tabs value={chartType} onValueChange={(value) => setChartType(value as ChartType)}>
                <TabsList>
                  <TabsTrigger value="daily">日线图</TabsTrigger>
                  <TabsTrigger value="minute">分时图</TabsTrigger>
                </TabsList>
              </Tabs>

              {/* Tab 控制项 */}
              <div className="flex items-center gap-3">
                {/* 日线图控制项：指标设置（预留） */}
                {chartType === 'daily' && (
                  <div className="flex items-center gap-2">
                    {/* TODO: 添加指标设置 */}
                  </div>
                )}

                {/* 分时图控制项：周期和日期选择 */}
                {chartType === 'minute' && (
                  <div className="flex items-center gap-2">
                    <Select value={minutePeriod} onValueChange={(value) => setMinutePeriod(value as MinutePeriod)}>
                      <SelectTrigger className="w-[100px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="1">1分钟</SelectItem>
                        <SelectItem value="5">5分钟</SelectItem>
                        <SelectItem value="15">15分钟</SelectItem>
                        <SelectItem value="30">30分钟</SelectItem>
                        <SelectItem value="60">60分钟</SelectItem>
                      </SelectContent>
                    </Select>

                    <Popover>
                      <PopoverTrigger asChild>
                        <Button
                          variant="outline"
                          className={cn(
                            "w-[200px] justify-start text-left font-normal",
                            !minuteDate && "text-muted-foreground"
                          )}
                        >
                          <CalendarIcon className="mr-2 h-4 w-4" />
                          {minuteDate ? format(new Date(minuteDate), 'yyyy年MM月dd日', { locale: zhCN }) : "选择日期"}
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-auto p-0">
                        <Calendar
                          mode="single"
                          selected={minuteDate ? new Date(minuteDate) : undefined}
                          onSelect={(date) => {
                            if (date) {
                              setMinuteDate(format(date, 'yyyy-MM-dd'))
                            }
                          }}
                          disabled={(date) =>
                            date > new Date() || date < new Date("1990-01-01")
                          }
                          initialFocus
                        />
                      </PopoverContent>
                    </Popover>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* 错误提示（仅在分时图模式下显示） */}
          {error && chartType === 'minute' && (
            <Alert className="mb-4 bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800">
              <AlertDescription className="flex items-start">
                <svg className="w-5 h-5 text-yellow-600 dark:text-yellow-400 mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <div className="flex-1">
                  <p className="text-yellow-800 dark:text-yellow-200 font-medium">{error}</p>
                  {error.includes('非交易日') && (
                    <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-2">
                      提示：请选择工作日日期，或查看日线图了解历史走势
                    </p>
                  )}
                </div>
              </AlertDescription>
            </Alert>
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
        </CardContent>
      </Card>
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
