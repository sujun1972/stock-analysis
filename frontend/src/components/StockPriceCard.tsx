'use client'

import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'
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

// 回测相关类型定义
interface SignalPoint {
  date: string
  price: number
}

interface SignalPoints {
  buy: SignalPoint[]
  sell: SignalPoint[]
}

interface EquityCurvePoint {
  date: string
  total: number
  cash?: number
  holdings?: number
}

interface StockPriceCardProps {
  stockCode: string
  stockName?: string
  defaultChartType?: 'daily' | 'minute'
  showHeader?: boolean
  className?: string
  onIndicatorsChange?: (indicators: string[]) => void
  // 回测模式相关（可选）
  backtestMode?: boolean
  signalPoints?: SignalPoints
  equityCurve?: EquityCurvePoint[]
  // 外部提供的数据（可选，用于回测模式）
  externalData?: FeatureData[]
}

/**
 * 股价走势卡片组件
 *
 * 功能：
 * - 切换日线图/分时图
 * - 选择显示的技术指标
 * - 分时图支持多周期（1/5/15/30/60分钟）
 * - 自动加载和缓存数据
 * - 支持回测模式（显示买卖信号和权益曲线）
 *
 * @example
 * ```tsx
 * // 普通模式
 * <StockPriceCard
 *   stockCode="000001"
 *   stockName="平安银行"
 *   defaultChartType="daily"
 *   showHeader={true}
 * />
 *
 * // 回测模式
 * <StockPriceCard
 *   stockCode="000001"
 *   stockName="平安银行"
 *   backtestMode={true}
 *   signalPoints={{ buy: [...], sell: [...] }}
 *   equityCurve={[...]}
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
  backtestMode = false,
  signalPoints,
  equityCurve,
  externalData,
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

  // 指标设置对话框显示状态
  const [showIndicatorSettings, setShowIndicatorSettings] = useState(false)

  /**
   * 指标显示状态管理
   * - 从 localStorage 读取用户的指标偏好设置
   * - 默认开启成交量和MACD，其他指标默认关闭
   * - 支持5种技术指标：成交量、MACD、KDJ、RSI、BOLL
   */
  const [visibleIndicators, setVisibleIndicators] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('chart_visible_indicators')
      if (saved) {
        try {
          return JSON.parse(saved)
        } catch (e) {
          console.error('Failed to parse saved indicators:', e)
        }
      }
    }
    return {
      volume: true,   // 成交量 - 默认开启
      macd: true,     // MACD - 默认开启
      kdj: false,     // KDJ - 默认关闭
      rsi: false,     // RSI - 默认关闭
      boll: false     // BOLL - 默认关闭
    }
  })

  /**
   * 持久化指标设置
   * - 自动保存到 localStorage，实现跨会话记忆
   * - 通知父组件指标变化（如果提供了回调）
   */
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('chart_visible_indicators', JSON.stringify(visibleIndicators))
    }
    if (onIndicatorsChange) {
      onIndicatorsChange(Object.keys(visibleIndicators).filter(key => visibleIndicators[key as keyof typeof visibleIndicators]))
    }
  }, [visibleIndicators, onIndicatorsChange])

  /**
   * 检测数据中是否包含技术指标
   * - 用于控制设置对话框中指标选项的可用性
   * - 无数据的指标会被禁用并显示"(无数据)"提示
   */
  const hasMACD = features.some(d => d.MACD !== null && d.MACD !== undefined)
  const hasKDJ = features.some(d => d.KDJ_K !== null && d.KDJ_K !== undefined)
  const hasRSI = features.some(d =>
    (d.RSI6 !== null && d.RSI6 !== undefined) ||
    (d.RSI12 !== null && d.RSI12 !== undefined) ||
    (d.RSI24 !== null && d.RSI24 !== undefined)
  )
  const hasBOLL = features.some(d => d.BOLL_UPPER !== null && d.BOLL_UPPER !== undefined)

  // 加载日线数据
  const loadDailyData = async () => {
    // 如果提供了外部数据（回测模式），直接使用
    if (externalData && externalData.length > 0) {
      setFeatures(externalData)
      return
    }

    // 否则从API加载
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
  }, [stockCode, chartType, externalData])

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
      return (
        <EChartsStockChart
          data={features}
          stockCode={stockCode}
          backtestMode={backtestMode}
          signalPoints={signalPoints}
          equityCurve={equityCurve}
          externalVisibleIndicators={visibleIndicators}
          hideSettingsButton={true}  // 隐藏内部的设置按钮
        />
      )
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
              onClick={() => setShowIndicatorSettings(true)}
            >
              <Settings2 className="w-4 h-4" />
              <span>指标设置</span>
            </Button>
          )}
        </div>

        {/* 指标设置对话框（使用 Portal 渲染到 body，确保遮罩层正确覆盖） */}
        {showIndicatorSettings && typeof window !== 'undefined' && createPortal(
          <div
            className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[9999]"
            onClick={() => setShowIndicatorSettings(false)}
            style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0 }}
          >
            <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">选择显示的指标</h3>
                <button
                  onClick={() => setShowIndicatorSettings(false)}
                  className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="space-y-3">
                {/* 成交量 */}
                <label className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={visibleIndicators.volume}
                    onChange={(e) => setVisibleIndicators({ ...visibleIndicators, volume: e.target.checked })}
                    className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500"
                  />
                  <span className="ml-3 text-gray-900 dark:text-white">成交量 (Volume)</span>
                </label>

                {/* MACD */}
                <label className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={visibleIndicators.macd}
                    onChange={(e) => setVisibleIndicators({ ...visibleIndicators, macd: e.target.checked })}
                    disabled={!hasMACD}
                    className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500 disabled:opacity-50"
                  />
                  <span className={`ml-3 ${hasMACD ? 'text-gray-900 dark:text-white' : 'text-gray-400 dark:text-gray-600'}`}>
                    MACD {!hasMACD && '(无数据)'}
                  </span>
                </label>

                {/* KDJ */}
                <label className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={visibleIndicators.kdj}
                    onChange={(e) => setVisibleIndicators({ ...visibleIndicators, kdj: e.target.checked })}
                    disabled={!hasKDJ}
                    className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500 disabled:opacity-50"
                  />
                  <span className={`ml-3 ${hasKDJ ? 'text-gray-900 dark:text-white' : 'text-gray-400 dark:text-gray-600'}`}>
                    KDJ {!hasKDJ && '(无数据)'}
                  </span>
                </label>

                {/* RSI */}
                <label className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={visibleIndicators.rsi}
                    onChange={(e) => setVisibleIndicators({ ...visibleIndicators, rsi: e.target.checked })}
                    disabled={!hasRSI}
                    className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500 disabled:opacity-50"
                  />
                  <span className={`ml-3 ${hasRSI ? 'text-gray-900 dark:text-white' : 'text-gray-400 dark:text-gray-600'}`}>
                    RSI {!hasRSI && '(无数据)'}
                  </span>
                </label>

                {/* BOLL */}
                <label className="flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={visibleIndicators.boll}
                    onChange={(e) => setVisibleIndicators({ ...visibleIndicators, boll: e.target.checked })}
                    disabled={!hasBOLL}
                    className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500 disabled:opacity-50"
                  />
                  <span className={`ml-3 ${hasBOLL ? 'text-gray-900 dark:text-white' : 'text-gray-400 dark:text-gray-600'}`}>
                    布林带 (BOLL) {!hasBOLL && '(无数据)'}
                  </span>
                </label>
              </div>

              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => setShowIndicatorSettings(false)}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  确定
                </button>
              </div>
            </div>
          </div>,
          document.body
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
