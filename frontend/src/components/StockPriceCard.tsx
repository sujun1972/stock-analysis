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
  dateRange?: { start: string; end: string }  // 可选的日期范围（回测模式使用）
  defaultChartType?: 'daily' | 'minute'
  showHeader?: boolean
  showCard?: boolean  // 是否显示外层卡片（默认true）
  className?: string
  onIndicatorsChange?: (indicators: string[]) => void
  // 回测模式相关（可选）
  backtestMode?: boolean
  backtestKlineData?: FeatureData[]  // 回测模式下的K线数据（优先使用，与信号精确匹配）
  signalPoints?: SignalPoints
  equityCurve?: EquityCurvePoint[]
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
 * - 支持嵌套布局（可选择是否显示外层卡片）
 *
 * @example
 * ```tsx
 * // 普通模式（带卡片）
 * <StockPriceCard
 *   stockCode="000001"
 *   stockName="平安银行"
 *   defaultChartType="daily"
 *   showHeader={true}
 *   showCard={true}  // 默认值
 * />
 *
 * // 回测模式（带卡片）
 * <StockPriceCard
 *   stockCode="000001"
 *   stockName="平安银行"
 *   dateRange={{ start: '2024-01-01', end: '2024-12-31' }}
 *   backtestMode={true}
 *   backtestKlineData={[...]}  // 回测返回的K线数据（与信号精确匹配）
 *   signalPoints={{ buy: [...], sell: [...] }}
 *   equityCurve={[...]}
 * />
 *
 * // 嵌入模式（不显示卡片，适合放在其他Card内）
 * <Card>
 *   <CardHeader>自定义标题</CardHeader>
 *   <CardContent>
 *     <StockPriceCard
 *       stockCode="000001"
 *       stockName="平安银行"
 *       showCard={false}  // 不显示内部卡片
 *       showHeader={false}  // 不显示内部标题
 *     />
 *   </CardContent>
 * </Card>
 * ```
 */
export default function StockPriceCard({
  stockCode,
  stockName,
  dateRange,
  defaultChartType = 'daily',
  showHeader = true,
  showCard = true,
  className = '',
  onIndicatorsChange,
  backtestMode = false,
  backtestKlineData,
  signalPoints,
  equityCurve,
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
   * 控制 body 滚动：打开对话框时禁用，关闭时恢复
   */
  useEffect(() => {
    if (showIndicatorSettings) {
      // 保存当前滚动位置
      const scrollY = window.scrollY
      document.body.style.overflow = 'hidden'
      document.body.style.position = 'fixed'
      document.body.style.top = `-${scrollY}px`
      document.body.style.width = '100%'
    } else {
      // 恢复滚动
      const scrollY = document.body.style.top
      document.body.style.overflow = ''
      document.body.style.position = ''
      document.body.style.top = ''
      document.body.style.width = ''
      if (scrollY) {
        window.scrollTo(0, parseInt(scrollY || '0') * -1)
      }
    }
  }, [showIndicatorSettings])

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
    try {
      setIsLoading(true)
      setError(null)

      /**
       * 回测模式：双数据源智能合并策略
       *
       * 问题背景：
       * - 回测K线数据：包含OHLCV和MA，与买卖信号精确对应，但缺少技术指标
       * - API完整数据：包含所有技术指标，但可能与回测信号的日期范围不完全匹配
       *
       * 解决方案：
       * 1. 使用回测数据的OHLCV（保证与信号点对应）
       * 2. 从API获取技术指标数据
       * 3. 按日期合并两个数据源
       */
      if (backtestMode && backtestKlineData && backtestKlineData.length > 0) {
        const params: any = { limit: 500 }
        if (dateRange?.end) {
          params.end_date = dateRange.end
        }

        try {
          // 步骤1: 从API获取完整的技术指标数据
          const response = await apiClient.getFeatures(stockCode, params)
          const apiData = response.data

          // 步骤2: 创建日期映射表（用于O(1)查找）
          const apiDataMap = new Map<string, FeatureData>()
          apiData.forEach(item => {
            // 统一日期格式为 YYYY-MM-DD（移除时间部分）
            const dateKey = item.date.split(' ')[0].split('T')[0]
            apiDataMap.set(dateKey, item)
          })

          // 步骤3: 智能合并数据
          const mergedData = backtestKlineData.map(backtestItem => {
            const dateKey = backtestItem.date.split(' ')[0].split('T')[0]
            const apiItem = apiDataMap.get(dateKey)

            return {
              // 使用回测数据的OHLCV（与信号精确对应）
              date: backtestItem.date,
              open: backtestItem.open,
              high: backtestItem.high,
              low: backtestItem.low,
              close: backtestItem.close,
              volume: backtestItem.volume,
              // MA优先使用回测数据，回退到API数据
              MA5: backtestItem.MA5 ?? apiItem?.MA5 ?? null,
              MA20: backtestItem.MA20 ?? apiItem?.MA20 ?? null,
              MA60: backtestItem.MA60 ?? apiItem?.MA60 ?? null,
              // 技术指标从API数据获取
              MACD: apiItem?.MACD ?? null,
              MACD_SIGNAL: apiItem?.MACD_SIGNAL ?? null,
              MACD_HIST: apiItem?.MACD_HIST ?? null,
              KDJ_K: apiItem?.KDJ_K ?? null,
              KDJ_D: apiItem?.KDJ_D ?? null,
              KDJ_J: apiItem?.KDJ_J ?? null,
              RSI6: apiItem?.RSI6 ?? null,
              RSI12: apiItem?.RSI12 ?? null,
              RSI24: apiItem?.RSI24 ?? null,
              BOLL_UPPER: apiItem?.BOLL_UPPER ?? null,
              BOLL_MIDDLE: apiItem?.BOLL_MIDDLE ?? null,
              BOLL_LOWER: apiItem?.BOLL_LOWER ?? null
            }
          })

          setFeatures(mergedData)
        } catch (apiError) {
          // API加载失败时的降级处理：仍然显示回测K线和信号，但技术指标不可用
          console.error('加载技术指标失败，降级使用回测K线数据:', apiError)
          const basicData = backtestKlineData.map(d => ({
            ...d,
            MA5: d.MA5 ?? null,
            MA20: d.MA20 ?? null,
            MA60: d.MA60 ?? null,
            MACD: null,
            MACD_SIGNAL: null,
            MACD_HIST: null,
            KDJ_K: null,
            KDJ_D: null,
            KDJ_J: null,
            RSI6: null,
            RSI12: null,
            RSI24: null,
            BOLL_UPPER: null,
            BOLL_MIDDLE: null,
            BOLL_LOWER: null
          }))
          setFeatures(basicData)
        }

        setIsLoading(false)
        return
      }

      // 普通模式：直接从API加载完整数据
      const params: any = { limit: 500 }
      if (dateRange?.end) {
        params.end_date = dateRange.end
      }

      const response = await apiClient.getFeatures(stockCode, params)
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
  }, [stockCode, chartType, dateRange, backtestKlineData])

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

  // 图表内容部分
  const chartContent = (
    <div className="space-y-4">
        {/* 图表类型切换和控制栏 */}
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
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

            {/* 当不显示卡片时，在这里显示股票信息 */}
            {!showCard && stockName && (
              <Badge variant="outline" className="text-sm">
                {stockName} ({stockCode})
              </Badge>
            )}
          </div>

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
      </div>
  )

  // 如果不显示卡片，直接返回内容
  if (!showCard) {
    return chartContent
  }

  // 显示卡片
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

      <CardContent>
        {chartContent}
      </CardContent>
    </Card>
  )
}
