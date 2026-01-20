'use client'

import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

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

interface SignalPoints {
  buy: SignalPoint[]
  sell: SignalPoint[]
}

interface BacktestKLineChartProps {
  data: KLineData[]
  signalPoints: SignalPoints
  stockCode: string
}

export default function BacktestKLineChart({
  data,
  signalPoints,
  stockCode
}: BacktestKLineChartProps) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstanceRef = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    if (!chartRef.current || !data || data.length === 0) return

    // 初始化图表
    if (!chartInstanceRef.current) {
      chartInstanceRef.current = echarts.init(chartRef.current)
    }

    const chart = chartInstanceRef.current

    // 准备数据
    const sortedData = [...data].sort((a, b) =>
      new Date(a.date).getTime() - new Date(b.date).getTime()
    )

    const dates = sortedData.map(d => d.date)
    const ohlcData = sortedData.map(d => [d.open, d.close, d.low, d.high])
    const volumeData = sortedData.map((d) => ({
      value: d.volume,
      itemStyle: {
        color: d.close >= d.open ? '#ef4444' : '#22c55e'
      }
    }))

    // MA线数据
    const ma5Data = sortedData.map(d => d.MA5 ?? '-')
    const ma20Data = sortedData.map(d => d.MA20 ?? '-')
    const ma60Data = sortedData.map(d => d.MA60 ?? '-')

    // 准备买卖信号markPoint数据
    const buyMarkPoints = signalPoints.buy.map(point => ({
      name: '买入',
      coord: [point.date, point.price],
      value: '买',
      symbol: 'pin',
      symbolSize: 50,
      itemStyle: {
        color: '#ef4444'
      },
      label: {
        show: true,
        formatter: '买',
        color: '#fff',
        fontSize: 12
      }
    }))

    const sellMarkPoints = signalPoints.sell.map(point => ({
      name: '卖出',
      coord: [point.date, point.price],
      value: '卖',
      symbol: 'pin',
      symbolSize: 50,
      symbolRotate: 180,
      itemStyle: {
        color: '#22c55e'
      },
      label: {
        show: true,
        formatter: '卖',
        color: '#fff',
        fontSize: 12
      }
    }))

    const option: echarts.EChartsOption = {
      animation: false,
      backgroundColor: '#ffffff',
      title: {
        text: `${stockCode} 回测K线图`,
        left: 'center',
        textStyle: {
          fontSize: 16,
          fontWeight: 'bold'
        }
      },
      legend: {
        data: ['K线', 'MA5', 'MA20', 'MA60', '成交量'],
        top: 35,
        left: 'center'
      },
      grid: [
        {
          left: '8%',
          right: '8%',
          top: '12%',
          height: '55%'
        },
        {
          left: '8%',
          right: '8%',
          top: '72%',
          height: '18%'
        }
      ],
      xAxis: [
        {
          type: 'category',
          data: dates,
          gridIndex: 0,
          boundaryGap: false,
          axisLine: { onZero: false },
          splitLine: { show: false },
          axisLabel: { show: false }
        },
        {
          type: 'category',
          data: dates,
          gridIndex: 1,
          boundaryGap: false,
          axisLine: { onZero: false },
          splitLine: { show: false },
          axisLabel: {
            show: true,
            formatter: (value: string) => {
              const date = new Date(value)
              return `${date.getMonth() + 1}-${date.getDate()}`
            }
          }
        }
      ],
      yAxis: [
        {
          scale: true,
          gridIndex: 0,
          splitArea: {
            show: true
          }
        },
        {
          scale: true,
          gridIndex: 1,
          splitArea: {
            show: true
          }
        }
      ],
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: [0, 1],
          start: 70,
          end: 100
        },
        {
          show: true,
          xAxisIndex: [0, 1],
          type: 'slider',
          bottom: '2%',
          start: 70,
          end: 100
        }
      ],
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        },
        borderWidth: 1,
        borderColor: '#ccc',
        padding: 10,
        textStyle: {
          color: '#000'
        }
      },
      series: [
        // K线
        {
          name: 'K线',
          type: 'candlestick',
          data: ohlcData,
          xAxisIndex: 0,
          yAxisIndex: 0,
          itemStyle: {
            color: '#ef4444',
            color0: '#22c55e',
            borderColor: '#ef4444',
            borderColor0: '#22c55e'
          },
          // 关键: 添加买卖信号markPoint
          markPoint: {
            data: [...buyMarkPoints, ...sellMarkPoints],
            animation: true,
            animationDuration: 500
          }
        },
        // MA5
        {
          name: 'MA5',
          type: 'line',
          data: ma5Data,
          xAxisIndex: 0,
          yAxisIndex: 0,
          smooth: true,
          lineStyle: {
            opacity: 0.8,
            width: 1,
            color: '#f59e0b'
          },
          showSymbol: false
        },
        // MA20
        {
          name: 'MA20',
          type: 'line',
          data: ma20Data,
          xAxisIndex: 0,
          yAxisIndex: 0,
          smooth: true,
          lineStyle: {
            opacity: 0.8,
            width: 1,
            color: '#10b981'
          },
          showSymbol: false
        },
        // MA60
        {
          name: 'MA60',
          type: 'line',
          data: ma60Data,
          xAxisIndex: 0,
          yAxisIndex: 0,
          smooth: true,
          lineStyle: {
            opacity: 0.8,
            width: 1,
            color: '#8b5cf6'
          },
          showSymbol: false
        },
        // 成交量
        {
          name: '成交量',
          type: 'bar',
          data: volumeData,
          xAxisIndex: 1,
          yAxisIndex: 1
        }
      ]
    }

    chart.setOption(option)

    // 响应式调整
    const handleResize = () => {
      chart.resize()
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
    }
  }, [data, signalPoints, stockCode])

  // 清理
  useEffect(() => {
    return () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.dispose()
        chartInstanceRef.current = null
      }
    }
  }, [])

  return (
    <div className="w-full bg-white dark:bg-gray-800 rounded-lg shadow-lg p-4">
      <div ref={chartRef} style={{ width: '100%', height: '600px' }} />

      {/* 信号统计 */}
      <div className="mt-4 grid grid-cols-2 gap-4">
        <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-red-500 rounded-full"></div>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              买入信号: {signalPoints.buy.length} 次
            </span>
          </div>
        </div>
        <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 bg-green-500 rounded-full"></div>
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              卖出信号: {signalPoints.sell.length} 次
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
