'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import { createPortal } from 'react-dom'
import * as echarts from 'echarts'
import { apiClient } from '@/lib/api-client'
import { useEChartsTheme } from '@/hooks/useEChartsTheme'
import {
  formatVolume as formatVolumeUtil,
  removeDateTimePart as removeDateTimePartUtil,
  formatDateWithWeekday as formatDateWithWeekdayUtil,
  loadIndicatorSettings,
  saveIndicatorSettings,
  DEFAULT_INDICATORS,
  type IndicatorSettings,
} from './chart-utils'

/**
 * 规整指标设置：MACD/KDJ/RSI 互斥（业界标准单选），按优先级保留第一个 true 的。
 */
function enforceSingleIndicator(settings: IndicatorSettings): IndicatorSettings {
  const result = { ...settings }
  const order: Array<keyof IndicatorSettings> = ['macd', 'kdj', 'rsi']
  let picked = false
  for (const key of order) {
    if (result[key] && !picked) {
      picked = true
    } else if (result[key]) {
      result[key] = false
    }
  }
  return result
}

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

// 筹码分布数据（每个价位的持仓占比）
interface ChipItem {
  price: number
  percent: number
}

interface EChartsStockChartProps {
  data: ChartData[]
  stockCode: string
  // 回测模式相关（可选）
  backtestMode?: boolean
  signalPoints?: SignalPoints
  equityCurve?: EquityCurvePoint[]
  // 筹码分布数据（可选，提供时会在 K 线主图右侧嵌入横向条形图）
  // 单日快照：ChipItem[] —— 回测或简化场景
  // 历史全量：Map<YYYY-MM-DD, ChipItem[]> —— 支持 K 线 hover 联动按日期切换
  chipsData?: ChipItem[]
  chipsHistory?: Map<string, ChipItem[]>
  // 外部控制指标设置（可选）。chips 字段可选，未提供时由内部默认值兜底
  externalVisibleIndicators?: {
    volume: boolean
    macd: boolean
    kdj: boolean
    rsi: boolean
    boll: boolean
    chips?: boolean
  }
  onIndicatorsChange?: (indicators: any) => void
  // K 线 hover 到某日但 chipsHistory 无该日数据时触发，父组件可按需拉取 ±30 天窗口补充
  onChipsDateMiss?: (date: string) => void
  // 已向后端确认过的筹码日期区间（YYYY-MM-DD），子组件用来区分"加载中"和"已确认无数据"
  chipsFetchedRanges?: Array<{ start: string; end: string }>
  hideSettingsButton?: boolean  // 是否隐藏设置按钮
}

