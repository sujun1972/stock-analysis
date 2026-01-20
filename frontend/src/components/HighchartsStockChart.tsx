'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import Highcharts from 'highcharts/highstock'
import HighchartsReact from 'highcharts-react-official'
import { apiClient } from '@/lib/api-client'

interface ChartData {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  MA5?: number | null
  MA20?: number | null
  MA60?: number | null
  MACD?: number | null
  MACD_SIGNAL?: number | null
  MACD_HIST?: number | null
  KDJ_K?: number | null
  KDJ_D?: number | null
  KDJ_J?: number | null
}

interface HighchartsStockChartProps {
  data: ChartData[]
  stockCode: string
}

export default function HighchartsStockChart({ data, stockCode }: HighchartsStockChartProps) {
  const chartRef = useRef<HighchartsReact.RefObject>(null)
  const [allData, setAllData] = useState<ChartData[]>(data)
  const [isLoading, setIsLoading] = useState(false)
  const loadedRangeRef = useRef({ min: 0, max: 0 })

  // 初始化数据范围
  useEffect(() => {
    if (data.length > 0) {
      const sortedInitial = [...data].sort((a, b) =>
        new Date(a.date).getTime() - new Date(b.date).getTime()
      )
      const minTime = new Date(sortedInitial[0].date).getTime()
      const maxTime = new Date(sortedInitial[sortedInitial.length - 1].date).getTime()
      loadedRangeRef.current = { min: minTime, max: maxTime }
      setAllData(sortedInitial)
    }
  }, [data])

  // 动态加载更多历史数据
  const loadMoreData = useCallback(async (min: number, max: number) => {
    if (isLoading) return

    const currentMin = loadedRangeRef.current.min

    // 如果用户缩放到的范围接近已加载的最早数据，加载更多历史数据
    const threshold = (loadedRangeRef.current.max - loadedRangeRef.current.min) * 0.1
    if (min < currentMin + threshold) {
      setIsLoading(true)

      try {
        // 加载全部历史数据
        const newData = await apiClient.getFeatures(stockCode, {
          feature_type: 'technical'
        }) as unknown as ChartData[]
        const sortedNew = [...newData].sort((a, b) =>
          new Date(a.date).getTime() - new Date(b.date).getTime()
        )

        // 合并新旧数据，去重
        const combined = [...sortedNew, ...allData]
        const uniqueData = Array.from(
          new Map(combined.map(item => [item.date, item])).values()
        ).sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime())

        setAllData(uniqueData)

        // 更新已加载的范围
        if (uniqueData.length > 0) {
          loadedRangeRef.current.min = new Date(uniqueData[0].date).getTime()
        }
      } catch (error) {
        console.error('加载历史数据失败:', error)
      } finally {
        setIsLoading(false)
      }
    }
  }, [stockCode, allData, isLoading])

  // Highcharts需要按时间升序排列（从旧到新）
  const sortedData = allData

  // 准备数据
  const ohlc = sortedData.map(d => [new Date(d.date).getTime(), d.open, d.high, d.low, d.close])
  const volume = sortedData.map(d => [new Date(d.date).getTime(), d.volume])
  const ma5 = sortedData.filter(d => d.MA5).map(d => [new Date(d.date).getTime(), d.MA5])
  const ma20 = sortedData.filter(d => d.MA20).map(d => [new Date(d.date).getTime(), d.MA20])
  const ma60 = sortedData.filter(d => d.MA60).map(d => [new Date(d.date).getTime(), d.MA60])

  const macd = sortedData.filter(d => d.MACD).map(d => [new Date(d.date).getTime(), d.MACD])
  const macdSignal = sortedData.filter(d => d.MACD_SIGNAL).map(d => [new Date(d.date).getTime(), d.MACD_SIGNAL])
  const macdHist = sortedData.filter(d => d.MACD_HIST).map(d => [new Date(d.date).getTime(), d.MACD_HIST])

  const kdjK = sortedData.filter(d => d.KDJ_K).map(d => [new Date(d.date).getTime(), d.KDJ_K])
  const kdjD = sortedData.filter(d => d.KDJ_D).map(d => [new Date(d.date).getTime(), d.KDJ_D])
  const kdjJ = sortedData.filter(d => d.KDJ_J).map(d => [new Date(d.date).getTime(), d.KDJ_J])

  const options: Highcharts.Options = {
    chart: {
      height: 900,
      events: {
        load: function() {
          if (isLoading) {
            this.showLoading('加载历史数据...')
          }
        }
      }
    },
    rangeSelector: {
      selected: 1,
      buttons: [{
        type: 'month',
        count: 1,
        text: '1月'
      }, {
        type: 'month',
        count: 3,
        text: '3月'
      }, {
        type: 'month',
        count: 6,
        text: '6月'
      }, {
        type: 'year',
        count: 1,
        text: '1年'
      }, {
        type: 'all',
        text: '全部'
      }]
    },
    title: {
      text: ''
    },
    xAxis: {
      events: {
        afterSetExtremes: function(e: any) {
          // 当用户缩放或平移时间轴时触发
          loadMoreData(e.min, e.max)
        }
      }
    },
    yAxis: [
      {
        // 主图：价格
        labels: {
          align: 'right',
          x: -3
        },
        title: {
          text: '价格'
        },
        height: '50%',
        lineWidth: 2,
        resize: {
          enabled: true
        }
      },
      {
        // 成交量
        labels: {
          align: 'right',
          x: -3
        },
        title: {
          text: '成交量'
        },
        top: '52%',
        height: '15%',
        offset: 0,
        lineWidth: 2
      },
      {
        // MACD
        labels: {
          align: 'right',
          x: -3
        },
        title: {
          text: 'MACD'
        },
        top: '69%',
        height: '15%',
        offset: 0,
        lineWidth: 2
      },
      {
        // KDJ
        labels: {
          align: 'right',
          x: -3
        },
        title: {
          text: 'KDJ'
        },
        top: '86%',
        height: '14%',
        offset: 0,
        lineWidth: 2
      }
    ],
    tooltip: {
      split: true,
      shared: true
    },
    series: [
      {
        type: 'candlestick',
        name: 'K线',
        data: ohlc,
        yAxis: 0,
        color: '#22c55e',
        upColor: '#ef4444',
        lineColor: '#22c55e',
        upLineColor: '#ef4444',
      },
      {
        type: 'line',
        name: 'MA5',
        data: ma5,
        yAxis: 0,
        color: '#f59e0b',
        lineWidth: 1,
      },
      {
        type: 'line',
        name: 'MA20',
        data: ma20,
        yAxis: 0,
        color: '#10b981',
        lineWidth: 1,
      },
      {
        type: 'line',
        name: 'MA60',
        data: ma60,
        yAxis: 0,
        color: '#8b5cf6',
        lineWidth: 1,
      },
      {
        type: 'column',
        name: '成交量',
        data: volume,
        yAxis: 1,
        color: '#3b82f680',
      },
      {
        type: 'column',
        name: 'MACD柱',
        data: macdHist,
        yAxis: 2,
        color: '#ef4444',
        negativeColor: '#22c55e',
      },
      {
        type: 'line',
        name: 'DIF',
        data: macd,
        yAxis: 2,
        color: '#ef4444',
        lineWidth: 1,
      },
      {
        type: 'line',
        name: 'DEA',
        data: macdSignal,
        yAxis: 2,
        color: '#3b82f6',
        lineWidth: 1,
      },
      {
        type: 'line',
        name: 'K',
        data: kdjK,
        yAxis: 3,
        color: '#3b82f6',
        lineWidth: 1,
      },
      {
        type: 'line',
        name: 'D',
        data: kdjD,
        yAxis: 3,
        color: '#f59e0b',
        lineWidth: 1,
      },
      {
        type: 'line',
        name: 'J',
        data: kdjJ,
        yAxis: 3,
        color: '#8b5cf6',
        lineWidth: 1,
      },
    ],
  }

  return (
    <div className="w-full">
      <HighchartsReact
        highcharts={Highcharts}
        constructorType={'stockChart'}
        options={options}
        ref={chartRef}
      />
    </div>
  )
}
