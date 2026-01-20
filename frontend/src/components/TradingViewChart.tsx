'use client'

import { useEffect, useRef } from 'react'
import { createChart, IChartApi, Time } from 'lightweight-charts'

interface ChartData {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  MA5?: number
  MA20?: number
  MA60?: number
  MACD?: number
  MACD_SIGNAL?: number
  MACD_HIST?: number
  KDJ_K?: number
  KDJ_D?: number
  KDJ_J?: number
}

interface TradingViewChartProps {
  data: ChartData[]
  height?: number
}

export default function TradingViewChart({ data, height = 600 }: TradingViewChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!chartContainerRef.current || data.length === 0) return

    // 创建图表
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: height,
      layout: {
        background: { color: '#ffffff' },
        textColor: '#333',
      },
      grid: {
        vertLines: { color: '#f0f0f0' },
        horzLines: { color: '#f0f0f0' },
      },
      crosshair: {
        mode: 1, // Normal crosshair
      },
      rightPriceScale: {
        borderColor: '#d1d4dc',
      },
      timeScale: {
        borderColor: '#d1d4dc',
        timeVisible: true,
        secondsVisible: false,
      },
    })

    chartRef.current = chart

    // 准备K线数据
    const candlestickData = data.map(d => ({
      time: (new Date(d.date).getTime() / 1000) as Time,
      open: d.open,
      high: d.high,
      low: d.low,
      close: d.close,
    }))

    // 添加K线图系列
    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#ef4444',
      downColor: '#22c55e',
      borderUpColor: '#ef4444',
      borderDownColor: '#22c55e',
      wickUpColor: '#ef4444',
      wickDownColor: '#22c55e',
    })
    candlestickSeries.setData(candlestickData)

    // 添加MA5均线
    if (data[0]?.MA5 !== undefined) {
      const ma5Data = data
        .filter(d => d.MA5 !== null && d.MA5 !== undefined)
        .map(d => ({
          time: (new Date(d.date).getTime() / 1000) as Time,
          value: d.MA5!,
        }))
      const ma5Series = chart.addLineSeries({
        color: '#f59e0b',
        lineWidth: 2,
        title: 'MA5',
      })
      ma5Series.setData(ma5Data)
    }

    // 添加MA20均线
    if (data[0]?.MA20 !== undefined) {
      const ma20Data = data
        .filter(d => d.MA20 !== null && d.MA20 !== undefined)
        .map(d => ({
          time: (new Date(d.date).getTime() / 1000) as Time,
          value: d.MA20!,
        }))
      const ma20Series = chart.addLineSeries({
        color: '#10b981',
        lineWidth: 2,
        title: 'MA20',
      })
      ma20Series.setData(ma20Data)
    }

    // 添加MA60均线
    if (data[0]?.MA60 !== undefined) {
      const ma60Data = data
        .filter(d => d.MA60 !== null && d.MA60 !== undefined)
        .map(d => ({
          time: (new Date(d.date).getTime() / 1000) as Time,
          value: d.MA60!,
        }))
      const ma60Series = chart.addLineSeries({
        color: '#8b5cf6',
        lineWidth: 2,
        title: 'MA60',
      })
      ma60Series.setData(ma60Data)
    }

    // 自适应时间范围
    chart.timeScale().fitContent()

    // 响应式调整大小
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth })
      }
    }
    window.addEventListener('resize', handleResize)

    // 清理函数
    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [data, height])

  return (
    <div className="space-y-0">
      {/* 主图：K线 + 均线 */}
      <div>
        <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 px-2">
          价格走势（K线图）
        </div>
        <div ref={chartContainerRef} />
      </div>
    </div>
  )
}
