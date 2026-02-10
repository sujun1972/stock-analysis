/**
 * 回测结果展示组件
 * 展示回测的关键指标和结果
 */

'use client'

import { memo, useEffect, useRef } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import dynamic from 'next/dynamic'
import * as echarts from 'echarts'

// 动态导入图表组件
const PerformanceMetrics = dynamic(() => import('@/components/PerformanceMetrics'), {
  ssr: false
})

interface BacktestResultViewProps {
  result: any
}

const BacktestResultView = memo(function BacktestResultView({
  result
}: BacktestResultViewProps) {
  if (!result) return null

  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstanceRef = useRef<echarts.ECharts | null>(null)

  // 权益曲线图表
  useEffect(() => {
    if (!chartRef.current || !result.equity_curve || result.equity_curve.length === 0) return

    // 初始化图表
    if (!chartInstanceRef.current) {
      chartInstanceRef.current = echarts.init(chartRef.current)
    }

    const chart = chartInstanceRef.current

    // 准备数据
    const dates = result.equity_curve.map((item: any) => {
      if (item.date) {
        // 格式化日期: 2024-01-01 -> 1/2 (X轴显示用)
        const date = new Date(item.date)
        return `${date.getMonth() + 1}/${date.getDate()}`
      }
      return ''
    })

    // 保存完整日期信息用于Tooltip
    const fullDates = result.equity_curve.map((item: any) => {
      if (item.date) {
        const date = new Date(item.date)
        const year = date.getFullYear()
        const month = String(date.getMonth() + 1).padStart(2, '0')
        const day = String(date.getDate()).padStart(2, '0')
        return `${year}-${month}-${day}`
      }
      return ''
    })

    const totalData = result.equity_curve.map((item: any) => item.total || 0)
    const cashData = result.equity_curve.map((item: any) => item.cash || 0)
    const holdingsData = result.equity_curve.map((item: any) => item.holdings || 0)

    // 配置图表选项
    const option: echarts.EChartsOption = {
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross'
        },
        formatter: function (params: any) {
          const dataIndex = params[0].dataIndex
          const fullDate = fullDates[dataIndex]
          const tradingDay = dataIndex + 1

          let result = `<div style="font-weight:bold; margin-bottom:5px;">${fullDate} (第 ${tradingDay} 个交易日)</div>`
          params.forEach((param: any) => {
            const value = Number(param.value).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
            result += `
              <div style="display:flex; justify-content:space-between; align-items:center; margin-top:3px;">
                <span>
                  <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${param.color};margin-right:5px;"></span>
                  ${param.seriesName}:
                </span>
                <span style="font-weight:bold; margin-left:10px;">
                  ¥${value}
                </span>
              </div>
            `
          })
          return result
        }
      },
      legend: {
        data: ['总资产', '持仓市值', '现金'],
        top: 10
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '60px',
        top: 50,
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: dates,
        name: '日期',
        nameLocation: 'middle',
        nameGap: 35,
        axisLabel: {
          rotate: 45,
          interval: 'auto'
        },
        axisPointer: {
          label: {
            formatter: function (params: any) {
              // X轴十字准星标签显示完整日期
              // params.value 是X轴的显示值(如 "1/2"),需要找到对应的索引
              const displayValue = params.value
              const dataIndex = dates.findIndex((d: string) => d === displayValue)
              if (dataIndex !== -1 && fullDates[dataIndex]) {
                return fullDates[dataIndex]
              }
              return displayValue
            }
          }
        }
      },
      yAxis: {
        type: 'value',
        name: '资产(元)',
        axisLabel: {
          formatter: (value: number) => {
            if (value >= 1000000) {
              return (value / 1000000).toFixed(1) + 'M'
            } else if (value >= 1000) {
              return (value / 1000).toFixed(1) + 'K'
            }
            return value.toFixed(0)
          }
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
          name: '总资产',
          type: 'line',
          data: totalData,
          smooth: true,
          lineStyle: {
            width: 2,
            color: '#3b82f6'
          },
          itemStyle: {
            color: '#3b82f6'
          },
          showSymbol: false
        },
        {
          name: '持仓市值',
          type: 'line',
          data: holdingsData,
          smooth: true,
          lineStyle: {
            width: 1.5,
            color: '#10b981'
          },
          itemStyle: {
            color: '#10b981'
          },
          showSymbol: false
        },
        {
          name: '现金',
          type: 'line',
          data: cashData,
          smooth: true,
          lineStyle: {
            width: 1.5,
            color: '#f59e0b'
          },
          itemStyle: {
            color: '#f59e0b'
          },
          showSymbol: false
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
  }, [result.equity_curve])

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
    <div className="space-y-6">
      {/* 策略信息卡片 */}
      <Card className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 border-blue-200 dark:border-blue-800">
        <CardHeader>
          <CardTitle>{result.strategy_info?.display_name || result.strategy_name || '回测结果'}</CardTitle>
          <CardDescription>
            {result.backtest_params?.stock_pool && `股票池: ${result.backtest_params.stock_pool.length} 只 | `}
            {result.backtest_params?.start_date && result.backtest_params?.end_date &&
              `周期: ${result.backtest_params.start_date} 至 ${result.backtest_params.end_date}`}
            {result.metrics?.total_trades !== undefined && ` | 交易次数: ${result.metrics.total_trades}`}
          </CardDescription>
        </CardHeader>
      </Card>

      {/* 绩效指标 */}
      {result.metrics && (
        <PerformanceMetrics
          metrics={result.metrics}
          mode={result.mode || 'single'}
        />
      )}

      {/* 权益曲线图表 */}
      {result.equity_curve && result.equity_curve.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>权益曲线</CardTitle>
            <CardDescription>总资产、现金和持仓市值的变化</CardDescription>
          </CardHeader>
          <CardContent>
            <div
              ref={chartRef}
              style={{ width: '100%', height: '400px' }}
            />
          </CardContent>
        </Card>
      )}

      {/* 交易明细（如果有） */}
      {result.trades && result.trades.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>交易明细 (最近 {Math.min(result.trades.length, 20)} 笔)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                      日期
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                      操作
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                      价格
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                      数量
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase">
                      金额
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {result.trades.slice(0, 20).map((trade: any, idx: number) => (
                    <tr key={idx}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                        {trade.date}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className={`px-2 py-1 rounded ${
                          trade.type === 'buy'
                            ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300'
                            : 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300'
                        }`}>
                          {trade.type === 'buy' ? '买入' : '卖出'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                        ¥{trade.price.toFixed(2)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                        {trade.shares}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-gray-100">
                        ¥{trade.amount.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {result.total_trades > 20 && (
              <p className="mt-4 text-sm text-muted-foreground text-center">
                共 {result.total_trades} 笔交易，显示最近 20 笔
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
})

BacktestResultView.displayName = 'BacktestResultView'

export default BacktestResultView
