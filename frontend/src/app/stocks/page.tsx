'use client'

import { useEffect, useState, useMemo, useCallback, useRef, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api-client'
import { useStockStore } from '@/stores/stock-store'
import { useAuthStore } from '@/stores/auth-store'
import { useStockListStore } from '@/stores/stock-list-store'
import { Card, CardContent } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
} from '@/components/ui/pagination'
import {
  ChevronLeft,
  ChevronRight,
  BookmarkPlus,
  Trash2,
  Pencil,
  X,
  ChevronDown,
  ChevronUp,
  Filter,
  Sparkles,
  Loader2,
  ArrowUpDown,
} from 'lucide-react'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { useSmartRefresh } from '@/hooks/useMarketStatus'
import { LazyConceptSelect } from '@/components/stocks/LazyConceptSelect'
import { AddToListDialog } from './components/AddToListDialog'
import { RenameListDialog } from './components/RenameListDialog'
import { StockTableRow } from './components/StockTableRow'
import { StockCard } from './components/StockCard'
import { BatchAnalysisDialog } from './components/BatchAnalysisDialog'
import { ColumnVisibilityMenu } from './components/ColumnVisibilityMenu'
import { useStockTableColumns } from './hooks/useStockTableColumns'
import { StockTableSkeleton, StockCardSkeleton } from '@/components/shared/Skeleton'
import { SortIndicator } from '@/components/shared'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import type { StockList, StockInfo } from '@/types'
import type { Strategy } from '@/types/strategy'
import { toast } from 'sonner'

// ── 辅助函数 ──────────────────────────────────────────────────
function toTsCode(code: string): string {
  if (code.includes('.')) return code.toUpperCase()
  if (code.startsWith('6')) return `${code}.SH`
  if (code.startsWith('4') || code.startsWith('8')) return `${code}.BJ`
  return `${code}.SZ`
}

// 多列排序：URL 序列化协议 'key:order,key:order,...'
type SortKey = { key: string; order: 'asc' | 'desc' }

const DEFAULT_SORT: SortKey[] = [{ key: 'pct_change', order: 'desc' }]

function parseSortParam(raw: string | null): SortKey[] {
  if (!raw) return DEFAULT_SORT
  const parsed: SortKey[] = []
  const seen = new Set<string>()
  raw.split(',').forEach((chunk) => {
    const s = chunk.trim()
    if (!s) return
    const [k, o] = s.includes(':') ? s.split(':') : [s, 'desc']
    const key = k.trim()
    if (!key || seen.has(key)) return
    parsed.push({ key, order: o?.trim().toLowerCase() === 'asc' ? 'asc' : 'desc' })
    seen.add(key)
  })
  return parsed.length ? parsed : DEFAULT_SORT
}

function serializeSort(keys: SortKey[]): string {
  return keys.map((k) => `${k.key}:${k.order}`).join(',')
}

function isDefaultSort(keys: SortKey[]): boolean {
  return keys.length === 1 && keys[0].key === DEFAULT_SORT[0].key && keys[0].order === DEFAULT_SORT[0].order
}

// 市场筛选值 → 中文 chip 文案（与 filtersGrid 中 SelectItem 的 value/label 对齐）
const MARKET_LABELS: Record<string, string> = {
  SSE: '上海主板',
  SZSE: '深圳主板',
  创业板: '创业板',
  科创板: '科创板',
  北交所: '北交所',
}

// 计算下一轮排序状态（纯函数，便于推理 / 测试）
// - 普通点击：单列循环 desc → asc → 默认排序
// - Shift+点击：在现有列表中追加；已存在则该列方向循环 desc → asc → 移除
function computeNextSort(prev: SortKey[], key: string, shift: boolean): SortKey[] {
  const idx = prev.findIndex((s) => s.key === key)
  if (shift) {
    if (idx < 0) return [...prev, { key, order: 'desc' }]
    if (prev[idx].order === 'desc') {
      return prev.map((s, i) => (i === idx ? { ...s, order: 'asc' as const } : s))
    }
    const removed = prev.filter((_, i) => i !== idx)
    return removed.length ? removed : DEFAULT_SORT
  }
  if (prev.length === 1 && prev[0].key === key) {
    return prev[0].order === 'desc' ? [{ key, order: 'asc' }] : DEFAULT_SORT
  }
  return [{ key, order: 'desc' }]
}

// 表头排序按钮：显示标签 + 方向箭头；多列排序时附带优先级数字角标
// 关键：indicator 槽位**始终保留**，未激活显示淡灰双向箭头，激活显示主色单向箭头。
// 这样切换排序状态时按钮宽度恒定，避免列宽抖动；同时给可排序列一个视觉提示
function SortHeaderButton({
  sortKey,
  label,
  sortKeys,
  onClick,
}: {
  sortKey: string
  label: string
  sortKeys: SortKey[]
  onClick: (key: string, event?: React.MouseEvent) => void
}) {
  const idx = sortKeys.findIndex((s) => s.key === sortKey)
  const active = idx >= 0
  const order = active ? sortKeys[idx].order : 'desc'
  const showPriority = active && sortKeys.length > 1
  // 动态 aria-label 告知屏幕阅读器当前排序状态（未排序 / 升 / 降 + 多列优先级）
  const stateText = !active ? '当前未排序' : order === 'desc' ? '当前降序' : '当前升序'
  const ariaLabel = `按${label}排序，${stateText}${showPriority ? `，优先级第 ${idx + 1}` : ''}`
  return (
    <button
      type="button"
      onClick={(e) => onClick(sortKey, e)}
      className="inline-flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-200 focus-ring rounded-sm"
      aria-label={ariaLabel}
      title="点击单列排序；Shift+点击 追加为次级排序键"
    >
      {label}
      {/* 占位槽位：未激活淡灰双向，激活主色单向。固定 12px 宽，保宽度恒定 */}
      <span className="inline-flex w-3 justify-center shrink-0">
        {active
          ? <SortIndicator order={order} className="h-3 w-3 text-info" />
          : <ArrowUpDown className="h-3 w-3 text-gray-300 dark:text-gray-600" />
        }
      </span>
      {showPriority && (
        <span className="ml-0.5 inline-flex items-center justify-center w-3.5 h-3.5 rounded-full text-[9px] font-bold bg-primary/15 text-primary">
          {idx + 1}
        </span>
      )}
    </button>
  )
}

