'use client'

import { useState, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useDataPage } from '@/hooks/useDataPage'
import { stkLimitDApi, type StkLimitDData, type StkLimitDStatistics } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { RefreshCw, TrendingUp, TrendingDown, DollarSign, CalendarDays } from 'lucide-react'

// ============== 页面组件 ==============

export default function StkLimitDPage() {
  // 查询筛选状态
  const [tsCode, setTsCode] = useState('')
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)

  const dp = useDataPage<StkLimitDData, StkLimitDStatistics>({
    apiCall: (params) => stkLimitDApi.getData(params),
    syncFn: () => stkLimitDApi.syncAsync(),
    taskName: ['tasks.sync_stk_limit_d_incremental', 'tasks.sync_stk_limit_d_full_history'],
    bulkOps: {
      tableKey: 'stk_limit_d',
      syncFn: (params) => stkLimitDApi.syncFullHistory(params),
      taskName: 'tasks.sync_stk_limit_d_full_history',
    },
    paginationMode: 'page',
    pageSize: 30,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      return params
    },
    syncSuccessMessage: '每日涨跌停价格数据同步完成',
  })

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '总记录数',
        value: s.total_records.toLocaleString(),
        icon: DollarSign,
        iconColor: 'text-blue-600',
      },
      {
        label: '交易日数',
        value: `${s.trading_days}`,
        icon: CalendarDays,
        iconColor: 'text-orange-600',
      },
      {
        label: '股票数量',
        value: `${s.stock_count}`,
        icon: TrendingUp,
        iconColor: 'text-green-600',
      },
      {
        label: '平均涨幅空间',
        value: `${s.avg_up_range.toFixed(2)}`,
        subValue: '元',
        icon: TrendingDown,
        iconColor: 'text-purple-600',
      },
    ]
  }, [dp.statistics])

  // 表格列定义
  const columns: Column<StkLimitDData>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => row.trade_date.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')
    },
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'pre_close',
      header: (
        <>
          <span className="sm:hidden">昨收</span>
          <span className="hidden sm:inline">昨日收盘价</span>
        </>
      ),
      accessor: (row) => row.pre_close?.toFixed(2) || '-'
    },
    {
      key: 'up_limit',
      header: (
        <>
          <span className="sm:hidden">涨停</span>
          <span className="hidden sm:inline">涨停价</span>
        </>
      ),
      accessor: (row) => (
        <span className="text-red-600 font-medium">
          {row.up_limit?.toFixed(2) || '-'}
        </span>
      )
    },
    {
      key: 'down_limit',
      header: (
        <>
          <span className="sm:hidden">跌停</span>
          <span className="hidden sm:inline">跌停价</span>
        </>
      ),
      accessor: (row) => (
        <span className="text-green-600 font-medium">
          {row.down_limit?.toFixed(2) || '-'}
        </span>
      )
    },
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: StkLimitDData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">交易日期</span>
        <span className="font-medium">
          {item.trade_date.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">股票代码</span>
        <span className="font-medium">{item.ts_code}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">昨日收盘价</span>
        <span>{item.pre_close?.toFixed(2) || '-'}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">涨停价</span>
        <span className="text-red-600 font-medium">{item.up_limit?.toFixed(2) || '-'}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">跌停价</span>
        <span className="text-green-600 font-medium">{item.down_limit?.toFixed(2) || '-'}</span>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="每日涨跌停价格"
        description="获取全市场（包含A/B股和基金）每日涨跌停价格，包括涨停价格，跌停价格等，每个交易日8点40左右更新当日股票涨跌停价格。"
        details={<>
          <div>接口：stk_limit</div>
          <a href="https://tushare.pro/document/2?doc_id=183" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="每日涨跌停价格"
            />
          </div>
        }
      />

      <StatisticsCards items={statsCards} />

      {/* 筛选和操作区域 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label htmlFor="ts-code">股票代码</Label>
              <Input
                id="ts-code"
                placeholder="如：000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>开始日期</Label>
              <DatePicker
                date={startDate}
                onDateChange={setStartDate}
                placeholder="选择开始日期"
              />
            </div>

            <div className="space-y-2">
              <Label>结束日期</Label>
              <DatePicker
                date={endDate}
                onDateChange={setEndDate}
                placeholder="选择结束日期"
              />
            </div>

            <div className="flex items-end">
              <Button
                variant="default"
                onClick={dp.handleQuery}
                disabled={dp.isLoading}
                className="w-full"
              >
                {dp.isLoading ? '查询中...' : '查询'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <DataTable
          columns={columns}
          data={dp.data}
          loading={dp.isLoading}
          emptyMessage="暂无数据"
          mobileCard={mobileCard}
          pagination={{
            page: dp.page,
            pageSize: dp.pageSize,
            total: dp.total,
            onPageChange: dp.handlePageChange,
          }}
        />
      </Card>

      {/* 同步确认弹窗（无日期参数） */}
      <SyncDialog
        open={dp.syncDialogOpen}
        onOpenChange={dp.setSyncDialogOpen}
        onConfirm={dp.handleSyncConfirm}
        title="同步每日涨跌停价格"
        description="将从 Tushare 增量同步最新涨跌停价格数据，无需选择日期。"
        disabled={dp.syncing}
      />
    </div>
  )
}
