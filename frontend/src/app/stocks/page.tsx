'use client'

import { useEffect, useState, useMemo, useCallback, useRef, Suspense } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { apiClient } from '@/lib/api-client'
import { useStockStore } from '@/store/stock-store'
import { useAuthStore } from '@/stores/auth-store'
import { useStockListStore } from '@/stores/stock-list-store'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog'
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
  Copy,
  Check,
} from 'lucide-react'
import { useSmartRefresh } from '@/hooks/useMarketStatus'
import { LazyConceptSelect } from '@/components/stocks/LazyConceptSelect'
import type { StockList } from '@/types'
import type { Strategy } from '@/types/strategy'

// ── 辅助函数 ──────────────────────────────────────────────────
function toTsCode(code: string): string {
  if (code.includes('.')) return code.toUpperCase()
  if (code.startsWith('6')) return `${code}.SH`
  if (code.startsWith('4') || code.startsWith('8')) return `${code}.BJ`
  return `${code}.SZ`
}

// ── 添加到列表 Dialog ──────────────────────────────────────────
interface AddToListDialogProps {
  open: boolean
  onClose: () => void
  selectedCodes: string[]          // ts_code 列表
  onSuccess: () => void
}

function AddToListDialog({ open, onClose, selectedCodes, onSuccess }: AddToListDialogProps) {
  const { lists, createList, addStocks } = useStockListStore()
  const [mode, setMode] = useState<'new' | 'existing'>('existing')
  const [newName, setNewName] = useState('')
  const [selectedListId, setSelectedListId] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [localError, setLocalError] = useState('')

  // 默认选中第一个列表
  useEffect(() => {
    if (open) {
      setMode(lists.length === 0 ? 'new' : 'existing')
      setSelectedListId(lists.length > 0 ? lists[0].id : null)
      setNewName('')
      setLocalError('')
    }
  }, [open, lists])

  const handleConfirm = async () => {
    if (selectedCodes.length === 0) return
    setLocalError('')
    setSubmitting(true)
    try {
      let targetListId = selectedListId
      if (mode === 'new') {
        if (!newName.trim()) { setLocalError('请输入列表名称'); setSubmitting(false); return }
        const created = await createList(newName.trim())
        targetListId = created.id
      }
      if (!targetListId) { setLocalError('请选择目标列表'); setSubmitting(false); return }
      const result = await addStocks(targetListId, selectedCodes)
      onSuccess()
      onClose()
      // 不在这里 toast，由调用方处理
    } catch (err: any) {
      setLocalError(err?.response?.data?.detail || err.message || '操作失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-[420px]">
        <DialogHeader>
          <DialogTitle>添加 {selectedCodes.length} 只股票到列表</DialogTitle>
          <DialogDescription>选择目标列表，或创建一个新列表</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="flex gap-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                checked={mode === 'existing'}
                onChange={() => setMode('existing')}
                disabled={lists.length === 0}
                className="accent-blue-600"
              />
              <span className={lists.length === 0 ? 'text-gray-400' : ''}>追加到已有列表</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                checked={mode === 'new'}
                onChange={() => setMode('new')}
                className="accent-blue-600"
              />
              <span>新建列表</span>
            </label>
          </div>

          {mode === 'existing' ? (
            <Select
              value={selectedListId?.toString() ?? ''}
              onValueChange={(v) => setSelectedListId(Number(v))}
            >
              <SelectTrigger>
                <SelectValue placeholder="选择列表..." />
              </SelectTrigger>
              <SelectContent>
                {lists.map((l) => (
                  <SelectItem key={l.id} value={l.id.toString()}>
                    {l.name}（{l.stock_count} 只）
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <Input
              placeholder="新列表名称（最多50个字符）"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              maxLength={50}
              autoFocus
            />
          )}

          {localError && (
            <p className="text-sm text-red-500">{localError}</p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={submitting}>取消</Button>
          <Button onClick={handleConfirm} disabled={submitting}>
            {submitting ? '处理中...' : '确认添加'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── 重命名列表 Dialog ──────────────────────────────────────────
interface RenameListDialogProps {
  open: boolean
  list: StockList | null
  onClose: () => void
}

function RenameListDialog({ open, list, onClose }: RenameListDialogProps) {
  const { updateList } = useStockListStore()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [localError, setLocalError] = useState('')

  useEffect(() => {
    if (open && list) {
      setName(list.name)
      setDescription(list.description ?? '')
      setLocalError('')
    }
  }, [open, list])

  const handleConfirm = async () => {
    if (!list) return
    setLocalError('')
    setSubmitting(true)
    try {
      await updateList(list.id, name.trim(), description.trim() || undefined)
      onClose()
    } catch (err: any) {
      setLocalError(err?.response?.data?.detail || err.message || '操作失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-[380px]">
        <DialogHeader>
          <DialogTitle>重命名列表</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <div>
            <Label>列表名称</Label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={50}
              autoFocus
            />
          </div>
          <div>
            <Label>描述（可选）</Label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={200}
              placeholder="为这个列表添加一段描述..."
            />
          </div>
          {localError && <p className="text-sm text-red-500">{localError}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={submitting}>取消</Button>
          <Button onClick={handleConfirm} disabled={submitting || !name.trim()}>
            {submitting ? '保存中...' : '保存'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ── 顶级游资观点 Dialog ──────────────────────────────────────
interface HotMoneyViewDialogProps {
  open: boolean
  onClose: () => void
  stockName: string
  stockCode: string
  content: string   // 已由后端完成占位符替换的最终文本
  loading: boolean
}

function HotMoneyViewDialog({ open, onClose, stockName, stockCode, content, loading }: HotMoneyViewDialogProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      const el = document.createElement('textarea')
      el.value = content
      document.body.appendChild(el)
      el.select()
      document.execCommand('copy')
      document.body.removeChild(el)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-[680px] max-h-[85vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>
            顶级游资观点：{stockName}（{stockCode}）
          </DialogTitle>
          <DialogDescription>复制下方提示词到 AI 对话框，获取游资视角分析</DialogDescription>
        </DialogHeader>
        <div className="flex-1 overflow-y-auto min-h-0">
          {loading ? (
            <div className="flex items-center justify-center py-12 text-gray-400 text-sm">加载中...</div>
          ) : (
            <pre className="whitespace-pre-wrap text-sm text-gray-800 dark:text-gray-200 bg-gray-50 dark:bg-gray-800 rounded-lg p-4 leading-relaxed font-mono">
              {content}
            </pre>
          )}
        </div>
        <DialogFooter className="mt-4">
          <Button variant="outline" onClick={onClose}>关闭</Button>
          <Button onClick={handleCopy} disabled={loading || !content} className="gap-2">
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
            {copied ? '已复制' : '复制全文'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
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
  const {
    lists,
    fetchLists,
    deleteList,
    removeStocks,
  } = useStockListStore()

  // activeListId 直接从 URL 读取，不依赖 store（列表作为筛选条件，后端处理过滤）
  const activeListId = searchParams.get('list') ? Number(searchParams.get('list')) : null

  // ── 筛选 / 分页状态（从 URL 初始化） ──
  // marketFilter 编码：'SSE'=上海主板, 'SZSE'=深圳主板, '创业板'/'科创板'/'北交所' 直接匹配 market 字段, 'all'=全部
  const [marketFilter, setMarketFilter] = useState<string>(() => searchParams.get('market') ?? 'all')

  // ── 选股策略列表（已发布 + 当前用户自己的） ──
  const [stockSelectionStrategies, setStockSelectionStrategies] = useState<Strategy[]>([])
  const [industryFilter, setIndustryFilter] = useState<string>(() => searchParams.get('industry') ?? 'all')
  const [conceptFilter, setConceptFilter] = useState<string>(() => searchParams.get('concept') ?? 'all')
  const [currentPage, setCurrentPage] = useState(() => Number(searchParams.get('page') ?? '1'))
  const [totalStocks, setTotalStocks] = useState(0)
  const [pageSize, setPageSize] = useState(() => Number(searchParams.get('pageSize') ?? '20'))
  const [sortBy, setSortBy] = useState(() => searchParams.get('sortBy') ?? 'pct_change')
  const [sortOrder, setSortOrder] = useState(() => searchParams.get('sortOrder') ?? 'desc')
  const [industries, setIndustries] = useState<{ value: string; label: string; count: number }[]>([])

  // ── URL 同步：每次筛选/分页状态变化时更新地址栏 ──
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
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)

  // ── 顶级游资观点弹窗 ──
  const [hotMoneyDialogOpen, setHotMoneyDialogOpen] = useState(false)
  const [hotMoneyStock, setHotMoneyStock] = useState<{ name: string; code: string } | null>(null)
  const [hotMoneyContent, setHotMoneyContent] = useState<string>('')
  const [hotMoneyLoading, setHotMoneyLoading] = useState(false)

  const user = useAuthStore((s) => s.user)

  // ── 加载行业列表 ──
  useEffect(() => {
    apiClient.getStockIndustries().then(setIndustries).catch(() => {})
  }, [])

  // ── 加载选股策略列表（已发布 + 当前用户自己的） ──
  useEffect(() => {
    const fetchStrategies = async () => {
      try {
        const [publishedRes, myRes] = await Promise.all([
          apiClient.getStrategies({ strategy_type: 'stock_selection', publish_status: 'approved', is_enabled: true }),
          user?.id ? apiClient.getStrategies({ strategy_type: 'stock_selection', user_id: user.id }) : Promise.resolve(null),
        ])
        const published: Strategy[] = (publishedRes?.data as any)?.items ?? publishedRes?.data ?? []
        const mine: Strategy[] = (myRes?.data as any)?.items ?? myRes?.data ?? []
        // 合并去重：我的策略优先，相同 id 保留一份
        const merged = [...mine]
        const myIds = new Set(mine.map((s) => s.id))
        published.forEach((s) => { if (!myIds.has(s.id)) merged.push(s) })
        setStockSelectionStrategies(merged)
      } catch {
        // 加载失败静默处理
      }
    }
    fetchStrategies()
  }, [user?.id])

  // ── 已登录时加载自选列表 ──
  useEffect(() => {
    if (isAuthenticated) {
      fetchLists()
    }
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

      const params: any = {
        skip: (currentPage - 1) * pageSize,
        limit: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
        list_status: 'L',
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
    } catch (err: any) {
      setError(err.message || '加载股票列表失败')
      if (!silent) { setStocks([]); setTotalStocks(0) }
    } finally {
      if (!silent) setLoading(false)
    }
  }, [currentPage, marketFilter, industryFilter, conceptFilter, pageSize, sortBy, sortOrder, stockSelectionStrategyId, activeListId, setStocks, setLoading, setError])

  const loadStocks = useCallback(() => fetchStocks(false), [fetchStocks])

  useEffect(() => {
    loadStocks()
    setSelectedCodes(new Set()) // 切页时清空选择
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

  const totalPages = Math.ceil((totalStocks ?? 0) / pageSize)

  // ── 全选当前页 ──
  const displayedStocks = Array.isArray(stocks) ? stocks : []
  const displayedTsCodes = useMemo(
    () => displayedStocks.map((s) => toTsCode(s.code)),
    [displayedStocks]
  )
  const allCurrentPageSelected =
    displayedTsCodes.length > 0 && displayedTsCodes.every((c) => selectedCodes.has(c))
  const someCurrentPageSelected =
    displayedTsCodes.some((c) => selectedCodes.has(c)) && !allCurrentPageSelected

  const toggleSelectAll = () => {
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
  }

  const goToPage = useCallback((page: number) => {
    setCurrentPage(page)
    updateURL({ page })
  }, [updateURL])

  const [selectingAll, setSelectingAll] = useState(false)

  const handleSelectAllFiltered = async () => {
    setSelectingAll(true)
    try {
      const params: Parameters<typeof apiClient.getStockCodes>[0] = {
        list_status: 'L',
        limit: 5000,
      }
      if (marketFilter === 'SSE') { params.market = '主板'; params.exchange = 'SSE' }
      else if (marketFilter === 'SZSE') { params.market = '主板'; params.exchange = 'SZSE' }
      else if (marketFilter !== 'all') { params.market = marketFilter }
      if (industryFilter !== 'all') params.industry = industryFilter
      if (conceptFilter !== 'all') params.concept_code = conceptFilter
      if (stockSelectionStrategyId) params.stock_selection_strategy_id = Number(stockSelectionStrategyId)
      if (activeListId !== null) params.user_stock_list_id = activeListId

      const result = await apiClient.getStockCodes(params)
      const tsCodes = result.codes
      setSelectedCodes((prev) => {
        const next = new Set(prev)
        tsCodes.forEach((c) => next.add(c))
        return next
      })
      setToast({ msg: `已选中全部 ${tsCodes.length} 只股票`, type: 'success' })
    } catch (err: any) {
      setToast({ msg: err?.message || '获取全部股票失败', type: 'error' })
    } finally {
      setSelectingAll(false)
    }
  }

  const toggleStock = (tsCode: string) => {
    setSelectedCodes((prev) => {
      const next = new Set(prev)
      if (next.has(tsCode)) next.delete(tsCode)
      else next.add(tsCode)
      return next
    })
  }

  // ── 从激活列表移除选中股票 ──
  const handleRemoveFromList = async () => {
    if (!activeListId || selectedCodes.size === 0) return
    const codes = Array.from(selectedCodes)
    try {
      const result = await removeStocks(activeListId, codes)
      setSelectedCodes(new Set())
      setToast({ msg: `已从列表移除 ${result.removed} 只股票`, type: 'success' })
    } catch (err: any) {
      setToast({ msg: err?.response?.data?.detail || '移除失败', type: 'error' })
    }
  }

  // ── 删除列表 ──
  const handleDeleteList = async (listId: number) => {
    if (!confirm('确定要删除这个列表吗？列表中的股票记录也会一并删除。')) return
    try {
      await deleteList(listId)
      setToast({ msg: '列表已删除', type: 'success' })
    } catch (err: any) {
      setToast({ msg: err?.response?.data?.detail || '删除失败', type: 'error' })
    }
  }

  // ── 当前激活列表对象 ──
  const visibleStocks = displayedStocks

  return (
    <div className="space-y-6">
      {/* Toast 提示 */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-white text-sm transition-all ${toast.type === 'success' ? 'bg-green-600' : 'bg-red-600'}`}>
          {toast.msg}
        </div>
      )}

      {/* 页面标题行 */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">股票列表</h1>
        <p className="text-gray-600 dark:text-gray-300 mt-1">
          共 {(totalStocks ?? 0).toLocaleString()} 只股票
        </p>
      </div>

      {/* 错误提示 */}
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
                <p className="text-xs text-blue-600 dark:text-blue-400 mt-0.5">
                  基于近60日价格数据运行选股策略，结果仅供参考
                </p>
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

      {/* 批量操作浮动栏（已登录且有选中时显示） */}
      {isAuthenticated && selectedCodes.size > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-3 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-xl shadow-xl px-5 py-3">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            已选 <strong>{selectedCodes.size}</strong> 只
          </span>
          <Button
            size="sm"
            variant="outline"
            onClick={() => setSelectedCodes(new Set())}
          >
            <X className="h-4 w-4 mr-1" />
            取消
          </Button>
          {activeListId !== null && (
            <Button
              size="sm"
              variant="destructive"
              onClick={handleRemoveFromList}
            >
              <Trash2 className="h-4 w-4 mr-1" />
              从列表移除
            </Button>
          )}
          <Button
            size="sm"
            onClick={() => setAddDialogOpen(true)}
          >
            <BookmarkPlus className="h-4 w-4 mr-1" />
            添加到列表
          </Button>
        </div>
      )}

      {/* 搜索和筛选 */}
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
                    <SelectItem key={ind.value} value={ind.value}>
                      {ind.label}（{ind.count}）
                    </SelectItem>
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
                  if (v === 'all') {
                    updateURL({ stock_selection_strategy_id: null, page: null })
                  } else {
                    updateURL({ stock_selection_strategy_id: Number(v), page: null })
                  }
                }}
              >
                <SelectTrigger id="strategy-filter">
                  <SelectValue placeholder="选择选股策略..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">不使用策略</SelectItem>
                  {stockSelectionStrategies.length > 0 && (
                    <>
                      {/* 我的策略（未发布也显示） */}
                      {stockSelectionStrategies.filter((s) => s.user_id === user?.id).length > 0 && (
                        <>
                          <div className="px-2 py-1 text-xs text-gray-400 font-medium">我的策略</div>
                          {stockSelectionStrategies
                            .filter((s) => s.user_id === user?.id)
                            .map((s) => (
                              <SelectItem key={s.id} value={String(s.id)}>
                                {s.display_name}
                                {s.publish_status !== 'approved' && (
                                  <span className="ml-1 text-xs text-gray-400">（未发布）</span>
                                )}
                              </SelectItem>
                            ))}
                        </>
                      )}
                      {/* 已发布的其他策略 */}
                      {stockSelectionStrategies.filter((s) => s.user_id !== user?.id && s.publish_status === 'approved').length > 0 && (
                        <>
                          <div className="px-2 py-1 text-xs text-gray-400 font-medium">已发布策略</div>
                          {stockSelectionStrategies
                            .filter((s) => s.user_id !== user?.id && s.publish_status === 'approved')
                            .map((s) => (
                              <SelectItem key={s.id} value={String(s.id)}>
                                {s.display_name}
                              </SelectItem>
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

            {/* 自选列表筛选（仅已登录用户） */}
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
                  <SelectTrigger id="list-filter">
                    <SelectValue placeholder="选择列表..." />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">全部股票</SelectItem>
                    {lists.map((list) => (
                      <div key={list.id} className="flex items-center group">
                        <SelectItem value={String(list.id)} className="flex-1">
                          {list.name}
                          <span className="ml-1 text-xs text-gray-400">({list.stock_count})</span>
                        </SelectItem>
                        <span className="flex items-center gap-1 pr-2 opacity-0 group-hover:opacity-100">
                          <button
                            title="重命名"
                            onMouseDown={(e) => { e.preventDefault(); e.stopPropagation(); setRenameTarget(list); setRenameDialogOpen(true) }}
                            className="p-0.5 hover:text-blue-600 rounded"
                          >
                            <Pencil className="h-3 w-3" />
                          </button>
                          <button
                            title="删除"
                            onMouseDown={(e) => { e.preventDefault(); e.stopPropagation(); handleDeleteList(list.id) }}
                            className="p-0.5 hover:text-red-600 rounded"
                          >
                            <Trash2 className="h-3 w-3" />
                          </button>
                        </span>
                      </div>
                    ))}
                    {lists.length === 0 && (
                      <div className="px-3 py-2 text-sm text-gray-400">暂无列表</div>
                    )}
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
          ) : visibleStocks.length === 0 ? (
            <div className="text-center py-12">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="mt-4 text-gray-600 dark:text-gray-400">
                {activeListId !== null ? '列表中暂无股票' : '没有找到股票'}
              </p>
              {totalStocks === 0 && activeListId === null && (
                <p className="mt-2 text-sm text-gray-500 dark:text-gray-500">
                  请前往<a href="/sync" className="text-blue-600 dark:text-blue-400 underline hover:text-blue-800 dark:hover:text-blue-300">数据同步</a>页面同步股票列表
                </p>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-800">
                  <tr>
                    {/* 勾选列（仅已登录用户） */}
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
                              <button
                                className="h-4 w-4 flex items-center justify-center rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                                aria-label="全选选项"
                              >
                                <ChevronDown className="h-3 w-3" />
                              </button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="start">
                              <DropdownMenuItem onClick={toggleSelectAll}>
                                全选当前页（{displayedTsCodes.length} 只）
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                onClick={handleSelectAllFiltered}
                                disabled={selectingAll}
                              >
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
                      <button
                        onClick={() => {
                          if (sortBy === 'pct_change') {
                            const next = sortOrder === 'desc' ? 'asc' : 'desc'
                            setSortOrder(next)
                            updateURL({ sortOrder: next })
                          } else {
                            setSortBy('pct_change')
                            setSortOrder('desc')
                            updateURL({ sortBy: null, sortOrder: null })
                          }
                        }}
                        className="inline-flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-200"
                      >
                        涨跌幅
                        {sortBy === 'pct_change' && (
                          <svg className="w-3 h-3 text-blue-600 dark:text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                            {sortOrder === 'desc'
                              ? <path fillRule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L10 13.586l3.293-3.293a1 1 0 011.414 0z" clipRule="evenodd" />
                              : <path fillRule="evenodd" d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z" clipRule="evenodd" />
                            }
                          </svg>
                        )}
                      </button>
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">操作</th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                  {visibleStocks.map((stock) => {
                    const tsCode = toTsCode(stock.code)
                    const isSelected = selectedCodes.has(tsCode)
                    return (
                      <tr
                        key={stock.code}
                        className={`transition-colors ${isSelected ? 'bg-blue-50 dark:bg-blue-900/20' : 'hover:bg-gray-50 dark:hover:bg-gray-800/50'}`}
                        onClick={isAuthenticated ? () => toggleStock(tsCode) : undefined}
                        style={isAuthenticated ? { cursor: 'pointer' } : undefined}
                      >
                        {isAuthenticated && (
                          <td className="px-4 py-4 w-10" onClick={(e) => e.stopPropagation()}>
                            <Checkbox
                              checked={isSelected}
                              onCheckedChange={() => toggleStock(tsCode)}
                              aria-label={`选择 ${stock.name}`}
                            />
                          </td>
                        )}
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium" onClick={(e) => e.stopPropagation()}>
                          <a
                            href={`/analysis?code=${stock.code}`}
                            className="text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
                          >
                            {stock.name}({stock.code})
                          </a>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">
                          {stock.latest_price ? (
                            <span className={
                              stock.pct_change != null
                                ? stock.pct_change > 0 ? 'text-red-600 dark:text-red-400'
                                : stock.pct_change < 0 ? 'text-green-600 dark:text-green-400'
                                : 'text-gray-900 dark:text-white'
                                : 'text-gray-900 dark:text-white'
                            }>
                              {stock.latest_price.toFixed(2)}
                            </span>
                          ) : '-'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">
                          {stock.pct_change != null ? (
                            <span className={stock.pct_change > 0 ? 'text-red-600 dark:text-red-400' : stock.pct_change < 0 ? 'text-green-600 dark:text-green-400' : 'text-gray-600 dark:text-gray-400'}>
                              {stock.pct_change > 0 ? '+' : ''}{stock.pct_change.toFixed(2)}%
                            </span>
                          ) : '-'}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                          <button
                            onClick={async () => {
                              setHotMoneyStock({ name: stock.name, code: stock.code })
                              setHotMoneyContent('')
                              setHotMoneyLoading(true)
                              setHotMoneyDialogOpen(true)
                              try {
                                const res = await apiClient.getPromptTemplateByKey(
                                  'top_speculative_investor_v1',
                                  { stock_name: stock.name, stock_code: stock.code }
                                )
                                if (res?.code === 200 && res.data?.user_prompt_template) {
                                  const parts = [res.data.system_prompt, res.data.user_prompt_template].filter(Boolean)
                                  setHotMoneyContent(parts.join('\n\n'))
                                }
                              } catch {
                                setHotMoneyContent('加载失败，请重试')
                              } finally {
                                setHotMoneyLoading(false)
                              }
                            }}
                            className="text-xs px-2 py-1 rounded border border-yellow-400 text-yellow-600 hover:bg-yellow-50 dark:border-yellow-500 dark:text-yellow-400 dark:hover:bg-yellow-900/20 transition-colors whitespace-nowrap"
                          >
                            游资观点
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* 分页工具栏 */}
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
                        <ChevronLeft className="h-4 w-4" />
                        <span className="hidden md:inline">上一页</span>
                      </Button>
                    </PaginationItem>
                    {currentPage - 2 > 1 && (
                      <>
                        <PaginationItem>
                          <PaginationLink onClick={() => goToPage(1)} isActive={false} className="cursor-pointer">1</PaginationLink>
                        </PaginationItem>
                        {currentPage - 2 > 2 && (
                          <PaginationItem className="hidden md:inline-flex"><PaginationEllipsis /></PaginationItem>
                        )}
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
                        {currentPage + 2 < totalPages - 1 && (
                          <PaginationItem className="hidden md:inline-flex"><PaginationEllipsis /></PaginationItem>
                        )}
                        <PaginationItem>
                          <PaginationLink onClick={() => goToPage(totalPages)} isActive={false} className="cursor-pointer">{totalPages}</PaginationLink>
                        </PaginationItem>
                      </>
                    )}
                    <PaginationItem>
                      <Button variant="outline" size="sm" onClick={() => goToPage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages} className="gap-1">
                        <span className="hidden md:inline">下一页</span>
                        <ChevronRight className="h-4 w-4" />
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
      <HotMoneyViewDialog
        open={hotMoneyDialogOpen}
        onClose={() => { setHotMoneyDialogOpen(false); setHotMoneyStock(null) }}
        stockName={hotMoneyStock?.name ?? ''}
        stockCode={hotMoneyStock?.code ?? ''}
        content={hotMoneyContent}
        loading={hotMoneyLoading}
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
