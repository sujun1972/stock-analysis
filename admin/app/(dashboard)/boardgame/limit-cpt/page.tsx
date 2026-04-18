'use client'

import { useState, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DatePicker } from '@/components/ui/date-picker'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useDataPage } from '@/hooks/useDataPage'
import { limitCptApi, type LimitCptData, type LimitCptStatistics } from '@/lib/api'
import { axiosInstance } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { RefreshCw, TrendingUp, BarChart3, Layers, Calendar } from 'lucide-react'

export default function LimitCptPage() {
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)

  const dp = useDataPage<LimitCptData, LimitCptStatistics>({
    apiCall: (params) => limitCptApi.getData(params),
    syncFn: (params) => limitCptApi.syncAsync(params),
    taskName: 'tasks.sync_limit_cpt',
    bulkOps: {
      tableKey: 'limit_cpt',
      syncFn: (params) => axiosInstance.post('/api/limit-cpt/sync-async', null, { params }),
      taskName: 'tasks.sync_limit_cpt',
    },
    paginationMode: 'page',
    pageSize: 100,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      return params
    },
    onBackfillDate: (dateStr) => setTradeDate(new Date(dateStr + 'T00:00:00')),
    syncSuccessMessage: '最强板块统计数据已更新',
  })

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      { label: '交易天数', value: s.trading_days, icon: Calendar, iconColor: 'text-blue-600' },
      { label: '板块数量', value: s.concept_count, icon: Layers, iconColor: 'text-green-600' },
      {
        label: '平均涨停家数',
        value: <span className="text-red-600">{s.avg_up_nums?.toFixed(2) || 0}家</span>,
        icon: BarChart3,
        iconColor: 'text-red-600',
      },
      {
        label: '最大涨停家数',
        value: <span className="text-red-600">{s.max_up_nums || 0}家</span>,
        icon: TrendingUp,
        iconColor: 'text-orange-600',
      },
    ]
  }, [dp.statistics])

  // 表格列定义
  const columns: Column<LimitCptData>[] = useMemo(() => [
    {
      key: 'rank',
      header: '排名',
      accessor: (row) => (
        <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300 font-semibold text-sm">
          {row.rank}
        </span>
      ),
      width: 70,
      sortable: true,
      cellClassName: 'text-center whitespace-nowrap'
    },
    {
      key: 'name',
      header: '板块',
      accessor: (row) => (
        <span className="font-medium">
          {row.name || '-'}
          <span className="text-xs text-gray-500 ml-1">[{row.ts_code}]</span>
        </span>
      ),
      width: 220,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'days',
      header: '上榜天数',
      accessor: (row) => {
        const daysValue = row.days || 0
        return (
          <span className={daysValue >= 5 ? 'text-red-600 font-semibold' : ''}>
            {daysValue}天
          </span>
        )
      },
      width: 90,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'up_stat',
      header: '连板高度',
      accessor: (row) => (
        <span className="text-red-600 font-semibold">
          {row.up_stat || '-'}
        </span>
      ),
      width: 90,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'cons_nums',
      header: '连板家数',
      accessor: (row) => {
        const consValue = row.cons_nums || 0
        return (
          <span className={consValue >= 3 ? 'text-red-600 font-semibold' : ''}>
            {consValue}家
          </span>
        )
      },
      width: 90,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'up_nums',
      header: '涨停家数',
      accessor: (row) => {
        const upValue = row.up_nums || 0
        return (
          <span className={upValue >= 5 ? 'text-red-600 font-semibold' : ''}>
            {upValue}家
          </span>
        )
      },
      width: 90,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'pct_chg',
      header: '涨跌幅',
      accessor: (row) => {
        const pct = row.pct_chg || 0
        const isPositive = pct >= 0
        return (
          <span className={isPositive ? 'text-red-600' : 'text-green-600'}>
            {isPositive ? '+' : ''}{pct.toFixed(2)}%
          </span>
        )
      },
      width: 90,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    }
  ], [])

  // 移动端卡片
  const mobileCard = useCallback((item: LimitCptData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300 font-semibold text-xs">
            {item.rank}
          </span>
          <div>
            <span className="font-medium">{item.name || '-'}</span>
            <span className="text-xs text-gray-500 ml-2">[{item.ts_code}]</span>
          </div>
        </div>
        <TrendingUp className="h-4 w-4 text-red-600" />
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="flex flex-col">
          <span className="text-gray-600">上榜天数</span>
          <span className={item.days >= 5 ? 'text-red-600 font-semibold' : ''}>
            {item.days || 0}天
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-gray-600">连板高度</span>
          <span className="text-red-600 font-semibold">{item.up_stat || '-'}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-gray-600">涨停家数</span>
          <span className={item.up_nums >= 5 ? 'text-red-600 font-semibold' : ''}>
            {item.up_nums || 0}家
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-gray-600">连板家数</span>
          <span className={item.cons_nums >= 3 ? 'text-red-600 font-semibold' : ''}>
            {item.cons_nums || 0}家
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-gray-600">涨跌幅</span>
          <span className={(item.pct_chg || 0) >= 0 ? 'text-red-600' : 'text-green-600'}>
            {(item.pct_chg || 0) >= 0 ? '+' : ''}{(item.pct_chg || 0).toFixed(2)}%
          </span>
        </div>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="最强板块统计"
        description="获取每天涨停股票最多最强的概念板块，可以分析强势板块的轮动，判断资金动向"
        details={<>
          <div>接口：limit_cpt_list</div>
          <a href="https://tushare.pro/document/2?doc_id=357" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="最强板块统计"
            />
          </div>
        }
      />

      <StatisticsCards items={statsCards} />

      {/* 筛选区 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
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
            emptyMessage="暂无数据"
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
