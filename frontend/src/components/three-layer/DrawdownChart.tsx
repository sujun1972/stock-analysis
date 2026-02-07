'use client'

import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'

interface DrawdownPoint {
  date: string
  drawdown: number
}

interface DrawdownChartProps {
  data: DrawdownPoint[]
  maxDrawdown: number
  title?: string
}

/**
 * 回撤曲线图表组件
 * 用于展示策略的回撤情况
 */
export default function DrawdownChart({
  data,
  maxDrawdown,
  title = '回撤曲线'
}: DrawdownChartProps) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstanceRef = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    if (!chartRef.current || !data || data.length === 0) return

    // 初始化图表
    if (!chartInstanceRef.current) {
      chartInstanceRef.current = echarts.init(chartRef.current)
    }

    const chart = chartInstanceRef.current

    const dates = data.map(d => d.date)
    const drawdowns = data.map(d => d.drawdown * 100) // 转换为百分比

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
          type: 'cross'
        },
        formatter: function (params: any) {
          const param = params[0]
          return `
            <div style="font-weight:bold; margin-bottom:5px;">${param.axisValue}</div>
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <span>
                <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${param.color};margin-right:5px;"></span>
                回撤:
              </span>
              <span style="font-weight:bold; margin-left:10px; color:#ef4444;">
                ${param.value.toFixed(2)}%
              </span>
            </div>
          `
        }
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        top: 60,
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
        name: '回撤 (%)',
        max: 0,
        axisLabel: {
          formatter: '{value}%'
        },
        splitLine: {
          lineStyle: {
            type: 'dashed',
            opacity: 0.3
          }
        }
      },
      series: [
        {
          name: '回撤',
          type: 'line',
          data: drawdowns,
          smooth: true,
          lineStyle: {
            width: 2,
            color: '#ef4444'
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(239, 68, 68, 0.1)' },
              { offset: 1, color: 'rgba(239, 68, 68, 0.3)' }
            ])
          },
          showSymbol: false,
          markLine: {
            symbol: ['none', 'none'],
            data: [
              {
                name: '最大回撤',
                yAxis: maxDrawdown * 100,
                label: {
                  formatter: `最大回撤: ${(maxDrawdown * 100).toFixed(2)}%`,
                  position: 'end'
                },
                lineStyle: {
                  color: '#dc2626',
                  type: 'dashed',
                  width: 2
                }
              }
            ]
          }
        }
      ],
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
  }, [data, maxDrawdown, title])

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
    <div
      ref={chartRef}
      style={{ width: '100%', height: '300px' }}
    />
  )
}