export default function EChartsStockChart({
  data,
  stockCode,
  backtestMode = false,
  signalPoints,
  equityCurve,
  chipsData,
  chipsHistory,
  externalVisibleIndicators,
  onIndicatorsChange,
  onChipsDateMiss,
  chipsFetchedRanges,
  hideSettingsButton = false
}: EChartsStockChartProps) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstanceRef = useRef<echarts.ECharts | null>(null)
  const { theme, echartsTheme, palette } = useEChartsTheme()
  const [allData, setAllData] = useState<ChartData[]>(data)
  const allDataRef = useRef<ChartData[]>(data)  // ref 版本，供事件回调读取最新值
  const [isLoading, setIsLoading] = useState(false)
  const isLoadingRef = useRef(false)  // ref 版本，供事件回调读取最新值
  const hasLoadedAllDataRef = useRef(false)  // 标记是否已加载全部数据
  const currentDataZoomRef = useRef<{ start: number; end: number } | null>(null)  // 保存当前缩放位置

  // 筹码当前显示日期（hover 联动）：null 表示显示最新日（默认）
  // 用 ref 让 ECharts 事件回调读最新值，避免闭包陈旧
  const activeChipsDateRef = useRef<string | null>(null)
  // 鼠标当前停留的日期（无论是否命中缓存）；用于"数据到达后自动回填"
  const hoverDateRef = useRef<string | null>(null)
  // 筹码日期显示 UI：用 state 驱动 React 重渲染 badge 文字
  const [activeChipsDateLabel, setActiveChipsDateLabel] = useState<string | null>(null)

  // 初始化/变更时用 chipsHistory 里的最新日期作为默认 badge 文案
  useEffect(() => {
    if (chipsHistory instanceof Map && chipsHistory.size > 0) {
      const keys = Array.from(chipsHistory.keys()).sort()
      const latest = keys[keys.length - 1] ?? null
      // 只有当前没激活 hover 日期时才覆盖（避免打断 hover）
      if (activeChipsDateRef.current === null) {
        setActiveChipsDateLabel(latest)
      }
    } else {
      setActiveChipsDateLabel(null)
    }
  }, [chipsHistory])

  /**
   * 指标显示状态管理
   *
   * 业界标准（同花顺/东方财富/富途/TradingView）：
   * - 主图：K 线 + MA，可叠加 BOLL
   * - 成交量：固定副图（量价不可分）
   * - 技术指标副图：MACD / KDJ / RSI 底部 Tab 单选切换，一次只显示一个
   *
   * 为向后兼容外部 `externalVisibleIndicators` 接口，内部仍用 IndicatorSettings
   * 结构保存；macd/kdj/rsi 三者保持互斥（最多一个为 true）。
   */
  const [visibleIndicators, setVisibleIndicators] = useState<IndicatorSettings>(() => {
    if (externalVisibleIndicators) {
      // 外部接口可能没有 chips 字段，用 DEFAULT_INDICATORS.chips 兜底
      return enforceSingleIndicator({ chips: DEFAULT_INDICATORS.chips, ...externalVisibleIndicators })
    }
    return enforceSingleIndicator(loadIndicatorSettings())
  })

  /**
   * 外部控制模式：同步外部指标设置变化（仍强制单选规整）
   */
  useEffect(() => {
    if (externalVisibleIndicators) {
      setVisibleIndicators(enforceSingleIndicator({ chips: DEFAULT_INDICATORS.chips, ...externalVisibleIndicators }))
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

  /**
   * 派生：当前激活的技术指标副图（单选）。
   * 用于底部 Tab 栏高亮显示与图表渲染判断。
   */
  const activeIndicator: 'macd' | 'kdj' | 'rsi' | 'none' =
    visibleIndicators.macd ? 'macd'
    : visibleIndicators.kdj ? 'kdj'
    : visibleIndicators.rsi ? 'rsi'
    : 'none'

  /**
   * 切换技术指标副图（底部 Tab 点击触发）。
   * 副图必定显示一个，点击目标 Tab 切过去并关闭其余。
   */
  const switchIndicator = (target: 'macd' | 'kdj' | 'rsi') => {
    setVisibleIndicators(prev => {
      const next: IndicatorSettings = { ...prev, macd: false, kdj: false, rsi: false }
      next[target] = true
      onIndicatorsChange?.(next)
      return next
    })
  }

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
  // 筹码数据是否可用（不看用户开关）：组件作用域可用，供弹窗 disabled 状态判断
  const hasChipsData =
    (chipsHistory instanceof Map && chipsHistory.size > 0) ||
    (Array.isArray(chipsData) && chipsData.length > 0)

  /**
   * 兜底默认激活：activeIndicator 为 'none' 但有可用指标时，自动激活第一个
   * （优先级 MACD → KDJ → RSI，与 Tab 顺序一致）。
   * 场景：旧 localStorage 三项全 false、父组件传了全 false 的 externalVisibleIndicators。
   */
  useEffect(() => {
    if (activeIndicator !== 'none') return
    const target: 'macd' | 'kdj' | 'rsi' | null =
      hasMACD ? 'macd' : hasKDJ ? 'kdj' : hasRSI ? 'rsi' : null
    if (target) switchIndicator(target)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeIndicator, hasMACD, hasKDJ, hasRSI])

  // 技术指标副图（单选）最终是否渲染：需要 activeIndicator 选中且对应数据存在
  const showMACDPanel = activeIndicator === 'macd' && hasMACD
  const showKDJPanel = activeIndicator === 'kdj' && hasKDJ
  const showRSIPanel = activeIndicator === 'rsi' && hasRSI
  const showIndicatorPanel = showMACDPanel || showKDJPanel || showRSIPanel

  // 计算启用的副图数量（单选后最多 2：成交量 + 1 个技术指标）
  const subPanelCount = [
    visibleIndicators.volume,
    showIndicatorPanel
  ].filter(Boolean).length

  // 图表布局配置常量（像素）—— 业界标准比例 ~70/15/15
  const MAIN_CHART_HEIGHT = 480    // 主图（K线）高度
  const VOLUME_PANEL_HEIGHT = 100  // 成交量副图高度
  const SUB_PANEL_HEIGHT = 110     // 其他副图（MACD/KDJ/RSI）高度
  const PANEL_GAP = 0              // 面板间隔
  const LEGEND_HEIGHT = 20         // 单个图例高度
  const LEGEND_PADDING = 10        // 图例上下padding
  const ZOOM_HEIGHT = 0            // DataZoom 滑块已移除，保留常量占位便于未来恢复
  const TOP_PADDING = 10           // 顶部padding
  const BOTTOM_PADDING = 10        // 底部padding

  // 动态计算图表总高度（单位：像素）
  const volumeHeight = visibleIndicators.volume
    ? (LEGEND_PADDING + LEGEND_HEIGHT + LEGEND_PADDING + VOLUME_PANEL_HEIGHT + PANEL_GAP)
    : 0
  const indicatorPanelHeight = showIndicatorPanel
    ? (LEGEND_PADDING + LEGEND_HEIGHT + LEGEND_PADDING + SUB_PANEL_HEIGHT + PANEL_GAP)
    : 0

  const chartHeight = TOP_PADDING + 30 + MAIN_CHART_HEIGHT +
                     (subPanelCount > 0 ? PANEL_GAP + LEGEND_PADDING : 0) +
                     volumeHeight +
                     indicatorPanelHeight +
                     ZOOM_HEIGHT + BOTTOM_PADDING

  // 主题切换：dispose 旧 instance，让下一轮 effect 以新主题重新 init
  useEffect(() => {
    if (chartInstanceRef.current) {
      chartInstanceRef.current.dispose()
      chartInstanceRef.current = null
    }
  }, [theme])

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
      chartInstanceRef.current = echarts.init(chartRef.current, echartsTheme)
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

    // 计算启用的副图顺序映射（单选后最多 volume + 1 个技术指标）
    const enabledIndicators: string[] = []
    if (visibleIndicators.volume) enabledIndicators.push('volume')
    if (showMACDPanel) enabledIndicators.push('macd')
    else if (showKDJPanel) enabledIndicators.push('kdj')
    else if (showRSIPanel) enabledIndicators.push('rsi')

    // 动态构建图例（使用像素定位）
    // BOLL 三轨在 series 里仍独立（用不同颜色），图例只列 'BOLL上轨' 代表三者
    // 中轨/下轨从图例 data 里删掉，但 series 仍渲染（图例 data 不影响 series 显示）
    const mainLegendData = (() => {
      const base = ['K线', 'MA5', 'MA20', 'MA60']
      if (visibleIndicators.boll && hasBOLL) base.push('BOLL上轨')
      if (hasEquityData) base.push('权益曲线')
      return base
    })()

    const legends: any[] = [
      {
        data: mainLegendData,
        top: TOP_PADDING,
        left: 'center',
        icon: 'roundRect',
        itemWidth: 12,
        itemHeight: 4,
        itemGap: 12,
        textStyle: { fontWeight: 'bold', fontSize: 12 },
        // 显示更短的图例文字（'BOLL上轨' → 'BOLL'）
        formatter: (name: string) => name === 'BOLL上轨' ? 'BOLL' : name,
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

    // 技术指标副图图例（单选）
    if (showMACDPanel) {
      legends.push({
        data: ['DIF', 'DEA', 'MACD'],
        top: currentTop,
        left: 'center',
        textStyle: { fontWeight: 'bold' }
      })
    } else if (showKDJPanel) {
      legends.push({
        data: ['K', 'D', 'J'],
        top: currentTop,
        left: 'center',
        textStyle: { fontWeight: 'bold' }
      })
    } else if (showRSIPanel) {
      legends.push({
        data: ['RSI'],
        top: currentTop,
        left: 'center',
        textStyle: { fontWeight: 'bold' }
      })
    }

    // 是否启用右侧筹码分布面板（A 股看盘软件惯例：K 线主图右侧嵌入横向筹码条）
    // 闸门：① 用户在指标设置中开启 chips ② 有 chipsHistory 或 chipsData 数据
    const hasChipsHistory = chipsHistory instanceof Map && chipsHistory.size > 0
    const hasChips = visibleIndicators.chips && hasChipsData
    // 主图右边距：有筹码图时让出右侧 26% 给它（绘图区 + 右侧价格刻度）
    const MAIN_RIGHT = hasChips ? '26%' : '8%'

    // 构建图表网格，定义每个面板的绘图区域
    const grids = [
      {
        left: '8%',
        right: MAIN_RIGHT,
        top: TOP_PADDING + 30,  // 30为主图图例高度
        height: MAIN_CHART_HEIGHT
      }
    ]

    // 计算副图网格的垂直位置
    let gridTop = TOP_PADDING + 30 + MAIN_CHART_HEIGHT + PANEL_GAP + LEGEND_PADDING

    // 成交量网格（right 与主图保持一致，确保跨面板垂直十字线 x 坐标对齐）
    if (visibleIndicators.volume) {
      grids.push({
        left: '8%',
        right: MAIN_RIGHT,
        top: gridTop + LEGEND_HEIGHT + LEGEND_PADDING,
        height: VOLUME_PANEL_HEIGHT
      })
      gridTop += VOLUME_PANEL_HEIGHT + PANEL_GAP + LEGEND_HEIGHT + LEGEND_PADDING * 2
    }

    // 技术指标副图网格（单选：MACD / KDJ / RSI 三选一共享同一个 grid）
    if (showIndicatorPanel) {
      grids.push({
        left: '8%',
        right: MAIN_RIGHT,
        top: gridTop + LEGEND_HEIGHT + LEGEND_PADDING,
        height: SUB_PANEL_HEIGHT
      })
    }

    // 筹码分布 grid：位于 K 线主图右侧，与主图同垂直范围、同价格 Y 轴刻度
    // 索引为 normalGridCount（= 现有 grid 数量），筹码图的 xAxis/yAxis/series 都引用该索引
    const normalGridCount = grids.length
    const chipsGridIndex = normalGridCount
    if (hasChips) {
      grids.push({
        // left 74% + right 6%：与主图 right 26% 无缝对齐，右侧留 6% 给价格刻度
        left: '75%',
        right: '6%',
        top: TOP_PADDING + 30,
        height: MAIN_CHART_HEIGHT
      } as any)
    }

    /**
     * 根据日期取当日筹码数据源（支持 hover 联动切换日期）
     * 1. 指定日期 + chipsHistory 命中 → 该日的 chips + 该日收盘价（当日现价）
     * 2. 否则 → chipsData + K 线最后一日收盘价（退化场景）
     */
    const getChipsForDate = (dateKey: string | null): { chips: ChipItem[]; referencePrice: number | null; date: string | null } => {
      if (dateKey && hasChipsHistory) {
        const bucket = (chipsHistory as Map<string, ChipItem[]>).get(dateKey)
        if (bucket && bucket.length > 0) {
          // 当日的参考价：从 sortedData 取匹配日期的收盘价，取不到退回到最新收盘价
          const dayBar = sortedData.find(d => removeDateTimePart(d.date) === dateKey)
          const refPrice = dayBar?.close ?? (sortedData.length > 0 ? sortedData[sortedData.length - 1].close : null)
          return { chips: bucket, referencePrice: refPrice ?? null, date: dateKey }
        }
      }
      // 兜底：chipsData（单日）或 chipsHistory 中的最新一日
      if (hasChipsHistory) {
        const dates = Array.from((chipsHistory as Map<string, ChipItem[]>).keys()).sort()
        const latestDate = dates[dates.length - 1]
        const bucket = (chipsHistory as Map<string, ChipItem[]>).get(latestDate) ?? []
        const lastBar = sortedData.length > 0 ? sortedData[sortedData.length - 1] : null
        return { chips: bucket, referencePrice: lastBar?.close ?? null, date: latestDate }
      }
      const lastBar = sortedData.length > 0 ? sortedData[sortedData.length - 1] : null
      return {
        chips: (chipsData as ChipItem[]) ?? [],
        referencePrice: lastBar?.close ?? null,
        date: lastBar ? removeDateTimePart(lastBar.date) : null
      }
    }

    // 初次渲染取 activeChipsDateRef 当前值（通常是 null → 最新日）
    const initialChipSelection = getChipsForDate(activeChipsDateRef.current)
    const latestClose = initialChipSelection.referencePrice

    /**
     * 计算 K 线主图当前可视价格范围（基于 dataZoom 切片）
     * 用于：① 主图 y 轴显式 min/max ② 筹码图档位过滤
     * 两者共用同一 [loBound, hiBound] 是筹码图与 K 线垂直对齐的关键
     */
    const computeKlinePriceBounds = (): { loBound: number; hiBound: number } | null => {
      if (sortedData.length === 0) return null
      const zoomStart = currentDataZoomRef.current?.start ?? 70
      const zoomEnd = currentDataZoomRef.current?.end ?? 100
      const startIdx = Math.max(0, Math.floor((zoomStart / 100) * sortedData.length))
      const endIdx = Math.min(sortedData.length, Math.ceil((zoomEnd / 100) * sortedData.length))
      const slice = sortedData.slice(startIdx, endIdx)
      const lows = slice.map(d => d.low).filter(v => v != null && !isNaN(v))
      const highs = slice.map(d => d.high).filter(v => v != null && !isNaN(v))
      if (lows.length === 0 || highs.length === 0) return null
      const klineLow = Math.min(...lows)
      const klineHigh = Math.max(...highs)
      // 上下各留 3% 边距，避免顶/底紧贴边
      return { loBound: klineLow * 0.97, hiBound: klineHigh * 1.03 }
    }

    // 主图 y 轴显式 min/max（让 ECharts 不再自行 scale 留白）
    const klineBounds = computeKlinePriceBounds()
    const mainYAxisMin = klineBounds ? klineBounds.loBound : null
    const mainYAxisMax = klineBounds ? klineBounds.hiBound : null

    /**
     * 计算筹码图档位列表 + 与主图 y 轴对齐的关键步骤：
     * 在数据档位的基础上，按主图 y 轴 [loBound, hiBound] 等距生成"网格档位"作为骨架，
     * 让 category 轴铺满整个主图 y 轴范围。这样：
     *   - 主图 y 轴 [67, 100] → 筹码 category 也覆盖 [67, 100]
     *   - 现价 85.33（不论是否有数据）一定能精确对位
     * 真实数据档位的 percent 写入对应位置；没有数据的网格档 percent=0（不画 bar 但占位）
     */
    const computeVisibleChips = (sourceChips?: ChipItem[], refPrice?: number | null) => {
      const source = sourceChips ?? initialChipSelection.chips
      if (!hasChips || !klineBounds || source.length === 0) {
        return { visible: [] as ChipItem[], loBound: 0, hiBound: 0 }
      }
      const { loBound, hiBound } = klineBounds

      // 1. 实际数据档位（过滤到主图 y 范围内）
      const dataChips = [...source]
        .sort((a, b) => a.price - b.price)
        .filter(c => c.price >= loBound && c.price <= hiBound)

      // 2. 等距骨架：按主图 grid 高度自适应档数，保证每档 >=5px、最多 120 档
      //    数据档位会被合并到最近的骨架档；骨架档保证 category 铺满 [loBound, hiBound]
      const N = Math.max(40, Math.min(120, Math.floor(MAIN_CHART_HEIGHT / 5)))
      const step = (hiBound - loBound) / (N - 1)
      const gridPrices = Array.from({ length: N }, (_, i) => loBound + i * step)

      // 3. 把数据档累加到最近的骨架档（同一骨架价位可能有多档数据落入）
      const percentByGrid = new Array(N).fill(0)
      for (const dc of dataChips) {
        const idx = Math.round((dc.price - loBound) / step)
        const safeIdx = Math.max(0, Math.min(N - 1, idx))
        percentByGrid[safeIdx] += dc.percent
      }

      // 4. 若 refPrice 在范围内，把它附近的骨架档锁定为"现价档"（用于 markLine 精确定位）
      // 这里只返回骨架；现价定位由 series 构建处用同样的网格化算法计算
      void refPrice  // refPrice 留给上层 markLine 计算用

      const visible: ChipItem[] = gridPrices.map((p, i) => ({ price: p, percent: percentByGrid[i] }))
      return { visible, loBound, hiBound }
    }

    const { visible: sortedChips } = computeVisibleChips(initialChipSelection.chips, latestClose)

    const option: echarts.EChartsOption = {
      animation: false,
      backgroundColor: palette.background,
      legend: legends,
      grid: grids,
      // 顶层 axisPointer：启用跨 grid 联动，让垂直十字线穿透所有副图（K线→成交量→MACD→KDJ→RSI）
      // 只联动常规面板的 xAxis（索引 0..normalGridCount-1），筹码图 xAxis 独立
      axisPointer: {
        link: [{ xAxisIndex: Array.from({ length: normalGridCount }, (_, i) => i) }],
        label: {
          backgroundColor: palette.axisPointerLine
        }
      },
      xAxis: [
        // 常规面板的 category xAxis（K 线/成交量/技术指标共用日期轴）
        ...Array.from({ length: normalGridCount }, (_, index) => ({
          type: 'category' as const,
          data: dates,
          gridIndex: index,
          boundaryGap: false,
          axisLine: { onZero: false },
          splitLine: { show: false },
          axisLabel: {
            show: index === normalGridCount - 1,  // 只在最后一个常规面板显示x轴标签
            formatter: removeDateTimePart
          },
          axisTick: { show: index === normalGridCount - 1 },
          axisPointer: {
            show: true,
            type: 'line' as const,
            // 只让主图 (index 0) 触发 tooltip；其他面板 hover 时仍通过 link 同步显示十字线
            triggerTooltip: index === 0,
            lineStyle: {
              color: palette.axisPointerLine,
              width: 1,
              type: 'dashed' as const
            },
            label: {
              show: index === normalGridCount - 1,
              formatter: (params: any) => removeDateTimePart(params.value || '')
            }
          }
        })),
        // 筹码图专用 xAxis：占比百分比（value 类型，与日期轴完全独立）
        ...(hasChips ? [{
          type: 'value' as const,
          gridIndex: chipsGridIndex,
          position: 'top' as const,
          axisLabel: {
            fontSize: 9,
            formatter: (v: number) => v.toFixed(1) + '%'
          },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { show: false },
          axisPointer: { show: false }
        }] : [])
      ],
      yAxis: [
        // 常规面板 yAxis
        ...Array.from({ length: normalGridCount }, (_, index) => {
          const isMainPanel = index === 0
          const isRSIPanel = index > 0 && enabledIndicators[index - 1] === 'rsi'
          const isVolumePanel = index > 0 && enabledIndicators[index - 1] === 'volume'

          const yAxisConfig: any = {
            scale: true,
            gridIndex: index,
            // 主图（K线）：永远用 dataZoom 视图内的 [low*0.97, high*1.03] 锁定 y 轴
            // —— 不依赖 ECharts 的 scale 自动算法，避免视图内空白且与筹码图严格垂直对齐
            // RSI 固定 0-100；其他面板显式 null 重置（防止 RSI/KDJ 切换时 min/max 残留）
            min: isMainPanel && mainYAxisMin != null
              ? mainYAxisMin
              : isRSIPanel ? 0 : null,
            max: isMainPanel && mainYAxisMax != null
              ? mainYAxisMax
              : isRSIPanel ? 100 : null,
            // 主图用淡 splitLine（不要满屏条纹）；副图保留 splitArea 增强参考
            splitArea: { show: !isMainPanel },
            splitLine: isMainPanel ? { show: true, lineStyle: { color: palette.divider, opacity: 0.3 } } : { show: false },
            axisPointer: {
              show: true,
              type: 'line',
              lineStyle: {
                color: palette.axisPointerLine,
                width: 1,
                type: 'dashed'
              },
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
        // 筹码图 yAxis：category 类型（每个价位一条 bar），价格由低到高排列。
        // 仅保留落在 K 线价格范围内的档位（见 sortedChips 过滤），
        // 并显示价格刻度（稀疏），让用户能将筹码价位与 K 线价位对齐阅读。
        ...(hasChips ? [{
          type: 'category' as const,
          gridIndex: chipsGridIndex,
          data: sortedChips.map(d => d.price.toFixed(2)),
          position: 'right' as const,
          // 稀疏显示价格刻度：档位数 / 6 步长
          axisLabel: {
            show: true,
            fontSize: 9,
            color: '#9ca3af',
            interval: Math.max(1, Math.floor(sortedChips.length / 6))
          },
          axisLine: { show: false },
          axisTick: { show: false },
          splitLine: { show: false },
          axisPointer: { show: false },
          inverse: false
        }] : [])
      ],
      // 仅保留 inside 缩放（鼠标滚轮/双指捏合/拖拽），移除底部 slider 滑块
      // 与同花顺/东财/富途等主流 A 股软件保持一致——缩放交互走手势而非滑块
      dataZoom: [
        {
          type: 'inside',
          // 只绑定常规面板（K 线/成交量/指标），筹码图的 value xAxis 不参与缩放
          xAxisIndex: Array.from({ length: normalGridCount }, (_, i) => i),
          start: currentDataZoomRef.current?.start ?? 70,
          end: currentDataZoomRef.current?.end ?? 100
        }
      ],
      tooltip: {
        trigger: 'axis',
        axisPointer: {
          type: 'cross',
          // 只联动常规面板的 xAxis，筹码图 xAxis 不参与 tooltip 联动
          link: [{ xAxisIndex: Array.from({ length: normalGridCount }, (_, i) => i) }],
          crossStyle: {
            color: palette.axisPointerLine,
            width: 1,
            type: 'dashed'
          }
        },
        // 智能定位：默认放鼠标右侧 +20px；若会越过主图右边界（覆盖筹码图）则反弹到鼠标左侧
        // mainRightPct 与 grid.right 同步：有筹码时 26%，无筹码时 8%
        position: (point: number[], _params: any, _dom: any, _rect: any, size: any) => {
          const [mouseX, mouseY] = point
          const viewW = size.viewSize[0]
          const tipW = size.contentSize[0]
          const tipH = size.contentSize[1]
          const mainRightPct = hasChips ? 0.26 : 0.08
          const mainRightBound = viewW * (1 - mainRightPct)
          let x = mouseX + 20
          if (x + tipW > mainRightBound) {
            x = mouseX - tipW - 20
          }
          if (x < 8) x = 8
          const y = mouseY < tipH + 20 ? mouseY + 20 : 10
          return [x, y]
        },
        backgroundColor: palette.tooltipBg,
        borderWidth: 1,
        borderColor: palette.tooltipBorder,
        padding: 10,
        textStyle: {
          color: palette.tooltipText
        },
        formatter: (params: any) => {
          if (!Array.isArray(params)) return ''

          // 主组（开/收/低/高 + 涨跌幅）：突出显示
          const createPriceRow = (label: string, value: string, color: string) =>
            `<div style="display:flex;justify-content:space-between;align-items:center;font-size:12px;">
              <span style="color:#9ca3af;">${label}</span>
              <span style="margin-left:24px;color:${color};font-weight:600;">${value}</span>
            </div>`
          // 副组（MA/BOLL/RSI 等指标）：小一号字 + 灰色标签
          const createIndicatorRow = (label: string, value: string, color: string) =>
            `<div style="display:flex;justify-content:space-between;align-items:center;font-size:11px;">
              <span style="color:#9ca3af;">${label}</span>
              <span style="margin-left:24px;color:${color};">${value}</span>
            </div>`

          const divider = `<div style="height:1px;background:${palette.divider};margin:6px 0;opacity:0.5;"></div>`

          // 标题：日期+星期
          let result = `<div style="font-weight:600;font-size:12px;margin-bottom:6px;">${formatDateWithWeekday(params[0].axisValue)}</div>`
          let priceContent = ''
          let indicatorContent = ''

          // 提取K线数据 + 计算涨跌幅（与前一日收盘价比较）
          let klineData: any = null
          let klineDataIndex = -1
          params.forEach((param: any) => {
            if (param.seriesName === 'K线' && Array.isArray(param.value)) {
              klineData = param.value
              klineDataIndex = param.dataIndex
            }
          })
          const isRising = klineData && klineData[2] >= klineData[1]
          const priceColor = isRising ? '#ef4444' : '#22c55e'

          // 涨跌幅 = (收 - 前收) / 前收 × 100%；前一日收盘从 sortedData 取
          let pctChangeStr = '-'
          let pctColor = palette.tooltipText
          if (klineData && klineDataIndex > 0) {
            const prevBar = sortedData[klineDataIndex - 1]
            if (prevBar && prevBar.close > 0) {
              const pct = ((Number(klineData[2]) - prevBar.close) / prevBar.close) * 100
              pctChangeStr = (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%'
              pctColor = pct >= 0 ? '#ef4444' : '#22c55e'
            }
          }

          params.forEach((param: any) => {
            const { seriesName, value, color } = param
            const dataIndex = param.dataIndex

            if (seriesName === '成交量') {
              const volumeValue = Array.isArray(value) ? value[1] : value
              indicatorContent += createIndicatorRow('成交量', formatVolume(volumeValue), color)
            } else if (seriesName === '权益曲线' && equityDataForTooltip[dataIndex]) {
              const equity = equityDataForTooltip[dataIndex]!
              indicatorContent += `<div style="margin-top:6px;padding-top:6px;border-top:1px solid ${palette.divider};font-size:11px;">
                <div style="font-weight:600;color:#ec4899;margin-bottom:3px;">权益曲线</div>
                <div style="color:#9ca3af;">总资产 <span style="color:${palette.tooltipText};">¥${equity.total.toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2})}</span></div>
                <div style="color:#9ca3af;">持仓 <span style="color:${palette.tooltipText};">¥${(equity.holdings || 0).toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2})}</span></div>
                <div style="color:#9ca3af;">现金 <span style="color:${palette.tooltipText};">¥${(equity.cash || 0).toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2})}</span></div>
              </div>`
            } else if (seriesName === 'K线' && Array.isArray(value)) {
              priceContent += createPriceRow('开', Number(value[1]).toFixed(2), priceColor)
              priceContent += createPriceRow('收', Number(value[2]).toFixed(2), priceColor)
              priceContent += createPriceRow('低', Number(value[3]).toFixed(2), priceColor)
              priceContent += createPriceRow('高', Number(value[4]).toFixed(2), priceColor)
              priceContent += createPriceRow('涨跌幅', pctChangeStr, pctColor)
            } else if (seriesName !== '权益曲线') {
              const displayValue = Array.isArray(value) ? value[1] : value
              if (displayValue !== '-' && displayValue !== null && displayValue !== undefined) {
                const formattedValue = typeof displayValue === 'number' ? displayValue.toFixed(2) : displayValue
                indicatorContent += createIndicatorRow(seriesName, formattedValue, color)
              }
            }
          })

          // 组装：日期 → 价格主组（开/收/低/高 + 涨跌幅） → 指标副组（MA/BOLL/RSI/成交量等）
          if (priceContent) result += divider + priceContent
          if (indicatorContent) result += divider + indicatorContent
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
        if (showMACDPanel) {
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
        if (showKDJPanel) {
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
              showSymbol: false,
              // KDJ 超买(80)/超卖(20) 参考线（A 股惯例），标签内嵌绘图区右上/右下
              markLine: {
                silent: true,
                symbol: 'none',
                lineStyle: {
                  color: '#999',
                  type: 'dashed' as const,
                  width: 1
                },
                label: {
                  color: '#999',
                  fontSize: 10,
                  backgroundColor: 'transparent'
                },
                data: [
                  { yAxis: 80, label: { formatter: '超买(80)', position: 'insideEndTop' } },
                  { yAxis: 20, label: { formatter: '超卖(20)', position: 'insideEndBottom' } }
                ]
              }
            }
          )
          gridIndex++
        }

        // RSI
        if (showRSIPanel) {
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
              label: {
                color: '#999',
                fontSize: 10,
                backgroundColor: 'transparent'
              },
              data: [
                { yAxis: 70, label: { formatter: '超买(70)', position: 'insideEndTop' } },
                { yAxis: 30, label: { formatter: '超卖(30)', position: 'insideEndBottom' } }
              ]
            },
            // 超买/超卖区域填充（淡色背景，强化信号视觉）
            markArea: {
              silent: true,
              itemStyle: { opacity: 0.08 },
              data: [
                [{ yAxis: 70, itemStyle: { color: '#ef4444' } }, { yAxis: 100 }],  // 超买区（红）
                [{ yAxis: 0, itemStyle: { color: '#22c55e' } }, { yAxis: 30 }],   // 超卖区（绿）
              ]
            }
          })
        }

        // 筹码分布（主图右侧横向条形图）
        if (hasChips) {
          // 按盈亏分区着色：绿=盈利筹码（价格 < 现价 -1%），红=亏损（> 现价 +1%），黄=当前价±1%
          const chipBars = sortedChips.map(d => {
            let color = '#60a5fa'
            if (latestClose != null) {
              if (d.price < latestClose * 0.99) color = '#22c55e'
              else if (d.price > latestClose * 1.01) color = '#ef4444'
              else color = '#facc15'
            }
            return {
              value: d.percent,
              itemStyle: { color, opacity: 0.85 }
            }
          })

          // 找到最接近现价的档位索引，用于 markLine 定位到 category 轴
          const currentPriceIdx = latestClose != null
            ? sortedChips.reduce((best, c, i) =>
                Math.abs(c.price - latestClose) < Math.abs(sortedChips[best].price - latestClose) ? i : best,
                0)
            : -1

          series.push({
            name: '筹码分布',
            type: 'bar',
            data: chipBars,
            xAxisIndex: chipsGridIndex,
            yAxisIndex: chipsGridIndex,
            barMaxWidth: 2,  // 细条
            barCategoryGap: '10%',
            tooltip: {
              trigger: 'item',
              formatter: (params: any) => {
                const price = sortedChips[params.dataIndex]?.price ?? 0
                return `价格：${Number(price).toFixed(2)}<br/>占比：${Number(params.value).toFixed(2)}%`
              }
            },
            // 现价标注线（category 轴用索引而非价格值定位）
            ...(currentPriceIdx >= 0 ? {
              markLine: {
                silent: true,
                symbol: 'none',
                lineStyle: { color: '#f59e0b', width: 1.5, type: 'dashed' as const },
                label: {
                  formatter: `现价 ${latestClose!.toFixed(2)}`,
                  color: '#f59e0b',
                  fontSize: 10,
                  position: 'insideEndTop' as const
                },
                data: [{ yAxis: currentPriceIdx }]
              }
            } : {})
          } as any)
        }

        return series
      })()
    }

    // 应用图表配置
    if (!chart) return

    // 检测网格数量或 series 集合是否变化
    // 指标副图 Tab 切换（如 KDJ→RSI）时 grid 数量相同但 series 完全不同，
    // 若仅 merge，旧 series 上的 markLine / 图形会被残留，必须 replaceMerge series
    const currentOption = chart.getOption() as any
    const currentGridCount = (currentOption && Array.isArray(currentOption.grid)) ? currentOption.grid.length : 0
    const newGridCount = grids.length
    const currentSeriesNames = (currentOption && Array.isArray(currentOption.series))
      ? currentOption.series.map((s: any) => s.name).join(',')
      : ''
    const newSeriesNames = (option.series as any[]).map((s: any) => s.name).join(',')
    const gridChanged = currentGridCount !== newGridCount
    const seriesChanged = currentSeriesNames !== newSeriesNames

    // 网格数量变化时完全替换配置；仅 series 集合变化（指标 Tab 切换）时同时替换 series + yAxis，
    // 否则 RSI→KDJ 切换会保留 RSI 的 yAxis min/max=0-100，把 KDJ 的 J 值截断
    chart.setOption(option, {
      notMerge: gridChanged,
      replaceMerge: gridChanged
        ? ['grid', 'xAxis', 'yAxis', 'series']
        : (seriesChanged ? ['series', 'yAxis'] : undefined)
    })

    // 确保布局正确
    chart.resize()

    /**
     * 清空筹码图 series（hover 到无数据日期或加载中时使用），保留 grid/yAxis 不抖动
     */
    const clearChipsPanel = () => {
      if (!hasChips) return
      const currentOpt = chart.getOption() as any
      chart.setOption({
        series: (currentOpt.series as any[]).map((s: any) =>
          s.name === '筹码分布' ? { ...s, data: [], markLine: { ...s.markLine, data: [] } } : s
        )
      })
    }

    /**
     * 根据"筹码日期"+"K 线缩放范围"重新渲染筹码图（yAxis + series）。
     * 被 dataZoom 事件（缩放时调用，不传日期）和 updateAxisPointer 事件（hover 时传日期）共享。
     * `dateOverride === undefined` 表示沿用 activeChipsDateRef.current。
     */
    const refreshChipsPanel = (dateOverride?: string | null) => {
      if (!hasChips) return
      const dateKey = dateOverride !== undefined ? dateOverride : activeChipsDateRef.current
      const { chips: dayChips, referencePrice } = getChipsForDate(dateKey)
      const { visible } = computeVisibleChips(dayChips, referencePrice)

      const chipBars = visible.map(d => {
        let color = '#60a5fa'
        if (referencePrice != null) {
          if (d.price < referencePrice * 0.99) color = '#22c55e'
          else if (d.price > referencePrice * 1.01) color = '#ef4444'
          else color = '#facc15'
        }
        return { value: d.percent, itemStyle: { color, opacity: 0.85 } }
      })
      const currentIdx = referencePrice != null && visible.length > 0
        ? visible.reduce((best, c, i) =>
            Math.abs(c.price - referencePrice) < Math.abs(visible[best].price - referencePrice) ? i : best, 0)
        : -1

      const currentOpt = chart.getOption() as any
      chart.setOption({
        yAxis: (currentOpt.yAxis as any[]).map((y: any, i: number) =>
          i === chipsGridIndex
            ? {
                ...y,
                data: visible.map(d => d.price.toFixed(2)),
                axisLabel: { ...y.axisLabel, interval: Math.max(1, Math.floor(visible.length / 6)) }
              }
            : y
        ),
        series: (currentOpt.series as any[]).map((s: any) => {
          if (s.name === '筹码分布') {
            return {
              ...s,
              data: chipBars,
              markLine: currentIdx >= 0
                ? {
                    ...s.markLine,
                    data: [{ yAxis: currentIdx }],
                    label: {
                      ...(s.markLine?.label ?? {}),
                      formatter: `现价 ${referencePrice!.toFixed(2)}`
                    }
                  }
                : s.markLine
            }
          }
          // K 线主图也加一条同色水平线（当日收盘价），与筹码图现价虚线视觉对齐
          if (s.name === 'K线' && referencePrice != null) {
            return {
              ...s,
              markLine: {
                silent: true,
                symbol: 'none',
                lineStyle: { color: '#f59e0b', width: 1, type: 'dashed' as const, opacity: 0.6 },
                label: { show: false },
                data: [{ yAxis: referencePrice }]
              }
            }
          }
          return s
        })
      })
    }

    // 数据到达后的回填渲染：chipsHistory 变化触发 effect 重跑时，
    // 若用户鼠标仍停在某日期且该日新数据已到达，自动激活并刷图。
    // 解决"hover 到空洞日期 → 父组件拉数据 → 数据到达但鼠标没动 → 图不更新"的死局。
    if (hasChipsHistory && hoverDateRef.current) {
      const historyMap = chipsHistory as Map<string, ChipItem[]>
      const stickyDate = hoverDateRef.current
      const bucket = historyMap.get(stickyDate)
      if (bucket && bucket.length > 0 && activeChipsDateRef.current !== stickyDate) {
        // 数据到达且非空 → 切换显示
        activeChipsDateRef.current = stickyDate
        setActiveChipsDateLabel(stickyDate)
        requestAnimationFrame(() => refreshChipsPanel(stickyDate))
      } else if (bucket && bucket.length === 0 && activeChipsDateLabel?.includes('加载中')) {
        // 数据到达但确认无数据 → badge 从"加载中"改为"无数据"
        setActiveChipsDateLabel(`${stickyDate}（无数据）`)
      }
    }

    // 监听 dataZoom 事件：① 懒加载更多历史 ② 同步筹码图到当前 K 线可视价格范围
    chart.off('dataZoom')
    chart.on('dataZoom', (evt: any) => {
      // 同步最新 dataZoom 百分比（ECharts 事件里可能有 batch；取第一项）
      const zoomPayload = Array.isArray(evt?.batch) ? evt.batch[0] : evt
      if (zoomPayload && typeof zoomPayload.start === 'number' && typeof zoomPayload.end === 'number') {
        currentDataZoomRef.current = { start: zoomPayload.start, end: zoomPayload.end }
      } else {
        // 事件载荷不含百分比时（某些版本），从图表 option 读回
        const opt = chart.getOption() as any
        if (opt?.dataZoom?.[0]) {
          currentDataZoomRef.current = {
            start: opt.dataZoom[0].start,
            end: opt.dataZoom[0].end
          }
        }
      }

      // 缩放后主图 y 轴跟着 dataZoom 重算可视价格范围（不再被早期低价数据撑开）
      const newBounds = computeKlinePriceBounds()
      if (newBounds) {
        const currentOpt = chart.getOption() as any
        chart.setOption({
          yAxis: (currentOpt.yAxis as any[]).map((y: any, i: number) =>
            i === 0 ? { ...y, min: newBounds.loBound, max: newBounds.hiBound } : y
          )
        })
      }

      refreshChipsPanel()
      loadMoreData()
    })

    // 监听 axisPointer 移动：鼠标划过某根 K 线时，把筹码图切换到该日
    // updateAxisPointer 是 ECharts 内部事件，带有 dataIndex 字段
    // 仅当筹码图启用且有历史数据时绑定，避免关闭后无谓触发 setState
    chart.off('updateAxisPointer')
    if (hasChips && hasChipsHistory) {
      chart.on('updateAxisPointer', (evt: any) => {
        const axesInfo = evt?.axesInfo ?? []
        const xInfo = axesInfo.find((a: any) => a.axisDim === 'x' && typeof a.value !== 'undefined')
        // value 可能是 category（日期字符串）或数字索引；我们主图 xAxis 是 category，value 直接是 dates[i]
        let dateKey: string | null = null
        if (xInfo) {
          if (typeof xInfo.value === 'string') {
            dateKey = removeDateTimePart(xInfo.value)
          } else if (typeof xInfo.value === 'number' && Number.isFinite(xInfo.value)) {
            const idx = Math.round(xInfo.value)
            if (idx >= 0 && idx < dates.length) dateKey = dates[idx]
          }
        }

        const historyMap = chipsHistory as Map<string, ChipItem[]>
        const latestDateKey = (() => {
          const keys = Array.from(historyMap.keys()).sort()
          return keys[keys.length - 1] ?? null
        })()

        // 鼠标离开：dateKey 为 null → 回到最新日
        if (!dateKey) {
          hoverDateRef.current = null
          if (activeChipsDateRef.current !== null) {
            activeChipsDateRef.current = null
            setActiveChipsDateLabel(latestDateKey)
            refreshChipsPanel(null)
          }
          return
        }

        // 同一 dateKey 反复触发时，hoverDateRef 已经是该值，直接早返回避免重复 setState
        if (hoverDateRef.current === dateKey) return
        hoverDateRef.current = dateKey

        const bucket = historyMap.get(dateKey)
        // date 是否已在父组件已拉取的任一区间内（区间已请求过后端，未返回该日 = 后端确认无数据）
        const inFetchedRange = (chipsFetchedRanges ?? []).some(
          r => dateKey >= r.start && dateKey <= r.end
        )

        if (bucket && bucket.length > 0) {
          // 命中且有数据：切换筹码图
          activeChipsDateRef.current = dateKey
          setActiveChipsDateLabel(dateKey)
          refreshChipsPanel(dateKey)
        } else if ((bucket && bucket.length === 0) || inFetchedRange) {
          // 已确认无数据：bucket 为空数组（按需拉取后写入的哨兵）或 date 在已拉区间但 bucket 不存在
          activeChipsDateRef.current = null
          setActiveChipsDateLabel(`${dateKey}（无数据）`)
          clearChipsPanel()
        } else {
          // 未命中且未拉过：badge 显示"加载中"，清空筹码图，触发父组件按需拉取
          activeChipsDateRef.current = null
          setActiveChipsDateLabel(`${dateKey}（加载中…）`)
          clearChipsPanel()
          onChipsDateMiss?.(dateKey)
        }
      })
    }

    // 响应式调整
    const handleResize = () => {
      chart.resize()
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.off('dataZoom')
      chart.off('updateAxisPointer')
    }
  }, [allData, visibleIndicators, hasBOLL, hasKDJ, hasMACD, hasRSI, loadMoreData, backtestMode, signalPoints, equityCurve, hasEquityData, chipsData, chipsHistory, chipsFetchedRanges, theme, palette, echartsTheme])

  // 显示加载状态
  useEffect(() => {
    if (chartInstanceRef.current) {
      if (isLoading) {
        chartInstanceRef.current.showLoading({
          text: '加载更多历史数据...',
          color: '#3b82f6',
          textColor: palette.loadingText,
          maskColor: palette.loadingMask,
          zlevel: 0
        })
      } else {
        chartInstanceRef.current.hideLoading()
      }
    }
  }, [isLoading, palette])

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
    <div className="w-full min-w-0 max-w-full overflow-hidden">
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

              {/* BOLL（叠加在主图） */}
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

              {/* 筹码分布（嵌入主图右侧） */}
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={visibleIndicators.chips}
                  onChange={(e) => setVisibleIndicators({ ...visibleIndicators, chips: e.target.checked })}
                  disabled={!hasChipsData}
                  className="w-5 h-5 text-blue-600 rounded focus:ring-blue-500 disabled:opacity-50"
                />
                <span className={`ml-3 ${hasChipsData ? 'text-gray-900 dark:text-white' : 'text-gray-400 dark:text-gray-600'}`}>
                  筹码分布 {!hasChipsData && '(无数据)'}
                </span>
              </label>

              <p className="text-xs text-gray-500 dark:text-gray-400 pt-2 border-t border-gray-200 dark:border-gray-700">
                MACD / KDJ / RSI 请在图表下方的 Tab 栏切换（业界标准：一次显示一个副图，避免纵向过长）
              </p>
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

      {/* 图表（min-w-0 防止 flex 父级被图表内部宽度撑开） */}
      {/* 相对定位容器，让筹码日期 badge 与复位按钮浮在右上 */}
      <div className="relative min-w-0 max-w-full">
        <div ref={chartRef} className="min-w-0 max-w-full" style={{ width: '100%', height: `${chartHeight}px` }} />
        {/* 复位按钮：把 dataZoom 和缩放重置到默认 70-100 视图 */}
        <button
          type="button"
          onClick={() => {
            const chart = chartInstanceRef.current
            if (!chart) return
            currentDataZoomRef.current = { start: 70, end: 100 }
            chart.dispatchAction({ type: 'dataZoom', start: 70, end: 100 })
          }}
          className="absolute top-1 right-20 px-2 py-0.5 text-[10px] rounded bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors duration-fast focus-ring"
          title="重置缩放视图"
        >
          ⟲ 复位
        </button>
        {activeChipsDateLabel && (
          <div
            className="pointer-events-none absolute top-1 right-2 px-1.5 py-0.5 text-[10px] rounded bg-gray-700/40 dark:bg-gray-200/30 text-gray-100 dark:text-gray-700 tabular-nums"
            title="筹码分布日期（移动鼠标切换）"
          >
            {activeChipsDateLabel}
          </div>
        )}
      </div>

      {/* 技术指标副图 Tab 切换栏（业界标准：底部 Tab 单选 MACD / KDJ / RSI） */}
      <div className="mt-2 flex items-center gap-1 border-t border-gray-200 dark:border-gray-700 pt-2 px-2 overflow-x-auto scrollbar-thin">
        {([
          { key: 'macd' as const, label: 'MACD', available: hasMACD },
          { key: 'kdj' as const,  label: 'KDJ',  available: hasKDJ },
          { key: 'rsi' as const,  label: 'RSI',  available: hasRSI },
        ]).map(tab => {
          const isActive = activeIndicator === tab.key
          const disabled = !tab.available
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => !disabled && !isActive && switchIndicator(tab.key)}
              disabled={disabled}
              className={[
                'px-3 py-1 text-xs rounded-md transition-colors duration-fast whitespace-nowrap tabular-nums focus-ring',
                isActive
                  ? 'bg-blue-600 text-white'
                  : disabled
                    ? 'text-gray-400 dark:text-gray-600 cursor-not-allowed'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
              ].join(' ')}
              aria-pressed={isActive}
              title={disabled ? `${tab.label}（无数据）` : tab.label}
            >
              {tab.label}
            </button>
          )
        })}
      </div>

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
