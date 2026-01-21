'use client'

import { useEffect, useRef } from 'react'
import * as echarts from 'echarts'
import type { MinuteData } from '@/types'

interface MinuteChartProps {
  data: MinuteData[]
  period: string
  stockCode: string
  stockName: string
}

export default function MinuteChart({ data, period, stockCode, stockName }: MinuteChartProps) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<echarts.ECharts | null>(null)

  useEffect(() => {
    if (!chartRef.current || data.length === 0) return

    // 初始化或获取图表实例
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current)
    }

    const chart = chartInstance.current

    // 清空图表，确保没有旧数据残留
    chart.clear()

    // 准备数据 - A股分时图使用收盘价绘制折线
    const times = data.map(item => {
      const timeStr = item.trade_time.split(' ')[1]
      return timeStr ? timeStr.substring(0, 5) : '' // 只显示时:分
    })
    const closePrices = data.map(item => item.close)
    const volumes = data.map(item => item.volume)

    // 计算均价线（当天累计成交额 / 累计成交量）
    let cumulativeAmount = 0
    let cumulativeVolume = 0
    const avgPrices = data.map(item => {
      cumulativeAmount += (item.close * item.volume)
      cumulativeVolume += item.volume
      return cumulativeVolume > 0 ? cumulativeAmount / cumulativeVolume : item.close
    })

    // 配置图表选项 - A股分时图样式
    const option: echarts.EChartsOption = {
      title: {
        text: `${stockName} (${stockCode}) - 分时图`,
        left: 'center',
        textStyle: {
          fontSize: 16
        }
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        },
        formatter: function(params: any) {
          if (!params || params.length === 0) return ''

          const dataIndex = params[0].dataIndex
          const item = data[dataIndex]

          // 安全检查：确保数据存在
          if (!item) return ''

          // 安全格式化数字
          const safeFormat = (value: any, decimals: number = 2) => {
            return value != null ? Number(value).toFixed(decimals) : '--'
          }

          return `
            <div style="padding: 8px;">
              <div style="font-weight: bold; margin-bottom: 4px;">${item.trade_time || ''}</div>
              <div>价格: ${safeFormat(item.close)}</div>
              <div>均价: ${safeFormat(avgPrices[dataIndex])}</div>
              <div>成交量: ${item.volume != null ? safeFormat(item.volume / 100, 0) : '--'}手</div>
              ${item.pct_change != null ? `<div>涨跌幅: ${safeFormat(item.pct_change)}%</div>` : ''}
            </div>
          `
        }
      },
      grid: [
        {
          left: '10%',
          right: '10%',
          top: '15%',
          height: '50%'
        },
        {
          left: '10%',
          right: '10%',
          top: '70%',
          height: '15%'
        }
      ],
      xAxis: [
        {
          type: 'category',
          data: times,
          gridIndex: 0,
          axisLabel: {
            interval: Math.max(Math.floor(data.length / 10), 0) // 显示约10个标签
          }
        },
        {
          type: 'category',
          data: times,
          gridIndex: 1,
          axisLabel: {
            show: false
          }
        }
      ],
      yAxis: [
        {
          scale: true,
          gridIndex: 0,
          splitLine: {
            show: true
          }
        },
        {
          scale: true,
          gridIndex: 1,
          splitLine: {
            show: false
          }
        }
      ],
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: [0, 1],
          start: 0,
          end: 100
        },
        {
          show: true,
          xAxisIndex: [0, 1],
          type: 'slider',
          bottom: '5%',
          start: 0,
          end: 100
        }
      ],
      series: [
        {
          name: '价格',
          type: 'line',
          data: closePrices,
          smooth: false,
          showSymbol: false,
          lineStyle: {
            color: '#3b82f6',  // 蓝色价格线
            width: 1
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
              { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
            ])
          },
          xAxisIndex: 0,
          yAxisIndex: 0
        },
        {
          name: '均价',
          type: 'line',
          data: avgPrices,
          smooth: false,
          showSymbol: false,
          lineStyle: {
            color: '#f59e0b',  // 橙色均价线
            width: 1
          },
          xAxisIndex: 0,
          yAxisIndex: 0
        },
        {
          name: '成交量',
          type: 'bar',
          data: volumes,
          itemStyle: {
            color: function(params: any) {
              const dataIndex = params.dataIndex
              if (dataIndex === 0) return '#94a3b8'
              // 当前价格比前一个价格高则红色，低则绿色
              return closePrices[dataIndex] >= closePrices[dataIndex - 1] ? '#ef4444' : '#22c55e'
            }
          },
          xAxisIndex: 1,
          yAxisIndex: 1
        }
      ]
    }

    // 强制替换而不是合并，避免旧数据残留
    chart.setOption(option, {
      notMerge: true,  // 不合并，完全替换
      lazyUpdate: false  // 立即更新
    })

    // 响应式调整
    const handleResize = () => {
      chart.resize()
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
    }
  }, [data, period, stockCode, stockName])

  // 清理
  useEffect(() => {
    return () => {
      if (chartInstance.current) {
        chartInstance.current.dispose()
        chartInstance.current = null
      }
    }
  }, [])

  if (data.length === 0) {
    return (
      <div className="h-96 flex flex-col items-center justify-center text-gray-500 dark:text-gray-400">
        <svg className="w-16 h-16 mb-4 text-gray-300 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
        <p className="text-lg font-medium">暂无分时数据</p>
        <p className="text-sm mt-2 text-gray-400 dark:text-gray-500">
          请选择其他交易日期或股票代码
        </p>
      </div>
    )
  }

  return (
    <div
      ref={chartRef}
      className="w-full"
      style={{ minHeight: '600px' }}
    />
  )
}
