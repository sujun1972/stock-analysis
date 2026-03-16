/**
 * 股票管理页面
 *
 * 功能：
 * - 股票列表展示（分页、搜索、筛选、排序）
 * - 同步股票列表和实时行情
 * - 查看股票详细信息
 * - 多维度筛选（市场、行业、概念、状态）
 *
 * 响应式设计：
 * - 使用 DataTable 组件自动处理桌面/移动端切换
 * - 桌面端（≥768px）：表格视图
 * - 移动端（<768px）：卡片视图
 *
 * 视觉优化：
 * - 市场标签差异化配色（上海主板/深圳主板/创业板/科创板）
 * - 操作按钮彩色化（蓝色同步/绿色刷新/灰色重置）
 * - 价格涨跌颜色标识（红涨绿跌）
 */
'use client'

import { useState, useEffect, useCallback, useMemo } from 'react'
import { toast } from 'sonner'
import { Search, RefreshCw, Database, TrendingUp, TrendingDown, Info } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import type { StockInfo } from '@/types/stock'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { DataTable, type Column } from '@/components/common/DataTable'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { StockDetailDialog } from '@/components/stocks/StockDetailDialog'
import { LazyConceptSelect } from '@/components/stocks/LazyConceptSelect'
import { useSystemConfig } from '@/contexts'

