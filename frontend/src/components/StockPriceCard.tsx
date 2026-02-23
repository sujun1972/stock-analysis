'use client'

import { useState, useEffect } from 'react'
import dynamic from 'next/dynamic'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Settings2, TrendingUp, Clock } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { aggregateMinuteData, type MinutePeriod } from '@/lib/minute-data-aggregator'
import type { FeatureData, MinuteData } from '@/types/stock'

// 动态导入图表组件（避免 SSR 问题）
const EChartsStockChart = dynamic(() => import('@/components/EChartsStockChart'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-[600px]">
      <div className="text-gray-500">加载图表中...</div>
    </div>
  ),
})

const MinuteChart = dynamic(() => import('@/components/MinuteChart'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-[400px]">
      <div className="text-gray-500">加载分时图中...</div>
    </div>
  ),
})

// 技术指标选项
export const INDICATOR_OPTIONS = [
  { value: 'volume', label: '成交量' },
  { value: 'macd', label: 'MACD' },
  { value: 'kdj', label: 'KDJ' },
  { value: 'rsi', label: 'RSI' },
  { value: 'boll', label: 'BOLL' },
] as const

// 分时图周期选项
export const MINUTE_PERIOD_OPTIONS = [
  { value: '1', label: '1分钟' },
  { value: '5', label: '5分钟' },
  { value: '15', label: '15分钟' },
  { value: '30', label: '30分钟' },
  { value: '60', label: '60分钟' },
] as const

interface StockPriceCardProps {
  stockCode: string
  stockName?: string
  defaultChartType?: 'daily' | 'minute'
  showHeader?: boolean
  className?: string
  onIndicatorsChange?: (indicators: string[]) => void
}

/**
 * 股价走势卡片组件
 *
 * 功能：
 * - 切换日线图/分时图
 * - 选择显示的技术指标
 * - 分时图支持多周期（1/5/15/30/60分钟）
 * - 自动加载和缓存数据
 *
 * @example
 * ```tsx
 * <StockPriceCard
 *   stockCode="000001"
 *   stockName="平安银行"
 *   defaultChartType="daily"
 *   showHeader={true}
 * />
 * ```
 */
