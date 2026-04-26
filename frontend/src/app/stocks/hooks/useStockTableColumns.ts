/**
 * 股票列表表格「显示列」偏好管理
 *
 * COLUMN_CONFIGS 是列定义单一数据源：ID / 标签 / 默认可见性 / 分组。
 * 用户偏好持久化到 localStorage（是个人偏好而非可分享状态，不走 URL）。
 *
 * 股票名、操作列为结构性必要，在此不声明——由 page.tsx 的表头/行直接硬渲染。
 */
import { useCallback, useEffect, useState } from 'react'

export type StockColumnId =
  | 'latest_price'
  | 'pct_change'
  | 'amount'
  | 'turnover_rate'
  | 'total_mv'
  | 'pe_ttm'
  | 'score_hot_money'
  | 'score_midline'
  | 'score_longterm'
  | 'score_cio'
  | 'cio_last_date'
  | 'roc'
  | 'earnings_yield'
  | 'intrinsic_margin'
  | 'followup_price'
  | 'followup_time'

export type StockColumnGroup = 'quote' | 'score' | 'cio' | 'value'

export interface StockColumnConfig {
  id: StockColumnId
  label: string
  default: boolean
  group: StockColumnGroup
}

// 列显示顺序以此数组为准。新增列在此追加一行即可
// 默认显示策略：CIO 综合评分作为唯一一档"高度浓缩的 AI 评级"放在量价旁边即可；
// 游资/中线/价值三个 sub-component 评分需要时手动开启，避免首屏 4 列徽章扎堆
// CIO 日期独立成列（默认隐），同时在 score_cio 单元格里以小字脚注顺带显示
export const COLUMN_CONFIGS: readonly StockColumnConfig[] = [
  { id: 'latest_price',     label: '最新价',   default: true,  group: 'quote' },
  { id: 'pct_change',       label: '涨跌幅',   default: true,  group: 'quote' },
  { id: 'amount',           label: '成交额',   default: true,  group: 'quote' },
  { id: 'turnover_rate',    label: '换手率',   default: true,  group: 'quote' },
  { id: 'total_mv',         label: '总市值',   default: true,  group: 'quote' },
  { id: 'pe_ttm',           label: 'PE-TTM',  default: true,  group: 'quote' },
  { id: 'score_hot_money',  label: '游资',     default: false, group: 'score' },
  { id: 'score_midline',    label: '中线',     default: false, group: 'score' },
  { id: 'score_longterm',   label: '价值',     default: false, group: 'score' },
  { id: 'score_cio',        label: 'CIO评分',  default: true,  group: 'score' },
  { id: 'cio_last_date',    label: 'CIO日期',  default: false, group: 'cio' },
  { id: 'roc',              label: 'ROC',     default: true,  group: 'value' },
  { id: 'earnings_yield',   label: '收益率',   default: true,  group: 'value' },
  { id: 'intrinsic_margin', label: '安全边际', default: true,  group: 'value' },
  { id: 'followup_price',   label: '关注价格', default: false, group: 'cio' },
  { id: 'followup_time',    label: '关注时间', default: false, group: 'cio' },
] as const

// 分组在菜单中的展示顺序（也是 UI 内部的分组渲染顺序）
export const COLUMN_GROUP_ORDER: readonly StockColumnGroup[] = ['quote', 'score', 'cio', 'value'] as const

export const COLUMN_GROUP_LABELS: Record<StockColumnGroup, string> = {
  quote: '行情',
  score: 'AI 评分',
  cio: 'CIO 跟踪',
  value: '价值度量',
}

// 版本号 bump 到 v3：v2→v3 默认列集合再次调整（cio_last_date 加回但默认隐；游资/中线/价值改默认隐）
// bump 一次让所有用户回到最新默认视图，避免"半新半旧"局面
const STORAGE_KEY = 'stocks:visible-columns:v3'

const KNOWN_IDS: ReadonlySet<StockColumnId> = new Set(COLUMN_CONFIGS.map(c => c.id))

function getDefaults(): Set<StockColumnId> {
  return new Set(COLUMN_CONFIGS.filter(c => c.default).map(c => c.id))
}

// 存储的是"当前可见列 id"的精确列表。读取时过滤掉已废弃的列 id（KNOWN_IDS 外的）。
// 新增列对老用户不会自动显示——他们的 localStorage 里没有这个 id 即隐藏；
// 用户可通过"恢复默认"按钮一键把新列纳入。这是 Linear/Notion 等的惯例，胜在可预期
function readFromStorage(): Set<StockColumnId> | null {
  if (typeof window === 'undefined') return null
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return null
    return new Set<StockColumnId>(
      parsed.filter((id): id is StockColumnId => typeof id === 'string' && KNOWN_IDS.has(id as StockColumnId))
    )
  } catch {
    return null
  }
}

export function useStockTableColumns() {
  // SSR 安全：首帧用默认值，mount 后从 localStorage 恢复，避免 hydration mismatch
  const [visible, setVisible] = useState<Set<StockColumnId>>(getDefaults)

  useEffect(() => {
    const stored = readFromStorage()
    if (stored) setVisible(stored)
  }, [])

  const persist = useCallback((next: Set<StockColumnId>) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(Array.from(next)))
    } catch {
      // 静默失败（隐私模式 / 配额爆），内存中状态仍生效
    }
  }, [])

  const toggle = useCallback((id: StockColumnId) => {
    setVisible(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      persist(next)
      return next
    })
  }, [persist])

  const resetToDefault = useCallback(() => {
    const next = getDefaults()
    setVisible(next)
    persist(next)
  }, [persist])

  const isVisible = useCallback((id: StockColumnId) => visible.has(id), [visible])

  return { visible, isVisible, toggle, resetToDefault }
}
