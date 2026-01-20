'use client'

import { useEffect, useRef } from 'react'
import { createChart, IChartApi, CrosshairMode, Time } from 'lightweight-charts'

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

interface TradingViewMultiChartProps {
  data: ChartData[]
}

export default function TradingViewMultiChart({ data }: TradingViewMultiChartProps) {
  const mainChartRef = useRef<HTMLDivElement>(null)
  const volumeChartRef = useRef<HTMLDivElement>(null)
  const macdChartRef = useRef<HTMLDivElement>(null)
  const kdjChartRef = useRef<HTMLDivElement>(null)

  const chartsRef = useRef<IChartApi[]>([])
  const isSyncingRef = useRef(false)

  useEffect(() => {
    if (!mainChartRef.current || data.length === 0) return

    // 清理旧图表
    chartsRef.current.forEach(chart => chart.remove())
    chartsRef.current = []

    const chartOptions = {
      layout: {
        background: { color: '#ffffff' },
        textColor: '#333',
      },
      grid: {
        vertLines: { color: '#f0f0f0' },
        horzLines: { color: '#f0f0f0' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
      },
      rightPriceScale: {
        borderColor: '#d1d4dc',
      },
      timeScale: {
        borderColor: '#d1d4dc',
        timeVisible: true,
        secondsVisible: false,
      },
    }

    // ========== 主图：K线 + 均线 ==========
    if (mainChartRef.current) {
      const mainChart = createChart(mainChartRef.current, {
        ...chartOptions,
        width: mainChartRef.current.clientWidth,
        height: 400,
      })
      chartsRef.current.push(mainChart)

      // K线数据
      const candlestickData = data.map(d => ({
        time: (new Date(d.date).getTime() / 1000) as Time,
        open: d.open,
        high: d.high,
        low: d.low,
        close: d.close,
      }))

      const candlestickSeries = mainChart.addCandlestickSeries({
        upColor: '#ef4444',
        downColor: '#22c55e',
        borderUpColor: '#ef4444',
        borderDownColor: '#22c55e',
        wickUpColor: '#ef4444',
        wickDownColor: '#22c55e',
      })
      candlestickSeries.setData(candlestickData)

      // MA均线
      if (data.some(d => d.MA5)) {
        const ma5Series = mainChart.addLineSeries({
          color: '#f59e0b',
          lineWidth: 2,
          title: 'MA5',
        })
        ma5Series.setData(
          data
            .filter(d => d.MA5 !== null && d.MA5 !== undefined)
            .map(d => ({
              time: (new Date(d.date).getTime() / 1000) as Time,
              value: d.MA5!,
            }))
        )
      }

      if (data.some(d => d.MA20)) {
        const ma20Series = mainChart.addLineSeries({
          color: '#10b981',
          lineWidth: 2,
          title: 'MA20',
        })
        ma20Series.setData(
          data
            .filter(d => d.MA20 !== null && d.MA20 !== undefined)
            .map(d => ({
              time: (new Date(d.date).getTime() / 1000) as Time,
              value: d.MA20!,
            }))
        )
      }

      if (data.some(d => d.MA60)) {
        const ma60Series = mainChart.addLineSeries({
          color: '#8b5cf6',
          lineWidth: 2,
          title: 'MA60',
        })
        ma60Series.setData(
          data
            .filter(d => d.MA60 !== null && d.MA60 !== undefined)
            .map(d => ({
              time: (new Date(d.date).getTime() / 1000) as Time,
              value: d.MA60!,
            }))
        )
      }

      mainChart.timeScale().fitContent()
    }

    // ========== 副图1：成交量 ==========
    if (volumeChartRef.current) {
      const volumeChart = createChart(volumeChartRef.current, {
        ...chartOptions,
        width: volumeChartRef.current.clientWidth,
        height: 150,
      })
      chartsRef.current.push(volumeChart)

      const volumeData = data.map(d => ({
        time: (new Date(d.date).getTime() / 1000) as Time,
        value: d.volume,
        color: d.close >= d.open ? '#ef444440' : '#22c55e40',
      }))

      const volumeSeries = volumeChart.addHistogramSeries({
        color: '#3b82f6',
        priceFormat: {
          type: 'volume',
        },
      })
      volumeSeries.setData(volumeData)
      volumeChart.timeScale().fitContent()
    }

    // ========== 副图2：MACD ==========
    if (macdChartRef.current && data.some(d => d.MACD !== null && d.MACD !== undefined)) {
      const macdChart = createChart(macdChartRef.current, {
        ...chartOptions,
        width: macdChartRef.current.clientWidth,
        height: 180,
      })
      chartsRef.current.push(macdChart)

      // MACD柱状图
      if (data.some(d => d.MACD_HIST)) {
        const macdHistData = data
          .filter(d => d.MACD_HIST !== null && d.MACD_HIST !== undefined)
          .map(d => ({
            time: (new Date(d.date).getTime() / 1000) as Time,
            value: d.MACD_HIST!,
            color: d.MACD_HIST! >= 0 ? '#ef444480' : '#22c55e80',
          }))

        const macdHistSeries = macdChart.addHistogramSeries({
          priceFormat: {
            type: 'price',
            precision: 4,
            minMove: 0.0001,
          },
        })
        macdHistSeries.setData(macdHistData)
      }

      // DIF线
      if (data.some(d => d.MACD)) {
        const macdSeries = macdChart.addLineSeries({
          color: '#ef4444',
          lineWidth: 2,
          title: 'DIF',
        })
        macdSeries.setData(
          data
            .filter(d => d.MACD !== null && d.MACD !== undefined)
            .map(d => ({
              time: (new Date(d.date).getTime() / 1000) as Time,
              value: d.MACD!,
            }))
        )
      }

      // DEA线
      if (data.some(d => d.MACD_SIGNAL)) {
        const signalSeries = macdChart.addLineSeries({
          color: '#3b82f6',
          lineWidth: 2,
          title: 'DEA',
        })
        signalSeries.setData(
          data
            .filter(d => d.MACD_SIGNAL !== null && d.MACD_SIGNAL !== undefined)
            .map(d => ({
              time: (new Date(d.date).getTime() / 1000) as Time,
              value: d.MACD_SIGNAL!,
            }))
        )
      }

      macdChart.timeScale().fitContent()
    }

    // ========== 副图3：KDJ ==========
    if (kdjChartRef.current && data.some(d => d.KDJ_K !== null && d.KDJ_K !== undefined)) {
      const kdjChart = createChart(kdjChartRef.current, {
        ...chartOptions,
        width: kdjChartRef.current.clientWidth,
        height: 180,
      })
      chartsRef.current.push(kdjChart)

      // K线
      if (data.some(d => d.KDJ_K)) {
        const kSeries = kdjChart.addLineSeries({
          color: '#3b82f6',
          lineWidth: 2,
          title: 'K',
        })
        kSeries.setData(
          data
            .filter(d => d.KDJ_K !== null && d.KDJ_K !== undefined)
            .map(d => ({
              time: (new Date(d.date).getTime() / 1000) as Time,
              value: d.KDJ_K!,
            }))
        )
      }

      // D线
      if (data.some(d => d.KDJ_D)) {
        const dSeries = kdjChart.addLineSeries({
          color: '#f59e0b',
          lineWidth: 2,
          title: 'D',
        })
        dSeries.setData(
          data
            .filter(d => d.KDJ_D !== null && d.KDJ_D !== undefined)
            .map(d => ({
              time: (new Date(d.date).getTime() / 1000) as Time,
              value: d.KDJ_D!,
            }))
        )
      }

      // J线
      if (data.some(d => d.KDJ_J)) {
        const jSeries = kdjChart.addLineSeries({
          color: '#8b5cf6',
          lineWidth: 2,
          title: 'J',
        })
        jSeries.setData(
          data
            .filter(d => d.KDJ_J !== null && d.KDJ_J !== undefined)
            .map(d => ({
              time: (new Date(d.date).getTime() / 1000) as Time,
              value: d.KDJ_J!,
            }))
        )
      }

      kdjChart.timeScale().fitContent()
    }

    // 响应式调整
    const handleResize = () => {
      chartsRef.current.forEach((chart, index) => {
        const container = [mainChartRef, volumeChartRef, macdChartRef, kdjChartRef][index]
        if (container?.current) {
          chart.applyOptions({ width: container.current.clientWidth })
        }
      })
    }
    window.addEventListener('resize', handleResize)

    // 同步所有图表的时间轴（缩放和平移）
    const syncCharts = (sourceChart: IChartApi) => {
      // 防止循环调用
      if (isSyncingRef.current) return

      isSyncingRef.current = true

      const timeScale = sourceChart.timeScale()
      const visibleRange = timeScale.getVisibleRange()

      if (visibleRange) {
        chartsRef.current.forEach(chart => {
          if (chart !== sourceChart) {
            chart.timeScale().setVisibleRange(visibleRange)
          }
        })
      }

      // 使用 requestAnimationFrame 确保在下一帧重置标志
      requestAnimationFrame(() => {
        isSyncingRef.current = false
      })
    }

    // 为每个图表添加时间轴变化监听
    chartsRef.current.forEach(chart => {
      chart.timeScale().subscribeVisibleTimeRangeChange(() => {
        syncCharts(chart)
      })
    })

    return () => {
      window.removeEventListener('resize', handleResize)
      chartsRef.current.forEach(chart => chart.remove())
    }
  }, [data])

  return (
    <div className="space-y-0">
      {/* 主图：K线 + 均线 */}
      <div className="w-full">
        <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 px-2">
          价格走势（K线图）
        </div>
        <div ref={mainChartRef} />
      </div>

      {/* 副图1：成交量 */}
      <div className="w-full border-t border-gray-200 dark:border-gray-700 mt-1">
        <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 px-2 pt-2">
          成交量
        </div>
        <div ref={volumeChartRef} />
      </div>

      {/* 副图2：MACD */}
      {data.some(d => d.MACD !== null && d.MACD !== undefined) && (
        <div className="w-full border-t border-gray-200 dark:border-gray-700 mt-1">
          <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 px-2 pt-2">
            MACD指标
          </div>
          <div ref={macdChartRef} />
        </div>
      )}

      {/* 副图3：KDJ */}
      {data.some(d => d.KDJ_K !== null && d.KDJ_K !== undefined) && (
        <div className="w-full border-t border-gray-200 dark:border-gray-700 mt-1">
          <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 px-2 pt-2">
            KDJ指标
          </div>
          <div ref={kdjChartRef} />
        </div>
      )}
    </div>
  )
}
