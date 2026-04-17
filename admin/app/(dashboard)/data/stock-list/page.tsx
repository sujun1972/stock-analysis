'use client'

import { useState, useMemo } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { DataTable, Column } from '@/components/common/DataTable'
import { useDataPage } from '@/hooks/useDataPage'
import { stockListApi } from '@/lib/api'
import type { StockListData, StockListStatistics } from '@/lib/api/stock-list-api'
import { RefreshCw, Database, TrendingUp, TrendingDown, PauseCircle, BarChart3 } from 'lucide-react'

export default function StockListPage() {
  const [listStatus, setListStatus] = useState<string>('all')
  const [market, setMarket] = useState<string>('all')
  const [exchange, setExchange] = useState<string>('all')
  const [isHs, setIsHs] = useState<string>('all')

  const dp = useDataPage<StockListData, StockListStatistics>({
    apiCall: (params) => stockListApi.getData(params),
    statisticsCall: () => stockListApi.getStatistics(),
    syncFn: () => stockListApi.syncAsync(),
    taskName: 'tasks.sync_stock_list',
    paginationMode: 'offset',
    pageSize: 30,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (listStatus !== 'all') params.list_status = listStatus
      if (market !== 'all') params.market = market
      if (exchange !== 'all') params.exchange = exchange
      if (isHs !== 'all') params.is_hs = isHs
      return params
    },
    syncSuccessMessage: '股票列表数据已更新',
  })

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      { label: '总股票数', value: s.total_count, subValue: '全部股票', icon: Database, iconColor: 'text-blue-600' },
      { label: '上市股票', value: <span className="text-green-600">{s.listed_count}</span>, subValue: '正常交易', icon: TrendingUp, iconColor: 'text-green-600' },
      { label: '退市股票', value: <span className="text-red-600">{s.delisted_count}</span>, subValue: '已退市', icon: TrendingDown, iconColor: 'text-red-600' },
      { label: '停牌股票', value: <span className="text-yellow-600">{s.suspended_count}</span>, subValue: '暂停上市', icon: PauseCircle, iconColor: 'text-yellow-600' },
      { label: '沪深港通', value: <span className="text-blue-600">{s.hs_count}</span>, subValue: '可通过港股通交易', icon: BarChart3, iconColor: 'text-blue-600' },
    ]
  }, [dp.statistics])

  const columns: Column<StockListData>[] = [
    {
      key: 'code',
      header: '股票代码',
      accessor: (row) => row.code,
      cellClassName: 'font-mono'
    },
    {
      key: 'name',
      header: '股票名称',
      accessor: (row) => row.name
    },
    {
      key: 'ts_code',
      header: 'TS代码',
      accessor: (row) => row.ts_code || '-',
      cellClassName: 'font-mono hidden lg:table-cell'
    },
    {
      key: 'market',
      header: '市场',
      accessor: (row) => row.market,
      cellClassName: 'hidden md:table-cell'
    },
    {
      key: 'exchange',
      header: '交易所',
      accessor: (row) => row.exchange,
      cellClassName: 'hidden lg:table-cell'
    },
    {
      key: 'list_status',
      header: '上市状态',
      accessor: (row) => {
        const statusMap: { [key: string]: { text: string; color: string } } = {
          'L': { text: '上市', color: 'text-green-600' },
          'D': { text: '退市', color: 'text-red-600' },
          'P': { text: '暂停', color: 'text-yellow-600' },
          'G': { text: '过会', color: 'text-blue-600' }
        }
        const status = statusMap[row.list_status] || { text: row.list_status, color: '' }
        return <span className={status.color}>{status.text}</span>
      }
    },
    {
      key: 'is_hs',
      header: '沪深港通',
      accessor: (row) => (row.is_hs === 'S' || row.is_hs === 'H') ? '是' : '否',
      cellClassName: 'hidden md:table-cell'
    },
    {
      key: 'industry',
      header: '行业',
      accessor: (row) => row.industry || '-',
      cellClassName: 'hidden xl:table-cell'
    },
    {
      key: 'area',
      header: '地区',
      accessor: (row) => row.area || '-',
      cellClassName: 'hidden 2xl:table-cell'
    },
    {
      key: 'list_date',
      header: '上市日期',
      accessor: (row) => row.list_date || '-',
      cellClassName: 'hidden lg:table-cell'
    }
  ]

  const mobileCard = (item: StockListData) => (
    <div className="p-4 space-y-2">
      <div className="flex justify-between items-start">
        <div>
          <div className="font-mono font-semibold">{item.code}</div>
          <div className="text-sm text-muted-foreground">{item.name}</div>
          {item.ts_code && (
            <div className="text-xs text-muted-foreground font-mono">{item.ts_code}</div>
          )}
        </div>
        <div className="text-right">
          <div className={`text-sm font-medium ${
            item.list_status === 'L' ? 'text-green-600' :
            item.list_status === 'D' ? 'text-red-600' :
            item.list_status === 'P' ? 'text-yellow-600' :
            'text-blue-600'
          }`}>
            {item.list_status === 'L' ? '上市' :
             item.list_status === 'D' ? '退市' :
             item.list_status === 'P' ? '暂停' :
             '过会'}
          </div>
          {item.list_date && (
            <div className="text-xs text-muted-foreground">{item.list_date}</div>
          )}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 pt-2 border-t">
        <div>
          <div className="text-xs text-muted-foreground">市场</div>
          <div className="text-sm font-medium">{item.market}</div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground">交易所</div>
          <div className="text-sm font-medium">{item.exchange}</div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground">行业</div>
          <div className="text-sm font-medium">{item.industry || '-'}</div>
        </div>
        <div>
          <div className="text-xs text-muted-foreground">沪深港通</div>
          <div className="text-sm font-medium">
            {(item.is_hs === 'S' || item.is_hs === 'H') ? '是' : '否'}
          </div>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="股票列表"
        description="获取基础信息数据，包括股票代码、名称、上市日期、退市日期等"
        details={<>
          <div>接口：stock_basic</div>
          <a href="https://tushare.pro/document/2?doc_id=25" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <Button onClick={() => dp.setSyncDialogOpen(true)} disabled={dp.syncing}>
            {dp.syncing ? (
              <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
            ) : (
              <><RefreshCw className="h-4 w-4 mr-1" />同步数据</>
            )}
          </Button>
        }
      />

      <SyncDialog
        open={dp.syncDialogOpen}
        onOpenChange={dp.setSyncDialogOpen}
        onConfirm={dp.handleSyncConfirm}
        title="同步股票列表"
        description="将从 Tushare 同步全部股票数据（含上市、退市、停牌等状态），无需选择日期。"
        disabled={dp.syncing}
      />

      <StatisticsCards
        items={statsCards}
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4"
      />

      {/* 筛选和操作区域 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">上市状态</label>
              <Select value={listStatus} onValueChange={setListStatus}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部状态</SelectItem>
                  <SelectItem value="L">上市</SelectItem>
                  <SelectItem value="D">退市</SelectItem>
                  <SelectItem value="P">暂停上市</SelectItem>
                  <SelectItem value="G">过会未交易</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">市场类型</label>
              <Select value={market} onValueChange={setMarket}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部市场</SelectItem>
                  <SelectItem value="主板">主板</SelectItem>
                  <SelectItem value="科创板">科创板</SelectItem>
                  <SelectItem value="创业板">创业板</SelectItem>
                  <SelectItem value="北交所">北交所</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">交易所</label>
              <Select value={exchange} onValueChange={setExchange}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部交易所</SelectItem>
                  <SelectItem value="SSE">上海证券交易所</SelectItem>
                  <SelectItem value="SZSE">深圳证券交易所</SelectItem>
                  <SelectItem value="BSE">北京证券交易所</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">沪深港通</label>
              <Select value={isHs} onValueChange={setIsHs}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部</SelectItem>
                  <SelectItem value="S">沪股通</SelectItem>
                  <SelectItem value="H">深股通</SelectItem>
                  <SelectItem value="N">非港股通</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button onClick={dp.handleQuery} disabled={dp.isLoading}>
              {dp.isLoading ? '查询中...' : '查询'}
            </Button>
            <Button
              onClick={() => {
                setListStatus('all')
                setMarket('all')
                setExchange('all')
                setIsHs('all')
              }}
              variant="ghost"
            >
              重置
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="pt-6">
          <DataTable
            columns={columns}
            data={dp.data}
            loading={dp.isLoading}
            mobileCard={mobileCard}
            pagination={{
              page: dp.page,
              pageSize: dp.pageSize,
              total: dp.total,
              onPageChange: dp.handlePageChange,
              onPageSizeChange: dp.handlePageSizeChange,
              pageSizeOptions: [10, 20, 30, 50, 100]
            }}
          />
        </CardContent>
      </Card>
    </div>
  )
}
