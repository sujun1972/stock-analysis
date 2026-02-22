'use client'

import { useState, useEffect, useMemo } from 'react'
import { toast } from 'sonner'
import { Search, RefreshCw, Database, TrendingUp, TrendingDown, ChevronLeft, ChevronRight } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import type { StockInfo, Concept, PaginatedResponse } from '@/types/stock'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { StockDetailDialog } from '@/components/stocks/StockDetailDialog'
import { LazyConceptSelect } from '@/components/stocks/LazyConceptSelect'

export default function StocksManagementPage() {
  // 数据状态
  const [stocks, setStocks] = useState<StockInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [totalStocks, setTotalStocks] = useState(0)

  // 股票详情弹窗状态
  const [selectedStock, setSelectedStock] = useState<StockInfo | null>(null)
  const [detailDialogOpen, setDetailDialogOpen] = useState(false)

  // 筛选和搜索
  const [search, setSearch] = useState('')
  const [marketFilter, setMarketFilter] = useState<string>('all')
  const [industryFilter, setIndustryFilter] = useState<string>('all')
  const [conceptFilter, setConceptFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')

  // 分页
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  // 排序
  const [sortBy, setSortBy] = useState<string>('pct_change')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  // 计算总页数
  const totalPages = Math.ceil(totalStocks / pageSize)

  // 加载股票列表
  const loadStocks = async () => {
    setLoading(true)
    try {
      const params: any = {
        skip: (currentPage - 1) * pageSize,
        limit: pageSize,
        sort_by: sortBy,
        sort_order: sortOrder,
      }

      if (search) params.search = search
      if (marketFilter !== 'all') params.market = marketFilter
      if (industryFilter !== 'all') params.industry = industryFilter
      if (conceptFilter !== 'all') params.concepts = conceptFilter
      if (statusFilter !== 'all') params.status = statusFilter

      const response = await apiClient.getStockList(params)
      setStocks(response.items || [])
      setTotalStocks(response.total || 0)
    } catch (error: any) {
      toast.error('加载股票列表失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  // 同步股票列表
  const handleSyncStocks = async () => {
    setSyncing(true)
    try {
      const response = await apiClient.syncStockList()
      toast.success(`股票列表同步成功！共 ${response.data?.total || 0} 只股票`)
      await loadStocks()
    } catch (error: any) {
      toast.error('同步股票列表失败: ' + (error.message || '未知错误'))
    } finally {
      setSyncing(false)
    }
  }

  // 同步实时行情
  const handleSyncRealtime = async () => {
    if (stocks.length === 0) {
      toast.warning('没有股票数据可同步')
      return
    }

    setSyncing(true)
    try {
      const codes = stocks.map(s => s.code)
      await apiClient.syncRealtimeQuotes({
        codes,
        batch_size: codes.length,
      })
      toast.success('实时行情同步成功！')
      await loadStocks()
    } catch (error: any) {
      toast.error('同步实时行情失败: ' + (error.message || '未知错误'))
    } finally {
      setSyncing(false)
    }
  }

  // 当筛选条件或分页变化时重新加载
  useEffect(() => {
    loadStocks()
  }, [currentPage, pageSize, search, marketFilter, industryFilter, conceptFilter, statusFilter, sortBy, sortOrder])

  // 重置筛选
  const handleResetFilters = () => {
    setSearch('')
    setMarketFilter('all')
    setIndustryFilter('all')
    setConceptFilter('all')
    setStatusFilter('all')
    setCurrentPage(1)
  }

  // 切换排序
  const handleToggleSort = () => {
    setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
  }

  // 获取价格颜色（A股规则：红涨绿跌）
  const getPriceColor = (pctChange?: number) => {
    if (!pctChange) return 'text-gray-500'
    if (pctChange > 0) return 'text-red-600'
    if (pctChange < 0) return 'text-green-600'
    return 'text-gray-500'
  }

  // 格式化涨跌幅
  const formatPctChange = (pctChange?: number) => {
    if (pctChange === undefined || pctChange === null) return '-'
    const sign = pctChange > 0 ? '+' : ''
    return `${sign}${pctChange.toFixed(2)}%`
  }

  // 格式化价格
  const formatPrice = (price?: number) => {
    if (!price) return '-'
    return price.toFixed(2)
  }

  // 格式化成交量（万手）
  const formatVolume = (volume?: number) => {
    if (!volume) return '-'
    return (volume / 10000).toFixed(2) + ' 万手'
  }

  // 格式化成交额（亿元）
  const formatAmount = (amount?: number) => {
    if (!amount) return '-'
    return (amount / 100000000).toFixed(2) + ' 亿'
  }

  // 渲染分页按钮
  const renderPaginationButtons = () => {
    const buttons: JSX.Element[] = []
    const maxButtons = 7

    if (totalPages <= maxButtons) {
      for (let i = 1; i <= totalPages; i++) {
        buttons.push(
          <Button
            key={i}
            variant={currentPage === i ? 'default' : 'outline'}
            size="sm"
            onClick={() => setCurrentPage(i)}
          >
            {i}
          </Button>
        )
      }
    } else {
      buttons.push(
        <Button
          key={1}
          variant={currentPage === 1 ? 'default' : 'outline'}
          size="sm"
          onClick={() => setCurrentPage(1)}
        >
          1
        </Button>
      )

      if (currentPage > 3) {
        buttons.push(<span key="ellipsis1" className="px-2">...</span>)
      }

      const start = Math.max(2, currentPage - 1)
      const end = Math.min(totalPages - 1, currentPage + 1)

      for (let i = start; i <= end; i++) {
        buttons.push(
          <Button
            key={i}
            variant={currentPage === i ? 'default' : 'outline'}
            size="sm"
            onClick={() => setCurrentPage(i)}
          >
            {i}
          </Button>
        )
      }

      if (currentPage < totalPages - 2) {
        buttons.push(<span key="ellipsis2" className="px-2">...</span>)
      }

      buttons.push(
        <Button
          key={totalPages}
          variant={currentPage === totalPages ? 'default' : 'outline'}
          size="sm"
          onClick={() => setCurrentPage(totalPages)}
        >
          {totalPages}
        </Button>
      )
    }

    return buttons
  }

  return (
    <div className="space-y-6">
      {/* 页头 */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">股票管理</h1>
        <p className="text-muted-foreground mt-2">
          查看和管理所有股票数据，包括基本信息和实时行情
        </p>
      </div>

      {/* 筛选和操作区 */}
      <Card>
        <CardHeader>
          <CardTitle>筛选和搜索</CardTitle>
          <CardDescription>使用下方工具筛选和搜索股票</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 搜索框 */}
          <div className="flex gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="搜索股票代码或名称..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>
            <Button
              variant="outline"
              onClick={handleResetFilters}
            >
              重置筛选
            </Button>
          </div>

          {/* 筛选器 */}
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
            <div>
              <label className="text-sm font-medium mb-2 block">市场</label>
              <Select value={marketFilter} onValueChange={setMarketFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="选择市场" />
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

            <div>
              <label className="text-sm font-medium mb-2 block">行业</label>
              <Select value={industryFilter} onValueChange={setIndustryFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="选择行业" />
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

            <div>
              <label className="text-sm font-medium mb-2 block">概念板块</label>
              <LazyConceptSelect
                value={conceptFilter}
                onSelect={setConceptFilter}
                includeAllOption={true}
                valueType="code"
                placeholder="选择概念..."
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">状态</label>
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger>
                  <SelectValue placeholder="选择状态" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部状态</SelectItem>
                  <SelectItem value="L">正常上市</SelectItem>
                  <SelectItem value="D">退市</SelectItem>
                  <SelectItem value="P">暂停上市</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="flex gap-2">
            <Button
              onClick={handleSyncStocks}
              disabled={syncing}
              variant="outline"
            >
              <Database className="h-4 w-4 mr-2" />
              同步股票列表
            </Button>
            <Button
              onClick={handleSyncRealtime}
              disabled={syncing || stocks.length === 0}
              variant="outline"
            >
              <RefreshCw className="h-4 w-4 mr-2" />
              同步当前页行情
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 股票列表 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>股票列表</CardTitle>
              <CardDescription>
                共 {totalStocks.toLocaleString()} 只股票，当前第 {currentPage}/{totalPages} 页
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">每页显示：</span>
              <Select
                value={pageSize.toString()}
                onValueChange={(value) => {
                  setPageSize(Number(value))
                  setCurrentPage(1)
                }}
              >
                <SelectTrigger className="w-20">
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
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
              <span className="ml-2 text-muted-foreground">加载中...</span>
            </div>
          ) : stocks.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              没有找到符合条件的股票
            </div>
          ) : (
            <>
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[120px]">股票代码</TableHead>
                      <TableHead className="w-[150px]">股票名称</TableHead>
                      <TableHead className="w-[100px]">市场</TableHead>
                      <TableHead className="w-[100px] text-right">最新价</TableHead>
                      <TableHead
                        className="w-[100px] text-right cursor-pointer hover:bg-muted/50"
                        onClick={handleToggleSort}
                      >
                        <div className="flex items-center justify-end gap-1">
                          涨跌幅
                          {sortOrder === 'desc' ? (
                            <TrendingDown className="h-4 w-4" />
                          ) : (
                            <TrendingUp className="h-4 w-4" />
                          )}
                        </div>
                      </TableHead>
                      <TableHead className="w-[120px] text-right">成交量</TableHead>
                      <TableHead className="w-[120px] text-right">成交额</TableHead>
                      <TableHead>所属概念</TableHead>
                      <TableHead className="w-[80px]">状态</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {stocks.map((stock) => (
                      <TableRow key={stock.code}>
                        <TableCell className="font-mono">
                          <button
                            onClick={() => {
                              setSelectedStock(stock)
                              setDetailDialogOpen(true)
                            }}
                            className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer"
                          >
                            {stock.code}
                          </button>
                        </TableCell>
                        <TableCell className="font-medium">
                          <button
                            onClick={() => {
                              setSelectedStock(stock)
                              setDetailDialogOpen(true)
                            }}
                            className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer"
                          >
                            {stock.name}
                          </button>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{stock.market}</Badge>
                        </TableCell>
                        <TableCell className={`text-right font-medium ${getPriceColor(stock.pct_change)}`}>
                          {formatPrice(stock.latest_price)}
                        </TableCell>
                        <TableCell className={`text-right font-medium ${getPriceColor(stock.pct_change)}`}>
                          {formatPctChange(stock.pct_change)}
                        </TableCell>
                        <TableCell className="text-right text-sm text-muted-foreground">
                          {formatVolume(stock.volume)}
                        </TableCell>
                        <TableCell className="text-right text-sm text-muted-foreground">
                          {formatAmount(stock.amount)}
                        </TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {stock.concepts?.slice(0, 3).map((concept) => (
                              <Badge key={concept.code} variant="secondary" className="text-xs">
                                {concept.name}
                              </Badge>
                            ))}
                            {stock.concepts && stock.concepts.length > 3 && (
                              <Badge variant="secondary" className="text-xs">
                                +{stock.concepts.length - 3}
                              </Badge>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          {stock.status === 'L' && <Badge variant="default">正常</Badge>}
                          {stock.status === 'D' && <Badge variant="destructive">退市</Badge>}
                          {stock.status === 'P' && <Badge variant="secondary">暂停</Badge>}
                          {!stock.status && <Badge variant="outline">未知</Badge>}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>

              {/* 分页 */}
              <div className="flex items-center justify-between mt-4">
                <div className="text-sm text-muted-foreground">
                  显示第 {(currentPage - 1) * pageSize + 1} 到 {Math.min(currentPage * pageSize, totalStocks)} 条，共 {totalStocks} 条
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(Math.max(1, currentPage - 1))}
                    disabled={currentPage === 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    上一页
                  </Button>
                  {renderPaginationButtons()}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setCurrentPage(Math.min(totalPages, currentPage + 1))}
                    disabled={currentPage === totalPages}
                  >
                    下一页
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* 股票详情弹窗 */}
      <StockDetailDialog
        stock={selectedStock}
        open={detailDialogOpen}
        onOpenChange={setDetailDialogOpen}
        onUpdate={loadStocks}
      />
    </div>
  )
}
