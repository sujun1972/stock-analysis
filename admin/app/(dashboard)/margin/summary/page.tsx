'use client'

import { useState, useMemo } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { useDataPage } from '@/hooks/useDataPage'
import { marginApi } from '@/lib/api'
import { apiClient } from '@/lib/api-client'
import { toDateStr } from '@/lib/date-utils'
import { RefreshCw, TrendingUp, TrendingDown, DollarSign, BarChart3, ListFilter } from 'lucide-react'

// ============== 类型定义 ==============

interface MarginData {
  trade_date: string
  exchange_id: string
  rzye: number | null
  rzmre: number | null
  rzche: number | null
  rqye: number | null
  rqmcl: number | null
  rzrqye: number | null
  rqyl: number | null
}

interface Statistics {
  avg_rzrqye: number
  total_rzrqye: number
  max_rzye: number
  max_rqye: number
}

// ============== 工具函数 ==============

const formatDate = (dateStr: string) => {
  if (!dateStr || dateStr.length !== 8) return dateStr || '-'
  return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
}

const toYi = (value: number | null | undefined) => {
  if (value === null || value === undefined) return '-'
  return (value / 100000000).toFixed(2) + '亿'
}

const toWan = (value: number | null | undefined) => {
  if (value === null || value === undefined) return '-'
  return value.toFixed(2) + '万股'
}

// ============== 页面组件 ==============

export default function MarginSummaryPage() {
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [exchangeId, setExchangeId] = useState<string>('')

  const dp = useDataPage<MarginData, Statistics>({
    apiCall: (params) => marginApi.getMargin(params),
    syncFn: (params) => marginApi.syncMarginAsync(params),
    taskName: 'tasks.sync_margin',
    bulkOps: {
      tableKey: 'margin',
      syncFn: (params) => apiClient.post('/api/margin/sync-async', null, { params }),
      taskName: 'tasks.sync_margin',
    },
    paginationMode: 'page',
    pageSize: 100,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      if (exchangeId) params.exchange_id = exchangeId
      return params
    },
  })

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      { label: '平均融资融券余额', value: toYi(s.avg_rzrqye), subValue: '所选时间段平均值', icon: BarChart3, iconColor: 'text-blue-600' },
      { label: '累计融资融券余额', value: toYi(s.total_rzrqye), subValue: '所选时间段累计值', icon: DollarSign, iconColor: 'text-orange-600' },
      { label: '最大融资余额', value: <span className="text-red-600">{toYi(s.max_rzye)}</span>, subValue: '所选时间段最大值', icon: TrendingUp, iconColor: 'text-red-600' },
      { label: '最大融券余额', value: <span className="text-green-600">{toYi(s.max_rqye)}</span>, subValue: '所选时间段最大值', icon: TrendingDown, iconColor: 'text-green-600' },
    ]
  }, [dp.statistics])

  // 表格列定义
  const columns: Column<MarginData>[] = useMemo(() => [
    { key: 'trade_date', header: '交易日期', accessor: (row) => formatDate(row.trade_date), width: 110, cellClassName: 'whitespace-nowrap' },
    { key: 'exchange_id', header: '交易所', accessor: (row) => row.exchange_id, width: 90, cellClassName: 'whitespace-nowrap' },
    { key: 'rzrqye', header: '融资融券余额', accessor: (row) => toYi(row.rzrqye), width: 130, sortable: true, cellClassName: 'text-right whitespace-nowrap' },
    { key: 'rzye', header: '融资余额', accessor: (row) => toYi(row.rzye), width: 120, sortable: true, cellClassName: 'text-right whitespace-nowrap' },
    { key: 'rzmre', header: '融资买入', accessor: (row) => toYi(row.rzmre), hideOnMobile: true, width: 110, sortable: true, cellClassName: 'text-right whitespace-nowrap' },
    { key: 'rzche', header: '融资偿还', accessor: (row) => toYi(row.rzche), hideOnMobile: true, width: 110, sortable: true, cellClassName: 'text-right whitespace-nowrap' },
    { key: 'rqye', header: '融券余额', accessor: (row) => toYi(row.rqye), width: 110, sortable: true, cellClassName: 'text-right whitespace-nowrap' },
    { key: 'rqmcl', header: '融券卖出量', accessor: (row) => toWan(row.rqmcl), hideOnMobile: true, width: 120, sortable: true, cellClassName: 'text-right whitespace-nowrap' },
    { key: 'rqyl', header: '融券余量', accessor: (row) => toWan(row.rqyl), hideOnMobile: true, width: 110, sortable: true, cellClassName: 'text-right whitespace-nowrap' },
  ], [])

  const mobileCard = (item: MarginData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-center mb-2">
        <span className="font-semibold text-base">{formatDate(item.trade_date)}</span>
        <span className="text-sm font-medium text-blue-600 dark:text-blue-400">{item.exchange_id}</span>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">融资融券余额</span>
          <span className="font-medium">{toYi(item.rzrqye)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">融资余额</span>
          <span>{toYi(item.rzye)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">融券余额</span>
          <span>{toYi(item.rqye)}</span>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="融资融券交易汇总"
        description="获取融资融券每日交易汇总数据"
        details={<>
          <div>接口：margin</div>
          <a href="https://tushare.pro/document/2?doc_id=58" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <div className="flex gap-2">
            <Button onClick={() => dp.setSyncDialogOpen(true)} disabled={dp.syncing}>
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
              tableName="融资融券交易汇总"
            />
          </div>
        }
      />

      <SyncDialog
        open={dp.syncDialogOpen}
        onOpenChange={dp.setSyncDialogOpen}
        onConfirm={dp.handleSyncConfirm}
        title="同步融资融券汇总数据"
        description="选择同步日期范围（留空则同步最新交易日数据）。"
        disabled={dp.syncing}
        showDateRange
        startDate={dp.syncStartDate}
        onStartDateChange={dp.setSyncStartDate}
        endDate={dp.syncEndDate}
        onEndDateChange={dp.setSyncEndDate}
      />

      <StatisticsCards items={statsCards} />

      {/* 筛选区域 */}
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
              <label className="text-sm font-medium mb-1 block">开始日期</label>
              <DatePicker date={startDate} onDateChange={setStartDate} placeholder="选择开始日期" />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">结束日期</label>
              <DatePicker date={endDate} onDateChange={setEndDate} placeholder="选择结束日期" />
            </div>
            <div className="w-full sm:w-44">
              <label className="text-sm font-medium mb-1 block">交易所</label>
              <Select value={exchangeId || 'ALL'} onValueChange={(v) => setExchangeId(v === 'ALL' ? '' : v)}>
                <SelectTrigger><SelectValue placeholder="选择交易所" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="SSE">上交所 (SSE)</SelectItem>
                  <SelectItem value="SZSE">深交所 (SZSE)</SelectItem>
                  <SelectItem value="BSE">北交所 (BSE)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button onClick={dp.handleQuery} disabled={dp.isLoading} className="w-full sm:w-auto">
              查询
            </Button>
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
            emptyMessage="暂无融资融券汇总数据"
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
