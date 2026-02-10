'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import * as echarts from 'echarts'
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
  RSI6?: number | null
  RSI12?: number | null
  RSI24?: number | null
  BOLL_UPPER?: number | null
  BOLL_MIDDLE?: number | null
  BOLL_LOWER?: number | null
}

interface EChartsStockChartProps {
  data: ChartData[]
  stockCode: string
}

export default function EChartsStockChart({ data, stockCode }: EChartsStockChartProps) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstanceRef = useRef<echarts.ECharts | null>(null)
  const [allData, setAllData] = useState<ChartData[]>(data)
  const [isLoading, setIsLoading] = useState(false)
  const hasLoadedAllDataRef = useRef(false)  // 标记是否已加载全部数据
  const currentDataZoomRef = useRef<{ start: number; end: number } | null>(null)  // 保存当前缩放位置

  // 指标显示状态（默认只显示成交量和MACD，从localStorage读取保存的设置）
  const [visibleIndicators, setVisibleIndicators] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('chart_visible_indicators')
      if (saved) {
        try {
          return JSON.parse(saved)
        } catch (e) {
          console.error('Failed to parse saved indicators:', e)
        }
      }
    }
    return {
      volume: true,   // 成交量 - 默认开启
      macd: true,     // MACD - 默认开启
      kdj: false,     // KDJ - 默认关闭
      rsi: false,     // RSI - 默认关闭
      boll: false     // BOLL - 默认关闭
    }
  })

  // 保存指标设置到 localStorage
  useEffect(() => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('chart_visible_indicators', JSON.stringify(visibleIndicators))
    }
  }, [visibleIndicators])

  // 设置对话框显示状态
  const [showSettings, setShowSettings] = useState(false)

  /**
   * 格式化成交量：将大数值转换为中国习惯的万/亿单位
   * @param value - 原始成交量数值
   * @returns 格式化后的字符串（如 "1.23亿" 或 "5678万"）
   */
  const formatVolume = (value: number): string => {
    if (value >= 100000000) {
      return (value / 100000000).toFixed(2) + '亿'
    } else if (value >= 10000) {
      return (value / 10000).toFixed(2) + '万'
    }
    return value.toFixed(0)
  }

  /**
   * 去除日期字符串中的时间部分
   * @param dateStr - 日期字符串（如 "2025-01-23" 或 "2025-01-23 00:00:00"）
   * @returns 只包含日期的字符串（如 "2025-01-23"）
   */
  const removeDateTimePart = useCallback((dateStr: string): string => {
    return dateStr.includes(' ') ? dateStr.split(' ')[0] : dateStr
  }, [])

  /**
   * 格式化日期：添加星期信息
   * @param dateStr - 日期字符串（如 "2025-01-23" 或 "2025-01-23 00:00:00"）
   * @returns 格式化后的日期字符串（如 "2025年01月23日 星期四"）
   */
  const formatDateWithWeekday = useCallback((dateStr: string): string => {
    const dateOnly = removeDateTimePart(dateStr)
    const date = new Date(dateOnly)
    const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    const weekday = weekdays[date.getDay()]
    return `${year}年${month}月${day}日 ${weekday}`
  }, [removeDateTimePart])

  // 检查数据是否可用
  // RSI支持多周期：RSI6, RSI12, RSI24
  const hasRSI = allData.some(d =>
    (d.RSI6 !== null && d.RSI6 !== undefined) ||
    (d.RSI12 !== null && d.RSI12 !== undefined) ||
    (d.RSI24 !== null && d.RSI24 !== undefined)
  )
  const hasBOLL = allData.some(d => d.BOLL_UPPER !== null && d.BOLL_UPPER !== undefined)
  const hasKDJ = allData.some(d => d.KDJ_K !== null && d.KDJ_K !== undefined)
  const hasMACD = allData.some(d => d.MACD !== null && d.MACD !== undefined)

  // 计算启用的副图数量 (用于动态计算图表高度)
  const subPanelCount = [
    visibleIndicators.volume,
    visibleIndicators.macd && hasMACD,
    visibleIndicators.kdj && hasKDJ,
    visibleIndicators.rsi && hasRSI
  ].filter(Boolean).length

  // 图表布局配置常量（像素）
  const MAIN_CHART_HEIGHT = 400    // 主图（K线）高度
  const VOLUME_PANEL_HEIGHT = 180  // 成交量副图高度
  const SUB_PANEL_HEIGHT = 150     // 其他副图（MACD/KDJ/RSI）高度
  const PANEL_GAP = 0              // 面板间隔
  const LEGEND_HEIGHT = 20         // 单个图例高度
  const LEGEND_PADDING = 10        // 图例上下padding
  const ZOOM_HEIGHT = 60           // DataZoom 滑块高度
  const TOP_PADDING = 10           // 顶部padding
  const BOTTOM_PADDING = 10        // 底部padding

  // 动态计算图表总高度（单位：像素）
  const volumeHeight = visibleIndicators.volume
    ? (LEGEND_PADDING + LEGEND_HEIGHT + LEGEND_PADDING + VOLUME_PANEL_HEIGHT + PANEL_GAP)
    : 0
  const otherPanelsCount = subPanelCount - (visibleIndicators.volume ? 1 : 0)
  const otherPanelsHeight = otherPanelsCount * (LEGEND_PADDING + LEGEND_HEIGHT + LEGEND_PADDING + SUB_PANEL_HEIGHT + PANEL_GAP)

  const chartHeight = TOP_PADDING + 30 + MAIN_CHART_HEIGHT +
                     (subPanelCount > 0 ? PANEL_GAP + LEGEND_PADDING : 0) +
                     volumeHeight +
                     otherPanelsHeight +
                     ZOOM_HEIGHT + BOTTOM_PADDING

  // 初始化数据
  useEffect(() => {
    if (data.length > 0) {
      const sortedInitial = [...data].sort((a, b) =>
        new Date(a.date).getTime() - new Date(b.date).getTime()
      )
      setAllData(sortedInitial)
      hasLoadedAllDataRef.current = false  // 重置加载标记
    }
  }, [data, stockCode])

  /**
   * 懒加载更多历史数据
   * 使用日期分页策略：当用户缩放到数据最早位置时，自动加载更早的数据
   *
   * @param startValue - 当前可见区域的起始索引
   * @param endValue - 当前可见区域的结束索引
   */
  const loadMoreData = useCallback(async (startValue: number, endValue: number) => {
    // 防止重复加载：已加载全部数据或正在加载中
    if (hasLoadedAllDataRef.current || isLoading) return

    const totalLength = allData.length
    if (totalLength === 0) return

    // 当用户缩放到数据的前20%位置时触发懒加载
    const threshold = Math.floor(totalLength * 0.2)
    if (startValue < threshold) {
      setIsLoading(true)

      // 保存当前视图位置，避免加载后图表跳转
      if (chartInstanceRef.current) {
        const option = chartInstanceRef.current.getOption() as any
        if (option.dataZoom && option.dataZoom[0]) {
          currentDataZoomRef.current = {
            start: option.dataZoom[0].start,
            end: option.dataZoom[0].end
          }
        }
      }

      try {
        // 计算请求参数：获取当前最早日期之前的数据
        const earliestDate = allData[0]?.date
        if (!earliestDate) return

        const endDate = new Date(earliestDate)
        endDate.setDate(endDate.getDate() - 1)
        const endDateStr = endDate.toISOString().split('T')[0]

        // 请求更早的500条数据
        const response = await apiClient.getFeatures(stockCode, {
          end_date: endDateStr,
          limit: 500
        })

        // 合并新旧数据并按日期排序
        if (response.data && response.data.length > 0) {
          const newChartData = response.data as unknown as ChartData[]
          const mergedData = [...newChartData, ...allData]
          const sortedData = mergedData.sort((a, b) =>
            new Date(a.date).getTime() - new Date(b.date).getTime()
          )
          setAllData(sortedData)
        }

        // 更新加载状态标记
        if (!response.has_more) {
          hasLoadedAllDataRef.current = true
        }
      } catch (error) {
        console.error('Failed to load more historical data:', error)
      } finally {
        setIsLoading(false)
      }
    }
  }, [stockCode, allData, isLoading])

  useEffect(() => {
    if (!chartRef.current || allData.length === 0) return

    // 初始化或获取图表实例
    if (!chartInstanceRef.current) {
      chartInstanceRef.current = echarts.init(chartRef.current)
    }

    const chart = chartInstanceRef.current
    if (!chart) return

    // 图表容器高度变化时，需要先resize
    chart.resize()

    // 准备数据（ECharts需要升序排列）
    const sortedData = [...allData].sort((a, b) =>
      new Date(a.date).getTime() - new Date(b.date).getTime()
    )

    // 提取日期和数据（格式化日期为 YYYY-MM-DD）
    const dates = sortedData.map(d => {
      const dateStr = d.date
      // 如果是 ISO 格式（包含 T），只取日期部分
      if (dateStr.includes('T')) {
        return dateStr.split('T')[0]
      }
      return dateStr
    })
    const ohlcData = sortedData.map(d => [d.open, d.close, d.low, d.high])
    const volumeData = sortedData.map((d, idx) => ({
      value: d.volume,
      itemStyle: {
        color: d.close >= d.open ? '#ef4444' : '#22c55e'
      }
    }))

    // MA线数据
    const ma5Data = sortedData.map(d => d.MA5 ?? '-')
    const ma20Data = sortedData.map(d => d.MA20 ?? '-')
    const ma60Data = sortedData.map(d => d.MA60 ?? '-')

    // MACD数据
    const macdData = sortedData.map(d => d.MACD ?? '-')
    const macdSignalData = sortedData.map(d => d.MACD_SIGNAL ?? '-')
    const macdHistData = sortedData.map((d, idx) => ({
      value: d.MACD_HIST ?? '-',
      itemStyle: {
        color: (d.MACD_HIST ?? 0) >= 0 ? '#ef4444' : '#22c55e'
      }
    }))

    // KDJ数据
    const kdjKData = sortedData.map(d => d.KDJ_K ?? '-')
    const kdjDData = sortedData.map(d => d.KDJ_D ?? '-')
    const kdjJData = sortedData.map(d => d.KDJ_J ?? '-')

    // RSI数据（优先使用RSI6，其次RSI12，最后RSI24）
    const rsiData = sortedData.map(d => d.RSI6 ?? d.RSI12 ?? d.RSI24 ?? '-')

    // BOLL数据
    const bollUpperData = sortedData.map(d => d.BOLL_UPPER ?? '-')
    const bollMiddleData = sortedData.map(d => d.BOLL_MIDDLE ?? '-')
    const bollLowerData = sortedData.map(d => d.BOLL_LOWER ?? '-')

    // 计算启用的指标数量和索引映射
    const enabledIndicators: string[] = []
    if (visibleIndicators.volume) enabledIndicators.push('volume')
    if (visibleIndicators.macd && hasMACD) enabledIndicators.push('macd')
    if (visibleIndicators.kdj && hasKDJ) enabledIndicators.push('kdj')
    if (visibleIndicators.rsi && hasRSI) enabledIndicators.push('rsi')

    // 动态构建图例（使用像素定位）
    const legends: any[] = [
      {
        data: visibleIndicators.boll && hasBOLL
          ? ['K线', 'MA5', 'MA20', 'MA60', 'BOLL上轨', 'BOLL中轨', 'BOLL下轨']
          : ['K线', 'MA5', 'MA20', 'MA60'],
        top: TOP_PADDING,
        left: 'center',
        textStyle: {
          fontWeight: 'bold'  // 加粗图例文字
        }
      }
    ]

    // 构建副图图例，计算每个图例的垂直位置
    let currentTop = TOP_PADDING + 30 + MAIN_CHART_HEIGHT + PANEL_GAP + LEGEND_PADDING

    // 成交量图例
    if (visibleIndicators.volume) {
      legends.push({
        data: ['成交量'],
        top: currentTop,
        left: 'center',
        textStyle: { fontWeight: 'bold' }
      })
      currentTop += VOLUME_PANEL_HEIGHT + PANEL_GAP + LEGEND_HEIGHT + LEGEND_PADDING * 2
    }

    // MACD图例
    if (visibleIndicators.macd && hasMACD) {
      legends.push({
        data: ['DIF', 'DEA', 'MACD'],
        top: currentTop,
        left: 'center',
        textStyle: { fontWeight: 'bold' }
      })
      currentTop += SUB_PANEL_HEIGHT + PANEL_GAP + LEGEND_HEIGHT + LEGEND_PADDING * 2
    }

    // KDJ图例
    if (visibleIndicators.kdj && hasKDJ) {
      legends.push({
        data: ['K', 'D', 'J'],
        top: currentTop,
        left: 'center',
        textStyle: { fontWeight: 'bold' }
      })
      currentTop += SUB_PANEL_HEIGHT + PANEL_GAP + LEGEND_HEIGHT + LEGEND_PADDING * 2
    }

    // RSI图例
    if (visibleIndicators.rsi && hasRSI) {
      legends.push({
        data: ['RSI'],
        top: currentTop,
        left: 'center',
        textStyle: { fontWeight: 'bold' }
      })
    }

    // 构建图表网格，定义每个面板的绘图区域
    const grids = [
      {
        left: '8%',
        right: '8%',
        top: TOP_PADDING + 30,  // 30为主图图例高度
        height: MAIN_CHART_HEIGHT
      }
    ]

    // 计算副图网格的垂直位置
    let gridTop = TOP_PADDING + 30 + MAIN_CHART_HEIGHT + PANEL_GAP + LEGEND_PADDING

    // 成交量网格
    if (visibleIndicators.volume) {
      grids.push({
        left: '8%',
        right: '8%',
        top: gridTop + LEGEND_HEIGHT + LEGEND_PADDING,
        height: VOLUME_PANEL_HEIGHT
      })
      gridTop += VOLUME_PANEL_HEIGHT + PANEL_GAP + LEGEND_HEIGHT + LEGEND_PADDING * 2
    }

    // MACD网格
    if (visibleIndicators.macd && hasMACD) {
      grids.push({
        left: '8%',
        right: '8%',
        top: gridTop + LEGEND_HEIGHT + LEGEND_PADDING,
        height: SUB_PANEL_HEIGHT
      })
      gridTop += SUB_PANEL_HEIGHT + PANEL_GAP + LEGEND_HEIGHT + LEGEND_PADDING * 2
    }

    // KDJ网格
    if (visibleIndicators.kdj && hasKDJ) {
      grids.push({
        left: '8%',
        right: '8%',
        top: gridTop + LEGEND_HEIGHT + LEGEND_PADDING,
        height: SUB_PANEL_HEIGHT
      })
      gridTop += SUB_PANEL_HEIGHT + PANEL_GAP + LEGEND_HEIGHT + LEGEND_PADDING * 2
    }

    // RSI网格
    if (visibleIndicators.rsi && hasRSI) {
      grids.push({
        left: '8%',
        right: '8%',
        top: gridTop + LEGEND_HEIGHT + LEGEND_PADDING,
        height: SUB_PANEL_HEIGHT
      })
    }

    const option: echarts.EChartsOption = {
      animation: false,
      backgroundColor: '#ffffff',
      legend: legends,
      grid: grids,
      xAxis: grids.map((_, index) => ({
        type: 'category' as const,
        data: dates,
        gridIndex: index,
        boundaryGap: false,
        axisLine: { onZero: false },
        splitLine: { show: false },
        axisLabel: {
          show: index === grids.length - 1,  // 只在最后一个面板显示x轴标签
          formatter: removeDateTimePart  // 格式化日期：只显示 YYYY-MM-DD
        },
        axisTick: { show: index === grids.length - 1 },   // 只在最后一个面板显示x轴刻度线
        axisPointer: {
          show: true,
          lineStyle: {
            color: '#999',
            width: 1,
            type: 'dashed'
          },
          label: {
            formatter: (params: any) => removeDateTimePart(params.value || '')
          }
        }
      })),
      yAxis: grids.map((_, index) => {
        const isRSIPanel = index > 0 && enabledIndicators[index - 1] === 'rsi'
        const isVolumePanel = index > 0 && enabledIndicators[index - 1] === 'volume'

        const yAxisConfig: any = {
          scale: true,
          gridIndex: index,
          ...(isRSIPanel ? { min: 0, max: 100 } : {}),  // RSI固定0-100范围
          splitArea: { show: true },
          axisPointer: {
            show: true,
            label: {
              show: true
            }
          }
        }

        // 成交量Y轴：添加万/亿单位格式化
        if (isVolumePanel) {
          yAxisConfig.axisLabel = {
            formatter: (value: number) => formatVolume(value)
          }
          yAxisConfig.axisPointer.label = {
            formatter: (params: any) => formatVolume(params.value)
          }
        }

        return yAxisConfig
      }),
      dataZoom: [
        {
          type: 'inside',
          xAxisIndex: Array.from({ length: grids.length }, (_, i) => i),
          start: currentDataZoomRef.current?.start ?? 70,
          end: currentDataZoomRef.current?.end ?? 100
        },
        {
          show: true,
          xAxisIndex: Array.from({ length: grids.length }, (_, i) => i),
          type: 'slider',
          bottom: 10,  // 固定在底部
          start: currentDataZoomRef.current?.start ?? 70,
          end: currentDataZoomRef.current?.end ?? 100
        }
      ],
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          link: [{ xAxisIndex: 'all' }],  // 让十字线在所有x轴上联动
          crossStyle: {
            color: '#999',
            width: 1,
            type: 'dashed'
          }
        },
        borderWidth: 1,
        borderColor: '#ccc',
        padding: 10,
        textStyle: {
          color: '#000'
        },
        formatter: (params: any) => {
          if (!Array.isArray(params)) return ''

          // 辅助函数：创建tooltip行项（左对齐标签，右对齐数值）
          const createTooltipRow = (marker: string, label: string, value: string, color: string) => {
            return `<div style="display: flex; justify-content: space-between; align-items: center;">
              <span>${marker}${label}:</span>
              <span style="margin-left: 20px; color: ${color};">${value}</span>
            </div>`
          }

          // 分隔线样式
          const divider = '<hr style="margin: 5px 0; border: none; border-top: 1px solid #ccc;" />'

          // 格式化日期并添加星期
          let result = `<div style="font-weight: bold; margin-bottom: 5px;">${formatDateWithWeekday(params[0].axisValue)}</div>`
          let hasKLine = false
          let klineContent = ''
          let otherContent = ''

          // 提取K线数据用于确定涨跌颜色
          let klineData: any = null
          params.forEach((param: any) => {
            if (param.seriesName === 'K线' && Array.isArray(param.value)) {
              klineData = param.value
            }
          })

          // 判断涨跌（收盘价 >= 开盘价为红色，否则为绿色）
          const isRising = klineData && klineData[2] >= klineData[1]
          const priceColor = isRising ? '#ef4444' : '#22c55e'

          params.forEach((param: any) => {
            const { seriesName, value, marker, color } = param

            if (seriesName === '成交量') {
              // 成交量：使用万/亿单位格式化
              const volumeValue = Array.isArray(value) ? value[1] : value
              otherContent += createTooltipRow(marker, seriesName, formatVolume(volumeValue), color)
            } else if (seriesName === 'K线' && Array.isArray(value)) {
              // K线数据：显示开高低收，保持2位小数，颜色与涨跌一致
              hasKLine = true
              klineContent += createTooltipRow(marker, '开', Number(value[1]).toFixed(2), priceColor)
              klineContent += createTooltipRow(marker, '收', Number(value[2]).toFixed(2), priceColor)
              klineContent += createTooltipRow(marker, '低', Number(value[3]).toFixed(2), priceColor)
              klineContent += createTooltipRow(marker, '高', Number(value[4]).toFixed(2), priceColor)
            } else {
              // 其他指标：MA、MACD、KDJ、RSI等
              const displayValue = Array.isArray(value) ? value[1] : value
              if (displayValue !== '-' && displayValue !== null && displayValue !== undefined) {
                const formattedValue = typeof displayValue === 'number' ? displayValue.toFixed(2) : displayValue
                otherContent += createTooltipRow(marker, seriesName, formattedValue, color)
              }
            }
          })

          // 组装最终结果：日期 -> K线 -> 其他指标
          if (hasKLine) {
            result += divider + klineContent
          }
          if (otherContent) {
            result += divider + otherContent
          }

          return result
        }
      },
      series: (() => {
        const series: any[] = []
        let gridIndex = 1 // 从1开始，因为主图占用gridIndex 0

        // 主图: K线 + MA + BOLL
        series.push(
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
            }
          },
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
          }
        )

        // BOLL (在主图上显示)
        if (visibleIndicators.boll && hasBOLL) {
          series.push(
            {
              name: 'BOLL上轨',
              type: 'line' as const,
              data: bollUpperData,
              xAxisIndex: 0,
              yAxisIndex: 0,
              smooth: true,
              lineStyle: {
                opacity: 0.6,
                width: 1,
                color: '#ec4899',
                type: 'dashed' as const
              },
              showSymbol: false
            },
            {
              name: 'BOLL中轨',
              type: 'line' as const,
              data: bollMiddleData,
              xAxisIndex: 0,
              yAxisIndex: 0,
              smooth: true,
              lineStyle: {
                opacity: 0.6,
                width: 1,
                color: '#06b6d4'
              },
              showSymbol: false
            },
            {
              name: 'BOLL下轨',
              type: 'line' as const,
              data: bollLowerData,
              xAxisIndex: 0,
              yAxisIndex: 0,
              smooth: true,
              lineStyle: {
                opacity: 0.6,
                width: 1,
                color: '#ec4899',
                type: 'dashed' as const
              },
              showSymbol: false
            }
          )
        }

        // 成交量
        if (visibleIndicators.volume) {
          series.push({
            name: '成交量',
            type: 'bar',
            data: volumeData,
            xAxisIndex: gridIndex,
            yAxisIndex: gridIndex
          })
          gridIndex++
        }

        // MACD
        if (visibleIndicators.macd && hasMACD) {
          series.push(
            {
              name: 'MACD',
              type: 'bar',
              data: macdHistData,
              xAxisIndex: gridIndex,
              yAxisIndex: gridIndex
            },
            {
              name: 'DIF',
              type: 'line',
              data: macdData,
              xAxisIndex: gridIndex,
              yAxisIndex: gridIndex,
              smooth: true,
              lineStyle: {
                opacity: 0.8,
                width: 1,
                color: '#ef4444'
              },
              showSymbol: false
            },
            {
              name: 'DEA',
              type: 'line',
              data: macdSignalData,
              xAxisIndex: gridIndex,
              yAxisIndex: gridIndex,
              smooth: true,
              lineStyle: {
                opacity: 0.8,
                width: 1,
                color: '#3b82f6'
              },
              showSymbol: false
            }
          )
          gridIndex++
        }

        // KDJ
        if (visibleIndicators.kdj && hasKDJ) {
          series.push(
            {
              name: 'K',
              type: 'line',
              data: kdjKData,
              xAxisIndex: gridIndex,
              yAxisIndex: gridIndex,
              smooth: true,
              lineStyle: {
                opacity: 0.8,
                width: 1,
                color: '#3b82f6'
              },
              showSymbol: false
            },
            {
              name: 'D',
              type: 'line',
              data: kdjDData,
              xAxisIndex: gridIndex,
              yAxisIndex: gridIndex,
              smooth: true,
              lineStyle: {
                opacity: 0.8,
                width: 1,
                color: '#f59e0b'
              },
              showSymbol: false
            },
            {
              name: 'J',
              type: 'line',
              data: kdjJData,
              xAxisIndex: gridIndex,
              yAxisIndex: gridIndex,
              smooth: true,
              lineStyle: {
                opacity: 0.8,
                width: 1,
                color: '#8b5cf6'
              },
              showSymbol: false
            }
          )
          gridIndex++
        }

        // RSI
        if (visibleIndicators.rsi && hasRSI) {
          series.push({
            name: 'RSI',
            type: 'line' as const,
            data: rsiData,
            xAxisIndex: gridIndex,
            yAxisIndex: gridIndex,
            smooth: true,
            lineStyle: {
              opacity: 0.8,
              width: 2,
              color: '#8b5cf6'
            },
            showSymbol: false,
            markLine: {
              silent: true,
              symbol: 'none',
              lineStyle: {
                color: '#999',
                type: 'dashed' as const,
                width: 1
              },
              data: [
                { yAxis: 70, label: { formatter: '超买(70)' } },
                { yAxis: 30, label: { formatter: '超卖(30)' } }
              ]
            }
          })
        }

        return series
      })()
    }

    // 应用图表配置
    if (!chart) return

    // 检测网格数量是否变化（指标增减时会改变网格数量）
    const currentOption = chart.getOption() as any
    const currentGridCount = (currentOption && Array.isArray(currentOption.grid)) ? currentOption.grid.length : 0
    const newGridCount = grids.length
    const shouldReplace = currentGridCount !== newGridCount

    // 网格数量变化时完全替换配置，否则合并更新（保留缩放状态）
    chart.setOption(option, {
      notMerge: shouldReplace,
      replaceMerge: shouldReplace ? ['grid', 'xAxis', 'yAxis', 'series'] : undefined
    })

    // 确保布局正确
    chart.resize()

    // 监听dataZoom事件以触发懒加载
    chart.on('dataZoom', (params: any) => {
      const dataZoom = chart.getOption().dataZoom as any[]
      if (dataZoom && dataZoom[0]) {
        const startValue = Math.floor((dataZoom[0].start / 100) * dates.length)
        const endValue = Math.floor((dataZoom[0].end / 100) * dates.length)
        loadMoreData(startValue, endValue)
      }
    })

    // 响应式调整
    const handleResize = () => {
      chart.resize()
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.off('dataZoom')
    }
  }, [allData, visibleIndicators, hasBOLL, hasKDJ, hasMACD, hasRSI, loadMoreData])

  // 显示加载状态
  useEffect(() => {
    if (chartInstanceRef.current) {
      if (isLoading) {
        chartInstanceRef.current.showLoading({
          text: '加载更多历史数据...',
          color: '#3b82f6',
          textColor: '#000',
          maskColor: 'rgba(255, 255, 255, 0.8)',
          zlevel: 0
        })
      } else {
        chartInstanceRef.current.hideLoading()
      }
    }
  }, [isLoading])

  // 监听容器高度变化，自动resize
  useEffect(() => {
    if (chartInstanceRef.current) {
      // 使用requestAnimationFrame确保DOM更新完成
      requestAnimationFrame(() => {
        if (chartInstanceRef.current) {
          chartInstanceRef.current.resize()
        }
      })
    }
  }, [chartHeight])

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
    <div className="w-full">
      {/* 设置按钮 */}
      <div className="mb-4 flex justify-end">
        <button
          onClick={() => setShowSettings(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          指标设置
        </button>
      </div>

      {/* 设置对话框 */}
      {showSettings && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={() => setShowSettings(false)}>
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-md w-full mx-4" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">选择显示的指标</h3>
              <button
                onClick={() => setShowSettings(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="space-y-3">
              {/* 成交量 */}
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={visibleIndicators.volume}
                  onChange={(e) => setVisibleIndicators({ ...visibleIndicators, volume: e.target.checked })}
                  className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500"
                />
                <span className="ml-3 text-gray-900 dark:text-white">成交量 (Volume)</span>
              </label>

              {/* MACD */}
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={visibleIndicators.macd}
                  onChange={(e) => setVisibleIndicators({ ...visibleIndicators, macd: e.target.checked })}
                  disabled={!hasMACD}
                  className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500 disabled:opacity-50"
                />
                <span className={`ml-3 ${hasMACD ? 'text-gray-900 dark:text-white' : 'text-gray-400 dark:text-gray-600'}`}>
                  MACD {!hasMACD && '(无数据)'}
                </span>
              </label>

              {/* KDJ */}
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={visibleIndicators.kdj}
                  onChange={(e) => setVisibleIndicators({ ...visibleIndicators, kdj: e.target.checked })}
                  disabled={!hasKDJ}
                  className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500 disabled:opacity-50"
                />
                <span className={`ml-3 ${hasKDJ ? 'text-gray-900 dark:text-white' : 'text-gray-400 dark:text-gray-600'}`}>
                  KDJ {!hasKDJ && '(无数据)'}
                </span>
              </label>

              {/* RSI */}
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={visibleIndicators.rsi}
                  onChange={(e) => setVisibleIndicators({ ...visibleIndicators, rsi: e.target.checked })}
                  disabled={!hasRSI}
                  className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500 disabled:opacity-50"
                />
                <span className={`ml-3 ${hasRSI ? 'text-gray-900 dark:text-white' : 'text-gray-400 dark:text-gray-600'}`}>
                  RSI {!hasRSI && '(无数据)'}
                </span>
              </label>

              {/* BOLL */}
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={visibleIndicators.boll}
                  onChange={(e) => setVisibleIndicators({ ...visibleIndicators, boll: e.target.checked })}
                  disabled={!hasBOLL}
                  className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500 disabled:opacity-50"
                />
                <span className={`ml-3 ${hasBOLL ? 'text-gray-900 dark:text-white' : 'text-gray-400 dark:text-gray-600'}`}>
                  布林带 (BOLL) {!hasBOLL && '(无数据)'}
                </span>
              </label>
            </div>

            <div className="mt-6 flex justify-end">
              <button
                onClick={() => {
                  setShowSettings(false)
                  // 关闭对话框后立即触发图表resize，确保布局正确
                  // 使用requestAnimationFrame确保DOM更新完成后再resize
                  requestAnimationFrame(() => {
                    if (chartInstanceRef.current) {
                      chartInstanceRef.current.resize()
                    }
                  })
                }}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              >
                确定
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 图表 */}
      <div ref={chartRef} style={{ width: '100%', height: `${chartHeight}px` }} />
    </div>
  )
}
