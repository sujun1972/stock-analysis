'use client'

import { useState, useMemo } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useDataPage } from '@/hooks/useDataPage'
import { slbLenApi } from '@/lib/api'
import { axiosInstance } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import type { SlbLenData, SlbLenStatistics } from '@/lib/api/slb-len'
import { RefreshCw, TrendingUp, TrendingDown, DollarSign, BarChart3, ListFilter } from 'lucide-react'

export default function SlbLenPage() {
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)

  const dp = useDataPage<SlbLenData, SlbLenStatistics>({
    apiCall: (params) => slbLenApi.getSlbLen(params),
    statisticsCall: (params) => slbLenApi.getSlbLenStatistics(params),
    syncFn: (params) => slbLenApi.syncSlbLenAsync(params),
    taskName: 'tasks.sync_slb_len',
    bulkOps: {
      tableKey: 'slb_len',
      syncFn: (params) => axiosInstance.post('/api/slb-len/sync-async', null, { params }),
      taskName: 'tasks.sync_slb_len',
    },
    paginationMode: 'offset',
    pageSize: 100,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      return params
    },
    syncSuccessMessage: '转融资交易汇总数据已更新',
  })

  // 格式化金额（数值已为亿元）
  const formatAmount = (amount: number | undefined | null) => {
    if (amount === null || amount === undefined) return '-'
    return amount.toFixed(2) + '亿'
  }

  // 格式化日期显示
  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-'
    if (dateStr.length === 8) {
      return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
    }
    return dateStr
  }

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      { label: '平均期末余额', value: formatAmount(s.avg_cb), subValue: '统计周期内均值', icon: TrendingUp, iconColor: 'text-blue-600' },
      { label: '最大期末余额', value: <span className="text-red-600">{formatAmount(s.max_cb)}</span>, subValue: '历史最高值', icon: BarChart3, iconColor: 'text-red-500' },
      { label: '累计竞价成交', value: formatAmount(s.total_auc_amount), subValue: '统计周期累计值', icon: DollarSign, iconColor: 'text-green-600' },
      { label: '累计偿还金额', value: formatAmount(s.total_repay_amount), subValue: '统计周期累计值', icon: TrendingDown, iconColor: 'text-orange-500' },
    ]
  }, [dp.statistics])

  const columns: Column<SlbLenData>[] = [
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => formatDate(row.trade_date),
      width: 110,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'ob',
      header: '期初余额',
      accessor: (row) => formatAmount(row.ob),
      width: 120,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'auc_amount',
      header: '竞价成交',
      accessor: (row) => formatAmount(row.auc_amount),
      hideOnMobile: true,
      width: 120,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'repo_amount',
      header: '再借成交',
      accessor: (row) => formatAmount(row.repo_amount),
      hideOnMobile: true,
      width: 120,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'repay_amount',
      header: '偿还金额',
      accessor: (row) => formatAmount(row.repay_amount),
      hideOnMobile: true,
      width: 120,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'cb',
      header: '期末余额',
      accessor: (row) => formatAmount(row.cb),
      width: 120,
      cellClassName: 'text-right whitespace-nowrap'
    }
  ]

  const mobileCard = (item: SlbLenData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-center mb-3">
        <span className="font-semibold text-base">{formatDate(item.trade_date)}</span>
        <span className="text-sm font-medium text-blue-600">期末 {formatAmount(item.cb)}</span>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">期初余额</span>
          <span className="font-medium">{formatAmount(item.ob)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">竞价成交</span>
          <span className="font-medium">{formatAmount(item.auc_amount)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">再借成交</span>
          <span className="font-medium">{formatAmount(item.repo_amount)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">偿还金额</span>
          <span className="font-medium">{formatAmount(item.repay_amount)}</span>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="转融资交易汇总"
        description="转融通融资汇总"
        details={<>
          <div>接口：slb_len</div>
          <a href="https://tushare.pro/document/2?doc_id=331" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="转融资交易汇总"
            />
          </div>
        }
      />

      <SyncDialog
        open={dp.syncDialogOpen}
        onOpenChange={dp.setSyncDialogOpen}
        onConfirm={dp.handleSyncConfirm}
        title="同步转融资交易汇总"
        description="选择同步日期范围（留空则同步最近30天数据）。"
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
            emptyMessage="暂无转融资数据"
            tableClassName="table-fixed w-full [&_th]:border-r [&_td]:border-r [&_th:last-child]:border-r-0 [&_td:last-child]:border-r-0 [&_th]:!text-center"
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
