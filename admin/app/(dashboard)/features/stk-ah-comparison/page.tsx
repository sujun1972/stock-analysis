'use client'

import { useState, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { useDataPage } from '@/hooks/useDataPage'
import { stkAhComparisonApi } from '@/lib/api'
import { apiClient } from '@/lib/api-client'
import { toDateStr } from '@/lib/date-utils'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { RefreshCw, TrendingUp, TrendingDown, BarChart3, Activity } from 'lucide-react'
import type { StkAhComparisonData, StkAhComparisonStatistics } from '@/lib/api/stk-ah-comparison'

// ============== 工具函数 ==============

const formatDate = (dateStr: string) => {
  if (!dateStr || dateStr.length !== 8) return dateStr
  return `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`
}

const formatNumber = (num: number | null | undefined, decimals: number = 2) => {
  if (num === null || num === undefined) return '-'
  return num.toFixed(decimals)
}

const formatPercent = (num: number | null | undefined) => {
  if (num === null || num === undefined) return '-'
  const sign = num >= 0 ? '+' : ''
  return `${sign}${num.toFixed(2)}%`
}

// ============== 页面组件 ==============

export default function StkAhComparisonPage() {
  // 查询筛选状态
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)

  // 同步弹窗额外字段
  const [syncHkCode, setSyncHkCode] = useState('')
  const [syncTsCode, setSyncTsCode] = useState('')
  const [syncTradeDate, setSyncTradeDate] = useState<Date | undefined>(undefined)

  const dp = useDataPage<StkAhComparisonData, StkAhComparisonStatistics>({
    apiCall: (params) => stkAhComparisonApi.getData(params),
    syncFn: (params) => stkAhComparisonApi.syncAsync(params),
    taskName: 'tasks.sync_stk_ah_comparison',
    bulkOps: {
      tableKey: 'stk_ah_comparison',
      syncFn: (params) => apiClient.post('/api/stk-ah-comparison/sync-async', null, { params }),
      taskName: 'tasks.sync_stk_ah_comparison',
    },
    paginationMode: 'page',
    pageSize: 30,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      return params
    },
    backfillDateField: 'resolved_date',
    onBackfillDate: (dateStr) => {
      if (!tradeDate) setTradeDate(new Date(dateStr + 'T00:00:00'))
    },
    syncSuccessMessage: 'AH股比价数据同步完成',
  })

  // 覆盖同步确认：需要额外传 syncHkCode / syncTsCode / syncTradeDate
  const handleCustomSyncConfirm = async () => {
    dp.setSyncDialogOpen(false)
    const params: Record<string, unknown> = {}
    if (syncHkCode.trim()) params.hk_code = syncHkCode.trim()
    if (syncTsCode.trim()) params.ts_code = syncTsCode.trim()
    if (syncTradeDate) params.trade_date = toDateStr(syncTradeDate)
    if (dp.syncStartDate) params.start_date = toDateStr(dp.syncStartDate)
    if (dp.syncEndDate) params.end_date = toDateStr(dp.syncEndDate)
    await dp.handleSyncDirect(params)
  }

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '股票数量',
        value: String(s.stock_count),
        subValue: 'AH同时上市',
        icon: BarChart3,
        iconColor: 'text-muted-foreground',
      },
      {
        label: '平均溢价率',
        value: <span className={`${(s.avg_premium ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
          {formatPercent(s.avg_premium)}
        </span>,
        subValue: 'A股相对港股溢价',
        icon: Activity,
        iconColor: 'text-muted-foreground',
      },
      {
        label: '最高溢价率',
        value: <span className="text-red-600">{formatPercent(s.max_premium)}</span>,
        subValue: '溢价最大的股票',
        icon: TrendingUp,
        iconColor: 'text-red-400',
      },
      {
        label: '最低溢价率',
        value: <span className="text-green-600">{formatPercent(s.min_premium)}</span>,
        subValue: '溢价最小的股票',
        icon: TrendingDown,
        iconColor: 'text-green-400',
      },
    ]
  }, [dp.statistics])

  const columns: Column<StkAhComparisonData>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => formatDate(row.trade_date)
    },
    {
      key: 'hk_code',
      header: '港股代码',
      accessor: (row) => row.hk_code
    },
    {
      key: 'hk_name',
      header: '港股名称',
      accessor: (row) => row.hk_name || '-'
    },
    {
      key: 'ts_code',
      header: 'A股代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'name',
      header: 'A股名称',
      accessor: (row) => row.name || '-'
    },
    {
      key: 'hk_close',
      header: '港股收盘价',
      accessor: (row) => formatNumber(row.hk_close),
      cellClassName: 'text-right'
    },
    {
      key: 'close',
      header: 'A股收盘价',
      accessor: (row) => formatNumber(row.close),
      cellClassName: 'text-right'
    },
    {
      key: 'ah_comparison',
      header: 'AH比价',
      accessor: (row) => formatNumber(row.ah_comparison),
      cellClassName: 'text-right'
    },
    {
      key: 'ah_premium',
      header: 'AH溢价率',
      accessor: (row) => (
        <span className={`font-medium ${(row.ah_premium ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
          {formatPercent(row.ah_premium)}
        </span>
      ),
      cellClassName: 'text-right'
    },
    {
      key: 'hk_pct_chg',
      header: '港股涨跌幅',
      accessor: (row) => (
        <span className={`font-medium ${(row.hk_pct_chg ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
          {formatPercent(row.hk_pct_chg)}
        </span>
      ),
      cellClassName: 'text-right'
    },
    {
      key: 'pct_chg',
      header: 'A股涨跌幅',
      accessor: (row) => (
        <span className={`font-medium ${(row.pct_chg ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
          {formatPercent(row.pct_chg)}
        </span>
      ),
      cellClassName: 'text-right'
    }
  ], [])

  const mobileCard = useCallback((item: StkAhComparisonData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <div>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {item.hk_name || item.hk_code} / {item.name || item.ts_code}
          </span>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {item.hk_code} / {item.ts_code}
          </div>
        </div>
        <span className="text-xs text-gray-600 dark:text-gray-400">{formatDate(item.trade_date)}</span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">港股价格:</span>
          <span className="font-medium">{formatNumber(item.hk_close)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">A股价格:</span>
          <span className="font-medium">{formatNumber(item.close)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">AH比价:</span>
          <span className="font-medium">{formatNumber(item.ah_comparison)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">溢价率:</span>
          <span className={`font-medium ${(item.ah_premium ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
            {formatPercent(item.ah_premium)}
          </span>
        </div>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="AH股比价"
        description="AH股比价数据，可根据交易日期获取历史"
        details={<>
          <div>接口：stk_ah_comparison</div>
          <a href="https://tushare.pro/document/2?doc_id=399" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="AH股比价"
            />
          </div>
        }
      />

      <StatisticsCards items={statsCards} />

      {/* 筛选区域 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="w-full sm:w-auto">
              <Label>交易日期</Label>
              <DatePicker date={tradeDate} onDateChange={setTradeDate} placeholder="留空默认最近有数据日期" />
            </div>
            <Button onClick={dp.handleQuery} disabled={dp.isLoading} className="w-full sm:w-auto">
              <RefreshCw className={`h-4 w-4 mr-1 ${dp.isLoading ? 'animate-spin' : ''}`} />
              查询
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="p-0">
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
        </CardContent>
      </Card>

      {/* 同步对话框 */}
      <SyncDialog
        open={dp.syncDialogOpen}
        onOpenChange={dp.setSyncDialogOpen}
        onConfirm={handleCustomSyncConfirm}
        title="同步AH股比价数据"
        description="所有参数均为可选，不填写参数将同步最近30天数据"
        disabled={dp.syncing}
      >
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="sync-hk-code">港股代码</Label>
            <Input
              id="sync-hk-code"
              placeholder="如：02068.HK"
              value={syncHkCode}
              onChange={(e) => setSyncHkCode(e.target.value)}
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="sync-ts-code">A股代码</Label>
            <Input
              id="sync-ts-code"
              placeholder="如：601068.SH"
              value={syncTsCode}
              onChange={(e) => setSyncTsCode(e.target.value)}
            />
          </div>

          <div className="grid gap-2">
            <Label>交易日期</Label>
            <DatePicker date={syncTradeDate} onDateChange={setSyncTradeDate} placeholder="选择交易日期" />
          </div>

          <div className="grid gap-2">
            <Label>日期范围（可选）</Label>
            <div className="flex gap-2 items-center">
              <DatePicker date={dp.syncStartDate} onDateChange={dp.setSyncStartDate} placeholder="开始日期" />
              <span className="text-muted-foreground">至</span>
              <DatePicker date={dp.syncEndDate} onDateChange={dp.setSyncEndDate} placeholder="结束日期" />
            </div>
          </div>

          <div className="rounded-lg bg-amber-50 dark:bg-amber-950 p-3 border border-amber-200 dark:border-amber-800">
            <p className="text-sm text-amber-800 dark:text-amber-200">
              <strong>注意：</strong>此接口消耗 5000 积分起，单次最大返回 1000 条数据。数据从2025年8月12日开始，每天盘后17:00更新。
            </p>
          </div>
        </div>
      </SyncDialog>
    </div>
  )
}
