/**
 * 股票筛选弹窗组件
 *
 * 功能特性：
 * - 表格展示股票（带勾选框）
 * - 筛选器（市场、行业、概念）
 * - 搜索功能
 * - 分页展示
 * - 全选当前页 / 全选所有筛选结果
 * - 实时显示已选数量
 *
 * 使用场景：
 * - 回测页面批量选择股票
 */

'use client'

import { useState, useCallback, useMemo, useEffect } from 'react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Checkbox } from '@/components/ui/checkbox'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
} from '@/components/ui/pagination'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { ChevronLeft, ChevronRight, Loader2 } from 'lucide-react'
import { LazyConceptSelect } from '@/components/stocks/LazyConceptSelect'
import { useStockFilter, fetchAllStockCodes } from '@/hooks/useStockFilter'

interface StockSelectionDialogProps {
  /** 是否打开弹窗 */
  open: boolean
  /** 关闭弹窗回调 */
  onClose: () => void
  /** 确认选择回调 */
  onConfirm: (stockCodes: string[]) => void
  /** 已选股票代码列表（用于初始化） */
  initialSelected?: string[]
  /** 最大可选数量 */
  maxSelection?: number
  /** 已有股票数量（用于计算剩余可选数量） */
  existingCount?: number
}

export function StockSelectionDialog({
  open,
  onClose,
  onConfirm,
  initialSelected = [],
  maxSelection = 500,
  existingCount = 0
}: StockSelectionDialogProps) {
  // 使用股票筛选 Hook
  const {
    stocks,
    total,
    totalPages,
    loading,
    error,
    filters,
    updateFilters,
    goToPage,
    setPageSize,
    setSort
  } = useStockFilter({}, open) // 只在打开时自动加载

  // 已选股票代码集合
  const [selectedCodes, setSelectedCodes] = useState<Set<string>>(new Set(initialSelected))
  const [selectingAll, setSelectingAll] = useState(false)

  // 重置选择状态
  useEffect(() => {
    if (open) {
      setSelectedCodes(new Set(initialSelected))
    }
  }, [open, initialSelected])

  // 可用配额
  const availableQuota = maxSelection - existingCount

  /**
   * 切换单个股票的选择状态
   */
  const toggleStock = useCallback((code: string) => {
    setSelectedCodes(prev => {
      const newSet = new Set(prev)
      if (newSet.has(code)) {
        newSet.delete(code)
      } else {
        // 检查是否超过配额
        if (newSet.size >= availableQuota) {
          return prev // 不做修改
        }
        newSet.add(code)
      }
      return newSet
    })
  }, [availableQuota])

  /**
   * 全选当前页
   */
  const selectCurrentPage = useCallback(() => {
    setSelectedCodes(prev => {
      const newSet = new Set(prev)
      let added = 0
      for (const stock of stocks) {
        if (!newSet.has(stock.code)) {
          if (newSet.size + added >= availableQuota) {
            break
          }
          newSet.add(stock.code)
          added++
        }
      }
      return newSet
    })
  }, [stocks, availableQuota])

  /**
   * 取消全选当前页
   */
  const deselectCurrentPage = useCallback(() => {
    setSelectedCodes(prev => {
      const newSet = new Set(prev)
      for (const stock of stocks) {
        newSet.delete(stock.code)
      }
      return newSet
    })
  }, [stocks])

  /**
   * 全选所有筛选结果
   */
  const selectAllFiltered = useCallback(async () => {
    try {
      setSelectingAll(true)
      const allCodes = await fetchAllStockCodes(
        {
          market: filters.market,
          industry: filters.industry,
          concepts: filters.concepts,
          search: filters.search
        },
        availableQuota
      )

      setSelectedCodes(prev => {
        const newSet = new Set(prev)
        for (const code of allCodes) {
          if (newSet.size >= availableQuota) {
            break
          }
          newSet.add(code)
        }
        return newSet
      })
    } catch (err) {
      console.error('Failed to select all:', err)
      alert('全选失败，请重试')
    } finally {
      setSelectingAll(false)
    }
  }, [filters, availableQuota])

  /**
   * 清空选择
   */
  const clearSelection = useCallback(() => {
    setSelectedCodes(new Set())
  }, [])

  /**
   * 确认选择
   */
  const handleConfirm = useCallback(() => {
    onConfirm(Array.from(selectedCodes))
    onClose()
  }, [selectedCodes, onConfirm, onClose])

  /**
   * 当前页是否全部选中
   */
  const isCurrentPageSelected = useMemo(() => {
    return stocks.length > 0 && stocks.every(stock => selectedCodes.has(stock.code))
  }, [stocks, selectedCodes])

  /**
   * 当前页是否部分选中
   */
  const isCurrentPageIndeterminate = useMemo(() => {
    const selectedInPage = stocks.filter(stock => selectedCodes.has(stock.code)).length
    return selectedInPage > 0 && selectedInPage < stocks.length
  }, [stocks, selectedCodes])

  return (
    <Dialog open={open} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-6xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>从股票列表选择</DialogTitle>
          <DialogDescription>
            筛选并选择要添加到股票池的股票（还可添加 {availableQuota} 只）
          </DialogDescription>
        </DialogHeader>

        {/* 筛选器区域 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 py-4">
          <div className="space-y-2">
            <Label htmlFor="dialog-market-filter">市场筛选</Label>
            <Select
              value={filters.market}
              onValueChange={(value) => updateFilters({ market: value })}
            >
              <SelectTrigger id="dialog-market-filter">
                <SelectValue />
              </SelectTrigger>
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
            <Label htmlFor="dialog-industry-filter">行业筛选</Label>
            <Select
              value={filters.industry}
              onValueChange={(value) => updateFilters({ industry: value })}
            >
              <SelectTrigger id="dialog-industry-filter">
                <SelectValue placeholder="选择行业..." />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部行业</SelectItem>
                <SelectItem value="银行">银行</SelectItem>
                <SelectItem value="医药">医药</SelectItem>
                <SelectItem value="计算机">计算机</SelectItem>
                <SelectItem value="电子">电子</SelectItem>
                <SelectItem value="汽车">汽车</SelectItem>
                <SelectItem value="房地产">房地产</SelectItem>
                <SelectItem value="建筑">建筑</SelectItem>
                <SelectItem value="钢铁">钢铁</SelectItem>
                <SelectItem value="化工">化工</SelectItem>
                <SelectItem value="食品饮料">食品饮料</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="dialog-concept-filter">概念筛选</Label>
            <LazyConceptSelect
              value={filters.concepts || 'all'}
              onSelect={(value) => updateFilters({ concepts: value })}
              includeAllOption={true}
              valueType="code"
              placeholder="选择概念..."
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="dialog-search-input">搜索股票</Label>
            <Input
              id="dialog-search-input"
              type="text"
              placeholder="代码或名称..."
              value={filters.search}
              onChange={(e) => updateFilters({ search: e.target.value })}
            />
          </div>
        </div>

        {/* 错误提示 */}
        {error && (
          <Alert className="bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
            <AlertDescription className="text-red-800 dark:text-red-200">
              {error}
            </AlertDescription>
          </Alert>
        )}

        {/* 操作栏 */}
        <div className="flex items-center justify-between py-2 border-y">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <Checkbox
                id="select-current-page"
                checked={isCurrentPageSelected}
                onCheckedChange={(checked) => {
                  if (checked) {
                    selectCurrentPage()
                  } else {
                    deselectCurrentPage()
                  }
                }}
                className={isCurrentPageIndeterminate ? 'data-[state=checked]:bg-blue-600' : ''}
              />
              <Label htmlFor="select-current-page" className="text-sm cursor-pointer">
                全选当前页
              </Label>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={selectAllFiltered}
              disabled={selectingAll || availableQuota === 0}
            >
              {selectingAll ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  加载中...
                </>
              ) : (
                '全选所有筛选结果'
              )}
            </Button>

            <Button
              variant="ghost"
              size="sm"
              onClick={clearSelection}
              disabled={selectedCodes.size === 0}
            >
              清空选择
            </Button>
          </div>

          <div className="text-sm font-medium">
            已选: <span className="text-blue-600 dark:text-blue-400">{selectedCodes.size}</span> / {availableQuota}
          </div>
        </div>

        {/* 股票表格 */}
        <div className="flex-1 overflow-auto border rounded-lg">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <Loader2 className="mx-auto h-12 w-12 animate-spin text-blue-600" />
                <p className="mt-4 text-gray-600 dark:text-gray-400">加载中...</p>
              </div>
            </div>
          ) : stocks.length === 0 ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-center">
                <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p className="mt-4 text-gray-600 dark:text-gray-400">没有找到股票</p>
              </div>
            </div>
          ) : (
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-800 sticky top-0">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider w-12">
                    <span className="sr-only">选择</span>
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    股票
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    最新价
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    <button
                      onClick={() => {
                        if (filters.sortBy === 'pct_change') {
                          setSort('pct_change', filters.sortOrder === 'desc' ? 'asc' : 'desc')
                        } else {
                          setSort('pct_change', 'desc')
                        }
                      }}
                      className="inline-flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-200"
                    >
                      涨跌幅
                      {filters.sortBy === 'pct_change' && (
                        <svg className="w-3 h-3 text-blue-600 dark:text-blue-400" fill="currentColor" viewBox="0 0 20 20">
                          {filters.sortOrder === 'desc' ? (
                            <path fillRule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L10 13.586l3.293-3.293a1 1 0 011.414 0z" clipRule="evenodd" />
                          ) : (
                            <path fillRule="evenodd" d="M14.707 12.707a1 1 0 01-1.414 0L10 9.414l-3.293 3.293a1 1 0 01-1.414-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 010 1.414z" clipRule="evenodd" />
                          )}
                        </svg>
                      )}
                    </button>
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                {stocks.map((stock) => {
                  const isSelected = selectedCodes.has(stock.code)
                  const isDisabled = !isSelected && selectedCodes.size >= availableQuota

                  return (
                    <tr
                      key={stock.code}
                      className={`${isSelected ? 'bg-blue-50 dark:bg-blue-900/20' : ''} ${isDisabled ? 'opacity-50' : 'hover:bg-gray-50 dark:hover:bg-gray-800'}`}
                    >
                      <td className="px-4 py-4 whitespace-nowrap">
                        <Checkbox
                          checked={isSelected}
                          onCheckedChange={() => toggleStock(stock.code)}
                          disabled={isDisabled}
                        />
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900 dark:text-white">
                        {stock.name}
                        <span className="ml-2 text-gray-500 dark:text-gray-400">({stock.code})</span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">
                        {stock.latest_price ? (
                          <span className={
                            stock.pct_change !== null && stock.pct_change !== undefined
                              ? stock.pct_change > 0
                                ? 'text-red-600 dark:text-red-400'
                                : stock.pct_change < 0
                                  ? 'text-green-600 dark:text-green-400'
                                  : 'text-gray-900 dark:text-white'
                              : 'text-gray-900 dark:text-white'
                          }>
                            {stock.latest_price.toFixed(2)}
                          </span>
                        ) : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-right font-medium">
                        {stock.pct_change !== null && stock.pct_change !== undefined ? (
                          <span className={stock.pct_change > 0 ? 'text-red-600 dark:text-red-400' : stock.pct_change < 0 ? 'text-green-600 dark:text-green-400' : 'text-gray-600 dark:text-gray-400'}>
                            {stock.pct_change > 0 ? '+' : ''}{stock.pct_change.toFixed(2)}%
                          </span>
                        ) : '-'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>

        {/* 分页工具栏 */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between py-3 border-t">
            <div className="flex items-center gap-4">
              <p className="text-sm text-gray-700 dark:text-gray-300">
                显示 <span className="font-medium">{((filters.page || 1) - 1) * (filters.pageSize || 20) + 1}</span> - <span className="font-medium">{Math.min((filters.page || 1) * (filters.pageSize || 20), total)}</span>
                {' '}共 <span className="font-medium">{total}</span> 条
              </p>
              <div className="flex items-center gap-2">
                <Label htmlFor="dialog-page-size" className="text-sm">每页</Label>
                <Select
                  value={(filters.pageSize || 20).toString()}
                  onValueChange={(value) => setPageSize(Number(value))}
                >
                  <SelectTrigger id="dialog-page-size" className="w-[80px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="10">10</SelectItem>
                    <SelectItem value="20">20</SelectItem>
                    <SelectItem value="30">30</SelectItem>
                    <SelectItem value="50">50</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Pagination>
              <PaginationContent>
                <PaginationItem>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => goToPage(Math.max(1, (filters.page || 1) - 1))}
                    disabled={(filters.page || 1) === 1}
                    className="gap-1"
                  >
                    <ChevronLeft className="h-4 w-4" />
                    上一页
                  </Button>
                </PaginationItem>

                {(filters.page || 1) > 2 && (
                  <>
                    <PaginationItem>
                      <PaginationLink onClick={() => goToPage(1)} className="cursor-pointer">
                        1
                      </PaginationLink>
                    </PaginationItem>
                    {(filters.page || 1) > 3 && (
                      <PaginationItem>
                        <PaginationEllipsis />
                      </PaginationItem>
                    )}
                  </>
                )}

                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter(page => page >= (filters.page || 1) - 1 && page <= (filters.page || 1) + 1)
                  .map(page => (
                    <PaginationItem key={page}>
                      <PaginationLink
                        onClick={() => goToPage(page)}
                        isActive={(filters.page || 1) === page}
                        className="cursor-pointer"
                      >
                        {page}
                      </PaginationLink>
                    </PaginationItem>
                  ))}

                {(filters.page || 1) < totalPages - 1 && (
                  <>
                    {(filters.page || 1) < totalPages - 2 && (
                      <PaginationItem>
                        <PaginationEllipsis />
                      </PaginationItem>
                    )}
                    <PaginationItem>
                      <PaginationLink onClick={() => goToPage(totalPages)} className="cursor-pointer">
                        {totalPages}
                      </PaginationLink>
                    </PaginationItem>
                  </>
                )}

                <PaginationItem>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => goToPage(Math.min(totalPages, (filters.page || 1) + 1))}
                    disabled={(filters.page || 1) === totalPages}
                    className="gap-1"
                  >
                    下一页
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          </div>
        )}

        {/* 底部操作按钮 */}
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            取消
          </Button>
          <Button onClick={handleConfirm} disabled={selectedCodes.size === 0}>
            确认添加 ({selectedCodes.size})
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
