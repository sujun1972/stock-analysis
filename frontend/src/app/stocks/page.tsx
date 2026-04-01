'use client'

import { useEffect, useState, useMemo, useCallback, useRef } from 'react'
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
  BookmarkCheck,
  Trash2,
  Pencil,
  List,
  X,
  ChevronDown,
  Plus,
} from 'lucide-react'
import { useSmartRefresh } from '@/hooks/useMarketStatus'
import { LazyConceptSelect } from '@/components/stocks/LazyConceptSelect'
import type { StockList } from '@/types'

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

// ── 主页面 ────────────────────────────────────────────────────
export default function StocksPage() {
  const { stocks, setStocks, setLoading, isLoading, error, setError } = useStockStore()
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const {
    lists,
    activeListId,
    activeListItems,
    activeListCodes,
    isLoadingLists,
    fetchLists,
    setActiveList,
    deleteList,
    removeStocks,
  } = useStockListStore()

  // ── 筛选 / 分页状态 ──
  const [searchTerm, setSearchTerm] = useState('')
  const [marketFilter, setMarketFilter] = useState<string>('all')
  const [industryFilter, setIndustryFilter] = useState<string>('all')
  const [conceptFilter, setConceptFilter] = useState<string>('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [totalStocks, setTotalStocks] = useState(0)
  const [pageSize, setPageSize] = useState(20)
  const [sortBy, setSortBy] = useState('pct_change')
  const [sortOrder, setSortOrder] = useState('desc')
  const [industries, setIndustries] = useState<{ value: string; label: string; count: number }[]>([])

  // ── 选股状态 ──
  const [selectedCodes, setSelectedCodes] = useState<Set<string>>(new Set())

  // ── Dialog 状态 ──
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [renameDialogOpen, setRenameDialogOpen] = useState(false)
  const [renameTarget, setRenameTarget] = useState<StockList | null>(null)
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null)

  // ── 加载行业列表 ──
  useEffect(() => {
    apiClient.getStockIndustries().then(setIndustries).catch(() => {})
  }, [])

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
      if (marketFilter !== 'all') params.market = marketFilter
      if (industryFilter !== 'all') params.industry = industryFilter
      if (conceptFilter !== 'all') params.concept_code = conceptFilter
      if (searchTerm?.trim()) params.search = searchTerm.trim()

      const response = await apiClient.getStockList(params)
      setStocks(response.items || [])
      setTotalStocks(response.total ?? 0)
    } catch (err: any) {
      setError(err.message || '加载股票列表失败')
      if (!silent) { setStocks([]); setTotalStocks(0) }
    } finally {
      if (!silent) setLoading(false)
    }
  }, [currentPage, marketFilter, industryFilter, conceptFilter, searchTerm, pageSize, sortBy, sortOrder, setStocks, setLoading, setError])

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
  const activeList = useMemo(
    () => lists.find((l) => l.id === activeListId) ?? null,
    [lists, activeListId]
  )

  // ── 激活列表视图时，把表格股票过滤为列表成分股 ──
  const visibleStocks = useMemo(() => {
    if (activeListId === null) return displayedStocks
    // 列表视图：显示激活列表中在当前页也存在的股票；若搜索/筛选无结果，直接显示列表成分股
    const listCodes = new Set(activeListItems.map((i) => i.code))
    const filtered = displayedStocks.filter((s) => listCodes.has(s.code))
    // 如果当前筛选器有内容，用过滤后结果；否则直接展示列表成分股行情
    if (searchTerm || marketFilter !== 'all' || industryFilter !== 'all' || conceptFilter !== 'all') {
      return filtered
    }
    // 无筛选器：直接渲染列表成分股（带行情的 activeListItems）
    return activeListItems.map((item) => ({
      code: item.code,
      ts_code: item.ts_code,
      name: item.name,
      market: item.market,
      industry: item.industry,
      latest_price: item.latest_price,
      pct_change: item.pct_change,
      change_amount: item.change_amount,
    } as any))
  }, [activeListId, displayedStocks, activeListItems, searchTerm, marketFilter, industryFilter, conceptFilter])

  return (
    <div className="space-y-6">
      {/* Toast 提示 */}
      {toast && (
        <div className={`fixed top-4 right-4 z-50 px-4 py-3 rounded-lg shadow-lg text-white text-sm transition-all ${toast.type === 'success' ? 'bg-green-600' : 'bg-red-600'}`}>
          {toast.msg}
        </div>
      )}

      {/* 页面标题行 */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">股票列表</h1>
          <p className="text-gray-600 dark:text-gray-300 mt-1">
            {activeList
              ? <span>自选列表：<strong>{activeList.name}</strong>（{activeList.stock_count} 只）</span>
              : <span>共 {(totalStocks ?? 0).toLocaleString()} 只股票</span>
            }
          </p>
        </div>

        {/* 自选列表管理（仅已登录用户） */}
        {isAuthenticated && (
          <div className="flex items-center gap-2 flex-wrap">
            {/* 激活列表时显示退出按钮 */}
            {activeList && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => { setActiveList(null); setSelectedCodes(new Set()) }}
              >
                <X className="h-4 w-4 mr-1" />
                退出列表视图
              </Button>
            )}

            {/* 列表选择下拉 */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant={activeList ? 'default' : 'outline'} size="sm" disabled={isLoadingLists}>
                  <List className="h-4 w-4 mr-1" />
                  {activeList ? activeList.name : '我的列表'}
                  <ChevronDown className="h-3 w-3 ml-1" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                {lists.length === 0 && (
                  <div className="px-3 py-2 text-sm text-gray-500">暂无列表</div>
                )}
                {lists.map((list) => (
                  <DropdownMenuItem
                    key={list.id}
                    className="flex items-center justify-between group cursor-pointer"
                    onSelect={(e) => {
                      e.preventDefault()
                      setActiveList(list.id === activeListId ? null : list.id)
                      setSelectedCodes(new Set())
                    }}
                  >
                    <span className={`truncate flex-1 ${list.id === activeListId ? 'font-semibold text-blue-600 dark:text-blue-400' : ''}`}>
                      {list.name}
                      <span className="ml-1 text-xs text-gray-400">({list.stock_count})</span>
                    </span>
                    <span className="flex items-center gap-1 ml-2 opacity-0 group-hover:opacity-100">
                      <button
                        title="重命名"
                        onClick={(e) => { e.stopPropagation(); setRenameTarget(list); setRenameDialogOpen(true) }}
                        className="p-0.5 hover:text-blue-600 rounded"
                      >
                        <Pencil className="h-3 w-3" />
                      </button>
                      <button
                        title="删除"
                        onClick={(e) => { e.stopPropagation(); handleDeleteList(list.id) }}
                        className="p-0.5 hover:text-red-600 rounded"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    </span>
                  </DropdownMenuItem>
                ))}
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onSelect={(e) => { e.preventDefault(); setAddDialogOpen(true) }}
                  className="cursor-pointer"
                  disabled={selectedCodes.size === 0}
                >
                  <Plus className="h-4 w-4 mr-2" />
                  将选中股票添加到列表...
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        )}
      </div>

      {/* 错误提示 */}
      {error && (
        <Alert className="bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
          <AlertDescription className="text-red-800 dark:text-red-200">{error}</AlertDescription>
        </Alert>
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label htmlFor="market-filter">市场筛选</Label>
              <Select value={marketFilter} onValueChange={(v) => { setMarketFilter(v); setCurrentPage(1) }}>
                <SelectTrigger id="market-filter"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部市场</SelectItem>
                  <SelectItem value="上海主板">上海主板</SelectItem>
                  <SelectItem value="深圳主板">深圳主板</SelectItem>
                  <SelectItem value="创业板">创业板</SelectItem>
                  <SelectItem value="科创板">科创板</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="industry-filter">行业筛选</Label>
              <Select value={industryFilter} onValueChange={(v) => { setIndustryFilter(v); setCurrentPage(1) }}>
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
              <Label htmlFor="concept-filter">概念筛选</Label>
              <LazyConceptSelect
                value={conceptFilter}
                onSelect={(v) => { setConceptFilter(v); setCurrentPage(1) }}
                includeAllOption={true}
                valueType="code"
                placeholder="选择概念..."
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="search-input">搜索股票</Label>
              <Input
                id="search-input"
                type="text"
                placeholder="输入股票代码或名称..."
                value={searchTerm}
                onChange={(e) => { setSearchTerm(e.target.value); setCurrentPage(1) }}
              />
            </div>
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
                        {/* shadcn Checkbox 原生支持 "indeterminate" 作为 checked 值 */}
                        <Checkbox
                          checked={someCurrentPageSelected ? 'indeterminate' : allCurrentPageSelected}
                          onCheckedChange={toggleSelectAll}
                          aria-label="全选当前页"
                        />
                      </th>
                    )}
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">股票</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">最新价</th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      <button
                        onClick={() => {
                          if (sortBy === 'pct_change') setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
                          else { setSortBy('pct_change'); setSortOrder('desc') }
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
                    {/* 已登录时显示"是否在当前列表"标记列 */}
                    {isAuthenticated && activeListId !== null && (
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider w-12">列表</th>
                    )}
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                  {visibleStocks.map((stock) => {
                    const tsCode = toTsCode(stock.code)
                    const isSelected = selectedCodes.has(tsCode)
                    const inActiveList = activeListCodes.has(tsCode)
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
                        {isAuthenticated && activeListId !== null && (
                          <td className="px-4 py-4 text-center w-12">
                            {inActiveList && (
                              <BookmarkCheck className="h-4 w-4 text-blue-500 mx-auto" />
                            )}
                          </td>
                        )}
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* 分页工具栏（仅全局视图显示） */}
          {activeListId === null && totalPages > 1 && (
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
                    <Select value={pageSize.toString()} onValueChange={(v) => { setPageSize(Number(v)); setCurrentPage(1) }}>
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
                      <Button variant="outline" size="sm" onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1} className="gap-1">
                        <ChevronLeft className="h-4 w-4" />
                        <span className="hidden md:inline">上一页</span>
                      </Button>
                    </PaginationItem>
                    {currentPage > 2 && (
                      <>
                        <PaginationItem>
                          <PaginationLink onClick={() => setCurrentPage(1)} isActive={false} className="cursor-pointer">1</PaginationLink>
                        </PaginationItem>
                        {currentPage > 3 && (
                          <PaginationItem className="hidden md:inline-flex"><PaginationEllipsis /></PaginationItem>
                        )}
                      </>
                    )}
                    {Array.from({ length: totalPages }, (_, i) => i + 1)
                      .filter(page => page >= currentPage - 2 && page <= currentPage + 2)
                      .map(page => (
                        <PaginationItem key={page} className={page === currentPage ? '' : 'hidden md:inline-flex'}>
                          <PaginationLink onClick={() => setCurrentPage(page)} isActive={currentPage === page} className="cursor-pointer">{page}</PaginationLink>
                        </PaginationItem>
                      ))}
                    {currentPage < totalPages - 1 && (
                      <>
                        {currentPage < totalPages - 2 && (
                          <PaginationItem className="hidden md:inline-flex"><PaginationEllipsis /></PaginationItem>
                        )}
                        <PaginationItem>
                          <PaginationLink onClick={() => setCurrentPage(totalPages)} isActive={false} className="cursor-pointer">{totalPages}</PaginationLink>
                        </PaginationItem>
                      </>
                    )}
                    <PaginationItem>
                      <Button variant="outline" size="sm" onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages} className="gap-1">
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
    </div>
  )
}
