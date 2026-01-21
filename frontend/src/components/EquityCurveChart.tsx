'use client'

import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

interface EquityPoint {
  date: string
  value: number
}

interface StrategyData {
  name: string
  data: EquityPoint[]
  color?: string
}

interface EquityCurveChartProps {
  // 单策略模式
  strategyData?: EquityPoint[]
  // 多策略对比模式
  strategies?: StrategyData[]
  benchmarkData?: EquityPoint[]
  title?: string
}

export default function EquityCurveChart({
  strategyData,
  strategies,
  benchmarkData,
  title = '资金曲线对比'
}: EquityCurveChartProps) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstanceRef = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    if (!chartRef.current) return

    // 判断是单策略还是多策略模式
    const hasData = (strategyData && strategyData.length > 0) || (strategies && strategies.length > 0)
    if (!hasData) return

    // 初始化图表
    if (!chartInstanceRef.current) {
      chartInstanceRef.current = echarts.init(chartRef.current)
    }

    const chart = chartInstanceRef.current

    // 准备数据
    let dates: string[] = []
    const series: any[] = []

    if (strategies && strategies.length > 0) {
      // 多策略模式
      dates = strategies[0].data.map(d => d.date)

      strategies.forEach((strategy, idx) => {
        const values = strategy.data.map(d => d.value)
        const initialValue = values[0]
        const normalized = values.map(v => v / initialValue)

        series.push({
          name: strategy.name,
          type: 'line',
          data: normalized,
          smooth: true,
          lineStyle: {
            width: 3,
            color: strategy.color || ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b'][idx % 4]
          },
          showSymbol: false,
          emphasis: {
            focus: 'series',
            lineStyle: {
              width: 4
            }
          }
        })
      })
    } else if (strategyData) {
      // 单策略模式
      dates = strategyData.map(d => d.date)
      const strategyValues = strategyData.map(d => d.value)
      const initialValue = strategyValues[0]
      const normalizedStrategy = strategyValues.map(v => v / initialValue)

      series.push({
        name: '策略净值',
        type: 'line',
        data: normalizedStrategy,
        smooth: true,
        lineStyle: {
          width: 3,
          color: '#3b82f6'
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
            { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
          ])
        },
        showSymbol: false
      })
    }

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
          type: 'dashed',
          color: '#ef4444'
        },
        showSymbol: false
      })
    }

    // 配置图表选项
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
          type: 'cross',
          label: {
            backgroundColor: '#6a7985'
          }
        },
        formatter: function (params: any) {
          let result = `<div style="font-weight:bold; margin-bottom:5px;">${params[0].axisValue}</div>`
          params.forEach((param: any) => {
            const percentChange = ((param.value - 1) * 100).toFixed(2)
            const color = param.value >= 1 ? '#22c55e' : '#ef4444'
            result += `
              <div style="display:flex; justify-content:space-between; align-items:center; margin-top:3px;">
                <span>
                  <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${param.color};margin-right:5px;"></span>
                  ${param.seriesName}:
                </span>
                <span style="font-weight:bold; margin-left:10px; color:${color};">
                  ${percentChange}%
                </span>
              </div>
            `
          })
          return result
        }
      },
      legend: {
        data: series.map(s => s.name),
        top: 30,
        type: 'scroll'
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
        boundaryGap: false,
        data: dates,
        axisLabel: {
          formatter: (value: string) => {
            const date = new Date(value)
            return `${date.getMonth() + 1}/${date.getDate()}`
          }
        }
      },
      yAxis: {
        type: 'value',
        name: '归一化净值',
        axisLabel: {
          formatter: '{value}'
        },
        splitLine: {
          lineStyle: {
            type: 'dashed',
            opacity: 0.3
          }
        },
        axisPointer: {
          snap: true
        }
      },
      series: series,
      dataZoom: [
        {
          type: 'inside',
          start: 0,
          end: 100
        },
        {
          start: 0,
          end: 100,
          height: 20,
          bottom: 10
        }
      ]
    }

    chart.setOption(option, true)

    // 窗口resize时更新图表
    const handleResize = () => {
      chart.resize()
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
    }
  }, [strategyData, strategies, benchmarkData, title])

  // 组件卸载时销毁图表
  useEffect(() => {
    return () => {
      if (chartInstanceRef.current) {
        chartInstanceRef.current.dispose()
        chartInstanceRef.current = null
      }
    }
  }, [])

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
      <div
        ref={chartRef}
        style={{ width: '100%', height: '400px' }}
      />
    </div>
  )
}
