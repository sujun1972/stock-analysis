'use client'

import { useState, useMemo } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useDataPage } from '@/hooks/useDataPage'
import { topListApi, type TopListItem, type TopListStatistics } from '@/lib/api'
import { apiClient } from '@/lib/api-client'
import { toDateStr } from '@/lib/date-utils'
import { formatStockCode, pctChangeColor } from '@/lib/utils'
import { useSystemConfig } from '@/contexts'
import { TrendingUp, TrendingDown, BarChart3, ListFilter, RefreshCw } from 'lucide-react'

// ============== 页面组件 ==============

export default function TopListPage() {
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const { config } = useSystemConfig()

  const openStockAnalysis = (tsCode: string) => {
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(tsCode)), '_blank')
  }

  const dp = useDataPage<TopListItem, TopListStatistics>({
    apiCall: (params) => topListApi.getTopList(params),
    statisticsCall: (params) => topListApi.getStatistics(params),
    syncFn: (params) => topListApi.syncAsync(params),
    taskName: 'tasks.sync_top_list',
    bulkOps: {
      tableKey: 'top_list',
      syncFn: (params) => apiClient.post('/api/top-list/sync-async', null, { params }),
      taskName: 'tasks.sync_top_list',
    },
    paginationMode: 'page',
    pageSize: 100,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      return params
    },
    onBackfillDate: (dateStr) => setTradeDate(new Date(dateStr + 'T00:00:00')),
    syncSuccessMessage: '龙虎榜数据同步完成',
  })

  const toYi = (val: number | null | undefined) => {
    if (val === null || val === undefined) return '-'
    return (val / 10000).toFixed(2) + '亿'
  }

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '上榜股票数',
        value: s.stock_count,
        icon: BarChart3,
        iconColor: 'text-blue-600',
      },
      {
        label: '平均净买入(亿)',
        value: <span className={s.avg_net_amount >= 0 ? 'text-red-600' : 'text-green-600'}>{s.avg_net_amount >= 0 ? '+' : ''}{(s.avg_net_amount / 10000).toFixed(2)}</span>,
        icon: TrendingUp,
        iconColor: 'text-orange-600',
      },
      {
        label: '最大净买入(亿)',
        value: <span className="text-red-600">+{(s.max_net_amount / 10000).toFixed(2)}</span>,
        icon: TrendingUp,
        iconColor: 'text-green-600',
      },
      {
        label: '平均涨跌幅%',
        value: <span className={s.avg_pct_change >= 0 ? 'text-red-600' : 'text-green-600'}>{s.avg_pct_change >= 0 ? '+' : ''}{s.avg_pct_change.toFixed(2)}%</span>,
        icon: TrendingDown,
        iconColor: 'text-purple-600',
      },
    ]
  }, [dp.statistics])

  const columns: Column<TopListItem>[] = [
    {
      key: 'name',
      header: '股票',
      accessor: (row) => (
        <span
          className={`cursor-pointer hover:underline ${pctChangeColor(row.pct_change)}`}
          onClick={() => openStockAnalysis(row.ts_code)}
        >
          {row.name || '-'}[{formatStockCode(row.ts_code)}]
        </span>
      ),
      width: 160,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'close',
      header: '收盘价',
      accessor: (row) => (
        <span className={pctChangeColor(row.pct_change)}>
          {row.close !== null ? row.close.toFixed(2) : '-'}
        </span>
      ),
      width: 80,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'pct_change',
      header: '涨跌幅%',
      accessor: (row) => {
        if (row.pct_change === null) return '-'
        return (
          <span className={pctChangeColor(row.pct_change)}>
            {row.pct_change >= 0 ? '+' : ''}{row.pct_change.toFixed(2)}%
          </span>
        )
      },
      width: 100,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'turnover_rate',
      header: '换手率%',
      accessor: (row) => (
        <span className={pctChangeColor(row.pct_change)}>
          {row.turnover_rate !== null ? row.turnover_rate.toFixed(2) + '%' : '-'}
        </span>
      ),
      width: 100,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'amount',
      header: '总成交额',
      accessor: (row) => (
        <span className={pctChangeColor(row.pct_change)}>
          {toYi(row.amount)}
        </span>
      ),
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'net_amount',
      header: '净买入',
      accessor: (row) => {
        if (row.net_amount === null) return '-'
        const value = row.net_amount / 10000
        return (
          <span className={value >= 0 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'}>
            {value >= 0 ? '+' : ''}{value.toFixed(2)}亿
          </span>
        )
      },
      width: 100,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'l_amount',
      header: '榜单成交额',
      accessor: (row) => (
        <span className={pctChangeColor(row.pct_change)}>
          {toYi(row.l_amount)}
        </span>
      ),
      width: 120,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'reason',
      header: '上榜理由',
      accessor: (row) => (
        <div className="truncate" title={row.reason || '-'}>
          {row.reason || '-'}
        </div>
      ),
      width: 200
    }
  ]

  const mobileCard = (item: TopListItem) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div className="font-semibold text-base">{item.name}</div>
          <div className="text-sm text-gray-500">{item.ts_code}</div>
        </div>
        <div className="text-right">
          <div className="font-semibold">{item.close !== null ? `¥${item.close.toFixed(2)}` : '-'}</div>
          {item.pct_change !== null && (
            <div className={item.pct_change >= 0 ? 'text-red-600' : 'text-green-600'}>
              {item.pct_change >= 0 ? '+' : ''}{item.pct_change.toFixed(2)}%
            </div>
          )}
        </div>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">龙虎榜净买入:</span>
          {item.net_amount !== null && (
            <span className={item.net_amount >= 0 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'}>
              {item.net_amount >= 0 ? '+' : ''}{(item.net_amount / 10000).toFixed(2)}亿
            </span>
          )}
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">龙虎榜成交额:</span>
          <span>{item.l_amount !== null ? `${(item.l_amount / 10000).toFixed(2)}亿` : '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">换手率:</span>
          <span>{item.turnover_rate !== null ? `${item.turnover_rate.toFixed(2)}%` : '-'}</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-gray-600">上榜理由:</span>
          <span className="text-xs break-all">{item.reason || '-'}</span>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="龙虎榜每日明细"
        description="龙虎榜每日交易明细"
        details={<>
          <div>接口：top_list</div>
          <a href="https://tushare.pro/document/2?doc_id=106" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <div className="flex gap-2">
            <Button onClick={() => dp.handleSyncDirect({})} disabled={dp.syncing}>
              {dp.syncing ? (
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
              ) : (
                <><RefreshCw className="h-4 w-4 mr-1" />同步数据</>
              )}
            </Button>
            <BulkOpsButtons
              onFullSync={dp.handleFullSync}
              onClearConfirm={dp.handleClear}
              isClearDialogOpen={dp.isClearDialogOpen}
              setIsClearDialogOpen={dp.setIsClearDialogOpen}
              fullSyncing={dp.fullSyncing}
              isClearing={dp.isClearing}
              earliestHistoryDate={dp.earliestHistoryDate}
              tableName="龙虎榜每日明细"
            />
          </div>
        }
      />

      <StatisticsCards items={statsCards} />

      {/* 筛选和操作区域 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ListFilter className="h-5 w-5" />
            数据查询
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">交易日期</label>
              <DatePicker date={tradeDate} onDateChange={setTradeDate} />
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <Button onClick={dp.handleQuery} disabled={dp.isLoading} className="flex-1 sm:flex-none">
                查询
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="p-0 sm:p-6">
          <DataTable
            columns={columns}
            data={dp.data}
            loading={dp.isLoading}
            mobileCard={mobileCard}
            tableClassName="table-fixed w-full [&_th]:border-r [&_td]:border-r [&_th:last-child]:border-r-0 [&_td:last-child]:border-r-0 [&_th]:!text-center"
            sort={{
              key: dp.sortKey,
              direction: dp.sortDirection,
              onSort: dp.handleSort,
            }}
            pagination={{
              page: dp.page,
              pageSize: dp.pageSize,
              total: dp.total,
              onPageChange: dp.handlePageChange,
            }}
          />
        </CardContent>
      </Card>
    </div>
  )
}
