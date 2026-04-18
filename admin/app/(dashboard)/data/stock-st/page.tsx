'use client'

import { useState, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useDataPage } from '@/hooks/useDataPage'
import { stockStApi } from '@/lib/api'
import type { StockStData, StockStStatistics } from '@/lib/api'
import { axiosInstance } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { RefreshCw, BarChart3, Calendar, TrendingUp, Tag } from 'lucide-react'

export default function StockStPage() {
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState<string>('')
  const [stType, setStType] = useState<string>('ALL')

  const dp = useDataPage<StockStData, StockStStatistics>({
    apiCall: (params) => stockStApi.getData(params),
    statisticsCall: (params) => stockStApi.getStatistics(params),
    syncFn: () => stockStApi.syncAsync(),
    taskName: 'tasks.sync_stock_st_incremental',
    bulkOps: {
      tableKey: 'stock_st',
      syncFn: (params) => axiosInstance.post('/api/stock-st/sync-full-history', null, { params }),
      taskName: 'tasks.sync_stock_st_full_history',
    },
    paginationMode: 'page',
    pageSize: 30,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (stType !== 'ALL') params.st_type = stType
      return params
    },
    syncSuccessMessage: 'ST股票列表已更新',
  })

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      { label: '总记录数', value: s.total_records.toLocaleString(), subValue: '历史全部记录', icon: BarChart3, iconColor: 'text-blue-600' },
      { label: '唯一股票数', value: s.unique_stocks.toLocaleString(), subValue: '曾被ST的股票', icon: TrendingUp, iconColor: 'text-orange-600' },
      { label: '交易天数', value: s.trading_days.toLocaleString(), subValue: '有数据的交易日', icon: Calendar, iconColor: 'text-green-600' },
      { label: 'ST类型数', value: s.st_types.toLocaleString(), subValue: 'ST/*ST 等类型', icon: Tag, iconColor: 'text-purple-600' },
    ]
  }, [dp.statistics])

  // 表格列定义
  const columns: Column<StockStData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'name',
      header: '股票名称',
      accessor: (row) => row.name
    },
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => row.trade_date
    },
    {
      key: 'type',
      header: 'ST类型',
      accessor: (row) => (
        <span className="font-medium text-red-600">{row.type}</span>
      )
    },
    {
      key: 'type_name',
      header: '类型名称',
      accessor: (row) => row.type_name
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: StockStData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="space-y-2">
        <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">股票代码</span>
          <span className="font-medium">{item.ts_code}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">股票名称</span>
          <span className="font-medium">{item.name}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">交易日期</span>
          <span>{item.trade_date}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">ST类型</span>
          <span className="font-medium text-red-600">{item.type}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">类型名称</span>
          <span>{item.type_name}</span>
        </div>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="ST股票列表"
        description="获取ST股票列表，可根据交易日期获取历史上每天的ST列表"
        details={<>
          <div>接口：stock_st</div>
          <a href="https://tushare.pro/document/2?doc_id=397" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="ST股票列表"
            />
          </div>
        }
      />

      <SyncDialog
        open={dp.syncDialogOpen}
        onOpenChange={dp.setSyncDialogOpen}
        onConfirm={dp.handleSyncConfirm}
        title="同步ST股票列表"
        description="将从 Tushare 同步最新ST股票数据，无需选择日期。"
        disabled={dp.syncing}
      />

      <StatisticsCards items={statsCards} />

      {/* 筛选和操作 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">开始日期</label>
                <DatePicker date={startDate} onDateChange={setStartDate} placeholder="选择开始日期" />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">结束日期</label>
                <DatePicker date={endDate} onDateChange={setEndDate} placeholder="选择结束日期" />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">股票代码</label>
                <Input
                  placeholder="如：000001.SZ"
                  value={tsCode}
                  onChange={(e) => setTsCode(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">ST类型</label>
                <Select value={stType} onValueChange={setStType}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">全部</SelectItem>
                    <SelectItem value="S">*ST</SelectItem>
                    <SelectItem value="P">ST</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={dp.handleQuery} disabled={dp.isLoading}>
                <RefreshCw className={`h-4 w-4 mr-1 ${dp.isLoading ? 'animate-spin' : ''}`} />
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
            emptyMessage="暂无ST股票数据"
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