// ── 主页面 ────────────────────────────────────────────────────
function StocksPageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()

  // ── 从 URL 初始化所有筛选 / 分页状态 ──
  const stockSelectionStrategyId = searchParams.get('stock_selection_strategy_id')

  const { stocks, setStocks, setLoading, isLoading, error, setError } = useStockStore()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const { lists, fetchLists, deleteList, removeStocks } = useStockListStore()
  // 首次加载用骨架屏，后续 loading（排序/翻页/筛选）退化为轻量 spinner 避免 CLS
  const [isFirstLoad, setIsFirstLoad] = useState(true)

  const activeListId = searchParams.get('list') ? Number(searchParams.get('list')) : null

  // ── 筛选 / 分页状态 ──
  const [marketFilter, setMarketFilter] = useState<string>(() => searchParams.get('market') ?? 'all')
  const [stockSelectionStrategies, setStockSelectionStrategies] = useState<Strategy[]>([])
  const [industryFilter, setIndustryFilter] = useState<string>(() => searchParams.get('industry') ?? 'all')
  const [conceptFilter, setConceptFilter] = useState<string>(() => searchParams.get('concept') ?? 'all')
  const [currentPage, setCurrentPage] = useState(() => Number(searchParams.get('page') ?? '1'))
  const [totalStocks, setTotalStocks] = useState(0)
  const [pageSize, setPageSize] = useState(() => Number(searchParams.get('pageSize') ?? '20'))
  // 多列排序：URL 优先读 'sort'；缺省时回退兼容旧 'sortBy'/'sortOrder'；都没有则用默认
  const [sortKeys, setSortKeys] = useState<SortKey[]>(() => {
    const raw = searchParams.get('sort')
    if (raw !== null) return parseSortParam(raw)
    const legacyBy = searchParams.get('sortBy')
    if (legacyBy) {
      const legacyOrder = (searchParams.get('sortOrder') === 'asc') ? 'asc' : 'desc'
      return [{ key: legacyBy, order: legacyOrder }]
    }
    return DEFAULT_SORT
  })
  const [industries, setIndustries] = useState<{ value: string; label: string; count: number }[]>([])

  // ── URL 同步 ──
  const updateURL = useCallback((patch: Record<string, string | number | null>) => {
    const params = new URLSearchParams(searchParams.toString())
    // 旧 sortBy/sortOrder 已废弃；首次更新 URL 时顺手清掉，避免遗留
    params.delete('sortBy')
    params.delete('sortOrder')
    const defaults: Record<string, string | number> = { pageSize: 20, page: 1 }
    for (const [key, value] of Object.entries(patch)) {
      if (value === null || value === '' || value === 'all' || value === defaults[key]) {
        params.delete(key)
      } else {
        params.set(key, String(value))
      }
    }
    router.replace(`/stocks?${params.toString()}`, { scroll: false })
  }, [searchParams, router])

  // ── 选股状态 ──
  const [selectedCodes, setSelectedCodes] = useState<Set<string>>(new Set())

  // ── 表格显示列偏好（localStorage 持久化） ──
  const { visible: visibleColumns, isVisible, toggle: toggleColumn, resetToDefault: resetColumns } = useStockTableColumns()

  // ── Dialog 状态 ──
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [renameDialogOpen, setRenameDialogOpen] = useState(false)
  const [renameTarget, setRenameTarget] = useState<StockList | null>(null)
  const [batchAnalysisOpen, setBatchAnalysisOpen] = useState(false)
  // 批量分析"分析中"集合：仅用于轮询时检测"刚结束"以触发列表静默刷新（拉新评分）。
  // 不再展示在 UI 上（行级 AI 分析按钮已移除），用 ref 避免每 3s 触发组件重渲染
  const analyzingTsCodesRef = useRef<Set<string>>(new Set())
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false)
  const [filtersCollapsed, setFiltersCollapsed] = useState<boolean>(() => searchParams.get('filters') === 'collapsed')

  const user = useAuthStore((s) => s.user)

  // ── 加载行业列表 ──
  useEffect(() => {
    apiClient.getStockIndustries().then(setIndustries).catch(() => {})
  }, [])

  // ── 加载选股策略列表 ──
  useEffect(() => {
    const fetchStrategies = async () => {
      try {
        const [publishedRes, myRes] = await Promise.all([
          apiClient.getStrategies({ strategy_type: 'stock_selection', publish_status: 'approved', is_enabled: true }),
          user?.id ? apiClient.getStrategies({ strategy_type: 'stock_selection', user_id: user.id }) : Promise.resolve(null),
        ])
        const extractStrategies = (res: { data?: unknown } | null): Strategy[] => {
          const data = res?.data as { items?: Strategy[] } | Strategy[] | undefined
          if (Array.isArray(data)) return data
          if (data && 'items' in data) return data.items ?? []
          return []
        }
        const published = extractStrategies(publishedRes)
        const mine = extractStrategies(myRes)
        const merged = [...mine]
        const myIds = new Set(mine.map((s) => s.id))
        published.forEach((s) => { if (!myIds.has(s.id)) merged.push(s) })
        setStockSelectionStrategies(merged)
      } catch {
        // silent
      }
    }
    fetchStrategies()
  }, [user?.id])

  // ── 已登录时加载自选列表 ──
  useEffect(() => {
    if (isAuthenticated) fetchLists()
  }, [isAuthenticated, fetchLists])

  // ── 股票列表加载 ──
  // silent=true 的静默刷新只更新当前已显示行的数据（按 ts_code 定向拉取 + 原位合并），
  // 不改变行的集合和顺序，也不改变 totalStocks，避免翻页/排序状态被异步刷新打乱
  const fetchStocks = useCallback(async (silent: boolean = false) => {
    try {
      if (!silent) setLoading(true)
      setError(null)

      if (silent) {
        const existing = useStockStore.getState().stocks
        const displayedTsCodes = Array.isArray(existing)
          ? existing.map((s) => s.ts_code || toTsCode(s.code)).filter(Boolean)
          : []
        if (displayedTsCodes.length === 0) return
        const response = await apiClient.getStockList({
          ts_codes: displayedTsCodes.join(','),
          limit: displayedTsCodes.length,
          list_status: 'L',
          include_analysis: true,
        })
        const fetched = response.items || []
        const byCode = new Map(fetched.map((s: StockInfo) => [s.code, s]))
        const merged = existing.map((prev) => {
          const next = byCode.get(prev.code)
          return next ? { ...prev, ...next } : prev
        })
        setStocks(merged)
        return
      }

      const params: Record<string, string | number | boolean> = {
        skip: (currentPage - 1) * pageSize,
        limit: pageSize,
        sort: serializeSort(sortKeys),
        list_status: 'L',
        include_analysis: true,
      }
      if (marketFilter === 'SSE') { params.market = '主板'; params.exchange = 'SSE' }
      else if (marketFilter === 'SZSE') { params.market = '主板'; params.exchange = 'SZSE' }
      else if (marketFilter !== 'all') { params.market = marketFilter }
      if (industryFilter !== 'all') params.industry = industryFilter
      if (conceptFilter !== 'all') params.concept_code = conceptFilter
      if (stockSelectionStrategyId) params.stock_selection_strategy_id = Number(stockSelectionStrategyId)
      if (activeListId !== null) params.user_stock_list_id = activeListId

      const response = await apiClient.getStockList(params)
      setStocks(response.items || [])
      setTotalStocks(response.total ?? 0)
    } catch (err: unknown) {
      const e = err as { message?: string }
      setError(e.message || '加载股票列表失败')
      if (!silent) { setStocks([]); setTotalStocks(0) }
    } finally {
      if (!silent) {
        setLoading(false)
        setIsFirstLoad(false)
      }
    }
  }, [currentPage, marketFilter, industryFilter, conceptFilter, pageSize, sortKeys, stockSelectionStrategyId, activeListId, setStocks, setLoading, setError])

  const loadStocks = useCallback(() => fetchStocks(false), [fetchStocks])

  useEffect(() => {
    loadStocks()
  }, [loadStocks])

  // 筛选条件变化时清空已选（结果集变了，旧选择可能不再属于当前集合）；翻页 / 排序不清空，支持跨页累积选择
  useEffect(() => {
    setSelectedCodes(new Set())
  }, [marketFilter, industryFilter, conceptFilter, pageSize, stockSelectionStrategyId, activeListId])

  // ── 智能刷新 ──
  const currentPageCodes = useMemo(() => {
    if (!Array.isArray(stocks)) return []
    return stocks.map((s) => s.code)
  }, [stocks])

  const currentPageCodesRef = useRef<string[]>(currentPageCodes)
  useEffect(() => { currentPageCodesRef.current = currentPageCodes }, [currentPageCodes])

  const refreshCallback = useCallback(async () => {
    const codes = currentPageCodesRef.current
    if (codes.length > 0) {
      await apiClient.syncRealtimeQuotes({ codes, batch_size: codes.length })
    }
    await fetchStocks(true)
  }, [fetchStocks])

  useSmartRefresh(refreshCallback, currentPageCodes, true)

  // ── 批量分析"分析中"股票轮询（每 3 秒） ──
  // 检测到某只股票"刚从分析中移除"时，触发列表静默刷新拉取最新评分
  useEffect(() => {
    if (!isAuthenticated) {
      analyzingTsCodesRef.current = new Set()
      return
    }
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | null = null
    const tick = async () => {
      try {
        const res = await apiClient.getActiveBatchTsCodes()
        if (cancelled) return
        const nextCodes: string[] = res?.data?.ts_codes ?? []
        const next = new Set(nextCodes)
        let removedAny = false
        analyzingTsCodesRef.current.forEach((ts) => { if (!next.has(ts)) removedAny = true })
        analyzingTsCodesRef.current = next
        if (removedAny) fetchStocks(true)
      } catch {
        // 静默失败，下个 tick 重试
      }
      if (!cancelled) timer = setTimeout(tick, 3000)
    }
    tick()
    return () => {
      cancelled = true
      if (timer) clearTimeout(timer)
    }
  }, [isAuthenticated, fetchStocks])

  const totalPages = Math.ceil((totalStocks ?? 0) / pageSize)

  // ── 全选 ──
  const displayedStocks = Array.isArray(stocks) ? stocks : []
  const displayedTsCodes = useMemo(
    () => displayedStocks.map((s) => toTsCode(s.code)),
    [displayedStocks]
  )
  const allCurrentPageSelected =
    displayedTsCodes.length > 0 && displayedTsCodes.every((c) => selectedCodes.has(c))
  const someCurrentPageSelected =
    displayedTsCodes.some((c) => selectedCodes.has(c)) && !allCurrentPageSelected

  const toggleSelectAll = useCallback(() => {
    if (allCurrentPageSelected) {
      setSelectedCodes((prev) => {
        const next = new Set(prev)
        displayedTsCodes.forEach((c) => next.delete(c))
        return next
      })
    } else {
      setSelectedCodes((prev) => {
        const next = new Set(prev)
        displayedTsCodes.forEach((c) => next.add(c))
        return next
      })
    }
  }, [allCurrentPageSelected, displayedTsCodes])

  const goToPage = useCallback((page: number) => {
    setCurrentPage(page)
    updateURL({ page })
  }, [updateURL])

  const [selectingAll, setSelectingAll] = useState(false)

  const handleSelectAllFiltered = useCallback(async () => {
    setSelectingAll(true)
    try {
      // limit 需覆盖全市场股票数 + 余量；后端 /codes/filtered 硬上限 10000
      const params: Parameters<typeof apiClient.getStockCodes>[0] = { list_status: 'L', limit: 10000 }
      if (marketFilter === 'SSE') { params.market = '主板'; params.exchange = 'SSE' }
      else if (marketFilter === 'SZSE') { params.market = '主板'; params.exchange = 'SZSE' }
      else if (marketFilter !== 'all') { params.market = marketFilter }
      if (industryFilter !== 'all') params.industry = industryFilter
      if (conceptFilter !== 'all') params.concept_code = conceptFilter
      if (stockSelectionStrategyId) params.stock_selection_strategy_id = Number(stockSelectionStrategyId)
      if (activeListId !== null) params.user_stock_list_id = activeListId

      const result = await apiClient.getStockCodes(params)
      setSelectedCodes((prev) => {
        const next = new Set(prev)
        result.codes.forEach((c) => next.add(c))
        return next
      })
      if (result.total > result.codes.length) {
        toast.warning(`已选中 ${result.codes.length} 只，筛选结果共 ${result.total} 只（单次上限 ${result.codes.length}），如需更多请缩小筛选范围`)
      } else {
        toast.success(`已选中全部 ${result.codes.length} 只股票`)
      }
    } catch (err: unknown) {
      const e = err as { message?: string }
      toast.error(e?.message || '获取全部股票失败')
    } finally {
      setSelectingAll(false)
    }
  }, [marketFilter, industryFilter, conceptFilter, stockSelectionStrategyId, activeListId])

  const toggleStock = useCallback((tsCode: string) => {
    setSelectedCodes((prev) => {
      const next = new Set(prev)
      if (next.has(tsCode)) next.delete(tsCode)
      else next.add(tsCode)
      return next
    })
  }, [])

  const handleRemoveFromList = useCallback(async () => {
    if (!activeListId || selectedCodes.size === 0) return
    try {
      const result = await removeStocks(activeListId, Array.from(selectedCodes))
      setSelectedCodes(new Set())
      toast.success(`已从列表移除 ${result.removed} 只股票`)
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      toast.error(e?.response?.data?.detail || '移除失败')
    }
  }, [activeListId, selectedCodes, removeStocks])

  const handleDeleteList = useCallback(async (listId: number) => {
    if (!confirm('确定要删除这个列表吗？列表中的股票记录也会一并删除。')) return
    try {
      await deleteList(listId)
      toast.success('列表已删除')
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      toast.error(e?.response?.data?.detail || '删除失败')
    }
  }, [deleteList])

  // 移动端激活筛选数（用于 Drawer 按钮徽章）
  const activeFilterCount = useMemo(() => {
    let n = 0
    if (marketFilter !== 'all') n++
    if (industryFilter !== 'all') n++
    if (conceptFilter !== 'all') n++
    if (stockSelectionStrategyId) n++
    if (activeListId !== null) n++
    return n
  }, [marketFilter, industryFilter, conceptFilter, stockSelectionStrategyId, activeListId])

  // 折叠态展示的激活筛选 chips；label 优先展示人类可读名（行业/策略/列表），
  // 兜底回 raw value。`onClear` 只负责清掉自己这一维，避免与 handleClearAllFilters 耦合
  const activeFilterChips = useMemo(() => {
    const chips: { key: string; label: string; onClear: () => void }[] = []
    if (marketFilter !== 'all') {
      chips.push({
        key: 'market',
        label: `市场: ${MARKET_LABELS[marketFilter] ?? marketFilter}`,
        onClear: () => { setMarketFilter('all'); setCurrentPage(1); updateURL({ market: null, page: null }) },
      })
    }
    if (industryFilter !== 'all') {
      const ind = industries.find((i) => i.value === industryFilter)
      chips.push({
        key: 'industry',
        label: `行业: ${ind?.label ?? industryFilter}`,
        onClear: () => { setIndustryFilter('all'); setCurrentPage(1); updateURL({ industry: null, page: null }) },
      })
    }
    if (conceptFilter !== 'all') {
      chips.push({
        key: 'concept',
        label: `板块: ${conceptFilter}`,
        onClear: () => { setConceptFilter('all'); setCurrentPage(1); updateURL({ concept: null, page: null }) },
      })
    }
    if (stockSelectionStrategyId) {
      const strat = stockSelectionStrategies.find((s) => String(s.id) === stockSelectionStrategyId)
      chips.push({
        key: 'strategy',
        label: `策略: ${strat?.display_name ?? stockSelectionStrategyId}`,
        onClear: () => { setCurrentPage(1); updateURL({ stock_selection_strategy_id: null, page: null }) },
      })
    }
    if (activeListId !== null) {
      const list = lists.find((l) => l.id === activeListId)
      chips.push({
        key: 'list',
        label: `列表: ${list?.name ?? activeListId}`,
        onClear: () => { setCurrentPage(1); setSelectedCodes(new Set()); updateURL({ list: null, page: null }) },
      })
    }
    return chips
  }, [marketFilter, industryFilter, conceptFilter, stockSelectionStrategyId, activeListId, industries, stockSelectionStrategies, lists, updateURL])

  // 清除全部筛选：合并 5 个维度的 URL patch 为一次 router.replace，避免多次跳转
  const handleClearAllFilters = useCallback(() => {
    setMarketFilter('all')
    setIndustryFilter('all')
    setConceptFilter('all')
    setCurrentPage(1)
    setSelectedCodes(new Set())
    updateURL({
      market: null, industry: null, concept: null,
      stock_selection_strategy_id: null, list: null, page: null,
    })
  }, [updateURL])

  // 排序点击（多列）：普通=切单列，Shift=追加/循环；同步到 URL
  const handleSortClick = useCallback((key: string, event?: React.MouseEvent) => {
    const shift = !!event?.shiftKey
    setSortKeys((prev) => {
      const next = computeNextSort(prev, key, shift)
      updateURL({ sort: isDefaultSort(next) ? null : serializeSort(next) })
      return next
    })
  }, [updateURL])

  // 筛选器 JSX：桌面端内联在 Card 中，移动端由 Sheet 渲染复用
  const filtersGrid = (
    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
      <div className="space-y-2">
        <Label htmlFor="market-filter">市场筛选</Label>
        <Select value={marketFilter} onValueChange={(v) => { setMarketFilter(v); setCurrentPage(1); updateURL({ market: v, page: null }) }}>
          <SelectTrigger id="market-filter"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部市场</SelectItem>
            <SelectItem value="SSE">上海主板</SelectItem>
            <SelectItem value="SZSE">深圳主板</SelectItem>
            <SelectItem value="创业板">创业板</SelectItem>
            <SelectItem value="科创板">科创板</SelectItem>
            <SelectItem value="北交所">北交所</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="industry-filter">行业筛选</Label>
        <Select value={industryFilter} onValueChange={(v) => { setIndustryFilter(v); setCurrentPage(1); updateURL({ industry: v, page: null }) }}>
          <SelectTrigger id="industry-filter"><SelectValue placeholder="选择行业..." /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部行业</SelectItem>
            {industries.map((ind) => (
              <SelectItem key={ind.value} value={ind.value}>{ind.label}（{ind.count}）</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label htmlFor="concept-filter">东方财富板块</Label>
        <LazyConceptSelect
          value={conceptFilter}
          onSelect={(v) => { setConceptFilter(v); setCurrentPage(1); updateURL({ concept: v, page: null }) }}
          includeAllOption={true}
          valueType="code"
          placeholder="选择板块..."
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="strategy-filter">选股策略</Label>
        <Select
          value={stockSelectionStrategyId ?? 'all'}
          onValueChange={(v) => {
            setCurrentPage(1)
            updateURL({ stock_selection_strategy_id: v === 'all' ? null : Number(v), page: null })
          }}
        >
          <SelectTrigger id="strategy-filter"><SelectValue placeholder="选择选股策略..." /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">不使用策略</SelectItem>
            {stockSelectionStrategies.length > 0 && (
              <>
                {stockSelectionStrategies.filter((s) => s.user_id === user?.id).length > 0 && (
                  <>
                    <div className="px-2 py-1 text-xs text-gray-500 dark:text-gray-400 font-medium">我的策略</div>
                    {stockSelectionStrategies.filter((s) => s.user_id === user?.id).map((s) => (
                      <SelectItem key={s.id} value={String(s.id)}>
                        {s.display_name}
                        {s.publish_status !== 'approved' && <span className="ml-1 text-xs text-gray-500 dark:text-gray-400">（未发布）</span>}
                      </SelectItem>
                    ))}
                  </>
                )}
                {stockSelectionStrategies.filter((s) => s.user_id !== user?.id && s.publish_status === 'approved').length > 0 && (
                  <>
                    <div className="px-2 py-1 text-xs text-gray-500 dark:text-gray-400 font-medium">已发布策略</div>
                    {stockSelectionStrategies.filter((s) => s.user_id !== user?.id && s.publish_status === 'approved').map((s) => (
                      <SelectItem key={s.id} value={String(s.id)}>{s.display_name}</SelectItem>
                    ))}
                  </>
                )}
              </>
            )}
            {stockSelectionStrategies.length === 0 && (
              <div className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">暂无选股策略</div>
            )}
          </SelectContent>
        </Select>
      </div>

      {isAuthenticated && (
        <div className="space-y-2">
          <Label htmlFor="list-filter">自选列表</Label>
          <Select
            value={activeListId !== null ? String(activeListId) : 'all'}
            onValueChange={(v) => {
              setCurrentPage(1)
              setSelectedCodes(new Set())
              updateURL({ list: v === 'all' ? null : Number(v), page: null })
            }}
          >
            <SelectTrigger id="list-filter"><SelectValue placeholder="选择列表..." /></SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部股票</SelectItem>
              {lists.map((list) => (
                <div key={list.id} className="flex items-center group">
                  <SelectItem value={String(list.id)} className="flex-1">
                    {list.name}<span className="ml-1 text-xs text-gray-500 dark:text-gray-400">({list.stock_count})</span>
                  </SelectItem>
                  <span className="flex items-center gap-1 pr-2 opacity-0 group-hover:opacity-100">
                    <button
                      type="button"
                      title="重命名"
                      aria-label={`重命名列表 ${list.name}`}
                      onMouseDown={(e) => { e.preventDefault(); e.stopPropagation(); setRenameTarget(list); setRenameDialogOpen(true) }}
                      className="p-0.5 hover:text-primary rounded focus-ring"
                    >
                      <Pencil className="h-3 w-3" />
                    </button>
                    <button
                      type="button"
                      title="删除"
                      aria-label={`删除列表 ${list.name}`}
                      onMouseDown={(e) => { e.preventDefault(); e.stopPropagation(); handleDeleteList(list.id) }}
                      className="p-0.5 hover:text-destructive rounded focus-ring-red"
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </span>
                </div>
              ))}
              {lists.length === 0 && <div className="px-3 py-2 text-sm text-gray-500 dark:text-gray-400">暂无列表</div>}
            </SelectContent>
          </Select>
        </div>
      )}
    </div>
  )

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">股票列表</h1>
        <p className="text-gray-600 dark:text-gray-300 mt-1">共 {(totalStocks ?? 0).toLocaleString()} 只股票</p>
      </div>

      {error && (
        <Alert className="bg-destructive/10 border-destructive/30">
          <AlertDescription className="text-destructive">{error}</AlertDescription>
        </Alert>
      )}

      {/* 批量操作浮动栏
         上部「建议行」仿 Gmail / Linear：根据已选/本页/总数三者关系推荐下一步（全选筛选结果 / 全选本页 / 清除）
         下部操作行：取消、添加到列表、批量 AI 分析等主动作 */}
      {isAuthenticated && selectedCodes.size > 0 && (
        <div
          className="fixed z-40 flex flex-col gap-2 bg-card border border-border shadow-xl
                     bottom-0 left-0 right-0 rounded-none px-3 py-2
                     md:bottom-6 md:left-1/2 md:right-auto md:-translate-x-1/2 md:rounded-xl md:px-5 md:py-3"
          style={{ paddingBottom: 'calc(env(safe-area-inset-bottom, 0px) + 0.5rem)' }}
        >
          {/* 建议行：上下文推荐，仅在存在有意义的下一步时渲染 */}
          {(() => {
            const pageSize = displayedTsCodes.length
            const total = totalStocks ?? 0
            const allFilteredSelected = total > 0 && selectedCodes.size >= total
            const hasMoreOnOtherPages = total > pageSize

            // 态 1：已跨页全选，提供清除入口
            if (allFilteredSelected) {
              return (
                <div className="flex items-center justify-center gap-1.5 text-xs text-muted-foreground whitespace-nowrap">
                  <span>已选中全部 <strong className="tabular-nums text-foreground">{total}</strong> 只筛选结果</span>
                  <button
                    type="button"
                    onClick={() => setSelectedCodes(new Set())}
                    className="text-primary font-medium hover:underline underline-offset-2 focus-ring rounded-sm"
                  >
                    清除选择
                  </button>
                </div>
              )
            }

            // 态 2：本页已全选且还有其他页，提示扩大选择
            if (allCurrentPageSelected && hasMoreOnOtherPages) {
              return (
                <div className="flex items-center justify-center gap-1.5 text-xs text-muted-foreground whitespace-nowrap">
                  <span>已选中本页 <strong className="tabular-nums text-foreground">{pageSize}</strong> 只</span>
                  <button
                    type="button"
                    onClick={handleSelectAllFiltered}
                    disabled={selectingAll}
                    className="inline-flex items-center gap-1 text-primary font-medium hover:underline underline-offset-2 disabled:opacity-60 disabled:no-underline focus-ring rounded-sm"
                  >
                    {selectingAll && <Loader2 className="h-3 w-3 animate-spin" />}
                    {selectingAll ? '加载中…' : `全选筛选结果（${total} 只）`}
                  </button>
                </div>
              )
            }

            // 态 3：部分选中（本页未满 / 跨页零散），提供两条捷径
            return (
              <div className="flex items-center justify-center gap-2 text-xs text-muted-foreground whitespace-nowrap">
                <button
                  type="button"
                  onClick={toggleSelectAll}
                  className="text-primary font-medium hover:underline underline-offset-2 focus-ring rounded-sm"
                >
                  全选本页（{pageSize}）
                </button>
                {hasMoreOnOtherPages && (
                  <>
                    <span className="text-muted-foreground/50">·</span>
                    <button
                      type="button"
                      onClick={handleSelectAllFiltered}
                      disabled={selectingAll}
                      className="inline-flex items-center gap-1 text-primary font-medium hover:underline underline-offset-2 disabled:opacity-60 disabled:no-underline focus-ring rounded-sm"
                    >
                      {selectingAll && <Loader2 className="h-3 w-3 animate-spin" />}
                      {selectingAll ? '加载中…' : `全选筛选结果（${total}）`}
                    </button>
                  </>
                )}
              </div>
            )
          })()}

          {/* 操作行：已选计数 + 主动作 */}
          <div className="flex items-center gap-2 md:gap-3 overflow-x-auto md:overflow-visible">
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300 whitespace-nowrap flex-shrink-0">
              已选 <strong className="tabular-nums">{selectedCodes.size}</strong> 只
            </span>
            <Button size="sm" variant="outline" onClick={() => setSelectedCodes(new Set())} className="flex-shrink-0">
              <X className="h-4 w-4 md:mr-1" /><span className="hidden sm:inline">取消</span>
            </Button>
            {activeListId !== null && (
              <Button size="sm" variant="destructive" onClick={handleRemoveFromList} className="flex-shrink-0">
                <Trash2 className="h-4 w-4 md:mr-1" /><span className="hidden sm:inline">从列表移除</span>
              </Button>
            )}
            <Button size="sm" onClick={() => setAddDialogOpen(true)} className="flex-shrink-0">
              <BookmarkPlus className="h-4 w-4 md:mr-1" /><span className="hidden sm:inline">添加到列表</span>
            </Button>
            <Button size="sm" variant="secondary" onClick={() => setBatchAnalysisOpen(true)} className="flex-shrink-0">
              <Sparkles className="h-4 w-4 md:mr-1" /><span className="hidden sm:inline">批量 AI 分析</span>
            </Button>
          </div>
        </div>
      )}

      {/* 桌面端筛选器（折叠态写 URL ?filters=collapsed，刷新保留） */}
      <Card className="hidden md:block">
        <Collapsible
          open={!filtersCollapsed}
          onOpenChange={(open) => {
            const nextCollapsed = !open
            setFiltersCollapsed(nextCollapsed)
            updateURL({ filters: nextCollapsed ? 'collapsed' : null })
          }}
        >
          <div className="flex items-center justify-between gap-3 px-6 py-3 border-b border-gray-200 dark:border-gray-800">
            <CollapsibleTrigger asChild>
              <button
                className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-200 hover:text-gray-900 dark:hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-2 dark:focus-visible:ring-offset-gray-900 rounded-sm min-w-0"
                aria-label={filtersCollapsed ? '展开筛选器' : '折叠筛选器'}
              >
                <Filter className="h-4 w-4 shrink-0" />
                <span>筛选器</span>
                {activeFilterCount > 0 && (
                  <span className="inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 rounded-full text-[11px] font-semibold bg-primary text-primary-foreground shrink-0">
                    {activeFilterCount}
                  </span>
                )}
                {filtersCollapsed ? (
                  <ChevronDown className="h-4 w-4 text-gray-500 dark:text-gray-400 shrink-0" />
                ) : (
                  <ChevronUp className="h-4 w-4 text-gray-500 dark:text-gray-400 shrink-0" />
                )}
              </button>
            </CollapsibleTrigger>
            <div className="flex items-center gap-2 shrink-0">
              {activeFilterCount > 0 && (
                <button
                  type="button"
                  onClick={handleClearAllFilters}
                  className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-destructive focus-ring rounded-sm"
                >
                  <X className="h-3.5 w-3.5" />
                  清除全部
                </button>
              )}
              <ColumnVisibilityMenu
                isVisible={isVisible}
                onToggle={toggleColumn}
                onReset={resetColumns}
                visibleCount={visibleColumns.size}
              />
            </div>
          </div>

          {filtersCollapsed && activeFilterChips.length > 0 && (
            <div className="flex flex-wrap gap-2 px-6 py-3">
              {activeFilterChips.map((chip) => (
                <span
                  key={chip.key}
                  className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs bg-primary/10 text-primary border border-primary/25"
                >
                  {chip.label}
                  <button
                    type="button"
                    onClick={chip.onClear}
                    className="ml-0.5 inline-flex items-center justify-center w-4 h-4 rounded-full hover:bg-primary/20 focus-ring"
                    aria-label={`清除 ${chip.label}`}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </span>
              ))}
            </div>
          )}

          <CollapsibleContent className="overflow-hidden data-[state=open]:animate-collapsible-down data-[state=closed]:animate-collapsible-up">
            <CardContent className="pt-6">
              {filtersGrid}
            </CardContent>
          </CollapsibleContent>
        </Collapsible>
      </Card>

      {/* 移动端筛选入口按钮 */}
      <div className="md:hidden">
        <Button
          variant="outline"
          size="sm"
          className="w-full justify-between"
          onClick={() => setMobileFiltersOpen(true)}
        >
          <span className="flex items-center gap-2">
            <Filter className="h-4 w-4" />
            筛选
            {activeFilterCount > 0 && (
              <span className="ml-1 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-semibold bg-blue-600 text-white">
                {activeFilterCount}
              </span>
            )}
          </span>
          <ChevronDown className="h-4 w-4 text-gray-500 dark:text-gray-400" />
        </Button>
      </div>

      {/* 移动端筛选抽屉 */}
      <Sheet open={mobileFiltersOpen} onOpenChange={setMobileFiltersOpen}>
        <SheetContent side="bottom" className="max-h-[85vh] overflow-y-auto rounded-t-xl">
          <SheetHeader className="mb-4">
            <SheetTitle>筛选{activeFilterCount > 0 ? ` (${activeFilterCount})` : ''}</SheetTitle>
          </SheetHeader>
          {filtersGrid}
          <div className="mt-6">
            <Button className="w-full" onClick={() => setMobileFiltersOpen(false)}>
              完成
            </Button>
          </div>
        </SheetContent>
      </Sheet>

      {/* 股票表格 */}
      <Card>
        <CardContent className="p-0">
          {isLoading && isFirstLoad ? (
            <>
              <StockCardSkeleton count={5} />
              <StockTableSkeleton rows={Math.min(pageSize, 10)} showCheckbox={isAuthenticated} />
            </>
          ) : isLoading ? (
            <div className="flex items-center justify-center py-6 text-sm text-gray-500 dark:text-gray-400 gap-2">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              <span>加载中...</span>
            </div>
          ) : displayedStocks.length === 0 ? (
            <div className="text-center py-12">
              <svg className="mx-auto h-12 w-12 text-gray-400 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="mt-4 text-gray-600 dark:text-gray-400">
                {activeListId !== null ? '列表中暂无股票' : '没有找到股票'}
              </p>
            </div>
          ) : (
            <>
            {/* 移动端卡片视图 */}
            <div className="md:hidden p-3 space-y-3">
              {displayedStocks.map((stock) => (
                <StockCard
                  key={stock.code}
                  stock={stock}
                  isAuthenticated={isAuthenticated}
                  isSelected={selectedCodes.has(toTsCode(stock.code))}
                  onToggleSelect={toggleStock}
                />
              ))}
            </div>

            {/* 桌面端表格视图 */}
            <div className="hidden md:block overflow-x-auto">
              <table className="min-w-full divide-y divide-divider">
                <thead className="bg-surface-base">
                  <tr>
                    {isAuthenticated && (
                      <th className="px-4 py-3 w-10">
                        <Checkbox
                          checked={someCurrentPageSelected ? 'indeterminate' : allCurrentPageSelected}
                          onCheckedChange={toggleSelectAll}
                          aria-label={allCurrentPageSelected ? '取消全选本页' : '全选本页'}
                        />
                      </th>
                    )}
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">股票</th>
                    {isVisible('latest_price') && (
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">最新价</th>
                    )}
                    {isVisible('pct_change') && (
                      <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">
                        <SortHeaderButton sortKey="pct_change" label="涨跌幅" sortKeys={sortKeys} onClick={handleSortClick} />
                      </th>
                    )}
                    {isVisible('amount') && (
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap" title="当日成交额（元）">
                        成交额
                      </th>
                    )}
                    {isVisible('turnover_rate') && (
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap" title="换手率（最近交易日 daily_basic）">
                        换手率
                      </th>
                    )}
                    {isVisible('total_mv') && (
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap" title="总市值（最近交易日 daily_basic）">
                        总市值
                      </th>
                    )}
                    {isVisible('pe_ttm') && (
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap" title="滚动市盈率 PE-TTM。亏损/＞500 标橙">
                        PE-TTM
                      </th>
                    )}
                    {([
                      ['score_hot_money', '游资', 'score_hot_money'],
                      ['score_midline', '中线', 'score_midline'],
                      ['score_longterm', '价值', 'score_longterm'],
                      ['cio_score', 'CIO评分', 'score_cio'],
                      ['cio_last_date', 'CIO日期', 'cio_last_date'],
                    ] as const).map(([sortKey, label, colId]) => isVisible(colId) && (
                      <th key={sortKey} className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap">
                        <SortHeaderButton sortKey={sortKey} label={label} sortKeys={sortKeys} onClick={handleSortClick} />
                      </th>
                    ))}
                    {/* 价值度量三列：ROC / EY（《股市稳赚》）+ 内在价值安全边际（《聪明的投资者》）*/}
                    {isVisible('roc') && (
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap" title="资本收益率 ROC = EBIT / (净营运资本 + 净固定资产)。衡量公司赚钱能力。">
                        <SortHeaderButton sortKey="roc" label="ROC" sortKeys={sortKeys} onClick={handleSortClick} />
                      </th>
                    )}
                    {isVisible('earnings_yield') && (
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap" title="收益率 EY = EBIT / EV。衡量股票相对便宜程度。">
                        <SortHeaderButton sortKey="earnings_yield" label="收益率" sortKeys={sortKeys} onClick={handleSortClick} />
                      </th>
                    )}
                    {isVisible('intrinsic_margin') && (
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap" title="格雷厄姆内在价值 = EPS × (8.5 + 2g)，g 封顶 15%。数值为相对当前价的安全边际（负值表示高估）。悬停看具体价和增长率来源。">
                        <SortHeaderButton sortKey="intrinsic_margin" label="安全边际" sortKeys={sortKeys} onClick={handleSortClick} />
                      </th>
                    )}
                    {isVisible('followup_price') && (
                      <th
                        className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap"
                        title="CIO 复查触发器：上/下方触发价"
                      >
                        关注价格
                      </th>
                    )}
                    {isVisible('followup_time') && (
                      <th
                        className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap"
                        title="CIO 复查触发器：最近一个时间事件"
                      >
                        <SortHeaderButton sortKey="cio_followup_time" label="关注时间" sortKeys={sortKeys} onClick={handleSortClick} />
                      </th>
                    )}
                  </tr>
                </thead>
                <tbody className="bg-card divide-y divide-divider">
                  {displayedStocks.map((stock) => (
                    <StockTableRow
                      key={stock.code}
                      stock={stock}
                      isAuthenticated={isAuthenticated}
                      isSelected={selectedCodes.has(toTsCode(stock.code))}
                      isVisible={isVisible}
                      onToggleSelect={toggleStock}
                    />
                  ))}
                </tbody>
              </table>
            </div>
            </>
          )}

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="px-6 py-4 border-t border-border">
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div className="flex items-center justify-between md:justify-start gap-4 md:gap-6">
                  <p className="text-sm text-gray-700 dark:text-gray-300">
                    <span className="md:hidden">第 <span className="font-medium">{currentPage}</span> / {totalPages} 页</span>
                    <span className="hidden md:inline">
                      显示 <span className="font-medium">{(currentPage - 1) * pageSize + 1}</span> - <span className="font-medium">{Math.min(currentPage * pageSize, totalStocks ?? 0)}</span>
                      {' '}共 <span className="font-medium">{totalStocks ?? 0}</span> 条
                    </span>
                  </p>
                  <div className="flex items-center gap-2">
                    <Label htmlFor="page-size" className="text-sm">每页</Label>
                    <Select value={pageSize.toString()} onValueChange={(v) => { setPageSize(Number(v)); setCurrentPage(1); updateURL({ pageSize: Number(v), page: null }) }}>
                      <SelectTrigger id="page-size" className="w-[80px]"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="20">20</SelectItem>
                        <SelectItem value="50">50</SelectItem>
                        <SelectItem value="100">100</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <Pagination>
                  <PaginationContent>
                    <PaginationItem>
                      <Button variant="outline" size="sm" onClick={() => goToPage(Math.max(1, currentPage - 1))} disabled={currentPage === 1} className="gap-1">
                        <ChevronLeft className="h-4 w-4" /><span className="hidden md:inline">上一页</span>
                      </Button>
                    </PaginationItem>
                    {currentPage - 2 > 1 && (
                      <>
                        <PaginationItem><PaginationLink onClick={() => goToPage(1)} isActive={false} className="cursor-pointer">1</PaginationLink></PaginationItem>
                        {currentPage - 2 > 2 && <PaginationItem className="hidden md:inline-flex"><PaginationEllipsis /></PaginationItem>}
                      </>
                    )}
                    {Array.from({ length: totalPages }, (_, i) => i + 1)
                      .filter(page => page >= currentPage - 2 && page <= currentPage + 2)
                      .map(page => (
                        <PaginationItem key={page} className={page === currentPage ? '' : 'hidden md:inline-flex'}>
                          <PaginationLink onClick={() => goToPage(page)} isActive={currentPage === page} className="cursor-pointer">{page}</PaginationLink>
                        </PaginationItem>
                      ))}
                    {currentPage + 2 < totalPages && (
                      <>
                        {currentPage + 2 < totalPages - 1 && <PaginationItem className="hidden md:inline-flex"><PaginationEllipsis /></PaginationItem>}
                        <PaginationItem><PaginationLink onClick={() => goToPage(totalPages)} isActive={false} className="cursor-pointer">{totalPages}</PaginationLink></PaginationItem>
                      </>
                    )}
                    <PaginationItem>
                      <Button variant="outline" size="sm" onClick={() => goToPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages} className="gap-1">
                        <span className="hidden md:inline">下一页</span><ChevronRight className="h-4 w-4" />
                      </Button>
                    </PaginationItem>
                  </PaginationContent>
                </Pagination>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Dialogs */}
      <AddToListDialog
        open={addDialogOpen}
        onClose={() => setAddDialogOpen(false)}
        selectedCodes={Array.from(selectedCodes)}
        onSuccess={() => {
          toast.success(`已将 ${selectedCodes.size} 只股票添加到列表`)
          setSelectedCodes(new Set())
          fetchLists()
        }}
      />
      <RenameListDialog
        open={renameDialogOpen}
        list={renameTarget}
        onClose={() => { setRenameDialogOpen(false); setRenameTarget(null) }}
      />
      <BatchAnalysisDialog
        open={batchAnalysisOpen}
        onClose={() => setBatchAnalysisOpen(false)}
        selectedTsCodes={Array.from(selectedCodes)}
        onSuccess={() => fetchStocks(true)}
      />
    </div>
  )
}

export default function StocksPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-muted-foreground">加载中...</div>}>
      <StocksPageContent />
    </Suspense>
  )
}
