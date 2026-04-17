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
import { useDataPage } from '@/hooks/useDataPage'
import { stkNineturnApi, type StkNineturnData, type StkNineturnStatistics } from '@/lib/api'
import { apiClient } from '@/lib/api-client'
import { toDateStr } from '@/lib/date-utils'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useSystemConfig } from '@/contexts'
import { formatStockCode } from '@/lib/utils'
import { RefreshCw, TrendingUp, TrendingDown, BarChart3, Activity, ListFilter } from 'lucide-react'

// ============== 页面组件 ==============

export default function StkNineturnPage() {
  // 查询筛选状态
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')

  // 同步弹窗额外字段
  const [syncTsCode, setSyncTsCode] = useState('')

  const { config } = useSystemConfig()

  const dp = useDataPage<StkNineturnData, StkNineturnStatistics>({
    apiCall: (params) => stkNineturnApi.getData(params),
    syncFn: (params) => stkNineturnApi.syncAsync(params),
    taskName: 'tasks.sync_stk_nineturn',
    bulkOps: {
      tableKey: 'stk_nineturn',
      syncFn: (params) => apiClient.post('/api/stk-nineturn/sync-async', null, { params }),
      taskName: 'tasks.sync_stk_nineturn',
    },
    paginationMode: 'page',
    pageSize: 100,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      return params
    },
    onBackfillDate: (dateStr) => {
      if (!startDate) setStartDate(new Date(dateStr + 'T00:00:00'))
    },
    syncSuccessMessage: '神奇九转指标数据同步完成',
  })

  // 覆盖同步确认：需要额外传 syncTsCode
  const handleCustomSyncConfirm = async () => {
    dp.setSyncDialogOpen(false)
    const params: Record<string, unknown> = {}
    if (syncTsCode.trim()) params.ts_code = syncTsCode.trim()
    if (dp.syncStartDate) params.start_date = toDateStr(dp.syncStartDate)
    if (dp.syncEndDate) params.end_date = toDateStr(dp.syncEndDate)
    await dp.handleSyncDirect(params)
  }

  const openStockAnalysis = useCallback((code: string) => {
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(code)), '_blank')
  }, [config])

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '总记录数',
        value: (s.total_records ?? 0).toLocaleString(),
        subValue: '条',
        icon: BarChart3,
        iconColor: 'text-blue-600',
      },
      {
        label: '覆盖股票',
        value: (s.stock_count ?? 0).toLocaleString(),
        subValue: '只',
        icon: Activity,
        iconColor: 'text-purple-600',
      },
      {
        label: '上九转信号',
        value: <span className="text-red-600">{(s.up_turn_count ?? 0).toLocaleString()}</span>,
        subValue: '次（潜在顶部）',
        icon: TrendingUp,
        iconColor: 'text-red-600',
      },
      {
        label: '下九转信号',
        value: <span className="text-green-600">{(s.down_turn_count ?? 0).toLocaleString()}</span>,
        subValue: '次（潜在底部）',
        icon: TrendingDown,
        iconColor: 'text-green-600',
      },
    ]
  }, [dp.statistics])

  // 移动端卡片
  const mobileCard = useCallback((item: StkNineturnData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div
            className="font-semibold text-base cursor-pointer hover:underline"
            onClick={() => openStockAnalysis(item.ts_code)}
          >
            {item.name ? `${item.name}[${formatStockCode(item.ts_code)}]` : item.ts_code}
          </div>
          <div className="text-sm text-gray-500">{item.trade_date ? item.trade_date.split(' ')[0] : '-'}</div>
        </div>
        <div className="flex gap-1">
          {item.nine_up_turn === '+9' && <span className="text-xs font-bold text-red-600">+9</span>}
          {item.nine_down_turn === '-9' && <span className="text-xs font-bold text-green-600">-9</span>}
        </div>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">收盘价</span>
          <span className="font-medium">{item.close !== null ? item.close.toFixed(2) : '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">上九转计数</span>
          <span className={item.up_count !== null && item.up_count >= 9 ? 'font-semibold text-red-600' : 'font-medium'}>
            {item.up_count !== null ? item.up_count.toFixed(1) : '-'}
            {item.up_count !== null && item.up_count < 9 && (
              <span className="text-gray-400 ml-1">({(9 - item.up_count).toFixed(1)}格)</span>
            )}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">下九转计数</span>
          <span className={item.down_count !== null && item.down_count >= 9 ? 'font-semibold text-green-600' : 'font-medium'}>
            {item.down_count !== null ? item.down_count.toFixed(1) : '-'}
            {item.down_count !== null && item.down_count < 9 && (
              <span className="text-gray-400 ml-1">({(9 - item.down_count).toFixed(1)}格)</span>
            )}
          </span>
        </div>
      </div>
    </div>
  ), [openStockAnalysis])

  // 桌面端表格列定义
  const columns: Column<StkNineturnData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票',
      accessor: (row) => (
        <span
          className="cursor-pointer hover:underline whitespace-nowrap"
          onClick={() => openStockAnalysis(row.ts_code)}
        >
          {row.name ? `${row.name}[${formatStockCode(row.ts_code)}]` : row.ts_code}
        </span>
      ),
      width: 150,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => row.trade_date ? row.trade_date.split(' ')[0] : '-',
      width: 110,
      sortable: true,
    },
    {
      key: 'close',
      header: '收盘价',
      accessor: (row) => row.close !== null ? row.close.toFixed(2) : '-',
      width: 90,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'up_count',
      header: '上九转计数',
      accessor: (row) => {
        if (row.up_count === null) return '-'
        const count = row.up_count.toFixed(1)
        return (
          <span className={row.up_count >= 9 ? 'text-red-600 font-semibold' : ''}>
            {count}
          </span>
        )
      },
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'down_count',
      header: '下九转计数',
      accessor: (row) => {
        if (row.down_count === null) return '-'
        const count = row.down_count.toFixed(1)
        return (
          <span className={row.down_count >= 9 ? 'text-green-600 font-semibold' : ''}>
            {count}
          </span>
        )
      },
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'nine_up_turn',
      header: '上九转',
      accessor: (row) => {
        if (row.nine_up_turn === '+9') {
          return <span className="text-red-600 font-bold">+9</span>
        }
        return '-'
      },
      width: 80
    },
    {
      key: 'nine_down_turn',
      header: '下九转',
      accessor: (row) => {
        if (row.nine_down_turn === '-9') {
          return <span className="text-green-600 font-bold">-9</span>
        }
        return '-'
      },
      width: 80
    }
  ], [openStockAnalysis])

  return (
    <div className="space-y-6">
      <PageHeader
        title="神奇九转指标"
        description="日线级别配合60min的九转效果，数据从20230101开始。"
        details={<>
          <div>接口：stk_nineturn</div>
          <a href="https://tushare.pro/document/2?doc_id=364" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="神奇九转指标"
            />
          </div>
        }
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
            <div className="w-full sm:w-48">
              <Label className="mb-1 block">股票代码</Label>
              <Input
                placeholder="如 000001 或 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="w-full sm:w-44">
              <Label className="mb-1 block">开始日期</Label>
              <DatePicker date={startDate} onDateChange={setStartDate} />
            </div>
            <div className="w-full sm:w-44">
              <Label className="mb-1 block">结束日期</Label>
              <DatePicker date={endDate} onDateChange={setEndDate} />
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <Button onClick={dp.handleQuery} disabled={dp.isLoading} className="flex-1 sm:flex-none">
                {dp.isLoading ? '查询中...' : '查询'}
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
            emptyMessage="暂无神奇九转指标数据"
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

      {/* 同步弹窗 */}
      <SyncDialog
        open={dp.syncDialogOpen}
        onOpenChange={dp.setSyncDialogOpen}
        onConfirm={handleCustomSyncConfirm}
        title="同步神奇九转指标数据"
        description="所有参数均为可选，不填写将同步最近30天数据（6000积分/次，数据从2023年起）。"
        disabled={dp.syncing}
      >
        <div className="py-4 space-y-4">
          <div>
            <Label className="mb-2 block">股票代码（可选）</Label>
            <Input
              placeholder="如 600000.SH，留空同步全市场"
              value={syncTsCode}
              onChange={(e) => setSyncTsCode(e.target.value)}
            />
          </div>
          <div>
            <Label className="mb-2 block">开始日期（可选）</Label>
            <DatePicker date={dp.syncStartDate} onDateChange={dp.setSyncStartDate} placeholder="留空同步最近30天" />
          </div>
          <div>
            <Label className="mb-2 block">结束日期（可选）</Label>
            <DatePicker date={dp.syncEndDate} onDateChange={dp.setSyncEndDate} placeholder="留空同步最近30天" />
          </div>
        </div>
      </SyncDialog>
    </div>
  )
}
