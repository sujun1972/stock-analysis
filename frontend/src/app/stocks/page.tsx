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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
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
  Filter,
  Sparkles,
} from 'lucide-react'
import { useSmartRefresh } from '@/hooks/useMarketStatus'
import { LazyConceptSelect } from '@/components/stocks/LazyConceptSelect'
import { HotMoneyViewDialog } from '@/components/stocks/HotMoneyViewDialog'
import { AddToListDialog } from './components/AddToListDialog'
import { RenameListDialog } from './components/RenameListDialog'
import { StockTableRow } from './components/StockTableRow'
import { BatchAnalysisDialog } from './components/BatchAnalysisDialog'
import type { StockList, StockInfo } from '@/types'
import type { Strategy } from '@/types/strategy'

// ── 辅助函数 ──────────────────────────────────────────────────
function toTsCode(code: string): string {
  if (code.includes('.')) return code.toUpperCase()
  if (code.startsWith('6')) return `${code}.SH`
  if (code.startsWith('4') || code.startsWith('8')) return `${code}.BJ`
  return `${code}.SZ`
}

// ── 主页面 ────────────────────────────────────────────────────
function StocksPageContent() {
  const searchParams = useSearchParams()
  const router = useRouter()

  // ── 从 URL 初始化所有筛选 / 分页状态 ──
  const stockSelectionStrategyId = searchParams.get('stock_selection_strategy_id')
  const [selectionStrategyName, setSelectionStrategyName] = useState<string | null>(null)

  const { stocks, setStocks, setLoading, isLoading, error, setError } = useStockStore()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const { lists, fetchLists, deleteList, removeStocks } = useStockListStore()

  const activeListId = searchParams.get('list') ? Number(searchParams.get('list')) : null

  // ── 筛选 / 分页状态 ──
  const [marketFilter, setMarketFilter] = useState<string>(() => searchParams.get('market') ?? 'all')
  const [stockSelectionStrategies, setStockSelectionStrategies] = useState<Strategy[]>([])
  const [industryFilter, setIndustryFilter] = useState<string>(() => searchParams.get('industry') ?? 'all')
  const [conceptFilter, setConceptFilter] = useState<string>(() => searchParams.get('concept') ?? 'all')
  const [currentPage, setCurrentPage] = useState(() => Number(searchParams.get('page') ?? '1'))
  const [totalStocks, setTotalStocks] = useState(0)
  const [pageSize, setPageSize] = useState(() => Number(searchParams.get('pageSize') ?? '20'))
  const [sortBy, setSortBy] = useState(() => searchParams.get('sortBy') ?? 'pct_change')
  const [sortOrder, setSortOrder] = useState(() => searchParams.get('sortOrder') ?? 'desc')
  const [industries, setIndustries] = useState<{ value: string; label: string; count: number }[]>([])

  // ── URL 同步 ──
  const updateURL = useCallback((patch: Record<string, string | number | null>) => {
    const params = new URLSearchParams(searchParams.toString())
    const defaults: Record<string, string | number> = { sortBy: 'pct_change', sortOrder: 'desc', pageSize: 20, page: 1 }
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

  // ── Dialog 状态 ──
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [renameDialogOpen, setRenameDialogOpen] = useState(false)
  const [renameTarget, setRenameTarget] = useState<StockList | null>(null)
  const [batchAnalysisOpen, setBatchAnalysisOpen] = useState(false)
  const [analyzingTsCodes, setAnalyzingTsCodes] = useState<Set<string>>(new Set())
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)

  // ── AI 分析弹窗状态 ──
  const [hotMoneyDialogOpen, setHotMoneyDialogOpen] = useState(false)
  const [hotMoneyStock, setHotMoneyStock] = useState<{ name: string; code: string; tsCode: string } | null>(null)
  const [promptStates, setPromptStates] = useState({
    hotMoney: { content: '', loading: false },
    dataCollection: { content: '', loading: false },
    midline: { content: '', loading: false },
    longterm: { content: '', loading: false },
    cio: { content: '', loading: false },
  })

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

  // ── Toast 自动消失 ──
  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 3000)
    return () => clearTimeout(t)
  }, [toast])

  // ── 股票列表加载 ──
  const fetchStocks = useCallback(async (silent: boolean = false) => {
    try {
      if (!silent) setLoading(true)
      setError(null)

      const params: Record<string, string | number | boolean> = {
        skip: (currentPage - 1) * pageSize,
        limit: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
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
      if (response.strategy_name) setSelectionStrategyName(response.strategy_name)
    } catch (err: unknown) {
      const e = err as { message?: string }
      setError(e.message || '加载股票列表失败')
      if (!silent) { setStocks([]); setTotalStocks(0) }
    } finally {
      if (!silent) setLoading(false)
    }
  }, [currentPage, marketFilter, industryFilter, conceptFilter, pageSize, sortBy, sortOrder, stockSelectionStrategyId, activeListId, setStocks, setLoading, setError])

  const loadStocks = useCallback(() => fetchStocks(false), [fetchStocks])

  useEffect(() => {
    loadStocks()
    setSelectedCodes(new Set())
  }, [loadStocks])

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
  useEffect(() => {
    if (!isAuthenticated) {
      setAnalyzingTsCodes(new Set())
      return
    }
    let cancelled = false
    let timer: ReturnType<typeof setTimeout> | null = null
    const tick = async () => {
      try {
        const res = await apiClient.getActiveBatchTsCodes()
        if (cancelled) return
        const nextCodes: string[] = res?.data?.ts_codes ?? []
        setAnalyzingTsCodes((prev) => {
          const next = new Set(nextCodes)
          let removedAny = false
          prev.forEach((ts) => { if (!next.has(ts)) removedAny = true })
          if (removedAny) fetchStocks(true)
          return next
        })
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
      const params: Parameters<typeof apiClient.getStockCodes>[0] = { list_status: 'L', limit: 5000 }
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
      setToast({ msg: `已选中全部 ${result.codes.length} 只股票`, type: 'success' })
    } catch (err: unknown) {
      const e = err as { message?: string }
      setToast({ msg: e?.message || '获取全部股票失败', type: 'error' })
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
      setToast({ msg: `已从列表移除 ${result.removed} 只股票`, type: 'success' })
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      setToast({ msg: e?.response?.data?.detail || '移除失败', type: 'error' })
    }
  }, [activeListId, selectedCodes, removeStocks])

  const handleDeleteList = useCallback(async (listId: number) => {
    if (!confirm('确定要删除这个列表吗？列表中的股票记录也会一并删除。')) return
    try {
      await deleteList(listId)
      setToast({ msg: '列表已删除', type: 'success' })
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } }
      setToast({ msg: e?.response?.data?.detail || '删除失败', type: 'error' })
    }
  }, [deleteList])

  // ── 打开 AI 分析弹窗 ──
  const handleOpenAnalysis = useCallback((stock: StockInfo) => {
    const ts = stock.ts_code ?? toTsCode(stock.code)
    setHotMoneyStock({ name: stock.name, code: stock.code, tsCode: ts })
    setPromptStates({
      hotMoney: { content: '', loading: true },
      dataCollection: { content: '', loading: true },
      midline: { content: '', loading: true },
      longterm: { content: '', loading: true },
      cio: { content: '', loading: true },
    })
    setHotMoneyDialogOpen(true)

    const vars = { stock_name: stock.name, stock_code: stock.code }
    interface PromptResponse { code?: number; data?: { system_prompt?: string; user_prompt_template?: string } }
    const toPrompt = (res: unknown): string => {
      const r = res as PromptResponse
      if (r?.code === 200 && r.data?.user_prompt_template) {
        return [r.data.system_prompt, r.data.user_prompt_template].filter(Boolean).join('\n\n')
      }
      return '加载失败，请重试'
    }

    Promise.all([
      apiClient.getPromptTemplateByKey('top_speculative_investor_v1', { ...vars, ts_code: ts }),
      apiClient.getPromptTemplateByKey('stock_data_collection_v1', vars),
      apiClient.getPromptTemplateByKey('midline_industry_expert_v1', { ...vars, ts_code: ts }),
      apiClient.getPromptTemplateByKey('longterm_value_watcher_v1', { ...vars, ts_code: ts }),
      apiClient.getPromptTemplateByKey('cio_directive_v1', { ...vars, ts_code: ts }),
    ]).then(([hotRes, dataRes, midRes, ltRes, cioRes]) => {
      setPromptStates({
        hotMoney: { content: toPrompt(hotRes), loading: false },
        dataCollection: { content: toPrompt(dataRes), loading: false },
        midline: { content: toPrompt(midRes), loading: false },
        longterm: { content: toPrompt(ltRes), loading: false },
        cio: { content: toPrompt(cioRes), loading: false },
      })
    }).catch(() => {
      const failed = { content: '加载失败，请重试', loading: false }
      setPromptStates({ hotMoney: failed, dataCollection: failed, midline: failed, longterm: failed, cio: failed })
    })
  }, [])

  // ── 排序点击 ──
  const handleSortClick = useCallback((key: string) => {
    if (sortBy === key) {
      const next = sortOrder === 'desc' ? 'asc' : 'desc'
      setSortOrder(next)
      updateURL({ sortBy: key === 'pct_change' ? null : key, sortOrder: key === 'pct_change' ? next : next })
    } else {
      setSortBy(key)
      setSortOrder('desc')
      updateURL({ sortBy: key === 'pct_change' ? null : key, sortOrder: key === 'pct_change' ? null : 'desc' })
    }
  }, [sortBy, sortOrder, updateURL])

  return (
    <div className="space-y-6">
      {/* Toast */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-white text-sm transition-all ${toast.type === 'success' ? 'bg-green-600' : 'bg-red-600'}`}>
          {toast.msg}
        </div>
      )}

      {/* 页面标题 */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">股票列表</h1>
        <p className="text-gray-600 dark:text-gray-300 mt-1">共 {(totalStocks ?? 0).toLocaleString()} 只股票</p>
      </div>

      {error && (
        <Alert className="bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
          <AlertDescription className="text-red-800 dark:text-red-200">{error}</AlertDescription>
        </Alert>
      )}

      {/* 选股策略 Banner */}
      {stockSelectionStrategyId && (
        <div className="flex items-center gap-3 px-4 py-3 border rounded-lg bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-700">
          <Filter className="h-4 w-4 flex-shrink-0 text-blue-600 dark:text-blue-400" />
          <div className="flex-1 min-w-0">
            {isLoading ? (
              <p className="text-sm text-blue-700 dark:text-blue-300">正在运行选股策略，请稍候...</p>
            ) : (
              <>
                <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
                  选股策略：<span className="font-semibold">{selectionStrategyName}</span>
                  <span className="ml-2 text-blue-600 dark:text-blue-400">共 {totalStocks} 只股票</span>
                </p>
                <p className="text-xs text-blue-600 dark:text-blue-400 mt-0.5">基于近60日价格数据运行选股策略，结果仅供参考</p>
              </>
            )}
          </div>
          <button
            onClick={() => { setCurrentPage(1); updateURL({ stock_selection_strategy_id: null, page: null }) }}
            className="flex-shrink-0 text-blue-500 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-200"
            title="清除策略筛选"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      )}

      {/* 批量操作浮动栏 */}
      {isAuthenticated && selectedCodes.size > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-xl shadow-xl px-5 py-3">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            已选 <strong>{selectedCodes.size}</strong> 只
          </span>
          <Button size="sm" variant="outline" onClick={() => setSelectedCodes(new Set())}>
            <X className="h-4 w-4 mr-1" />取消
          </Button>
          {activeListId !== null && (
            <Button size="sm" variant="destructive" onClick={handleRemoveFromList}>
              <Trash2 className="h-4 w-4 mr-1" />从列表移除
            </Button>
          )}
          <Button size="sm" onClick={() => setAddDialogOpen(true)}>
            <BookmarkPlus className="h-4 w-4 mr-1" />添加到列表
          </Button>
          <Button size="sm" variant="secondary" onClick={() => setBatchAnalysisOpen(true)}>
            <Sparkles className="h-4 w-4 mr-1" />批量 AI 分析
          </Button>
        </div>
      )}

      {/* 筛选器 */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
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
                          <div className="px-2 py-1 text-xs text-gray-400 font-medium">我的策略</div>
                          {stockSelectionStrategies.filter((s) => s.user_id === user?.id).map((s) => (
                            <SelectItem key={s.id} value={String(s.id)}>
                              {s.display_name}
                              {s.publish_status !== 'approved' && <span className="ml-1 text-xs text-gray-400">（未发布）</span>}
                            </SelectItem>
                          ))}
                        </>
                      )}
                      {stockSelectionStrategies.filter((s) => s.user_id !== user?.id && s.publish_status === 'approved').length > 0 && (
                        <>
                          <div className="px-2 py-1 text-xs text-gray-400 font-medium">已发布策略</div>
                          {stockSelectionStrategies.filter((s) => s.user_id !== user?.id && s.publish_status === 'approved').map((s) => (
                            <SelectItem key={s.id} value={String(s.id)}>{s.display_name}</SelectItem>
                          ))}
                        </>
                      )}
                    </>
                  )}
                  {stockSelectionStrategies.length === 0 && (
                    <div className="px-3 py-2 text-sm text-gray-400">暂无选股策略</div>
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
                          {list.name}<span className="ml-1 text-xs text-gray-400">({list.stock_count})</span>
                        </SelectItem>
                        <span className="flex items-center gap-1 pr-2 opacity-0 group-hover:opacity-100">
                          <button title="重命名" onMouseDown={(e) => { e.preventDefault(); e.stopPropagation(); setRenameTarget(list); setRenameDialogOpen(true) }} className="p-0.5 hover:text-blue-600 rounded">
                            <Pencil className="h-3 w-3" />
                          </button>
                          <button title="删除" onMouseDown={(e) => { e.preventDefault(); e.stopPropagation(); handleDeleteList(list.id) }} className="p-0.5 hover:text-red-600 rounded">
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </span>
                      </div>
                    ))}
                    {lists.length === 0 && <div className="px-3 py-2 text-sm text-gray-400">暂无列表</div>}
                  </SelectContent>
                </Select>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 股票表格 */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="text-center py-12">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-300 border-t-blue-600"></div>
              <p className="mt-4 text-gray-600 dark:text-gray-400">加载中...</p>
            </div>
          ) : displayedStocks.length === 0 ? (
            <div className="text-center py-12">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="mt-4 text-gray-600 dark:text-gray-400">
                {activeListId !== null ? '列表中暂无股票' : '没有找到股票'}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    {isAuthenticated && (
                      <th className="px-4 py-3 w-10">
                        <div className="flex items-center gap-0.5">
                          <Checkbox
                            checked={someCurrentPageSelected ? 'indeterminate' : allCurrentPageSelected}
                            onCheckedChange={toggleSelectAll}
                            aria-label="全选当前页"
                          />
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <button className="h-4 w-4 flex items-center justify-center rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300" aria-label="全选选项">
                                <ChevronDown className="h-3 w-3" />
                              </button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="start">
                              <DropdownMenuItem onClick={toggleSelectAll}>全选当前页（{displayedTsCodes.length} 只）</DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem onClick={handleSelectAllFiltered} disabled={selectingAll}>
                                {selectingAll ? '加载中...' : `全选所有筛选结果（${totalStocks} 只）`}
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </th>
                    )}
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">股票</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">最新价</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      <button onClick={() => handleSortClick('pct_change')} className="inline-flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-200">
                        涨跌幅
                        {sortBy === 'pct_change' && (
                          <svg className="w-3 h-3 text-blue-600 dark:text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                            {sortOrder === 'desc'
                              ? <path fillRule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L10 13.586l3.293-3.293a1 1 0 011.414 0z" clipRule="evenodd" />
                              : <path fillRule="evenodd" d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z" clipRule="evenodd" />}
                          </svg>
                        )}
                      </button>
                    </th>
                    {([['score_hot_money', '游资'], ['score_midline', '中线'], ['score_longterm', '价值'], ['cio_last_date', 'CIO日期']] as const).map(([key, label]) => (
                      <th key={key} className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        <button onClick={() => handleSortClick(key)} className="inline-flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-200">
                          {label}
                          {sortBy === key && (
                            <svg className="w-3 h-3 text-blue-600 dark:text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                              {sortOrder === 'desc'
                                ? <path fillRule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L10 13.586l3.293-3.293a1 1 0 011.414 0z" clipRule="evenodd" />
                                : <path fillRule="evenodd" d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z" clipRule="evenodd" />}
                            </svg>
                          )}
                        </button>
                      </th>
                    ))}
                    <th
                      className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider whitespace-nowrap"
                      title="CIO 复查触发器：上/下方触发价 + 近期关注事件"
                    >
                      下次关注
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">操作</th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                  {displayedStocks.map((stock) => (
                    <StockTableRow
                      key={stock.code}
                      stock={stock}
                      isAuthenticated={isAuthenticated}
                      isSelected={selectedCodes.has(toTsCode(stock.code))}
                      isAnalyzing={analyzingTsCodes.has(toTsCode(stock.code))}
                      onToggleSelect={toggleStock}
                      onOpenAnalysis={handleOpenAnalysis}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
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
                        <SelectItem value="10">10</SelectItem>
                        <SelectItem value="20">20</SelectItem>
                        <SelectItem value="30">30</SelectItem>
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
          setToast({ msg: `已将 ${selectedCodes.size} 只股票添加到列表`, type: 'success' })
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
      <HotMoneyViewDialog
        open={hotMoneyDialogOpen}
        onClose={() => { setHotMoneyDialogOpen(false); setHotMoneyStock(null) }}
        stockName={hotMoneyStock?.name ?? ''}
        stockCode={hotMoneyStock?.code ?? ''}
        tsCode={hotMoneyStock?.tsCode ?? ''}
        promptContent={promptStates.hotMoney.content}
        promptLoading={promptStates.hotMoney.loading}
        dataCollectionPrompt={promptStates.dataCollection.content}
        dataCollectionPromptLoading={promptStates.dataCollection.loading}
        midlinePrompt={promptStates.midline.content}
        midlinePromptLoading={promptStates.midline.loading}
        longtermPrompt={promptStates.longterm.content}
        longtermPromptLoading={promptStates.longterm.loading}
        cioPrompt={promptStates.cio.content}
        cioPromptLoading={promptStates.cio.loading}
        onSaved={() => fetchStocks(true)}
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
