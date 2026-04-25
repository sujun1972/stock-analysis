'use client'

import { useEffect, useRef, useState, useCallback } from 'react'
import * as echarts from 'echarts'
import { RefreshCw, Settings } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { useEChartsTheme } from '@/hooks/useEChartsTheme'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import {
  formatVolume as formatVolumeUtil,
  formatAmount as formatAmountUtil,
  removeDateTimePart as removeDateTimePartUtil,
  formatDateWithWeekday as formatDateWithWeekdayUtil,
  loadIndicatorSettings,
  saveIndicatorSettings,
  DEFAULT_INDICATORS,
  getLimitPct,
  CHART_HEIGHT_PRESETS,
  type IndicatorSettings,
  type ChartHeightMode,
} from './chart-utils'

/**
 * 规整指标设置：MACD/KDJ/RSI 互斥（业界标准单选），按优先级保留第一个 true 的。
 */
function enforceSingleIndicator(settings: IndicatorSettings): IndicatorSettings {
  const result = { ...settings }
  const order: Array<'macd' | 'kdj' | 'rsi'> = ['macd', 'kdj', 'rsi']
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
  amount?: number | null
  MA5?: number | null
  MA10?: number | null
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
  // 股票名称（用于识别 ST/*ST 以确定涨跌停幅度，可选）
  stockName?: string
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

/**
 * 把日 K 数据按"周（ISO 周）"或"月"聚合：开=组首 open / 收=组末 close / 高=max / 低=min / 量=sum / 额=sum
 * 聚合后 MA 在 ChartData 上重算（基于聚合后的 close）；技术指标（MACD/KDJ/RSI/BOLL）在周/月模式下置 null（用户专注趋势）
 */
function aggregateBars(daily: ChartData[], period: 'W' | 'M'): ChartData[] {
  if (daily.length === 0) return []
  const sorted = [...daily].sort((a, b) =>
    new Date(a.date.split('T')[0].split(' ')[0]).getTime() -
    new Date(b.date.split('T')[0].split(' ')[0]).getTime()
  )
  const groupKeyOf = (dateStr: string): string => {
    const ds = dateStr.split('T')[0].split(' ')[0]
    const d = new Date(ds)
    if (period === 'M') {
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    }
    // ISO 周：复制副本以防修改原对象，把日期归到当周四
    const tmp = new Date(d)
    tmp.setHours(0, 0, 0, 0)
    tmp.setDate(tmp.getDate() + 3 - ((tmp.getDay() + 6) % 7))
    const yearStart = new Date(tmp.getFullYear(), 0, 4)
    const week = 1 + Math.round(((tmp.getTime() - yearStart.getTime()) / 86400000 - 3 + ((yearStart.getDay() + 6) % 7)) / 7)
    return `${tmp.getFullYear()}-W${String(week).padStart(2, '0')}`
  }
  const groups = new Map<string, ChartData[]>()
  for (const d of sorted) {
    const k = groupKeyOf(d.date)
    if (!groups.has(k)) groups.set(k, [])
    groups.get(k)!.push(d)
  }
  const aggregated: ChartData[] = []
  const keys = Array.from(groups.keys()).sort()
  for (const k of keys) {
    const bars = groups.get(k)!
    if (bars.length === 0) continue
    const open = bars[0].open
    const close = bars[bars.length - 1].close
    const high = Math.max(...bars.map(b => b.high))
    const low = Math.min(...bars.map(b => b.low))
    const volume = bars.reduce((a, b) => a + (b.volume || 0), 0)
    const amount = bars.reduce((a, b) => a + (b.amount ?? 0), 0)
    aggregated.push({
      date: bars[bars.length - 1].date,  // 用组内末日作为锚点（同花顺/通达信惯例）
      open, close, high, low, volume, amount,
    })
  }
  // 重算 MA（基于聚合后的 close）
  const closes = aggregated.map(b => b.close)
  const computeSMA = (period: number) => {
    return aggregated.map((_, i) => {
      if (i < period - 1) return null
      let sum = 0
      for (let j = i - period + 1; j <= i; j++) sum += closes[j]
      return +(sum / period).toFixed(4)
    })
  }
  const ma5 = computeSMA(5)
  const ma10 = computeSMA(10)
  const ma20 = computeSMA(20)
  const ma60 = computeSMA(60)
  return aggregated.map((b, i) => ({
    ...b,
    MA5: ma5[i] ?? null,
    MA10: ma10[i] ?? null,
    MA20: ma20[i] ?? null,
    MA60: ma60[i] ?? null,
  }))
}

export default function EChartsStockChart({
  data,
  stockCode,
  stockName,
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
  // 浮层文字测宽：OffscreenCanvas（或 DOM canvas fallback）2D context；按字体+权重+文本缓存宽度
  // 保证 hover 切换时 ≥ 95% 缓存命中率，避免 measureText 频繁触发字体度量
  const chartMeasureCanvasRef = useRef<CanvasRenderingContext2D | OffscreenCanvasRenderingContext2D | null>(null)
  const chartMeasureCacheRef = useRef<Map<string, number>>(new Map())
  if (chartMeasureCanvasRef.current == null && typeof window !== 'undefined') {
    try {
      if (typeof OffscreenCanvas !== 'undefined') {
        chartMeasureCanvasRef.current = new OffscreenCanvas(1, 1).getContext('2d')
      } else {
        chartMeasureCanvasRef.current = document.createElement('canvas').getContext('2d')
      }
    } catch {
      chartMeasureCanvasRef.current = null
    }
  }
  const { theme, echartsTheme, palette } = useEChartsTheme()
  // K 线周期：日 / 周 / 月（同花顺标配；分时和分钟级见任务 20，本期不实现）
  const PERIOD_STORAGE_KEY = 'chart_period:v1'
  const [period, setPeriod] = useState<'D' | 'W' | 'M'>('D')
  // 客户端读取持久化的 period（SSR 安全：首帧 'D'，mount 后再读）
  useEffect(() => {
    if (typeof window === 'undefined') return
    try {
      const saved = localStorage.getItem(PERIOD_STORAGE_KEY)
      if (saved === 'W' || saved === 'M' || saved === 'D') setPeriod(saved)
    } catch {}
  }, [])
  useEffect(() => {
    if (typeof window === 'undefined') return
    try { localStorage.setItem(PERIOD_STORAGE_KEY, period) } catch {}
    // 切换 period 时重置缩放（周/月数据点数显著少于日 K，旧 zoom 百分比失去意义）
    currentDataZoomRef.current = { start: 70, end: 100 }
  }, [period])
  // 用户画线（v1：水平线）：双击锁定，右键删除，localStorage 持久化按 stockCode 隔离
  interface UserLine {
    id: string
    price: number
    createdAt: string
  }
  const userLinesStorageKey = `chart_user_lines:${stockCode}`
  const [userLines, setUserLines] = useState<UserLine[]>([])
  const userLinesRef = useRef<UserLine[]>([])  // ref 供 ECharts 事件回调读最新
  useEffect(() => {
    if (typeof window === 'undefined') { setUserLines([]); return }
    try {
      const saved = localStorage.getItem(userLinesStorageKey)
      const next = saved ? (JSON.parse(saved) as UserLine[]) : []
      setUserLines(Array.isArray(next) ? next : [])
    } catch {
      setUserLines([])
    }
  }, [userLinesStorageKey])
  useEffect(() => {
    userLinesRef.current = userLines
    if (typeof window === 'undefined') return
    try { localStorage.setItem(userLinesStorageKey, JSON.stringify(userLines)) } catch {}
  }, [userLines, userLinesStorageKey])

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
      // updater 在 render/commit 阶段执行——直接调父 setState 会报
      // "Cannot update a component while rendering another"，必须异步派发
      if (onIndicatorsChange) queueMicrotask(() => onIndicatorsChange(next))
      return next
    })
  }

  // 设置对话框显示状态（shadcn Dialog 已内置 body 锁滚动 + Esc 关闭 + 焦点管理）
  const [showSettings, setShowSettings] = useState(false)

  // 检查是否有权益曲线数据
  const hasEquityData = backtestMode && equityCurve && equityCurve.length > 0

  const formatVolume = formatVolumeUtil
  const formatAmount = formatAmountUtil
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
  // 主图高度三档预设（紧凑/标准/宽松，适配 13/15/27 寸屏幕），用户在指标设置弹窗切换
  const MAIN_CHART_HEIGHT = CHART_HEIGHT_PRESETS[visibleIndicators.chartHeightMode ?? 'standard']
  const VOLUME_PANEL_HEIGHT = 140  // 成交量副图高度（量价配合可读性，主图 ~29%）
  const SUB_PANEL_HEIGHT = 130     // 其他副图（MACD/KDJ/RSI）高度
  const PANEL_GAP = 8              // 副图间距——副图已隐顶/底刻度，留 8px 细缝区分面板即可
  const PANEL_INNER_TOP = 6        // 面板内 graphic 图例距 grid 顶的内边距（避开第一条 K 线/Bar）
  const ZOOM_HEIGHT = 0            // DataZoom 滑块已移除，保留常量占位便于未来恢复
  const TOP_PADDING = 10           // 顶部padding
  const BOTTOM_PADDING = 28        // 底部 padding——给 X 轴日期标签预留空间，避免裁剪

  // 动态计算图表总高度（单位：像素）
  // 副图 legend 已内嵌为 graphic 浮层，不再独占图例行高度
  const volumeHeight = visibleIndicators.volume ? (VOLUME_PANEL_HEIGHT + PANEL_GAP) : 0
  const indicatorPanelHeight = showIndicatorPanel ? (SUB_PANEL_HEIGHT + PANEL_GAP) : 0

  // 主图也已用 graphic 浮层取代 legend，TOP_PADDING 后直接接主图，无需 30px 图例占位
  const chartHeight = TOP_PADDING + MAIN_CHART_HEIGHT +
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

  const handleReset = useCallback(() => {
    const chart = chartInstanceRef.current
    if (!chart) return
    currentDataZoomRef.current = { start: 70, end: 100 }
    chart.dispatchAction({ type: 'dataZoom', start: 70, end: 100 })
  }, [])

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
    // 周/月 K 用 aggregateBars 聚合；日 K 直接排序
    const sortedDaily = [...allData].sort((a, b) =>
      new Date(removeDateTimePart(a.date)).getTime() - new Date(removeDateTimePart(b.date)).getTime()
    )
    const sortedData: ChartData[] = period === 'D'
      ? sortedDaily
      : aggregateBars(sortedDaily, period)
    const lastBar = sortedData.length > 0 ? sortedData[sortedData.length - 1] : null

    // 提取日期和数据（格式化日期为 YYYY-MM-DD）
    const dates = sortedData.map(d => {
      const dateStr = d.date
      // 处理 ISO 格式（2026-03-13T00:00:00）或带时间的格式（2026-03-13 00:00:00）
      return dateStr.split('T')[0].split(' ')[0]
    })
    // 涨跌停状态识别（A 股惯例：close 完全等于涨跌停价，精确到 2 位小数）
    // 周/月 K 是聚合数据，涨跌停判定不适用（业界做法：仅日 K 标识）
    const limitPctForStatus = getLimitPct(stockCode, stockName)
    const limitStatus: Array<'up' | 'down' | null> = sortedData.map((d, i) => {
      if (i === 0 || period !== 'D') return null
      const prev = sortedData[i - 1]
      const upPrice = +(prev.close * (1 + limitPctForStatus)).toFixed(2)
      const downPrice = +(prev.close * (1 - limitPctForStatus)).toFixed(2)
      if (Math.abs(d.close - upPrice) < 0.005) return 'up'
      if (Math.abs(d.close - downPrice) < 0.005) return 'down'
      return null
    })
    const ohlcData = sortedData.map((d, i) => {
      const status = limitStatus[i]
      if (!status) return [d.open, d.close, d.low, d.high]
      // 涨停：透明填充 + 红色加粗边框 + 红色发光阴影；跌停：绿色实心 + 加粗边框 + 绿色发光
      const itemStyle = status === 'up'
        ? { color: 'transparent', borderColor: '#ef4444', borderWidth: 2, shadowColor: '#ef4444', shadowBlur: 10 }
        : { color: '#22c55e', borderColor: '#22c55e', borderWidth: 2, shadowColor: '#22c55e', shadowBlur: 10 }
      return { value: [d.open, d.close, d.low, d.high], itemStyle }
    })
    const volumeData = sortedData.map((d, idx) => ({
      value: d.volume,
      itemStyle: {
        color: d.close >= d.open ? '#ef4444' : '#22c55e'
      }
    }))

    // 跳空缺口扫描：前一日 high < 今日 low（向上跳空）/ 前一日 low > 今日 high（向下跳空）
    // 业界标准（同花顺/通达信）：用淡色矩形填充缺口区域，让用户直观看到"是否回补"
    interface Gap { startDate: string; endDate: string; priceMin: number; priceMax: number; up: boolean }
    const gaps: Gap[] = []
    for (let i = 1; i < sortedData.length; i++) {
      const prev = sortedData[i - 1]
      const curr = sortedData[i]
      if (curr.low > prev.high) {
        const gapPct = (curr.low - prev.high) / prev.close
        if (gapPct >= 0.005) {
          gaps.push({ startDate: dates[i - 1], endDate: dates[i], priceMin: prev.high, priceMax: curr.low, up: true })
        }
      } else if (curr.high < prev.low) {
        const gapPct = (prev.low - curr.high) / prev.close
        if (gapPct >= 0.005) {
          gaps.push({ startDate: dates[i - 1], endDate: dates[i], priceMin: curr.high, priceMax: prev.low, up: false })
        }
      }
    }

    // 涨跌停参考线数据（按代码 + 名称识别板块；hover 联动重建 markLine 时也复用）
    // 周/月 K 不显示（涨跌停是日级概念，业界做法）
    const limitPct = getLimitPct(stockCode, stockName)
    const limitRefBar = period === 'D' && sortedData.length >= 2 ? sortedData[sortedData.length - 2] : null
    const limitUp = limitRefBar != null ? +(limitRefBar.close * (1 + limitPct)).toFixed(2) : null
    const limitDown = limitRefBar != null ? +(limitRefBar.close * (1 - limitPct)).toFixed(2) : null
    const limitPctLabel = `${(limitPct * 100).toFixed(0)}%`

    // MA线数据
    const ma5Data = sortedData.map(d => d.MA5 ?? '-')
    const ma10Data = sortedData.map(d => d.MA10 ?? '-')
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

    // 主图与副图均改为 graphic 浮层显示图例（含当前 hover 位的实时数值），
    // ECharts 内置 legend 全部移除——节省垂直空间，且数值随十字线移动实时更新。
    // BOLL 等开关由"指标设置"弹窗控制，不再依赖 legend 点击。
    const legends: any[] = []

    // 是否启用右侧筹码分布面板（A 股看盘软件惯例：K 线主图右侧嵌入横向筹码条）
    // 闸门：① 用户在指标设置中开启 chips ② 有 chipsHistory 或 chipsData 数据
    const hasChipsHistory = chipsHistory instanceof Map && chipsHistory.size > 0
    const hasChips = visibleIndicators.chips && hasChipsData
    // 主图右边距：有筹码图时让出右侧 26% 给它（绘图区 + 右侧价格刻度）
    const MAIN_RIGHT = hasChips ? '26%' : '8%'

    // 构建图表网格，定义每个面板的绘图区域
    // 主图直接接 TOP_PADDING（legend 已移除），副图之间用 PANEL_GAP 留缝
    const MAIN_TOP = TOP_PADDING
    const VOLUME_TOP = MAIN_TOP + MAIN_CHART_HEIGHT + PANEL_GAP
    const grids = [
      {
        left: '8%',
        right: MAIN_RIGHT,
        top: MAIN_TOP,
        height: MAIN_CHART_HEIGHT
      }
    ]

    // 计算副图网格的垂直位置
    let gridTop = VOLUME_TOP

    // 成交量网格（right 与主图保持一致，确保跨面板垂直十字线 x 坐标对齐）
    if (visibleIndicators.volume) {
      grids.push({
        left: '8%',
        right: MAIN_RIGHT,
        top: gridTop,
        height: VOLUME_PANEL_HEIGHT
      })
      gridTop += VOLUME_PANEL_HEIGHT + PANEL_GAP
    }

    // 技术指标副图网格（单选：MACD / KDJ / RSI 三选一共享同一个 grid）
    if (showIndicatorPanel) {
      grids.push({
        left: '8%',
        right: MAIN_RIGHT,
        top: gridTop,
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
      // 上下各留 3% 边距避免紧贴边；再按价格量级把边界 floor/ceil 到 nice step（整数 / 0.5 / 0.1 ...）
      // 让 51.0899 这种长尾浮点对齐成 51 — 否则 y 轴会出现 51.0899 / 53.6451 这种零碎刻度
      const rawLo = klineLow * 0.97
      const rawHi = klineHigh * 1.03
      const range = rawHi - rawLo
      const niceStep = (() => {
        if (range >= 200) return 5
        if (range >= 100) return 2
        if (range >= 50) return 1
        if (range >= 20) return 0.5
        if (range >= 10) return 1
        if (range >= 5) return 0.5
        if (range >= 2) return 0.1
        if (range >= 1) return 0.05
        return 0.01
      })()
      const loBound = Math.floor(rawLo / niceStep) * niceStep
      const hiBound = Math.ceil(rawHi / niceStep) * niceStep
      return { loBound, hiBound }
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

    // 面板内嵌图例浮层（替代 ECharts 内置 legend）
    // 业界惯例（同花顺/东财/富途）：每个面板左上角驻留"指标名 + 当前 hover 位实时数值"，鼠标移动时跟随
    // axisPointer 刷新；离开图表回落到最新一根。每个面板一个 group graphic 元素，id 形如 `legend-${panel}`
    // 便于后续 setOption 用 `replaceMerge: ['graphic']` 增量替换。
    const isPaletteLight = theme !== 'dark'
    const labelColor = isPaletteLight ? '#374151' : '#e5e7eb'
    const dimColor   = isPaletteLight ? '#6b7280' : '#9ca3af'
    // K 线红涨/绿跌（A 股业务约定，参考 frontend CLAUDE.md 语义色规范）：深色下提亮保证 WCAG AA 对比度
    const pick = (light: string, dark: string) => isPaletteLight ? light : dark
    const colorRed     = pick('#ef4444', '#f87171')
    const colorGreen   = pick('#22c55e', '#4ade80')
    const colorBlue    = pick('#3b82f6', '#60a5fa')
    const colorPurple  = pick('#8b5cf6', '#a78bfa')
    const colorAmber   = pick('#f59e0b', '#fbbf24')
    // MA 配色按"明度阶梯"递降，避开 BOLL（粉/青）和 K 线（红/绿）；
    // 经色弱审查（/tmp/kline_color_audit/report.md）调整：
    //   - 深色 MA20 旧值 #f87171 与 K 线红 #f87171 完全撞色（对比度 1.0），改为 #fca5a5（red-300）
    //   - 浅色 MA20 旧值 #dc2626 与 K 线红 #ef4444 仅差 1.28（同色相），改为 amber-900 #78350f 走纯明度阶梯
    //   - MA5/MA10/MA20 重建为同色相（amber/orange）+ 明度递降，色弱下也能区分
    // 深色 MA5 yellow-200 与白色现价线明度极接近 → 降到 amber-400
    const colorMa5     = pick('#fbbf24', '#facc15')   // amber-300 / yellow-400（最亮但不刺眼）
    const colorMa10    = pick('#d97706', '#f97316')   // amber-600 / orange-500（中等）
    const colorMa20    = pick('#78350f', '#c2410c')   // amber-900 / orange-700（最暗）
    const colorMa60    = pick('#7c3aed', '#a78bfa')   // violet-600 / violet-400（紫色拉开）
    // BOLL 上下轨：旧 #db2777/#f472b6 与 K 线红同为暖色调，色弱下混淆，下沉为低饱和粉灰让其"不抢戏"
    const colorBollUp  = pick('#9d174d', '#f9a8d4')   // pink-900 / pink-300
    const colorBollMid = pick('#0891b2', '#22d3ee')   // cyan-600 / cyan-400（保留）
    // 现价线：旧浅色 #f59e0b 对比度 2.15（< AA Large），深色 #fbbf24 与 MA5 撞色
    //   浅色加深至 amber-700；深色 MA 系列已锁 amber/orange，现价线必须跳出该色相 → 用 white 高亮
    //   注：现价线是导航锚，必须最显眼且与所有 MA 区分
    const colorPriceLine = pick('#b45309', '#ffffff') // amber-700 / 纯白
    // 用户画线：浅色 #06b6d4 对比度 2.43（< AA Large）—— 加深；
    // 深色与 BOLL 中轨 cyan-400 撞色 → 改为 sky-500 让明度差更大
    const colorUserLine  = pick('#0e7490', '#0ea5e9') // cyan-700 / sky-500
    // 筹码"接近现价"档：旧 #facc15 在浅色下对比度 1.53（接近不可见）；浅色加深，深色保持
    const colorChipsYellow = pick('#ca8a04', '#facc15') // yellow-600 / yellow-400

    const fmtNum = (v: any, digits = 2): string => {
      if (v == null || v === '-' || (typeof v === 'number' && isNaN(v))) return '--'
      const n = typeof v === 'number' ? v : parseFloat(v)
      return isNaN(n) ? '--' : n.toFixed(digits)
    }

    // 主图浮层：第 1 行 日期+OHLC+涨跌幅，第 2 行 MA5/MA20/MA60+BOLL（按可见性条件渲染）
    const buildMainLegendText = (idx: number): string => {
      if (idx < 0 || idx >= sortedData.length) return ''
      const d = sortedData[idx]
      const prev = idx > 0 ? sortedData[idx - 1] : null
      const isUp = d.close >= d.open
      const priceTag = isUp ? 'red' : 'green'
      let pctStr = '--'
      let pctTag = 'neutral'
      if (prev && prev.close > 0) {
        const pct = ((d.close - prev.close) / prev.close) * 100
        pctStr = (pct >= 0 ? '+' : '') + pct.toFixed(2) + '%'
        pctTag = pct >= 0 ? 'red' : 'green'
      }
      // 第 1 行：日期 + OHLC + 涨跌幅
      const line1: string[] = []
      line1.push(`{title|${formatDateWithWeekday(dates[idx])}}`)
      line1.push(`{label|开}{${priceTag}|${fmtNum(d.open)}}`)
      line1.push(`{label|高}{${priceTag}|${fmtNum(d.high)}}`)
      line1.push(`{label|低}{${priceTag}|${fmtNum(d.low)}}`)
      line1.push(`{label|收}{${priceTag}|${fmtNum(d.close)}}`)
      line1.push(`{${pctTag}|${pctStr}}`)
      // 第 2 行：MA + BOLL（参数标注与同花顺/通达信一致；MA10 是 A 股短线生命线）
      const line2: string[] = []
      const hasAnyMA = d.MA5 != null || d.MA10 != null || d.MA20 != null || d.MA60 != null
      if (hasAnyMA) line2.push('{title|MA(5,10,20,60)}')
      if (d.MA5 != null) line2.push(`{maShort|${fmtNum(d.MA5)}}`)
      if (d.MA10 != null) line2.push(`{maMid10|${fmtNum(d.MA10)}}`)
      if (d.MA20 != null) line2.push(`{maMid|${fmtNum(d.MA20)}}`)
      if (d.MA60 != null) line2.push(`{maLong|${fmtNum(d.MA60)}}`)
      if (visibleIndicators.boll && hasBOLL && d.BOLL_UPPER != null) {
        line2.push('{title|BOLL(20,2)}')
        line2.push(`{bollUp|${fmtNum(d.BOLL_UPPER)}}`)
        line2.push(`{bollMid|${fmtNum(d.BOLL_MIDDLE)}}`)
        line2.push(`{bollLow|${fmtNum(d.BOLL_LOWER)}}`)
      }
      const lines = [line1.join('')]
      if (line2.length > 0) lines.push(line2.join(''))
      return lines.join('\n')
    }

    const buildVolumeLegendText = (idx: number): string => {
      if (idx < 0 || idx >= sortedData.length) return ''
      const d = sortedData[idx]
      const tag = d.close >= d.open ? 'red' : 'green'
      // 量比 = 当日 volume / 前 5 日成交量均值（业界标准：通达信/同花顺）
      let ratioStr = '--'
      let ratioTag: 'red' | 'green' | 'neutral' = 'neutral'
      if (idx >= 5) {
        let sum = 0
        let cnt = 0
        for (let i = idx - 5; i < idx; i++) {
          const v = sortedData[i]?.volume
          if (typeof v === 'number' && !isNaN(v)) { sum += v; cnt++ }
        }
        if (cnt > 0) {
          const avg = sum / cnt
          if (avg > 0) {
            const ratio = d.volume / avg
            ratioStr = ratio.toFixed(2)
            if (ratio >= 1.5) ratioTag = 'red'
            else if (ratio <= 0.7) ratioTag = 'green'
            else ratioTag = 'neutral'
          }
        }
      }
      const segs: string[] = [
        `{title|成交量}{${tag}|${formatVolume(d.volume)}}`,
      ]
      if (d.amount != null) {
        segs.push(`{label|额}{${tag}|${formatAmount(d.amount)}}`)
      }
      segs.push(`{label|量比}{${ratioTag}|${ratioStr}}`)
      return segs.join('')
    }

    const buildMacdLegendText = (idx: number): string => {
      if (idx < 0 || idx >= sortedData.length) return ''
      const d = sortedData[idx]
      const histTag = (d.MACD_HIST ?? 0) >= 0 ? 'red' : 'green'
      return [
        '{title|MACD(12,26,9)}',
        `{label|DIF}{red|${fmtNum(d.MACD)}}`,
        `{label|DEA}{blue|${fmtNum(d.MACD_SIGNAL)}}`,
        `{label|MACD}{${histTag}|${fmtNum(d.MACD_HIST)}}`,
      ].join('')
    }

    const buildKdjLegendText = (idx: number): string => {
      if (idx < 0 || idx >= sortedData.length) return ''
      const d = sortedData[idx]
      return [
        '{title|KDJ(9,3,3)}',
        `{label|K}{blue|${fmtNum(d.KDJ_K)}}`,
        `{label|D}{amber|${fmtNum(d.KDJ_D)}}`,
        `{label|J}{purple|${fmtNum(d.KDJ_J)}}`,
      ].join('')
    }

    const buildRsiLegendText = (idx: number): string => {
      if (idx < 0 || idx >= sortedData.length) return ''
      const d = sortedData[idx]
      return [
        '{title|RSI(6,12,24)}',
        `{label|RSI6}{purple|${fmtNum(d.RSI6)}}`,
        `{label|RSI12}{amber|${fmtNum(d.RSI12)}}`,
        `{label|RSI24}{blue|${fmtNum(d.RSI24)}}`,
      ].join('')
    }

    // 用 rect+多段 text 在面板左上角叠出"浅色半透明面板 + 着色文字"，避免文字被 K 线/bar 遮挡。
    // 不用 ECharts 富文本 rich——某些版本下渲染不可靠（段间距/字色丢失），改用每段一个独立 text 元素累加排版。
    const overlayBg = isPaletteLight ? 'rgba(255,255,255,0.85)' : 'rgba(17,24,39,0.85)'
    const overlayBorder = isPaletteLight ? 'rgba(229,231,235,0.6)' : 'rgba(75,85,99,0.4)'

    type Seg = { text: string; color: string; fontWeight?: number; fontSize: number }
    const segStyles: Record<string, Omit<Seg, 'text'>> = {
      label:   { color: dimColor,   fontSize: 11 },
      neutral: { color: labelColor, fontSize: 11, fontWeight: 600 },
      title:   { color: labelColor, fontSize: 11, fontWeight: 700 },
      maShort: { color: colorMa5,    fontSize: 11, fontWeight: 600 },
      maMid10: { color: colorMa10,   fontSize: 11, fontWeight: 600 },
      maMid:   { color: colorMa20,   fontSize: 11, fontWeight: 600 },
      maLong:  { color: colorMa60,   fontSize: 11, fontWeight: 600 },
      bollUp:  { color: colorBollUp, fontSize: 11, fontWeight: 600 },
      bollMid: { color: colorBollMid,fontSize: 11, fontWeight: 600 },
      bollLow: { color: colorBollUp, fontSize: 11, fontWeight: 600 },
      red:     { color: colorRed,    fontSize: 11, fontWeight: 600 },
      green:   { color: colorGreen,  fontSize: 11, fontWeight: 600 },
      blue:    { color: colorBlue,   fontSize: 11, fontWeight: 600 },
      purple:  { color: colorPurple, fontSize: 11, fontWeight: 600 },
      amber:   { color: colorAmber,  fontSize: 11, fontWeight: 600 },
    }
    // 解析 '{tag|text}文本{tag|text}\n第二行' → Seg[][]（外层数组每项是一行）
    const TAG_RE = /\{([a-zA-Z][a-zA-Z]*)\|([^}]*)\}/g
    const parseRichText = (raw: string): Seg[][] => {
      const lines = raw.split('\n')
      return lines.map(line => {
        const segs: Seg[] = []
        let lastIdx = 0
        let m: RegExpExecArray | null
        TAG_RE.lastIndex = 0
        while ((m = TAG_RE.exec(line)) !== null) {
          if (m.index > lastIdx) {
            // 标签外的纯文本走默认 label 样式
            segs.push({ text: line.slice(lastIdx, m.index), ...segStyles.label })
          }
          const tag = m[1]
          const text = m[2]
          const style = segStyles[tag] ?? segStyles.label
          segs.push({ text, ...style })
          lastIdx = m.index + m[0].length
        }
        if (lastIdx < line.length) {
          segs.push({ text: line.slice(lastIdx), ...segStyles.label })
        }
        return segs
      })
    }

    // 段宽度真实测量：用 OffscreenCanvas（或 fallback DOM canvas）的 measureText
    // 避免 emoji / 全角数字 / 特殊符号在 CJK 1em 启发式下的偏差，浮层背景宽度更精准
    const SEG_PAD_RIGHT = 8
    const LINE_HEIGHT = 16
    const measureSeg = (s: Seg): number => {
      const canvas = chartMeasureCanvasRef.current
      if (!canvas) {
        // SSR / 极端环境兜底：CJK 1em / ASCII 0.6em 启发式
        let w = 0
        for (const ch of s.text) w += ch.charCodeAt(0) < 128 ? s.fontSize * 0.6 : s.fontSize * 1.0
        return w
      }
      const cacheKey = `${s.fontSize}-${s.fontWeight ?? 400}-${s.text}`
      const cache = chartMeasureCacheRef.current
      const hit = cache.get(cacheKey)
      if (hit != null) return hit
      // 字体栈与全局保持一致（拉丁 Inter，CJK 跟系统）；fallback 链让 measureText 选最近字体
      canvas.font = `${s.fontWeight ?? 400} ${s.fontSize}px Inter, "PingFang SC", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif`
      const w = canvas.measureText(s.text).width
      cache.set(cacheKey, w)
      return w
    }

    const buildLegendGraphics = (idx: number): any[] => {
      const elements: any[] = []
      const buildPanel = (panelId: string, topPx: number, raw: string) => {
        const lines = parseRichText(raw)
        // 计算面板背景宽高（取最长一行 + padding）
        const lineWidths = lines.map(line => line.reduce((acc, s) => acc + measureSeg(s) + SEG_PAD_RIGHT, 0))
        const maxLineW = Math.max(0, ...lineWidths) - SEG_PAD_RIGHT  // 末段不加间距
        const totalH = lines.length * LINE_HEIGHT
        const padH = 4
        const padV = 4

        // 背景 group：rect 浅色面板
        const groupChildren: any[] = [
          {
            type: 'rect',
            left: 0,
            top: 0,
            shape: { width: maxLineW + padH * 2, height: totalH + padV * 2, r: 4 },
            style: {
              fill: overlayBg,
              stroke: overlayBorder,
              lineWidth: 1,
            },
            silent: true,
          }
        ]
        // 文字 segs：按行累加 x
        lines.forEach((segs, lineIdx) => {
          let x = padH
          const y = padV + lineIdx * LINE_HEIGHT
          for (const s of segs) {
            if (s.text.length > 0) {
              groupChildren.push({
                type: 'text',
                left: x,
                top: y,
                style: {
                  text: s.text,
                  fill: s.color,
                  fontSize: s.fontSize,
                  fontWeight: s.fontWeight ?? 400,
                  textAlign: 'left',
                  textVerticalAlign: 'top',
                },
                silent: true,
              })
            }
            x += measureSeg(s) + SEG_PAD_RIGHT
          }
        })

        elements.push({
          id: panelId,
          type: 'group',
          left: '9%',
          top: topPx,
          z: 100,
          silent: true,
          children: groupChildren,
        })
      }

      buildPanel('legend-main', MAIN_TOP + PANEL_INNER_TOP, buildMainLegendText(idx))
      let panelTop = VOLUME_TOP
      if (visibleIndicators.volume) {
        buildPanel('legend-volume', panelTop + PANEL_INNER_TOP, buildVolumeLegendText(idx))
        panelTop += VOLUME_PANEL_HEIGHT + PANEL_GAP
      }
      if (showIndicatorPanel) {
        const text = showMACDPanel ? buildMacdLegendText(idx)
                   : showKDJPanel ? buildKdjLegendText(idx)
                   : showRSIPanel ? buildRsiLegendText(idx)
                   : ''
        if (text) buildPanel('legend-indicator', panelTop + PANEL_INNER_TOP, text)
      }
      return elements
    }

    const initialLegendIdx = sortedData.length - 1
    const initialGraphics = buildLegendGraphics(initialLegendIdx)

    const option: echarts.EChartsOption = {
      animation: false,
      backgroundColor: palette.background,
      legend: legends,
      graphic: { elements: initialGraphics } as any,
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
            margin: 10,                            // 与轴线留 10px 间距，避免标签与轴重叠
            hideOverlap: true,                     // 标签密集时自动隐藏溢出的，保留可读性
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
            // 底部日期 pill 隐藏——日期已在主图 graphic 浮层显示，避免重复
            label: { show: false }
          }
        })),
        // 筹码图专用 xAxis：占比百分比（value 类型，与日期轴完全独立）
        // axisLabel 故意隐藏——刻度文字若挂顶端会与主图顶部并列，看似"主图副标题"造成误读；
        // 筹码柱长度本身已直观表达占比，hover tooltip 会显示精确百分比，无需刻度
        ...(hasChips ? [{
          type: 'value' as const,
          gridIndex: chipsGridIndex,
          position: 'top' as const,
          axisLabel: { show: false },
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
          const isKDJPanel = index > 0 && enabledIndicators[index - 1] === 'kdj'
          const isVolumePanel = index > 0 && enabledIndicators[index - 1] === 'volume'

          // KDJ/RSI 固定刻度范围（A 股惯例：0-100 标尺易读；J 值偶尔溢出由参考线 + graphic 浮层数值显示）
          const fixedMin = isMainPanel && mainYAxisMin != null
            ? mainYAxisMin
            : isRSIPanel ? 0
            : isKDJPanel ? 0
            : null
          const fixedMax = isMainPanel && mainYAxisMax != null
            ? mainYAxisMax
            : isRSIPanel ? 100
            : isKDJPanel ? 100
            : null

          const yAxisConfig: any = {
            scale: true,
            gridIndex: index,
            // 主图（K线）：永远用 dataZoom 视图内的 [low*0.97, high*1.03] 锁定 y 轴
            // —— 不依赖 ECharts 的 scale 自动算法，避免视图内空白且与筹码图严格垂直对齐
            // KDJ/RSI 固定 0-100；其他面板显式 null 重置（防止 RSI/KDJ 切换时 min/max 残留）
            min: fixedMin,
            max: fixedMax,
            // KDJ/RSI 固定 0-100 刻度：interval 强制 25（显示 0/25/50/75/100），splitNumber 是建议值
            // 用 interval 才能强制；splitNumber 会被 ECharts nice scale 重写
            ...(isKDJPanel || isRSIPanel ? { interval: 25 } : {}),
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

          // 副图（成交量 / MACD / KDJ / RSI）默认隐藏顶/底边界刻度，避免与相邻面板的边界刻度重叠
          // （成交量底部 500.00万 与 KDJ 顶部 100.00 / 主图底部 50.00 与成交量顶部 4000万 重叠）
          const subPanelLabelExtras = !isMainPanel ? { showMinLabel: false, showMaxLabel: false } : {}

          // 十字线 Y 轴价格 pill：显式 show:true + backgroundColor + padding 让 pill 在 hover 时浮在右轴
          // 对照同花顺/通达信，是十字线"测价"功能的核心；之前因整体覆盖丢失 show:true 导致部分主题下不渲染
          const yAxisPointerPill = (formatter: (params: any) => string) => ({
            show: true,
            formatter,
            backgroundColor: theme === 'dark' ? '#374151' : '#1f2937',
            color: '#fff',
            padding: [3, 6] as [number, number],
            borderRadius: 3,
            fontSize: 11,
          })

          // 成交量Y轴：添加万/亿单位格式化
          if (isVolumePanel) {
            yAxisConfig.axisLabel = {
              ...subPanelLabelExtras,
              formatter: (value: number) => formatVolume(value)
            }
            yAxisConfig.axisPointer.label = yAxisPointerPill((params: any) => formatVolume(params.value))
          } else if (isMainPanel) {
            // 主图（K 线）：刻度统一 2 位小数（A 股价格惯例），避免 51.0899 这种长尾浮点
            // 保留 min/max 边界标签，让用户看到完整价格区间；防重叠靠加大 PANEL_GAP + 副图隐顶底
            yAxisConfig.axisLabel = {
              formatter: (value: number) => Number(value).toFixed(2)
            }
            yAxisConfig.axisPointer.label = yAxisPointerPill((params: any) => Number(params.value).toFixed(2))
          } else {
            // 其他副图（MACD/KDJ/RSI）：刻度保留 2 位小数，避免 ECharts 默认的浮点尾数
            yAxisConfig.axisLabel = {
              ...subPanelLabelExtras,
              formatter: (value: number) => Number(value).toFixed(2)
            }
            yAxisConfig.axisPointer.label = yAxisPointerPill((params: any) => Number(params.value).toFixed(2))
          }

          return yAxisConfig
        }),
        // 筹码图 yAxis：category 类型（每个价位一条 bar），价格由低到高排列。
        // 仅保留落在 K 线价格范围内的档位（见 sortedChips 过滤），
        // 并显示价格刻度（稀疏），让用户能将筹码价位与 K 线价位对齐阅读。
        ...(hasChips ? [(() => {
          // 在所有骨架档中预选目标显示价（每个 step 整数倍取最近的一档），其他档全部隐藏
          // 这样标签数始终 ≤ 8 个，互相不重叠，且对齐到主图相同的整数刻度
          const range = (klineBounds?.hiBound ?? 100) - (klineBounds?.loBound ?? 0)
          const step = range >= 100 ? 10 : range >= 50 ? 5 : range >= 20 ? 5 : range >= 10 ? 2 : range >= 5 ? 1 : 0.5
          const targetIndices = new Set<number>()
          if (sortedChips.length > 0) {
            const lo = sortedChips[0].price
            const hi = sortedChips[sortedChips.length - 1].price
            const startTick = Math.ceil(lo / step) * step
            for (let v = startTick; v <= hi + 1e-9; v += step) {
              // 找到最接近 v 的骨架档索引
              let bestIdx = 0
              let bestDiff = Infinity
              for (let i = 0; i < sortedChips.length; i++) {
                const diff = Math.abs(sortedChips[i].price - v)
                if (diff < bestDiff) { bestDiff = diff; bestIdx = i }
              }
              targetIndices.add(bestIdx)
            }
          }
          const labelInterval = (idx: number, _value: string): boolean => targetIndices.has(idx)
          // 标签格式化：显示整数（避免 76.40 → "76"）
          const labelFormatter = (value: string) => {
            const n = Number(value)
            if (!isFinite(n)) return value
            return step >= 1 ? String(Math.round(n)) : n.toFixed(2)
          }
          return {
            type: 'category' as const,
            gridIndex: chipsGridIndex,
            data: sortedChips.map(d => d.price.toFixed(2)),
            position: 'right' as const,
            axisLabel: {
              show: true,
              fontSize: 10,
              color: '#9ca3af',
              margin: 4,
              interval: labelInterval,
              formatter: labelFormatter
            },
            axisLine: { show: false },
            axisTick: { show: false },
            splitLine: { show: false },
            axisPointer: { show: false },
            inverse: false
          }
        })()] : [])
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
      // tooltip 弹层默认关闭——OHLC / MA / BOLL / 成交量 / 副图当前值已由顶部 graphic 浮层驻留显示，
      // 再弹一个浮窗会遮挡视图且与浮层重复（业界标准 同花顺/东财 的做法）。
      // 仅在回测模式（hasEquityData）保留 tooltip，专门显示权益曲线数据。
      // 注意：必须保留 trigger:'axis' 才能驱动 updateAxisPointer 事件，否则浮层无法跟随 hover 刷新。
      tooltip: {
        trigger: 'axis',
        show: hasEquityData,  // 非回测模式不显示 tooltip 弹层（但 axisPointer 仍触发联动）
        axisPointer: {
          type: 'cross',
          link: [{ xAxisIndex: Array.from({ length: normalGridCount }, (_, i) => i) }],
          crossStyle: {
            color: palette.axisPointerLine,
            width: 1,
            type: 'dashed'
          },
          // 隐藏 axisPointer 弹出的"X 轴日期 pill"——浮层日期已显示
          label: { show: false }
        },
        ...(hasEquityData ? {
          position: (point: number[], _params: any, _dom: any, _rect: any, size: any) => {
            const [mouseX, mouseY] = point
            const viewW = size.viewSize[0]
            const tipW = size.contentSize[0]
            const tipH = size.contentSize[1]
            const mainRightPct = hasChips ? 0.26 : 0.08
            const mainRightBound = viewW * (1 - mainRightPct)
            let x = mouseX + 20
            if (x + tipW > mainRightBound) x = mouseX - tipW - 20
            if (x < 8) x = 8
            const y = mouseY < tipH + 20 ? mouseY + 20 : 10
            return [x, y]
          },
          backgroundColor: palette.tooltipBg,
          borderWidth: 1,
          borderColor: palette.tooltipBorder,
          padding: 10,
          textStyle: { color: palette.tooltipText },
          // 回测模式：仅显示权益曲线段（OHLC 由浮层负责）
          formatter: (params: any) => {
            if (!Array.isArray(params)) return ''
            const equityParam = params.find((p: any) => p.seriesName === '权益曲线')
            if (!equityParam) return ''
            const equity = equityDataForTooltip[equityParam.dataIndex]
            if (!equity) return ''
            return `<div style="font-size:11px;">
              <div style="font-weight:600;color:#ec4899;margin-bottom:3px;">权益曲线</div>
              <div style="color:#9ca3af;">总资产 <span style="color:${palette.tooltipText};">¥${equity.total.toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2})}</span></div>
              <div style="color:#9ca3af;">持仓 <span style="color:${palette.tooltipText};">¥${(equity.holdings || 0).toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2})}</span></div>
              <div style="color:#9ca3af;">现金 <span style="color:${palette.tooltipText};">¥${(equity.cash || 0).toLocaleString('zh-CN',{minimumFractionDigits:2,maximumFractionDigits:2})}</span></div>
            </div>`
          }
        } : {})
      },
      series: (() => {
        const series: any[] = []
        let gridIndex = 1 // 从1开始，因为主图占用gridIndex 0

        // 主图: K线 + MA + BOLL
        // 现价水平虚线：贯穿主图绘图区，让用户瞬间看到当前价位于历史哪个位置（同花顺/东财惯例）
        // 用 [起点, 终点] 两点段显式声明跨主图整个 x 轴，避免 ECharts 把单 yAxis line 截断
        // 涨跌停线（limitUp/limitDown/limitPctLabel）和 lastBar 已在 sortedData 之后于外层算好
        const markLineSegments: any[] = []
        // 现价线只画当前视图右端 30%（业界做法）：缩到 5 年前历史时贯穿整图分散注意力，截短后视觉聚焦
        const computePriceLineStart = (): string => {
          const zoomStart = currentDataZoomRef.current?.start ?? 70
          const zoomEnd = currentDataZoomRef.current?.end ?? 100
          const cutoffPct = zoomStart + (zoomEnd - zoomStart) * 0.7
          const cutoffIdx = Math.max(0, Math.min(dates.length - 1, Math.floor((cutoffPct / 100) * dates.length)))
          return dates[cutoffIdx] ?? dates[0]
        }
        if (lastBar != null) {
          const priceLineStart = computePriceLineStart()
          markLineSegments.push([
            {
              coord: [priceLineStart, lastBar.close],
              symbol: 'none',
              lineStyle: { color: colorPriceLine, width: 1, type: 'dashed', opacity: 0.85 },
              label: {
                show: true,
                position: 'insideEndTop',
                formatter: `现价 ${lastBar.close.toFixed(2)}`,
                color: colorPriceLine,
                fontSize: 10,
                backgroundColor: 'transparent',
              },
            },
            { coord: [dates[dates.length - 1], lastBar.close], symbol: 'none' }
          ])
        }
        if (limitUp != null && limitDown != null) {
          markLineSegments.push([
            {
              coord: [dates[0], limitUp],
              symbol: 'none',
              lineStyle: { color: '#ef4444', width: 1, type: 'dashed', opacity: 0.45 },
              label: {
                show: true,
                position: 'insideEndTop',
                formatter: `涨停 ${limitUp.toFixed(2)} (+${limitPctLabel})`,
                color: '#ef4444',
                fontSize: 10,
                backgroundColor: 'transparent',
              },
            },
            { coord: [dates[dates.length - 1], limitUp], symbol: 'none' }
          ])
          markLineSegments.push([
            {
              coord: [dates[0], limitDown],
              symbol: 'none',
              lineStyle: { color: '#22c55e', width: 1, type: 'dashed', opacity: 0.45 },
              label: {
                show: true,
                position: 'insideEndBottom',
                formatter: `跌停 ${limitDown.toFixed(2)} (-${limitPctLabel})`,
                color: '#22c55e',
                fontSize: 10,
                backgroundColor: 'transparent',
              },
            },
            { coord: [dates[dates.length - 1], limitDown], symbol: 'none' }
          ])
        }
        // 用户画线（v1：水平线）：青色 #06b6d4 实线区分系统线（黄/红/绿）
        for (const line of userLines) {
          markLineSegments.push([
            {
              coord: [dates[0], line.price],
              symbol: 'none',
              lineStyle: { color: colorUserLine, width: 1, type: 'solid' as const, opacity: 0.9 },
              label: {
                show: true,
                position: 'insideEndTop' as const,
                formatter: `${line.price.toFixed(2)}`,
                color: colorUserLine,
                fontSize: 10,
                backgroundColor: 'transparent',
              },
            },
            { coord: [dates[dates.length - 1], line.price], symbol: 'none' }
          ])
        }
        const currentPriceLine = markLineSegments.length > 0
          ? {
              silent: true,
              symbol: 'none',
              data: markLineSegments,
            }
          : null

        series.push(
          {
            name: 'K线',
            type: 'candlestick',
            data: ohlcData,
            xAxisIndex: 0,
            yAxisIndex: 0,
            itemStyle: {
              color: 'transparent',
              color0: '#22c55e',
              borderColor: '#ef4444',
              borderColor0: '#22c55e'
            },
            // 现价水平虚线（无论是否有筹码图都贯穿主图）
            ...(currentPriceLine ? { markLine: currentPriceLine } : {}),
            // 跳空缺口淡色矩形：向上跳空红色 / 向下跳空绿色，opacity 0.15 不抢戏
            ...(gaps.length > 0 ? {
              markArea: {
                silent: true,
                data: gaps.map(g => ([
                  { coord: [g.startDate, g.priceMin], itemStyle: { color: g.up ? '#ef4444' : '#22c55e', opacity: 0.15 } },
                  { coord: [g.endDate, g.priceMax] }
                ]))
              }
            } : {}),
            // 涨跌停"封"/"跌"圆标 + 回测买卖信号合并到同一 markPoint.data，避免冲突
            ...(((backtestMode && (buyMarkPoints.length > 0 || sellMarkPoints.length > 0)) || limitStatus.some(s => s !== null)) ? {
              markPoint: {
                data: [
                  ...buyMarkPoints,
                  ...sellMarkPoints,
                  ...limitStatus.flatMap((s, i) => s ? [{
                    coord: [dates[i], s === 'up' ? sortedData[i].high * 1.012 : sortedData[i].low * 0.988],
                    value: s === 'up' ? '封' : '跌',
                    symbol: 'circle' as const,
                    symbolSize: 14,
                    itemStyle: { color: s === 'up' ? '#ef4444' : '#22c55e', borderColor: '#fff', borderWidth: 1 },
                    label: { show: true, color: '#fff', fontSize: 9, fontWeight: 'bold' as const }
                  }] : [])
                ],
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
              color: colorMa5
            },
            showSymbol: false
          },
          {
            name: 'MA10',
            type: 'line',
            data: ma10Data,
            xAxisIndex: 0,
            yAxisIndex: 0,
            smooth: true,
            lineStyle: {
              opacity: 0.8,
              width: 1,
              color: colorMa10
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
              width: 1.2,
              color: colorMa20
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
              color: colorMa60
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
                color: colorUserLine
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
              yAxisIndex: gridIndex,
              // 0 轴参考线（A 股惯例：DIF 上穿/下穿 0 轴是中长期多空分水岭）
              markLine: {
                silent: true,
                symbol: 'none',
                lineStyle: { color: '#999', type: 'dashed' as const, width: 1 },
                label: { show: false },
                data: [{ yAxis: 0 }]
              }
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
                color: colorPriceLine
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
              else if (d.price > latestClose * 1.01) color = '#fca5a5'
              else color = colorChipsYellow
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
                lineStyle: { color: colorPriceLine, width: 1.5, type: 'dashed' as const },
                label: {
                  formatter: `现价 ${latestClose!.toFixed(2)}`,
                  color: colorPriceLine,
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
    // graphic 用同 id 元素替换内嵌图例文字；网格/series 变化时一并重建
    chart.setOption(option, {
      notMerge: gridChanged,
      replaceMerge: gridChanged
        ? ['grid', 'xAxis', 'yAxis', 'series', 'graphic']
        : (seriesChanged ? ['series', 'yAxis', 'graphic'] : ['graphic'])
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
          else if (d.price > referencePrice * 1.01) color = '#fca5a5'
          else color = colorChipsYellow
        }
        return { value: d.percent, itemStyle: { color, opacity: 0.85 } }
      })
      const currentIdx = referencePrice != null && visible.length > 0
        ? visible.reduce((best, c, i) =>
            Math.abs(c.price - referencePrice) < Math.abs(visible[best].price - referencePrice) ? i : best, 0)
        : -1

      // 与初始构造保持一致的 nice step interval 规则——hover 切换日期时刻度仍对齐到整数
      const chipLabelInterval = (_idx: number, value: string): boolean => {
        const price = Number(value)
        if (!isFinite(price)) return false
        const range = (klineBounds?.hiBound ?? 100) - (klineBounds?.loBound ?? 0)
        const step = range >= 50 ? 5 : range >= 20 ? 2 : range >= 10 ? 2 : range >= 5 ? 1 : 0.5
        return Math.abs(price - Math.round(price / step) * step) < step / 4
      }

      const currentOpt = chart.getOption() as any
      chart.setOption({
        yAxis: (currentOpt.yAxis as any[]).map((y: any, i: number) =>
          i === chipsGridIndex
            ? {
                ...y,
                data: visible.map(d => d.price.toFixed(2)),
                axisLabel: { ...y.axisLabel, interval: chipLabelInterval }
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
            // 现价线起点取视图右端 70% 位置（与初始构造保持一致）
            const zoomStart = currentDataZoomRef.current?.start ?? 70
            const zoomEnd = currentDataZoomRef.current?.end ?? 100
            const cutoffPct = zoomStart + (zoomEnd - zoomStart) * 0.7
            const cutoffIdx = Math.max(0, Math.min(dates.length - 1, Math.floor((cutoffPct / 100) * dates.length)))
            const priceLineStart = dates[cutoffIdx] ?? dates[0]
            const segs: any[] = [
              [
                {
                  coord: [priceLineStart, referencePrice],
                  symbol: 'none',
                  lineStyle: { color: colorPriceLine, width: 1, type: 'dashed' as const, opacity: 0.85 },
                  label: {
                    show: true,
                    position: 'insideEndTop' as const,
                    formatter: `现价 ${referencePrice.toFixed(2)}`,
                    color: colorPriceLine,
                    fontSize: 10,
                    backgroundColor: 'transparent',
                  },
                },
                { coord: [dates[dates.length - 1], referencePrice], symbol: 'none' }
              ]
            ]
            // 涨跌停线在 hover 联动时保留（板块/ST 自适应）
            if (limitUp != null && limitDown != null) {
              segs.push([
                {
                  coord: [dates[0], limitUp],
                  symbol: 'none',
                  lineStyle: { color: '#ef4444', width: 1, type: 'dashed' as const, opacity: 0.45 },
                  label: {
                    show: true,
                    position: 'insideEndTop' as const,
                    formatter: `涨停 ${limitUp.toFixed(2)} (+${limitPctLabel})`,
                    color: '#ef4444',
                    fontSize: 10,
                    backgroundColor: 'transparent',
                  },
                },
                { coord: [dates[dates.length - 1], limitUp], symbol: 'none' }
              ])
              segs.push([
                {
                  coord: [dates[0], limitDown],
                  symbol: 'none',
                  lineStyle: { color: '#22c55e', width: 1, type: 'dashed' as const, opacity: 0.45 },
                  label: {
                    show: true,
                    position: 'insideEndBottom' as const,
                    formatter: `跌停 ${limitDown.toFixed(2)} (-${limitPctLabel})`,
                    color: '#22c55e',
                    fontSize: 10,
                    backgroundColor: 'transparent',
                  },
                },
                { coord: [dates[dates.length - 1], limitDown], symbol: 'none' }
              ])
            }
            // 用户画线在 hover 联动时也保留
            for (const line of userLinesRef.current) {
              segs.push([
                {
                  coord: [dates[0], line.price],
                  symbol: 'none',
                  lineStyle: { color: colorUserLine, width: 1, type: 'solid' as const, opacity: 0.9 },
                  label: {
                    show: true,
                    position: 'insideEndTop' as const,
                    formatter: `${line.price.toFixed(2)}`,
                    color: colorUserLine,
                    fontSize: 10,
                    backgroundColor: 'transparent',
                  },
                },
                { coord: [dates[dates.length - 1], line.price], symbol: 'none' }
              ])
            }
            return {
              ...s,
              markLine: {
                silent: true,
                symbol: 'none',
                data: segs,
              },
              // hover 联动重建 K 线 series 时同步保留缺口标注
              ...(gaps.length > 0 ? {
                markArea: {
                  silent: true,
                  data: gaps.map(g => ([
                    { coord: [g.startDate, g.priceMin], itemStyle: { color: g.up ? '#ef4444' : '#22c55e', opacity: 0.15 } },
                    { coord: [g.endDate, g.priceMax] }
                  ]))
                }
              } : {}),
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

      // 现价线只画视图右端 30% — dataZoom 变化时起点要跟随
      // hasChips 时 refreshChipsPanel 已重建 K 线 markLine；无 chips 时单独重建
      if (!hasChips && lastBar != null) {
        const zoomStart = currentDataZoomRef.current?.start ?? 70
        const zoomEnd = currentDataZoomRef.current?.end ?? 100
        const cutoffPct = zoomStart + (zoomEnd - zoomStart) * 0.7
        const cutoffIdx = Math.max(0, Math.min(dates.length - 1, Math.floor((cutoffPct / 100) * dates.length)))
        const priceLineStart = dates[cutoffIdx] ?? dates[0]
        const segs: any[] = [[
          {
            coord: [priceLineStart, lastBar.close],
            symbol: 'none',
            lineStyle: { color: colorPriceLine, width: 1, type: 'dashed' as const, opacity: 0.85 },
            label: {
              show: true,
              position: 'insideEndTop' as const,
              formatter: `现价 ${lastBar.close.toFixed(2)}`,
              color: colorPriceLine,
              fontSize: 10,
              backgroundColor: 'transparent',
            },
          },
          { coord: [dates[dates.length - 1], lastBar.close], symbol: 'none' }
        ]]
        if (limitUp != null && limitDown != null) {
          segs.push([
            { coord: [dates[0], limitUp], symbol: 'none',
              lineStyle: { color: '#ef4444', width: 1, type: 'dashed' as const, opacity: 0.45 },
              label: { show: true, position: 'insideEndTop' as const, formatter: `涨停 ${limitUp.toFixed(2)} (+${limitPctLabel})`, color: '#ef4444', fontSize: 10, backgroundColor: 'transparent' } },
            { coord: [dates[dates.length - 1], limitUp], symbol: 'none' }
          ])
          segs.push([
            { coord: [dates[0], limitDown], symbol: 'none',
              lineStyle: { color: '#22c55e', width: 1, type: 'dashed' as const, opacity: 0.45 },
              label: { show: true, position: 'insideEndBottom' as const, formatter: `跌停 ${limitDown.toFixed(2)} (-${limitPctLabel})`, color: '#22c55e', fontSize: 10, backgroundColor: 'transparent' } },
            { coord: [dates[dates.length - 1], limitDown], symbol: 'none' }
          ])
        }
        for (const line of userLinesRef.current) {
          segs.push([
            { coord: [dates[0], line.price], symbol: 'none',
              lineStyle: { color: colorUserLine, width: 1, type: 'solid' as const, opacity: 0.9 },
              label: { show: true, position: 'insideEndTop' as const, formatter: `${line.price.toFixed(2)}`, color: colorUserLine, fontSize: 10, backgroundColor: 'transparent' } },
            { coord: [dates[dates.length - 1], line.price], symbol: 'none' }
          ])
        }
        const currentOpt = chart.getOption() as any
        chart.setOption({
          series: (currentOpt.series as any[]).map((s: any) =>
            s.name === 'K线'
              ? { ...s, markLine: { silent: true, symbol: 'none', data: segs } }
              : s
          )
        })
      } else {
        refreshChipsPanel()
      }

      loadMoreData()
    })

    // 监听 axisPointer 移动：
    //  ① 把筹码图切换到鼠标当前日期（仅 hasChips && hasChipsHistory 时启用）
    //  ② 同步刷新所有面板的内嵌图例浮层（OHLC / MA / 成交量 / MACD / KDJ / RSI 当前值）
    chart.off('updateAxisPointer')
    let lastLegendIdx = initialLegendIdx
    chart.on('updateAxisPointer', (evt: any) => {
      const axesInfo = evt?.axesInfo ?? []
      // 找主图 x 轴上的 hover 信息（category 轴）
      const xInfo = axesInfo.find((a: any) => a.axisDim === 'x' && typeof a.value !== 'undefined')
      let hoverIdx: number | null = null
      let dateKey: string | null = null
      if (xInfo) {
        if (typeof xInfo.value === 'string') {
          dateKey = removeDateTimePart(xInfo.value)
          const i = dates.indexOf(dateKey)
          if (i >= 0) hoverIdx = i
        } else if (typeof xInfo.value === 'number' && Number.isFinite(xInfo.value)) {
          const idx = Math.round(xInfo.value)
          if (idx >= 0 && idx < dates.length) {
            hoverIdx = idx
            dateKey = dates[idx]
          }
        }
      }

      // —— 图例浮层刷新 ——（不论是否有筹码图都要做）
      const targetIdx = hoverIdx != null ? hoverIdx : initialLegendIdx
      if (targetIdx !== lastLegendIdx) {
        lastLegendIdx = targetIdx
        chart.setOption({ graphic: { elements: buildLegendGraphics(targetIdx) } } as any)
      }

      // —— 筹码图日期联动 ——
      if (!(hasChips && hasChipsHistory)) return

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
        r => dateKey! >= r.start && dateKey! <= r.end
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

    // 用户画线（v1）：双击主图锁定一条水平虚线，右键删除最近的一条
    // chart.getZr() 提供原生屏幕坐标事件；convertFromPixel 转回 yAxis 价格
    const zr = chart.getZr()
    const handleDblClick = (e: any) => {
      try {
        // 仅响应 K 线主图（gridIndex 0）；筹码图 / 副图忽略
        const point = chart.convertFromPixel({ gridIndex: 0 }, [e.offsetX, e.offsetY])
        if (!point || !Array.isArray(point) || point[1] == null) return
        const price = +Number(point[1]).toFixed(2)
        if (!isFinite(price) || price <= 0) return
        const newLine: UserLine = {
          id: `hline_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
          price,
          createdAt: new Date().toISOString(),
        }
        setUserLines(prev => [...prev, newLine])
      } catch {}
    }
    const handleContextMenu = (e: any) => {
      try {
        const point = chart.convertFromPixel({ gridIndex: 0 }, [e.offsetX, e.offsetY])
        if (!point || point[1] == null) return
        const targetPrice = Number(point[1])
        const yAxisRange = (mainYAxisMax ?? 100) - (mainYAxisMin ?? 0)
        const tolerance = Math.max(yAxisRange * 0.01, 0.05)
        const lines = userLinesRef.current
        let nearestIdx = -1
        let minDelta = Infinity
        for (let i = 0; i < lines.length; i++) {
          const delta = Math.abs(lines[i].price - targetPrice)
          if (delta < tolerance && delta < minDelta) {
            nearestIdx = i
            minDelta = delta
          }
        }
        if (nearestIdx >= 0) {
          if (e.event && typeof e.event.preventDefault === 'function') e.event.preventDefault()
          setUserLines(prev => prev.filter((_, i) => i !== nearestIdx))
        }
      } catch {}
    }
    zr.on('dblclick', handleDblClick)
    zr.on('contextmenu', handleContextMenu)

    // 响应式调整
    const handleResize = () => {
      chart.resize()
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.off('dataZoom')
      chart.off('updateAxisPointer')
      zr.off('dblclick', handleDblClick)
      zr.off('contextmenu', handleContextMenu)
    }
  }, [allData, period, userLines, visibleIndicators, hasBOLL, hasKDJ, hasMACD, hasRSI, loadMoreData, backtestMode, signalPoints, equityCurve, hasEquityData, chipsData, chipsHistory, chipsFetchedRanges, theme, palette, echartsTheme])

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
          <Button variant="outline" size="sm" onClick={() => setShowSettings(true)}>
            <Settings className="w-4 h-4 mr-2" /> 指标设置
          </Button>
        </div>
      )}

      {/* 设置对话框：shadcn Dialog 内置 Esc 关闭 / 遮罩点击 / 焦点循环 / body 锁滚动 */}
      <Dialog
        open={showSettings}
        onOpenChange={(open) => {
          setShowSettings(open)
          if (!open) {
            requestAnimationFrame(() => chartInstanceRef.current?.resize())
          }
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>选择显示的指标</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            <div className="flex items-center gap-3">
              <Checkbox
                id="indicator-volume"
                checked={visibleIndicators.volume}
                onCheckedChange={(v) => setVisibleIndicators({ ...visibleIndicators, volume: v === true })}
              />
              <Label htmlFor="indicator-volume" className="cursor-pointer">成交量 (Volume)</Label>
            </div>
            <div className="flex items-center gap-3">
              <Checkbox
                id="indicator-boll"
                checked={visibleIndicators.boll}
                disabled={!hasBOLL}
                onCheckedChange={(v) => setVisibleIndicators({ ...visibleIndicators, boll: v === true })}
              />
              <Label
                htmlFor="indicator-boll"
                className={hasBOLL ? 'cursor-pointer' : 'cursor-not-allowed text-muted-foreground'}
              >
                布林带 (BOLL) {!hasBOLL && '(无数据)'}
              </Label>
            </div>
            <div className="flex items-center gap-3">
              <Checkbox
                id="indicator-chips"
                checked={visibleIndicators.chips}
                disabled={!hasChipsData}
                onCheckedChange={(v) => setVisibleIndicators({ ...visibleIndicators, chips: v === true })}
              />
              <Label
                htmlFor="indicator-chips"
                className={hasChipsData ? 'cursor-pointer' : 'cursor-not-allowed text-muted-foreground'}
              >
                筹码分布 {!hasChipsData && '(无数据)'}
              </Label>
            </div>
            <p className="text-xs text-muted-foreground pt-2 border-t">
              MACD / KDJ / RSI 请在图表下方的 Tab 栏切换（业界标准：一次显示一个副图，避免纵向过长）
            </p>
            {/* 主图高度三档预设：紧凑（13 寸笔记本）/ 标准 / 宽松（27 寸 4K）*/}
            <div className="pt-3 border-t space-y-2">
              <Label className="text-sm font-medium">主图高度</Label>
              <RadioGroup
                value={visibleIndicators.chartHeightMode ?? 'standard'}
                onValueChange={(v) => setVisibleIndicators({
                  ...visibleIndicators,
                  chartHeightMode: v as ChartHeightMode,
                })}
                className="grid-cols-3 grid"
              >
                {([
                  { v: 'compact', label: '紧凑', hint: '13 寸 / 320px' },
                  { v: 'standard', label: '标准', hint: '默认 / 480px' },
                  { v: 'relaxed', label: '宽松', hint: '4K / 640px' },
                ] as const).map(opt => (
                  <Label
                    key={opt.v}
                    htmlFor={`height-${opt.v}`}
                    className="flex items-center gap-2 cursor-pointer rounded-md border px-2 py-1.5 hover:bg-muted/50 transition-colors duration-fast text-xs"
                  >
                    <RadioGroupItem id={`height-${opt.v}`} value={opt.v} />
                    <span className="flex flex-col leading-tight">
                      <span>{opt.label}</span>
                      <span className="text-muted-foreground text-[10px] tabular-nums">{opt.hint}</span>
                    </span>
                  </Label>
                ))}
              </RadioGroup>
            </div>
          </div>
          <div className="flex justify-end">
            <Button
              onClick={() => {
                setShowSettings(false)
                requestAnimationFrame(() => chartInstanceRef.current?.resize())
              }}
            >
              确定
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* 回测模式提示 */}
      {backtestMode && hasEquityData && (
        <div className="mb-2 px-3 py-2 bg-pink-50 dark:bg-pink-900/20 rounded-md border border-pink-200 dark:border-pink-800">
          <p className="text-xs text-pink-800 dark:text-pink-300">
            💡 粉色线为权益曲线（已归一化到价格范围），可直观看到资产变化与股价走势的关系
          </p>
        </div>
      )}

      {/* 图表（min-w-0 防止 flex 父级被图表内部宽度撑开） */}
      {/* 相对定位容器，让筹码日期 badge 浮在右上 */}
      <div className="relative min-w-0 max-w-full">
        <div ref={chartRef} className="min-w-0 max-w-full" style={{ width: '100%', height: `${chartHeight}px` }} />

        {/* 仅在筹码"加载中"或"无数据"状态显示 badge——常规情况下日期已由主图浮层呈现 */}
        {activeChipsDateLabel && /(加载中|无数据)/.test(activeChipsDateLabel) && (
          <div
            className="pointer-events-none absolute top-1 right-2 px-1.5 py-0.5 text-[10px] rounded bg-gray-700/40 dark:bg-gray-200/30 text-gray-100 dark:text-gray-700 tabular-nums"
            title="筹码分布日期"
          >
            {activeChipsDateLabel}
          </div>
        )}
      </div>

      {/* 底部工具栏：左侧 周期 + MACD/KDJ/RSI 单选 Tab，右侧 1M/3M/6M/1Y/All 快速时间窗 */}
      <div className="mt-2 flex items-center justify-between gap-2 border-t border-gray-200 dark:border-gray-700 pt-2 px-2">
        <div className="flex items-center gap-1 overflow-x-auto scrollbar-thin">
          {/* 周期切换：日 / 周 / 月（同花顺/通达信标配；分钟级见任务 20）*/}
          {([
            { key: 'D' as const, label: '日' },
            { key: 'W' as const, label: '周' },
            { key: 'M' as const, label: '月' },
          ]).map(tab => {
            const isActive = period === tab.key
            return (
              <button
                key={`period-${tab.key}`}
                type="button"
                onClick={() => !isActive && setPeriod(tab.key)}
                className={[
                  'px-2.5 py-1 text-xs rounded-md transition-colors duration-fast whitespace-nowrap tabular-nums focus-ring',
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                ].join(' ')}
                aria-pressed={isActive}
                title={`切换到${tab.label} K`}
              >
                {tab.label}
              </button>
            )
          })}
          <span className="mx-1 h-4 w-px bg-gray-200 dark:bg-gray-700" aria-hidden="true" />
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

        {/* 快速时间窗（业界标准：1M / 3M / 6M / 1Y / All） */}
        <div className="flex items-center gap-0.5 shrink-0">
          {userLines.length > 0 && (
            <button
              type="button"
              onClick={() => setUserLines([])}
              className="px-1.5 py-0.5 text-[11px] rounded text-cyan-600 dark:text-cyan-400 hover:bg-cyan-50 dark:hover:bg-cyan-900/20 transition-colors duration-fast focus-ring mr-1 tabular-nums"
              title="清除全部用户画线（双击空白主图可添加新线，右键单条线可单独删除）"
            >
              清线 {userLines.length}
            </button>
          )}
          <button
            type="button"
            onClick={handleReset}
            className="p-1 rounded text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors duration-fast focus-ring mr-1"
            title="重置缩放视图"
            aria-label="重置缩放视图"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
          {([
            { key: '1M', label: '1月', calendarDays: 30 },
            { key: '3M', label: '3月', calendarDays: 90 },
            { key: '6M', label: '6月', calendarDays: 180 },
            { key: '1Y', label: '1年', calendarDays: 365 },
            { key: 'All', label: '全部', calendarDays: -1 },
          ] as const).map(opt => (
            <button
              key={opt.key}
              type="button"
              onClick={() => {
                const chart = chartInstanceRef.current
                if (!chart) return
                const dataset = allDataRef.current
                const total = dataset.length
                if (total === 0) return
                let start = 0
                const end = 100
                if (opt.calendarDays > 0) {
                  // 用最新一根 K 线的日期作为锚点（避免今天非交易日时锚点漂移）
                  const lastDate = removeDateTimePart(dataset[total - 1].date)
                  const cutoff = new Date(lastDate)
                  cutoff.setDate(cutoff.getDate() - opt.calendarDays)
                  const cutoffStr = cutoff.toISOString().slice(0, 10)
                  const startIdx = dataset.findIndex(d => removeDateTimePart(d.date) >= cutoffStr)
                  start = startIdx >= 0 ? (startIdx / total) * 100 : 0
                }
                currentDataZoomRef.current = { start, end }
                chart.dispatchAction({ type: 'dataZoom', start, end })
                // 'All' 视图触发懒加载续载更早历史
                if (opt.calendarDays === -1) {
                  requestAnimationFrame(() => loadMoreData())
                }
              }}
              className="px-1.5 py-0.5 text-[11px] rounded text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors duration-fast focus-ring tabular-nums"
              title={`显示最近${opt.label}`}
            >
              {opt.key}
            </button>
          ))}
        </div>
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
