'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { createPortal } from 'react-dom'
import * as echarts from 'echarts'
import { apiClient } from '@/lib/api-client'
import {
  formatVolume as formatVolumeUtil,
  removeDateTimePart as removeDateTimePartUtil,
  formatDateWithWeekday as formatDateWithWeekdayUtil,
  loadIndicatorSettings,
  saveIndicatorSettings,
  CHART_LAYOUT,
  type IndicatorSettings,
} from './chart-utils'

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

// 回测相关类型定义
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

interface EChartsStockChartProps {
  data: ChartData[]
  stockCode: string
  // 回测模式相关（可选）
  backtestMode?: boolean
  signalPoints?: SignalPoints
  equityCurve?: EquityCurvePoint[]
  // 外部控制指标设置（可选）
  externalVisibleIndicators?: {
    volume: boolean
    macd: boolean
    kdj: boolean
    rsi: boolean
    boll: boolean
  }
  onIndicatorsChange?: (indicators: any) => void
  hideSettingsButton?: boolean  // 是否隐藏设置按钮
}

export default function EChartsStockChart({
  data,
  stockCode,
  backtestMode = false,
  signalPoints,
  equityCurve,
  externalVisibleIndicators,
  onIndicatorsChange,
  hideSettingsButton = false
}: EChartsStockChartProps) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstanceRef = useRef<echarts.ECharts | null>(null)
  const [allData, setAllData] = useState<ChartData[]>(data)
  const allDataRef = useRef<ChartData[]>(data)  // ref 版本，供事件回调读取最新值
  const [isLoading, setIsLoading] = useState(false)
  const isLoadingRef = useRef(false)  // ref 版本，供事件回调读取最新值
  const hasLoadedAllDataRef = useRef(false)  // 标记是否已加载全部数据
  const currentDataZoomRef = useRef<{ start: number; end: number } | null>(null)  // 保存当前缩放位置

  /**
   * 指标显示状态管理
   *
   * 支持两种模式：
   * 1. 外部控制模式：当传入 externalVisibleIndicators 时，使用外部状态
   *    - 由父组件（如 StockPriceCard）统一管理指标设置
   *    - 不保存到 localStorage，由父组件负责持久化
   *
   * 2. 独立模式：未传入 externalVisibleIndicators 时，自主管理
   *    - 从 localStorage 读取用户偏好
   *    - 自动保存设置变化到 localStorage
   */
  const [visibleIndicators, setVisibleIndicators] = useState<IndicatorSettings>(() => {
    if (externalVisibleIndicators) return externalVisibleIndicators
    return loadIndicatorSettings()
  })

  /**
   * 外部控制模式：同步外部指标设置变化
   */
  useEffect(() => {
    if (externalVisibleIndicators) {
      setVisibleIndicators(externalVisibleIndicators)
    }
  }, [externalVisibleIndicators])

  /**
   * 独立模式：持久化指标设置到 localStorage
   * 仅在非外部控制时执行
   */
  useEffect(() => {
    if (!externalVisibleIndicators) {
      saveIndicatorSettings(visibleIndicators)
    }
  }, [visibleIndicators, externalVisibleIndicators])

  // 设置对话框显示状态
  const [showSettings, setShowSettings] = useState(false)

  /**
   * 控制 body 滚动：打开对话框时禁用，关闭时恢复
   */
  useEffect(() => {
    if (showSettings) {
      // 保存当前滚动位置
      const scrollY = window.scrollY
      document.body.style.overflow = 'hidden'
      document.body.style.position = 'fixed'
      document.body.style.top = `-${scrollY}px`
      document.body.style.width = '100%'
    } else {
      // 恢复滚动
      const scrollY = document.body.style.top
      document.body.style.overflow = ''
      document.body.style.position = ''
      document.body.style.top = ''
      document.body.style.width = ''
      if (scrollY) {
        window.scrollTo(0, parseInt(scrollY || '0') * -1)
      }
    }
  }, [showSettings])

  // 检查是否有权益曲线数据
  const hasEquityData = backtestMode && equityCurve && equityCurve.length > 0

  const formatVolume = formatVolumeUtil
  const removeDateTimePart = removeDateTimePartUtil
  const formatDateWithWeekday = formatDateWithWeekdayUtil

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
        new Date(removeDateTimePart(a.date)).getTime() - new Date(removeDateTimePart(b.date)).getTime()
      )
      allDataRef.current = sortedInitial
      setAllData(sortedInitial)
      currentDataZoomRef.current = null  // 重置缩放位置，新股票从默认视图开始
      hasLoadedAllDataRef.current = false  // 重置加载标记
    }
  }, [data, stockCode])

  /**
   * 懒加载更多历史数据
   *
   * 触发条件：dataZoom 左端滑到数据总量的 20% 以内
   * 策略：以当前最早日期的前一天为 end_date，向后端请求 500 条更早数据
   * 视图锁定：用锚点日期重算 dataZoom 百分比，防止加载后视图跳位
   * 自动续载：若 has_more=true 且视图仍在左端，自动触发下一批（无需用户再次滑动）
   */
  const loadMoreData = useCallback(async () => {
    // 用 ref 读取最新值，避免闭包捕获旧 state
    if (hasLoadedAllDataRef.current || isLoadingRef.current) return

    const currentData = allDataRef.current
    if (currentData.length === 0) return

    // 读取图表当前 dataZoom 位置
    if (!chartInstanceRef.current) return
    const option = chartInstanceRef.current.getOption() as any
    if (!option.dataZoom?.[0]) return
    const zoomStart: number = option.dataZoom[0].start  // 百分比 0~100

    // 当视图滑到最左端 20% 时才触发
    const startValue = Math.floor((zoomStart / 100) * currentData.length)
    const threshold = Math.floor(currentData.length * 0.2)
    if (startValue >= threshold) return

    isLoadingRef.current = true
    setIsLoading(true)

    try {
      // 计算要请求的 end_date：当前最早日期的前一天
      const earliestDate = currentData[0]?.date
      if (!earliestDate) return
      const earliestDateOnly = earliestDate.split('T')[0].split(' ')[0]
      const endDate = new Date(earliestDateOnly + 'T00:00:00')
      endDate.setDate(endDate.getDate() - 1)
      const endDateStr = `${endDate.getFullYear()}-${String(endDate.getMonth() + 1).padStart(2, '0')}-${String(endDate.getDate()).padStart(2, '0')}`

      // 记录锚点日期：视图最左端可见的那条数据，用于加载后精确恢复视图位置
      const anchorIdx = Math.floor((zoomStart / 100) * currentData.length)
      const anchorDate = removeDateTimePart(currentData[Math.max(0, anchorIdx)]?.date ?? '')
      const zoomRange = (option.dataZoom[0].end as number) - zoomStart  // 视图宽度（百分比）

      // 请求更早的 500 条数据
      const response = await apiClient.getFeatures(stockCode, { end_date: endDateStr, limit: 500 })

      if (response.data && response.data.length > 0) {
        const newChartData = response.data as unknown as ChartData[]
        // 去重合并（key 为日期字符串）
        const dateSet = new Set(currentData.map(d => removeDateTimePart(d.date)))
        const dedupedNew = newChartData.filter(d => !dateSet.has(removeDateTimePart(d.date)))
        const sortedData = [...dedupedNew, ...currentData].sort((a, b) =>
          new Date(removeDateTimePart(a.date)).getTime() - new Date(removeDateTimePart(b.date)).getTime()
        )

        // 用锚点日期在新数组中找对应位置，重算百分比，保持视图不跳转
        const newAnchorIdx = sortedData.findIndex(d => removeDateTimePart(d.date) >= anchorDate)
        const newStart = newAnchorIdx >= 0 ? (newAnchorIdx / sortedData.length) * 100 : 0
        currentDataZoomRef.current = {
          start: Math.max(0, newStart),
          end: Math.min(100, newStart + zoomRange)
        }

        allDataRef.current = sortedData
        setAllData(sortedData)
      }

      if (!response.has_more) {
        hasLoadedAllDataRef.current = true
      }
    } catch (error) {
      console.error('Failed to load more historical data:', error)
    } finally {
      isLoadingRef.current = false
      setIsLoading(false)
    }

    // 如果还有更多数据，且当前视图仍在左端（start < 20%），自动继续加载下一批
    // 不依赖 dataZoom 事件重触发，直接调度下一次加载
    if (!hasLoadedAllDataRef.current) {
      const latestStart = currentDataZoomRef.current?.start ?? 0
      if (latestStart < 20) {
        setTimeout(() => loadMoreData(), 200)
      }
    }
  }, [stockCode])

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
      new Date(removeDateTimePart(a.date)).getTime() - new Date(removeDateTimePart(b.date)).getTime()
    )

    // 提取日期和数据（格式化日期为 YYYY-MM-DD）
    const dates = sortedData.map(d => {
      const dateStr = d.date
      // 处理 ISO 格式（2026-03-13T00:00:00）或带时间的格式（2026-03-13 00:00:00）
      return dateStr.split('T')[0].split(' ')[0]
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

    // 回测模式：处理买卖信号和权益曲线
    let normalizedEquityData: (number | null)[] = []
    const equityDataForTooltip: (EquityCurvePoint | null)[] = []
    let buyMarkPoints: any[] = []
    let sellMarkPoints: any[] = []

    if (backtestMode && signalPoints) {
      // 准备买卖信号markPoint数据
      buyMarkPoints = signalPoints.buy.map(point => ({
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

      sellMarkPoints = signalPoints.sell.map(point => ({
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
    }

    if (hasEquityData && equityCurve) {
      // 创建日期到权益的映射
      const equityMap = new Map<string, EquityCurvePoint>()
      equityCurve.forEach(point => {
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
    const mainLegendData = (() => {
      const base = ['K线', 'MA5', 'MA20', 'MA60']
      if (visibleIndicators.boll && hasBOLL) {
        base.push('BOLL上轨', 'BOLL中轨', 'BOLL下轨')
      }
      if (hasEquityData) {
        base.push('权益曲线')
      }
      return base
    })()

    const legends: any[] = [
      {
        data: mainLegendData,
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
            const dataIndex = param.dataIndex

            if (seriesName === '成交量') {
              // 成交量：使用万/亿单位格式化
              const volumeValue = Array.isArray(value) ? value[1] : value
              otherContent += createTooltipRow(marker, seriesName, formatVolume(volumeValue), color)
            } else if (seriesName === '权益曲线' && equityDataForTooltip[dataIndex]) {
              // 特殊处理权益曲线，显示真实资产数据
              const equity = equityDataForTooltip[dataIndex]!
              otherContent += `<div style="margin-top:8px; padding-top:8px; border-top:1px solid #eee;">
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
            } else if (seriesName === 'K线' && Array.isArray(value)) {
              // K线数据：显示开高低收，保持2位小数，颜色与涨跌一致
              hasKLine = true
              klineContent += createTooltipRow(marker, '开', Number(value[1]).toFixed(2), priceColor)
              klineContent += createTooltipRow(marker, '收', Number(value[2]).toFixed(2), priceColor)
              klineContent += createTooltipRow(marker, '低', Number(value[3]).toFixed(2), priceColor)
              klineContent += createTooltipRow(marker, '高', Number(value[4]).toFixed(2), priceColor)
            } else if (seriesName !== '权益曲线') {
              // 其他指标：MA、MACD、KDJ、RSI等（排除权益曲线）
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
            },
            // 回测模式：添加买卖信号markPoint
            ...(backtestMode && (buyMarkPoints.length > 0 || sellMarkPoints.length > 0) ? {
              markPoint: {
                data: [...buyMarkPoints, ...sellMarkPoints],
                animation: true,
                animationDuration: 500
              }
            } : {})
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

        // 权益曲线（回测模式，归一化后重叠在K线图上）
        if (hasEquityData) {
          series.push({
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
          })
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

    // 监听dataZoom事件以触发懒加载（直接调用最新版本，无需重绑定）
    chart.off('dataZoom')
    chart.on('dataZoom', () => {
      loadMoreData()
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
  }, [allData, visibleIndicators, hasBOLL, hasKDJ, hasMACD, hasRSI, loadMoreData, backtestMode, signalPoints, equityCurve, hasEquityData])

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
      {/* 设置按钮（仅在未隐藏且非外部控制时显示） */}
      {!hideSettingsButton && !externalVisibleIndicators && (
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
      )}

      {/* 设置对话框（使用 Portal 渲染到 body，确保遮罩层正确覆盖） */}
      {showSettings && typeof window !== 'undefined' && createPortal(
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[9999]"
          onClick={() => setShowSettings(false)}
          style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0 }}
        >
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
        </div>,
        document.body
      )}

      {/* 回测模式提示 */}
      {backtestMode && hasEquityData && (
        <div className="mb-2 px-3 py-2 bg-pink-50 dark:bg-pink-900/20 rounded-md border border-pink-200 dark:border-pink-800">
          <p className="text-xs text-pink-800 dark:text-pink-300">
            💡 粉色线为权益曲线（已归一化到价格范围），可直观看到资产变化与股价走势的关系
          </p>
        </div>
      )}

      {/* 图表 */}
      <div ref={chartRef} style={{ width: '100%', height: `${chartHeight}px` }} />

      {/* 回测信号统计 */}
      {backtestMode && signalPoints && (signalPoints.buy.length > 0 || signalPoints.sell.length > 0) && (
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
      )}
    </div>
  )
}
