/**
 * 股票K线图表轮播组件
 * 在回测结果页面中展示多个股票的K线图、交易信号和权益曲线
 *
 * 功能特性：
 * - 多股票轮播展示（支持上一页/下一页/股票选择下拉框）
 * - 显示买卖信号标记点
 * - 显示权益曲线
 * - 自动提取股票名称并在图表中显示
 * - 使用 Card 布局统一样式
 *
 * 数据流设计：
 * - 只传递股票代码和买卖信号数据（轻量级）
 * - StockPriceCard 组件自主从后端获取K线和技术指标数据
 * - 回测K线数据（来自后端）与API技术指标数据智能合并
 * - 保证买卖信号与K线数据精确对应
 */

'use client'

import { useState, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import StockPriceCard from '@/components/StockPriceCard'
import { StockCombobox } from './StockCombobox'

// 信号点接口
interface SignalPoint {
  date: string
  price: number
}

// K线数据接口
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

// 单个股票的信号数据（包含K线数据）
interface StockSignalData {
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

// 交易记录接口（用于提取股票名称）
interface TradeRecord {
  stock_code?: string
  code?: string
  symbol?: string
  stock_name?: string
  name?: string
  [key: string]: any
}

// 组件Props
interface StockChartsCarouselProps {
  stockCodes: string[]  // 股票代码列表
  dateRange?: { start: string; end: string }  // 可选的日期范围
  signalData: Record<string, StockSignalData>  // 买卖信号数据
  equityCurve?: EquityCurvePoint[]
  trades?: TradeRecord[]  // 添加 trades 参数用于获取股票名称
}

export default function StockChartsCarousel({ stockCodes, dateRange, signalData, equityCurve, trades }: StockChartsCarouselProps) {
  const [currentIndex, setCurrentIndex] = useState(0)

  // 从交易记录中提取股票代码与名称的映射（使用 useMemo 优化）
  const stockNameMap = useMemo(() => {
    const map = new Map<string, string>()
    if (trades) {
      trades.forEach((trade) => {
        const code = trade.stock_code || trade.code || trade.symbol
        const name = trade.stock_name || trade.name
        if (code && name && !map.has(code)) {
          map.set(code, name)
        }
      })
    }
    return map
  }, [trades])

  // 准备 Combobox 的选项数据
  const stockOptions = useMemo(() => {
    return stockCodes.map((code) => {
      const name = stockNameMap.get(code)
      const label = name ? `${name}(${code})` : code
      // searchText 包含代码和名称，方便搜索
      const searchText = name ? `${code} ${name} ${label}` : code
      return {
        value: code,
        label,
        searchText
      }
    })
  }, [stockCodes, stockNameMap])

  if (stockCodes.length === 0) {
    return null
  }

  const currentStockCode = stockCodes[currentIndex]
  const currentSignalData = signalData[currentStockCode]
  const currentStockName = stockNameMap.get(currentStockCode) || currentStockCode

  const handlePrevious = () => {
    setCurrentIndex((prev) => (prev > 0 ? prev - 1 : stockCodes.length - 1))
  }

  const handleNext = () => {
    setCurrentIndex((prev) => (prev < stockCodes.length - 1 ? prev + 1 : 0))
  }

  return (
    <Card>
      {/* 卡片头部：标题和控制栏 */}
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle>股票K线图、交易信号与权益曲线</CardTitle>
          {/* 多股票时显示轮播控制 */}
          {stockCodes.length > 1 && (
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
              {/* 股票选择下拉框 */}
              <StockCombobox
                value={currentStockCode}
                onValueChange={(value) => {
                  const selectedIndex = stockCodes.indexOf(value)
                  if (selectedIndex !== -1) {
                    setCurrentIndex(selectedIndex)
                  }
                }}
                options={stockOptions}
                placeholder="选择股票"
                width="w-[200px]"
              />
            </div>
          )}
        </div>
      </CardHeader>

      {/* 卡片内容：图表 */}
      <CardContent>
        <StockPriceCard
          stockCode={currentStockCode}
          stockName={currentStockName}
          dateRange={dateRange}
          defaultChartType="daily"
          showHeader={false}  // 不显示头部，因为外层Card已经有了
          showCard={false}    // 不显示内部卡片，因为外层已经有Card
          backtestMode={true}
          backtestKlineData={currentSignalData?.kline_data}
          signalPoints={{
            buy: currentSignalData?.buy_signals || [],
            sell: currentSignalData?.sell_signals || []
          }}
          equityCurve={equityCurve}
        />
      </CardContent>
    </Card>
  )
}
