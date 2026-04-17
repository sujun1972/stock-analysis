'use client'

import { useState, useMemo } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { useDataPage } from '@/hooks/useDataPage'
import { ccassHoldApi, type CcassHoldData, type CcassHoldStatistics } from '@/lib/api'
import { apiClient } from '@/lib/api-client'
import { toDateStr } from '@/lib/date-utils'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { RefreshCw, TrendingUp, Users, Percent, Database, ListFilter } from 'lucide-react'

// ============== 工具函数 ==============

const formatNumber = (value: number | null | undefined, decimals = 0): string => {
  if (value === null || value === undefined) return '-'
  return value.toLocaleString('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

// ============== 页面组件 ==============

export default function CcassHoldPage() {
  // 查询条件
  const [tsCode, setTsCode] = useState('')
  const [hkCode, setHkCode] = useState('')
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)

  const dp = useDataPage<CcassHoldData, CcassHoldStatistics>({
    apiCall: (params) => ccassHoldApi.getData(params),
    syncFn: (params) => ccassHoldApi.syncAsync(params),
    taskName: 'tasks.sync_ccass_hold',
    bulkOps: {
      tableKey: 'ccass_hold',
      syncFn: (params) => apiClient.post('/api/ccass-hold/sync-async', null, { params }),
      taskName: 'tasks.sync_ccass_hold',
    },
    paginationMode: 'page',
    pageSize: 100,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tsCode) params.ts_code = tsCode
      if (hkCode) params.hk_code = hkCode
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      return params
    },
    onBackfillDate: (dateStr) => {
      if (!tradeDate) setTradeDate(new Date(dateStr + 'T00:00:00'))
    },
    syncSuccessMessage: 'CCASS持股汇总数据同步完成',
  })

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '平均持股量',
        value: formatNumber(s.avg_shareholding),
        subValue: '股',
        icon: TrendingUp,
        iconColor: 'text-blue-600',
      },
      {
        label: '最大持股量',
        value: formatNumber(s.max_shareholding),
        subValue: '股',
        icon: Database,
        iconColor: 'text-orange-600',
      },
      {
        label: '平均参与者数',
        value: formatNumber(s.avg_hold_nums),
        subValue: '个',
        icon: Users,
        iconColor: 'text-green-600',
      },
      {
        label: '平均占比',
        value: formatNumber(s.avg_hold_ratio, 2),
        subValue: '%',
        icon: Percent,
        iconColor: 'text-purple-600',
      },
    ]
  }, [dp.statistics])

  const columns = useMemo((): Column<CcassHoldData>[] => [
    {
      header: '交易日期',
      accessor: (row) => row.trade_date,
      key: 'trade_date',
      sortable: true,
      width: 110,
      cellClassName: 'whitespace-nowrap'
    },
    {
      header: '股票代码',
      accessor: (row) => row.ts_code,
      key: 'ts_code',
      sortable: true,
      width: 110,
      cellClassName: 'whitespace-nowrap font-mono text-xs'
    },
    {
      header: '港交所代码',
      accessor: (row) => row.hk_code || '-',
      key: 'hk_code',
      width: 100,
      cellClassName: 'whitespace-nowrap font-mono text-xs'
    },
    {
      header: '股票名称',
      accessor: (row) => row.name || '-',
      key: 'name',
    },
    {
      header: '持股量(股)',
      accessor: (row) => formatNumber(row.shareholding),
      key: 'shareholding',
      sortable: true,
      width: 130,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      header: '参与者数目',
      accessor: (row) => formatNumber(row.hold_nums),
      key: 'hold_nums',
      sortable: true,
      width: 110,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      header: '占比(%)',
      accessor: (row) => formatNumber(row.hold_ratio, 2),
      key: 'hold_ratio',
      sortable: true,
      width: 90,
      cellClassName: 'text-right whitespace-nowrap'
    }
  ], [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="中央结算系统持股汇总"
        description="描述：获取中央结算系统持股汇总数据，覆盖全部历史数据，根据交易所披露时间，当日数据在下一交易日早上9点前完成入库"
        details={<>
          <div>接口：ccass_hold</div>
          <a href="https://tushare.pro/document/2?doc_id=295" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <div className="flex gap-2">
            <Button onClick={() => dp.setSyncDialogOpen(true)} disabled={dp.syncing}>
              {dp.syncing
                ? <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
                : <><RefreshCw className="h-4 w-4 mr-1" />同步数据</>}
            </Button>
            <BulkOpsButtons
              onFullSync={dp.handleFullSync}
              onClearConfirm={dp.handleClear}
              isClearDialogOpen={dp.isClearDialogOpen}
              setIsClearDialogOpen={dp.setIsClearDialogOpen}
              fullSyncing={dp.fullSyncing}
              isClearing={dp.isClearing}
              earliestHistoryDate={dp.earliestHistoryDate}
              tableName="CCASS持股汇总"
            />
          </div>
        }
      />

      <StatisticsCards items={statsCards} />

      {/* 查询筛选 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ListFilter className="h-4 w-4" />
            数据查询
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="space-y-1 w-full sm:w-auto">
              <Label htmlFor="ts_code">股票代码</Label>
              <Input
                id="ts_code"
                placeholder="如 000001 或 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value.toUpperCase())}
                className="w-full sm:w-40"
              />
            </div>
            <div className="space-y-1 w-full sm:w-auto">
              <Label htmlFor="hk_code">港交所代码</Label>
              <Input
                id="hk_code"
                placeholder="如 95009"
                value={hkCode}
                onChange={(e) => setHkCode(e.target.value)}
                className="w-full sm:w-32"
              />
            </div>
            <div className="space-y-1">
              <Label>交易日期</Label>
              <DatePicker date={tradeDate} onDateChange={setTradeDate} placeholder="留空加载最新" />
            </div>
            <Button onClick={dp.handleQuery} disabled={dp.isLoading}>
              {dp.isLoading ? '查询中...' : '查询'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="pt-4">
          <DataTable
            columns={columns}
            data={dp.data}
            loading={dp.isLoading}
            emptyMessage="暂无数据"
            tableClassName="table-fixed w-full [&_th]:border-r [&_th]:border-gray-200 [&_td]:border-r [&_td]:border-gray-100 [&_th:last-child]:border-r-0 [&_td:last-child]:border-r-0"
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
            mobileCard={(row) => (
              <div className="p-4 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="font-semibold text-sm">{row.name || row.ts_code}</span>
                  <span className="text-xs text-muted-foreground">{row.trade_date}</span>
                </div>
                <div className="text-xs text-muted-foreground font-mono">{row.ts_code}{row.hk_code ? ` · ${row.hk_code}` : ''}</div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">持股量</span>
                  <span className="font-medium">{formatNumber(row.shareholding)} 股</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">参与者数目</span>
                  <span className="font-medium">{formatNumber(row.hold_nums)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">占比</span>
                  <span className="font-medium">{formatNumber(row.hold_ratio, 2)}%</span>
                </div>
              </div>
            )}
          />
        </CardContent>
      </Card>

      {/* 同步对话框 */}
      <SyncDialog
        open={dp.syncDialogOpen}
        onOpenChange={dp.setSyncDialogOpen}
        onConfirm={dp.handleSyncConfirm}
        title="同步中央结算系统持股汇总"
        description="从Tushare接口同步数据（5000积分/次）。留空则同步最新数据。"
        disabled={dp.syncing}
        showDateRange
        startDate={dp.syncStartDate}
        onStartDateChange={dp.setSyncStartDate}
        endDate={dp.syncEndDate}
        onEndDateChange={dp.setSyncEndDate}
        startDateLabel="开始日期（可选）"
        endDateLabel="结束日期（可选）"
      />
    </div>
  )
}