export default function StockPriceCard({
  stockCode,
  stockName,
  defaultChartType = 'daily',
  showHeader = true,
  className = '',
  onIndicatorsChange,
}: StockPriceCardProps) {
  // 图表类型（日线/分时）
  const [chartType, setChartType] = useState<'daily' | 'minute'>(defaultChartType)

  // 分时图周期
  const [minutePeriod, setMinutePeriod] = useState<MinutePeriod>('5')

  // 数据状态
  const [features, setFeatures] = useState<FeatureData[]>([])
  const [minuteData, setMinuteData] = useState<MinuteData[]>([])
  const [aggregatedMinuteData, setAggregatedMinuteData] = useState<MinuteData[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 指标设置面板显示状态
  const [showIndicatorSettings, setShowIndicatorSettings] = useState(false)

  // 加载日线数据
  const loadDailyData = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const response = await apiClient.getFeatures(stockCode, { limit: 500 })
      setFeatures(response.data)
    } catch (err) {
      console.error('加载日线数据失败:', err)
      setError('加载数据失败，请稍后重试')
    } finally {
      setIsLoading(false)
    }
  }

  // 加载分时数据
  const loadMinuteData = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const today = new Date().toISOString().split('T')[0]
      const response = await apiClient.getMinuteData(stockCode, today)
      const records = response.data?.records || []
      setMinuteData(records)
      setAggregatedMinuteData(aggregateMinuteData(records, minutePeriod))
    } catch (err) {
      console.error('加载分时数据失败:', err)
      setError('加载分时数据失败，请稍后重试')
    } finally {
      setIsLoading(false)
    }
  }

  // 根据图表类型加载数据
  useEffect(() => {
    if (chartType === 'daily') {
      loadDailyData()
    } else {
      loadMinuteData()
    }
  }, [stockCode, chartType])

  // 分时图周期变化时重新聚合数据
  useEffect(() => {
    if (chartType === 'minute' && minuteData.length > 0) {
      setAggregatedMinuteData(aggregateMinuteData(minuteData, minutePeriod))
    }
  }, [minutePeriod, minuteData, chartType])

  // 渲染图表内容
  const renderChart = () => {
    if (error) {
      return (
        <div className="flex flex-col items-center justify-center h-[400px] text-gray-500">
          <TrendingUp className="w-12 h-12 mb-4 text-gray-400" />
          <p>{error}</p>
          <Button
            variant="outline"
            className="mt-4"
            onClick={() => (chartType === 'daily' ? loadDailyData() : loadMinuteData())}
          >
            重新加载
          </Button>
        </div>
      )
    }

    if (isLoading) {
      return (
        <div className="flex items-center justify-center h-[600px]">
          <div className="text-gray-500">加载中...</div>
        </div>
      )
    }

    if (chartType === 'daily') {
      if (features.length === 0) {
        return (
          <div className="flex flex-col items-center justify-center h-[400px] text-gray-500">
            <TrendingUp className="w-12 h-12 mb-4 text-gray-400" />
            <p>暂无数据</p>
          </div>
        )
      }
      return <EChartsStockChart data={features} stockCode={stockCode} />
    } else {
      if (aggregatedMinuteData.length === 0) {
        return (
          <div className="flex flex-col items-center justify-center h-[400px] text-gray-500">
            <Clock className="w-12 h-12 mb-4 text-gray-400" />
            <p>暂无分时数据</p>
          </div>
        )
      }
      return (
        <MinuteChart
          data={aggregatedMinuteData}
          period={minutePeriod}
          stockCode={stockCode}
          stockName={stockName || ''}
        />
      )
    }
  }

  return (
    <Card className={className}>
      {showHeader && (
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              <span>股价走势</span>
              {stockName && (
                <Badge variant="outline" className="ml-2">
                  {stockName} ({stockCode})
                </Badge>
              )}
            </CardTitle>
          </div>
        </CardHeader>
      )}

      <CardContent className="space-y-4">
        {/* 图表类型切换和控制栏 */}
        <div className="flex items-center justify-between gap-3">
          <Tabs value={chartType} onValueChange={(value) => setChartType(value as 'daily' | 'minute')}>
            <TabsList>
              <TabsTrigger value="daily" className="flex items-center gap-1.5">
                <TrendingUp className="w-4 h-4" />
                <span>日线图</span>
              </TabsTrigger>
              <TabsTrigger value="minute" className="flex items-center gap-1.5">
                <Clock className="w-4 h-4" />
                <span>分时图</span>
              </TabsTrigger>
            </TabsList>
          </Tabs>

          {/* 右侧：控制选项（分时图周期 或 日线图指标设置） */}
          {chartType === 'minute' ? (
            /* 分时图：显示周期选择器 */
            <Select
              value={minutePeriod}
              onValueChange={(value) => setMinutePeriod(value as MinutePeriod)}
            >
              <SelectTrigger className="w-[120px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {MINUTE_PERIOD_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            /* 日线图：显示指标设置按钮 */
            <Button
              variant="outline"
              size="sm"
              className="flex items-center gap-1.5"
              onClick={() => setShowIndicatorSettings(!showIndicatorSettings)}
            >
              <Settings2 className="w-4 h-4" />
              <span>指标设置</span>
            </Button>
          )}
        </div>

        {/* 指标设置提示（日线图） */}
        {chartType === 'daily' && showIndicatorSettings && (
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-md text-sm text-blue-800">
            <p className="flex items-center gap-2">
              <Settings2 className="w-4 h-4" />
              <span>
                技术指标可在图表右上角的设置按钮中配置。支持选择显示：成交量、MACD、KDJ、RSI、BOLL 等指标。
              </span>
            </p>
          </div>
        )}

        {/* 图表渲染区域 */}
        <div className="w-full">
          {renderChart()}
        </div>

        {/* 数据统计信息 */}
        <div className="flex items-center justify-between text-xs text-gray-500 pt-2 border-t">
          <div className="flex items-center gap-4">
            {chartType === 'daily' ? (
              <>
                <span>数据点数：{features.length}</span>
                {features.length > 0 && (
                  <span>
                    时间范围：{features[features.length - 1]?.date} ~ {features[0]?.date}
                  </span>
                )}
              </>
            ) : (
              <>
                <span>数据点数：{aggregatedMinuteData.length}</span>
                <span>周期：{minutePeriod}分钟</span>
                {aggregatedMinuteData.length > 0 && (
                  <span>
                    时间范围：
                    {aggregatedMinuteData[0]?.trade_time.split(' ')[1]?.substring(0, 5)} ~{' '}
                    {aggregatedMinuteData[aggregatedMinuteData.length - 1]?.trade_time
                      .split(' ')[1]
                      ?.substring(0, 5)}
                  </span>
                )}
              </>
            )}
          </div>
          <div className="text-gray-400">
            <span>股票代码：{stockCode}</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
