/**
 * 股票K线图表轮播组件
 * 支持多个股票的K线图展示，带分页功能
 *
 * 重构说明：
 * - 使用 StockPriceCard 组件替代 BacktestKLineChart
 * - 统一了图表组件，提升代码复用性
 * - 支持技术指标分析（MACD/KDJ/RSI/BOLL等）
 */

'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import StockPriceCard from '@/components/StockPriceCard'

// K线数据接口（来自后端）
interface KLineData {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  MA5?: number | null
  MA20?: number | null
  MA60?: number | null
}

// 信号点接口
interface SignalPoint {
  date: string
  price: number
}

// 单个股票的图表数据
interface StockChartData {
  kline_data: KLineData[]
  buy_signals: SignalPoint[]
  sell_signals: SignalPoint[]
}

// 权益曲线数据点
interface EquityCurvePoint {
  date: string
  total: number
  cash?: number
  holdings?: number
}

// 组件Props
interface StockChartsCarouselProps {
  stockCharts: Record<string, StockChartData>
  equityCurve?: EquityCurvePoint[]
}

export default function StockChartsCarousel({ stockCharts, equityCurve }: StockChartsCarouselProps) {
  const stockCodes = Object.keys(stockCharts)
  const [currentIndex, setCurrentIndex] = useState(0)

  if (stockCodes.length === 0) {
    return null
  }

  const currentStockCode = stockCodes[currentIndex]
  const currentChartData = stockCharts[currentStockCode]

  const handlePrevious = () => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : stockCodes.length - 1))
  }

  const handleNext = () => {
    setCurrentIndex((prev) => (prev < stockCodes.length - 1 ? prev + 1 : 0))
  }

  /**
   * 数据格式转换：KLineData -> FeatureData
   *
   * 回测数据只包含基础K线数据（OHLCV + MA），需要补充技术指标字段
   * 将缺失的技术指标字段设为 null，保持与 FeatureData 接口一致
   *
   * @param klineData 回测返回的K线数据
   * @returns StockPriceCard/EChartsStockChart 所需的完整数据格式
   */
  const convertToFeatureData = (klineData: KLineData[]) => {
    return klineData.map(d => ({
      ...d,
      // 补充技术指标字段（回测数据中不包含）
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
  }

  return (
    <div className="space-y-4">
      {/* 轮播控制栏 */}
      {stockCodes.length > 1 && (
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">股票K线图、交易信号与权益曲线</h3>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePrevious}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <span className="text-sm text-muted-foreground min-w-[100px] text-center">
              {currentIndex + 1} / {stockCodes.length}
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={handleNext}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* 使用 StockPriceCard 替代 BacktestKLineChart */}
      {currentChartData && (
        <StockPriceCard
          stockCode={currentStockCode}
          stockName={currentStockCode}
          defaultChartType="daily"
          showHeader={stockCodes.length === 1}  // 单个股票时显示头部
          backtestMode={true}
          signalPoints={{
            buy: currentChartData.buy_signals || [],
            sell: currentChartData.sell_signals || []
          }}
          equityCurve={equityCurve}
          externalData={convertToFeatureData(currentChartData.kline_data)}
        />
      )}

      {/* 快速导航 */}
      {stockCodes.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {stockCodes.map((code, index) => (
            <Button
              key={code}
              variant={index === currentIndex ? 'default' : 'outline'}
              size="sm"
              onClick={() => setCurrentIndex(index)}
              className="text-xs"
            >
              {code}
            </Button>
          ))}
        </div>
      )}
    </div>
  )
}
