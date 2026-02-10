/**
 * 股票K线图表轮播组件
 * 支持多个股票的K线图展示，带分页功能
 */

'use client'

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import BacktestKLineChart from '@/components/BacktestKLineChart'

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

interface SignalPoint {
  date: string
  price: number
}

interface StockChartData {
  kline_data: KLineData[]
  buy_signals: SignalPoint[]
  sell_signals: SignalPoint[]
}

interface EquityCurvePoint {
  date: string
  total: number
  cash?: number
  holdings?: number
}

interface StockChartsCarouselProps {
  stockCharts: Record<string, StockChartData>
  equityCurve?: EquityCurvePoint[]  // 权益曲线数据
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

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>股票K线图、交易信号与权益曲线</CardTitle>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePrevious}
              disabled={stockCodes.length <= 1}
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
              disabled={stockCodes.length <= 1}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {currentChartData && (
          <BacktestKLineChart
            data={currentChartData.kline_data}
            signalPoints={{
              buy: currentChartData.buy_signals || [],
              sell: currentChartData.sell_signals || []
            }}
            stockCode={currentStockCode}
            equityCurve={equityCurve}
          />
        )}

        {/* 快速导航 */}
        {stockCodes.length > 1 && (
          <div className="mt-4 flex flex-wrap gap-2">
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
      </CardContent>
    </Card>
  )
}
