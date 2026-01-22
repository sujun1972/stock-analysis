'use client'

import { useEffect, useState, useMemo } from 'react'
import { apiClient } from '@/lib/api-client'
import { useStockStore } from '@/store/stock-store'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
} from '@/components/ui/pagination'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useSmartRefresh } from '@/hooks/useMarketStatus'

export default function StocksPage() {
  const { stocks, setStocks, setLoading, isLoading, error, setError } = useStockStore()
  const [searchTerm, setSearchTerm] = useState('')
  const [marketFilter, setMarketFilter] = useState<string>('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [totalStocks, setTotalStocks] = useState(0)
  const [pageSize, setPageSize] = useState(20)
  const [sortBy, setSortBy] = useState('pct_change')
  const [sortOrder, setSortOrder] = useState('desc')

  useEffect(() => {
    loadStocks()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPage, marketFilter, searchTerm, pageSize, sortBy, sortOrder])

  const loadStocks = async () => {
    try {
      setLoading(true)
      setError(null)

      const params: any = {
        skip: (currentPage - 1) * pageSize,
        limit: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      }

      if (marketFilter !== 'all') {
        params.market = marketFilter
      }

      if (searchTerm && searchTerm.trim()) {
        params.search = searchTerm.trim()
      }

      const response = await apiClient.getStockList(params)
      setStocks(response.data)
      setTotalStocks(response.total)
    } catch (err: any) {
      setError(err.message || '加载股票列表失败')
      console.error('Failed to load stocks:', err)
    } finally {
      setLoading(false)
    }
  }

  // 获取当前页面显示的股票代码列表
  const currentPageCodes = useMemo(() => {
    return stocks.map(stock => stock.code)
  }, [stocks])

  // 使用智能刷新Hook - 只刷新当前页面的股票（自动后台刷新）
  useSmartRefresh(
    async () => {
      // 只同步当前页面股票的实时数据
      if (currentPageCodes.length > 0) {
        await apiClient.syncRealtimeQuotes({
          codes: currentPageCodes,
          batch_size: currentPageCodes.length
        })
      }

      // 然后重新加载股票列表
      await loadStocks()
    },
    currentPageCodes,  // 监控当前页面的股票
    true               // 启用自动刷新
  )

  const totalPages = Math.ceil(totalStocks / pageSize)

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          股票列表
        </h1>
        <p className="text-gray-600 dark:text-gray-300 mt-2">
          共 {totalStocks.toLocaleString()} 只股票
        </p>
      </div>

      {/* 错误提示 */}
      {error && (
        <Alert className="bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
          <AlertDescription className="text-red-800 dark:text-red-200">
            {error}
          </AlertDescription>
        </Alert>
      )}

      {/* 搜索和筛选 */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="market-filter">市场筛选</Label>
              <Select
                value={marketFilter}
                onValueChange={(value) => {
                  setMarketFilter(value)
                  setCurrentPage(1)
                }}
              >
                <SelectTrigger id="market-filter">
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
              <Label htmlFor="search-input">搜索股票</Label>
              <Input
                id="search-input"
                type="text"
                placeholder="输入股票代码或名称..."
                value={searchTerm}
                onChange={(e) => {
                  setSearchTerm(e.target.value)
                  setCurrentPage(1)
                }}
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
          ) : stocks.length === 0 ? (
            <div className="text-center py-12">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="mt-4 text-gray-600 dark:text-gray-400">没有找到股票</p>
              {totalStocks === 0 && (
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
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    股票
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    最新价
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    <button
                      onClick={() => {
                        if (sortBy === 'pct_change') {
                          setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
                        } else {
                          setSortBy('pct_change')
                          setSortOrder('desc')
                        }
                      }}
                      className="inline-flex items-center gap-1 hover:text-gray-700 dark:hover:text-gray-200"
                    >
                      涨跌幅
                      {sortBy === 'pct_change' && (
                        <svg
                          className="w-3 h-3 text-blue-600 dark:text-blue-400"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          {sortOrder === 'desc' ? (
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
                {stocks.map((stock) => (
                  <tr key={stock.code} className="table-row">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
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
                ))}
              </tbody>
            </table>
          </div>
        )}

          {/* 分页工具栏 */}
          {totalPages > 1 && (
            <div className="px-6 py-4 border-t border-gray-200 dark:border-gray-700">
              {/* 响应式布局：移动端垂直排列，桌面端水平排列（左右分布） */}
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                {/* 左侧区域：分页信息 + 每页条数选择器 */}
                <div className="flex items-center justify-between md:justify-start gap-4 md:gap-6">
                  {/* 分页信息：移动端显示简化版，桌面端显示详细信息 */}
                  <p className="text-sm text-gray-700 dark:text-gray-300">
                    <span className="md:hidden">第 <span className="font-medium">{currentPage}</span> / {totalPages} 页</span>
                    <span className="hidden md:inline">
                      显示 <span className="font-medium">{(currentPage - 1) * pageSize + 1}</span> - <span className="font-medium">{Math.min(currentPage * pageSize, totalStocks)}</span>
                      {' '}共 <span className="font-medium">{totalStocks}</span> 条
                    </span>
                  </p>
                  <div className="flex items-center gap-2">
                    <Label htmlFor="page-size" className="text-sm">每页</Label>
                    <Select
                      value={pageSize.toString()}
                      onValueChange={(value) => {
                        setPageSize(Number(value))
                        setCurrentPage(1)
                      }}
                    >
                      <SelectTrigger id="page-size" className="w-[80px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="10">10</SelectItem>
                        <SelectItem value="20">20</SelectItem>
                        <SelectItem value="30">30</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {/* 右侧区域：分页导航控件（桌面端靠右对齐） */}
                <Pagination>
                  <PaginationContent>
                    {/* 上一页按钮（移动端仅显示图标，桌面端显示文字） */}
                    <PaginationItem>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                        disabled={currentPage === 1}
                        className="gap-1"
                      >
                        <ChevronLeft className="h-4 w-4" />
                        <span className="hidden md:inline">上一页</span>
                      </Button>
                    </PaginationItem>

                    {/* 第一页链接（当前页距离第一页较远时显示） */}
                    {currentPage > 2 && (
                      <>
                        <PaginationItem>
                          <PaginationLink
                            onClick={() => setCurrentPage(1)}
                            isActive={false}
                            className="cursor-pointer"
                          >
                            1
                          </PaginationLink>
                        </PaginationItem>
                        {/* 省略号（仅桌面端显示） */}
                        {currentPage > 3 && (
                          <PaginationItem className="hidden md:inline-flex">
                            <PaginationEllipsis />
                          </PaginationItem>
                        )}
                      </>
                    )}

                    {/* 页码列表：移动端仅显示当前页，桌面端显示当前页前后2页 */}
                    {Array.from({ length: totalPages }, (_, i) => i + 1)
                      .filter(page => page >= currentPage - 2 && page <= currentPage + 2)
                      .map(page => (
                        <PaginationItem key={page} className={page === currentPage ? "" : "hidden md:inline-flex"}>
                          <PaginationLink
                            onClick={() => setCurrentPage(page)}
                            isActive={currentPage === page}
                            className="cursor-pointer"
                          >
                            {page}
                          </PaginationLink>
                        </PaginationItem>
                      ))}

                    {/* 最后一页链接（当前页距离最后一页较远时显示） */}
                    {currentPage < totalPages - 1 && (
                      <>
                        {/* 省略号（仅桌面端显示） */}
                        {currentPage < totalPages - 2 && (
                          <PaginationItem className="hidden md:inline-flex">
                            <PaginationEllipsis />
                          </PaginationItem>
                        )}
                        <PaginationItem>
                          <PaginationLink
                            onClick={() => setCurrentPage(totalPages)}
                            isActive={false}
                            className="cursor-pointer"
                          >
                            {totalPages}
                          </PaginationLink>
                        </PaginationItem>
                      </>
                    )}

                    {/* 下一页按钮（移动端仅显示图标，桌面端显示文字） */}
                    <PaginationItem>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                        disabled={currentPage === totalPages}
                        className="gap-1"
                      >
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
    </div>
  )
}
