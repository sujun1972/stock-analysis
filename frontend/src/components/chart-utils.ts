/**
 * 图表工具函数 - 从 EChartsStockChart 提取的纯函数
 */

/**
 * 格式化成交量：将大数值转换为中国习惯的万/亿单位
 */
export function formatVolume(value: number): string {
  if (value >= 100000000) {
    return (value / 100000000).toFixed(2) + '亿'
  } else if (value >= 10000) {
    return (value / 10000).toFixed(2) + '万'
  }
  return value.toFixed(0)
}

/**
 * 格式化成交额（原始单位：元）：转换为亿元/万元
 */
export function formatAmount(value: number | null | undefined): string {
  if (value == null || isNaN(value)) return '--'
  if (value >= 100000000) return (value / 100000000).toFixed(2) + '亿'
  if (value >= 10000) return (value / 10000).toFixed(2) + '万'
  return value.toFixed(0)
}

/**
 * 去除日期字符串中的时间部分
 */
export function removeDateTimePart(dateStr: string): string {
  return dateStr.split('T')[0].split(' ')[0]
}

/**
 * 格式化日期：添加星期信息
 */
export function formatDateWithWeekday(dateStr: string): string {
  const dateOnly = removeDateTimePart(dateStr)
  const date = new Date(dateOnly)
  const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const weekday = weekdays[date.getDay()]
  return `${year}年${month}月${day}日 ${weekday}`
}

/**
 * 图表布局常量（像素）
 */
export const CHART_LAYOUT = {
  MAIN_CHART_HEIGHT: 400,
  VOLUME_PANEL_HEIGHT: 80,
  INDICATOR_PANEL_HEIGHT: 100,
  GRID_GAP: 30,
  TOP_MARGIN: 60,
  BOTTOM_MARGIN: 40,
  DATAZOOM_HEIGHT: 30,
} as const

/**
 * 根据股票代码 + 名称识别涨跌停幅度（A 股板块差异）
 * - 6xxxxx → 上交所主板（10%），688xxx → 科创板（20%）
 * - 000/001/002/003 → 深交所主板/中小板（10%），300xxx → 创业板（20%）
 * - 4xxxxx / 8xxxxx / 920xxx → 北交所（30%）
 * - ST / *ST → 5%（在前述基础上覆盖）
 */
export function getLimitPct(code: string, name?: string): number {
  if (name) {
    const trimmed = name.trim()
    if (trimmed.startsWith('ST') || trimmed.startsWith('*ST') || trimmed.startsWith('S*ST') || trimmed.includes('ST')) {
      return 0.05
    }
  }
  // 取代码前 3-6 位（兼容 600519 / 600519.SH）
  const numericPart = code.split('.')[0]
  if (numericPart.startsWith('688')) return 0.20
  if (numericPart.startsWith('300') || numericPart.startsWith('301')) return 0.20
  if (numericPart.startsWith('6')) return 0.10
  if (numericPart.startsWith('4') || numericPart.startsWith('8') || numericPart.startsWith('920')) return 0.30
  // 深主板/中小板：000 / 001 / 002 / 003
  return 0.10
}

export interface IndicatorSettings {
  volume: boolean
  macd: boolean
  kdj: boolean
  rsi: boolean
  boll: boolean
  chips: boolean  // 是否在 K 线主图右侧嵌入筹码分布
}

export const DEFAULT_INDICATORS: IndicatorSettings = {
  volume: true,
  macd: true,
  kdj: false,
  rsi: false,
  boll: false,
  chips: true,  // 默认开启筹码分布（数据可用时）
}

/**
 * 从 localStorage 读取指标设置
 */
export function loadIndicatorSettings(): IndicatorSettings {
  if (typeof window !== 'undefined') {
    const saved = localStorage.getItem('chart_visible_indicators')
    if (saved) {
      try {
        // 旧版本可能没有 chips 字段，合并默认值兜底
        return { ...DEFAULT_INDICATORS, ...JSON.parse(saved) }
      } catch {
        // ignore
      }
    }
  }
  return { ...DEFAULT_INDICATORS }
}

/**
 * 保存指标设置到 localStorage
 */
export function saveIndicatorSettings(settings: IndicatorSettings): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem('chart_visible_indicators', JSON.stringify(settings))
  }
}
