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

interface EquityCurvePoint {
  date: string
  total: number
  cash?: number
  holdings?: number
}

interface BacktestKLineChartProps {
  data: KLineData[]
  signalPoints: SignalPoints
  stockCode: string
  equityCurve?: EquityCurvePoint[]  // 可选的权益曲线数据
}

export default function BacktestKLineChart({
  data,
  signalPoints,
  stockCode,
  equityCurve
}: BacktestKLineChartProps) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstanceRef = useRef<echarts.ECharts | null>(null)

  // 检查是否有权益曲线数据
  const hasEquityData = equityCurve && equityCurve.length > 0

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

    // 权益曲线数据（如果提供）- 归一化到价格范围
    let normalizedEquityData: (number | null)[] = []
    // 保存原始权益数据用于tooltip显示
    const equityDataForTooltip: (EquityCurvePoint | null)[] = []

    if (hasEquityData) {
      // 创建日期到权益的映射
      const equityMap = new Map<string, EquityCurvePoint>()
      equityCurve!.forEach(point => {
        equityMap.set(point.date, point)
      })

      // 提取原始权益数据
      const rawEquityData = dates.map(date => {
        const equity = equityMap.get(date)
        equityDataForTooltip.push(equity || null)
        return equity ? equity.total : null
      })

      // 检查是否有有效数据
      const validEquityData = rawEquityData.filter(v => v !== null && v > 0) as number[]

      if (validEquityData.length > 0) {
        // 计算权益的最小值和最大值
        const equityMin = Math.min(...validEquityData)
        const equityMax = Math.max(...validEquityData)

        // 计算价格的最小值和最大值（用于归一化）
        const allPrices = sortedData.flatMap(d => [d.open, d.high, d.low, d.close])
        const priceMin = Math.min(...allPrices)
        const priceMax = Math.max(...allPrices)

        // 将权益数据归一化到价格范围
        normalizedEquityData = rawEquityData.map(equity => {
          if (equity === null || equity === 0) return null
          // 归一化公式：映射到价格范围的80%-120%区间（留出一些边距）
          const normalized = priceMin + (equity - equityMin) / (equityMax - equityMin) * (priceMax - priceMin) * 0.4 + (priceMax - priceMin) * 0.3
          return normalized
        })
      }
    }

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
        data: hasEquityData
          ? ['K线', 'MA5', 'MA20', 'MA60', '权益曲线', '成交量']
          : ['K线', 'MA5', 'MA20', 'MA60', '成交量'],
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
        },
        formatter: (params: any) => {
          if (!Array.isArray(params) || params.length === 0) return ''

          const dataIndex = params[0].dataIndex
          const date = dates[dataIndex]

          let result = `<div style="font-weight:bold; margin-bottom:8px;">${date}</div>`

          params.forEach((param: any) => {
            const seriesName = param.seriesName

            // 特殊处理权益曲线，显示真实资产数据
            if (seriesName === '权益曲线' && equityDataForTooltip[dataIndex]) {
              const equity = equityDataForTooltip[dataIndex]!
              result += `<div style="margin-top:8px; padding-top:8px; border-top:1px solid #eee;">
                <div style="font-weight:bold; color:#ec4899; margin-bottom:4px;">
                  <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:#ec4899;margin-right:5px;"></span>
                  权益曲线
                </div>
                <div style="margin-left:15px;">
                  <div>总资产: ¥${equity.total.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                  <div>持仓市值: ¥${(equity.holdings || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                  <div>现金: ¥${(equity.cash || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</div>
                </div>
              </div>`
            }
            // K线数据
            else if (seriesName === 'K线' && Array.isArray(param.value)) {
              const [open, close, low, high] = param.value
              result += `<div style="margin-top:4px;">
                <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${param.color};margin-right:5px;"></span>
                ${seriesName}<br/>
                <div style="margin-left:15px;">
                  <div>开盘: ${open.toFixed(2)}</div>
                  <div>收盘: ${close.toFixed(2)}</div>
                  <div>最低: ${low.toFixed(2)}</div>
                  <div>最高: ${high.toFixed(2)}</div>
                </div>
              </div>`
            }
            // MA线和成交量
            else if (seriesName !== '权益曲线' && param.value !== '-') {
              const value = typeof param.value === 'number'
                ? param.value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                : param.value
              result += `<div style="margin-top:2px;">
                <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${param.color};margin-right:5px;"></span>
                ${seriesName}: ${value}
              </div>`
            }
          })

          return result
        }
      },
      series: ([
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
        // 权益曲线（归一化后重叠在K线图上）
        ...(hasEquityData ? [
          {
            name: '权益曲线',
            type: 'line',
            data: normalizedEquityData,
            xAxisIndex: 0,
            yAxisIndex: 0,
            smooth: true,
            lineStyle: {
              width: 2.5,
              color: '#ec4899',
              type: 'solid'
            },
            itemStyle: {
              color: '#ec4899'
            },
            showSymbol: false,
            z: 10  // 确保在K线上层显示
          }
        ] : []),
        // 成交量
        {
          name: '成交量',
          type: 'bar',
          data: volumeData,
          xAxisIndex: 1,
          yAxisIndex: 1
        }
      ] as any)
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
  }, [data, signalPoints, stockCode, equityCurve])

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
      {/* 权益曲线提示 */}
      {hasEquityData && (
        <div className="mb-2 px-3 py-2 bg-pink-50 dark:bg-pink-900/20 rounded-md border border-pink-200 dark:border-pink-800">
          <p className="text-xs text-pink-800 dark:text-pink-300">
            💡 粉色线为权益曲线（已归一化到价格范围），可直观看到资产变化与股价走势的关系
          </p>
        </div>
      )}

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
