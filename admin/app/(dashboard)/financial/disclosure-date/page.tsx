'use client'

import { useState, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { useDataPage } from '@/hooks/useDataPage'
import { financialDataApi } from '@/lib/api/financial-data'
import type { DisclosureDateData, DisclosureDateStatistics } from '@/lib/api/financial-data'
import { toDateStr } from '@/lib/date-utils'
import { RefreshCw, FileText, Calendar, TrendingUp, CheckCircle, Clock } from 'lucide-react'

// ============== 页面组件 ==============

export default function DisclosureDatePage() {
  // 查询筛选状态
  const [tsCode, setTsCode] = useState('')
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)

  const dp = useDataPage<DisclosureDateData, DisclosureDateStatistics>({
    apiCall: (params) => financialDataApi.getDisclosureDate(params),
    syncFn: () => financialDataApi.syncDisclosureDateAsync(),
    taskName: ['tasks.sync_disclosure_date', 'tasks.sync_disclosure_date_full_history'],
    bulkOps: {
      tableKey: 'disclosure_date',
      syncFn: (params) => financialDataApi.syncDisclosureDateFullHistoryAsync(params),
      taskName: 'tasks.sync_disclosure_date_full_history',
    },
    paginationMode: 'offset',
    pageSize: 30,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tsCode) params.ts_code = tsCode
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      return params
    },
    syncSuccessMessage: '财报披露计划数据同步完成',
  })

  // 统计卡片（5列布局）
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '总记录数',
        value: (s.total_count || 0).toLocaleString(),
        icon: FileText,
        iconColor: 'text-muted-foreground',
      },
      {
        label: '股票数量',
        value: (s.stock_count || 0).toLocaleString(),
        icon: TrendingUp,
        iconColor: 'text-muted-foreground',
      },
      {
        label: '报告期数量',
        value: (s.period_count || 0).toLocaleString(),
        icon: Calendar,
        iconColor: 'text-muted-foreground',
      },
      {
        label: '已披露',
        value: <span className="text-green-600">{(s.disclosed_count || 0).toLocaleString()}</span>,
        icon: CheckCircle,
        iconColor: 'text-green-600',
      },
      {
        label: '待披露',
        value: <span className="text-yellow-600">{(s.pending_count || 0).toLocaleString()}</span>,
        icon: Clock,
        iconColor: 'text-yellow-600',
      },
    ]
  }, [dp.statistics])

  // 表格列定义
  const columns: Column<DisclosureDateData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'end_date',
      header: '报告期',
      accessor: (row) => row.end_date
    },
    {
      key: 'ann_date',
      header: '公告日',
      accessor: (row) => row.ann_date
    },
    {
      key: 'pre_date',
      header: '预计披露日期',
      accessor: (row) => row.pre_date || '-'
    },
    {
      key: 'actual_date',
      header: '实际披露日期',
      accessor: (row) => row.actual_date || '-'
    },
    {
      key: 'status',
      header: '披露状态',
      accessor: (row) => (
        <span className={`px-2 py-1 rounded text-xs ${
          row.actual_date
            ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
            : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
        }`}>
          {row.actual_date ? '已披露' : '待披露'}
        </span>
      )
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: DisclosureDateData) => (
    <div className="p-4 space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">股票代码</span>
        <span className="font-medium">{item.ts_code}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">报告期</span>
        <span>{item.end_date}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">公告日</span>
        <span>{item.ann_date}</span>
      </div>
      {item.pre_date && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">预计披露日期</span>
          <span>{item.pre_date}</span>
        </div>
      )}
      {item.actual_date && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">实际披露日期</span>
          <span>{item.actual_date}</span>
        </div>
      )}
      <div className="flex justify-between items-center pt-2">
        <span className="text-sm text-gray-600 dark:text-gray-400">披露状态</span>
        <span className={`px-2 py-1 rounded text-xs ${
          item.actual_date
            ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
            : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
        }`}>
          {item.actual_date ? '已披露' : '待披露'}
        </span>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="财报披露计划"
        description="获取财报披露计划日期"
        details={<>
          <div>接口：disclosure_date</div>
          <a href="https://tushare.pro/document/2?doc_id=162" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="财报披露计划"
            />
          </div>
        }
      />

      <StatisticsCards
        items={statsCards}
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4"
      />

      {/* 筛选和操作 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="flex-1 w-full sm:w-auto">
              <Label className="mb-2 block">股票代码</Label>
              <Input placeholder="如: 600000.SH" value={tsCode} onChange={(e) => setTsCode(e.target.value)} />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <Label className="mb-2 block">开始日期（报告期）</Label>
              <DatePicker date={startDate} onDateChange={setStartDate} placeholder="选择开始日期" />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <Label className="mb-2 block">结束日期（报告期）</Label>
              <DatePicker date={endDate} onDateChange={setEndDate} placeholder="选择结束日期" />
            </div>
            <div className="flex gap-2">
              <Button onClick={dp.handleQuery} disabled={dp.isLoading}>
                {dp.isLoading ? '查询中...' : '查询'}
              </Button>
            </div>
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
            emptyMessage="暂无数据"
            pagination={{
              page: dp.page,
              pageSize: dp.pageSize,
              total: dp.total,
              onPageChange: dp.handlePageChange,
              onPageSizeChange: dp.handlePageSizeChange,
              pageSizeOptions: [10, 20, 30, 50, 100]
            }}
            mobileCard={mobileCard}
          />
        </CardContent>
      </Card>

      {/* 同步弹窗 */}
      <SyncDialog
        open={dp.syncDialogOpen}
        onOpenChange={dp.setSyncDialogOpen}
        onConfirm={dp.handleSyncConfirm}
        title="同步财报披露计划"
        description="将从 Tushare 增量同步最新财报披露计划数据，无需选择日期。"
        disabled={dp.syncing}
      />
    </div>
  )
}
