'use client'

import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

interface EquityPoint {
  date: string
  value: number
}

interface EquityCurveChartProps {
  strategyData: EquityPoint[]
  benchmarkData?: EquityPoint[]
  title?: string
}

export default function EquityCurveChart({
  strategyData,
  benchmarkData,
  title = '资金曲线对比'
}: EquityCurveChartProps) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstanceRef = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    if (!chartRef.current || !strategyData || strategyData.length === 0) return

    // 初始化图表
    if (!chartInstanceRef.current) {
      chartInstanceRef.current = echarts.init(chartRef.current)
    }

    const chart = chartInstanceRef.current

    // 准备数据
    const dates = strategyData.map(d => d.date)
    const strategyValues = strategyData.map(d => d.value)

    // 归一化到初始值=1,方便对比
    const initialValue = strategyValues[0]
    const normalizedStrategy = strategyValues.map(v => v / initialValue)

    const series: any[] = [
      {
        name: '策略净值',
        type: 'line',
        data: normalizedStrategy,
        smooth: true,
        lineStyle: {
          width: 2,
          color: '#3b82f6'
        },
        itemStyle: {
          color: '#3b82f6'
        },
        showSymbol: false,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
            { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
          ])
        }
      }
    ]

    // 添加基准数据
    if (benchmarkData && benchmarkData.length > 0) {
      const benchmarkValues = benchmarkData.map(d => d.value)
      const benchmarkInitial = benchmarkValues[0]
      const normalizedBenchmark = benchmarkValues.map(v => v / benchmarkInitial)

      series.push({
        name: '基准(沪深300)',
        type: 'line',
        data: normalizedBenchmark,
        smooth: true,
        lineStyle: {
          width: 2,
          color: '#ef4444',
          type: 'dashed'
        },
        itemStyle: {
          color: '#ef4444'
        },
        showSymbol: false
      })
    }

    const option: echarts.EChartsOption = {
      title: {
        text: title,
        left: 'center',
        textStyle: {
          fontSize: 16,
          fontWeight: 'bold'
        }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        },
        formatter: (params: any) => {
          if (!Array.isArray(params)) return ''

          const date = params[0].axisValue
          let tooltip = `<strong>${date}</strong><br/>`

          params.forEach((param: any) => {
            const value = param.value
            const returnPct = ((value - 1) * 100).toFixed(2)
            tooltip += `${param.marker} ${param.seriesName}: ${value.toFixed(4)} (${returnPct}%)<br/>`
          })

          return tooltip
        }
      },
      legend: {
        data: benchmarkData ? ['策略净值', '基准(沪深300)'] : ['策略净值'],
        top: 35,
        left: 'center'
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: 80,
        containLabel: true
      },
      xAxis: {
        type: 'category',
        data: dates,
        boundaryGap: false,
        axisLabel: {
          formatter: (value: string) => {
            // 只显示月-日
            const date = new Date(value)
            return `${date.getMonth() + 1}-${date.getDate()}`
          }
        }
      },
      yAxis: {
        type: 'value',
        name: '归一化净值',
        axisLabel: {
          formatter: (value: number) => value.toFixed(2)
        },
        splitLine: {
          lineStyle: {
            type: 'dashed'
          }
        }
      },
      dataZoom: [
        {
          type: 'inside',
          start: 0,
          end: 100
        },
        {
          type: 'slider',
          start: 0,
          end: 100,
          bottom: 10
        }
      ],
      series: series
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
  }, [strategyData, benchmarkData, title])

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
      <div ref={chartRef} style={{ width: '100%', height: '400px' }} />
    </div>
  )
}