export default function StocksManagementPage() {
  // 获取系统配置
  const { config } = useSystemConfig()

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

  // 获取股票分析URL（支持URL模板）
  const getStockAnalysisUrl = (code: string) => {
    const template = config?.stock_analysis_url || 'http://localhost:3000/analysis?code={code}'
    return template.replace('{code}', code)
  }

  // 加载股票列表
  const loadStocks = useCallback(async () => {
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
  }, [currentPage, pageSize, search, marketFilter, industryFilter, conceptFilter, statusFilter, sortBy, sortOrder])

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
  }, [loadStocks])

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
  const handleSort = (key: string) => {
    if (key === sortBy) {
      setSortOrder(prev => prev === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(key)
      setSortOrder('desc')
    }
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

  // 获取市场标签样式
  const getMarketBadgeClass = (market: string) => {
    const marketStyles: Record<string, string> = {
      '上海主板': 'bg-blue-100 text-blue-800 border-blue-200',
      '深圳主板': 'bg-cyan-100 text-cyan-800 border-cyan-200',
      '创业板': 'bg-purple-100 text-purple-800 border-purple-200',
      '科创板': 'bg-orange-100 text-orange-800 border-orange-200',
    }
    return marketStyles[market] || 'bg-gray-100 text-gray-800 border-gray-200'
  }

  // 定义表格列
  const columns: Column<StockInfo>[] = useMemo(() => [
    {
      key: 'name',
      header: '股票名称',
      accessor: (stock) => (
        <div className="flex items-center gap-2">
          <a
            href={getStockAnalysisUrl(stock.code)}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:text-blue-800 hover:underline cursor-pointer"
          >
            {stock.name}[{stock.code}]
          </a>
          <button
            onClick={(e) => {
              e.stopPropagation()
              setSelectedStock(stock)
              setDetailDialogOpen(true)
            }}
            className="text-gray-400 hover:text-blue-600 transition-colors"
            title="查看详情"
          >
            <Info className="h-4 w-4" />
          </button>
        </div>
      ),
      width: 200,
    },
    {
      key: 'market',
      header: '市场',
      accessor: (stock) => (
        <Badge variant="outline" className={getMarketBadgeClass(stock.market)}>
          {stock.market}
        </Badge>
      ),
      width: 100,
    },
    {
      key: 'latest_price',
      header: '最新价',
      accessor: (stock) => (
        <span className={`font-medium ${getPriceColor(stock.pct_change)}`}>
          {formatPrice(stock.latest_price)}
        </span>
      ),
      align: 'right',
      width: 100,
    },
    {
      key: 'pct_change',
      header: (
        <div className="flex items-center justify-end gap-1">
          涨跌幅
          {sortOrder === 'desc' ? (
            <TrendingDown className="h-4 w-4" />
          ) : (
            <TrendingUp className="h-4 w-4" />
          )}
        </div>
      ),
      accessor: (stock) => (
        <span className={`font-medium ${getPriceColor(stock.pct_change)}`}>
          {formatPctChange(stock.pct_change)}
        </span>
      ),
      align: 'right',
      sortable: true,
      width: 100,
    },
    {
      key: 'volume',
      header: '成交量',
      accessor: (stock) => (
        <span className="text-sm text-muted-foreground">{formatVolume(stock.volume)}</span>
      ),
      align: 'right',
      width: 120,
      hideOnMobile: true,
    },
    {
      key: 'amount',
      header: '成交额',
      accessor: (stock) => (
        <span className="text-sm text-muted-foreground">{formatAmount(stock.amount)}</span>
      ),
      align: 'right',
      width: 120,
      hideOnMobile: true,
    },
    {
      key: 'concepts',
      header: '所属概念',
      accessor: (stock) => (
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
      ),
      hideOnMobile: true,
    },
    {
      key: 'status',
      header: '状态',
      accessor: (stock) => (
        <>
          {stock.status === 'L' && <Badge variant="default">正常</Badge>}
          {stock.status === 'D' && <Badge variant="destructive">退市</Badge>}
          {stock.status === 'P' && <Badge variant="secondary">暂停</Badge>}
          {!stock.status && <Badge variant="outline">未知</Badge>}
        </>
      ),
      width: 80,
    },
  ], [sortOrder, config])

  // 移动端卡片渲染
  const mobileCard = useCallback((stock: StockInfo) => (
    <div className="border rounded-lg p-4 bg-white space-y-3">
      {/* 顶部：股票代码和名称 */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <a
              href={getStockAnalysisUrl(stock.code)}
              target="_blank"
              rel="noopener noreferrer"
              className="font-semibold text-base text-blue-600 hover:text-blue-800 hover:underline"
            >
              {stock.name}[{stock.code}]
            </a>
            <button
              onClick={(e) => {
                e.stopPropagation()
                setSelectedStock(stock)
                setDetailDialogOpen(true)
              }}
              className="text-gray-400 hover:text-blue-600 transition-colors shrink-0"
              title="查看详情"
            >
              <Info className="h-4 w-4" />
            </button>
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className={`text-lg font-bold ${getPriceColor(stock.pct_change)}`}>
            {formatPrice(stock.latest_price)}
          </div>
          <div className={`text-sm font-medium ${getPriceColor(stock.pct_change)}`}>
            {formatPctChange(stock.pct_change)}
          </div>
        </div>
      </div>

      {/* 市场和状态标签 */}
      <div className="flex flex-wrap gap-2">
        <Badge variant="outline" className={getMarketBadgeClass(stock.market)}>
          {stock.market}
        </Badge>
        {stock.status === 'L' && <Badge variant="default">正常</Badge>}
        {stock.status === 'D' && <Badge variant="destructive">退市</Badge>}
        {stock.status === 'P' && <Badge variant="secondary">暂停</Badge>}
        {!stock.status && <Badge variant="outline">未知</Badge>}
      </div>

      {/* 成交信息 */}
      <div className="grid grid-cols-2 gap-2 text-sm bg-gray-50 rounded p-2">
        <div>
          <span className="text-gray-500">成交量: </span>
          <span className="font-medium">{formatVolume(stock.volume)}</span>
        </div>
        <div>
          <span className="text-gray-500">成交额: </span>
          <span className="font-medium">{formatAmount(stock.amount)}</span>
        </div>
      </div>

      {/* 概念标签 */}
      {stock.concepts && stock.concepts.length > 0 && (
        <div className="space-y-1">
          <div className="text-xs text-gray-500">所属概念</div>
          <div className="flex flex-wrap gap-1">
            {stock.concepts.slice(0, 4).map((concept) => (
              <Badge key={concept.code} variant="secondary" className="text-xs">
                {concept.name}
              </Badge>
            ))}
            {stock.concepts.length > 4 && (
              <Badge variant="secondary" className="text-xs">
                +{stock.concepts.length - 4}
              </Badge>
            )}
          </div>
        </div>
      )}
    </div>
  ), [config])

  return (
    <div className="space-y-6">
      {/* 页头 */}
      <div className="flex flex-col gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">股票管理</h1>
          <p className="text-sm sm:text-base text-muted-foreground mt-2">
            查看和管理所有股票数据，包括基本信息和实时行情
          </p>
        </div>
      </div>

      {/* 筛选和操作区 */}
      <Card>
        <CardHeader>
          <CardTitle>筛选和搜索</CardTitle>
          <CardDescription>使用下方工具筛选和搜索股票</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 搜索框 */}
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="搜索股票代码或名称..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && loadStocks()}
                  className="pl-9"
                />
              </div>
            </div>
            <Button
              onClick={handleResetFilters}
              className="w-full sm:w-auto bg-gray-600 hover:bg-gray-700 text-white"
            >
              重置筛选
            </Button>
          </div>

          {/* 筛选器 */}
          <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
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
          <div className="flex flex-col sm:flex-row gap-2">
            <Button
              onClick={handleSyncStocks}
              disabled={syncing}
              className="w-full sm:w-auto bg-blue-600 hover:bg-blue-700 text-white"
            >
              <Database className="h-4 w-4 mr-2" />
              同步股票列表
            </Button>
            <Button
              onClick={handleSyncRealtime}
              disabled={syncing || stocks.length === 0}
              className="w-full sm:w-auto bg-green-600 hover:bg-green-700 text-white"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${syncing ? 'animate-spin' : ''}`} />
              同步当前页行情
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 股票列表 */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <CardTitle>股票列表</CardTitle>
              <CardDescription>
                共 {totalStocks.toLocaleString()} 只股票
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
          <DataTable
            data={stocks}
            columns={columns}
            loading={loading}
            emptyMessage="没有找到符合条件的股票"
            loadingMessage="加载中..."
            pagination={{
              page: currentPage,
              pageSize,
              total: totalStocks,
              onPageChange: setCurrentPage,
              onPageSizeChange: (size) => {
                setPageSize(size)
                setCurrentPage(1)
              },
              pageSizeOptions: [10, 20, 30, 50],
            }}
            sort={{
              key: sortBy,
              direction: sortOrder,
              onSort: (key, direction) => {
                if (key === 'pct_change') {
                  handleSort(key)
                }
              },
            }}
            mobileCard={mobileCard}
            rowKey={(stock) => stock.code}
          />
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