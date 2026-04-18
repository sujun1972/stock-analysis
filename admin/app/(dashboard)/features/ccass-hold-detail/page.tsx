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
import { ccassHoldDetailApi, type CcassHoldDetailData, type CcassHoldDetailStatistics } from '@/lib/api'
import { axiosInstance } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { RefreshCw, TrendingUp, Users, Calendar, Database, ListFilter } from 'lucide-react'

// ============== 工具函数 ==============

const formatNumber = (value: number | null | undefined, decimals = 0): string => {
  if (value === null || value === undefined) return '-'
  return value.toLocaleString('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

// ============== 页面组件 ==============

export default function CcassHoldDetailPage() {
  // 查询条件
  const [tsCode, setTsCode] = useState('')
  const [participantId, setParticipantId] = useState('')
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)

  // 同步弹窗额外字段
  const [syncTsCode, setSyncTsCode] = useState('')
  const [syncHkCode, setSyncHkCode] = useState('')
  const [syncTradeDate, setSyncTradeDate] = useState<Date | undefined>(undefined)

  const dp = useDataPage<CcassHoldDetailData, CcassHoldDetailStatistics>({
    apiCall: (params) => ccassHoldDetailApi.getData(params),
    syncFn: (params) => ccassHoldDetailApi.syncAsync(params),
    taskName: 'tasks.sync_ccass_hold_detail',
    bulkOps: {
      tableKey: 'ccass_hold_detail',
      syncFn: (params) => axiosInstance.post('/api/ccass-hold-detail/sync-async', null, { params }),
      taskName: 'tasks.sync_ccass_hold_detail',
    },
    paginationMode: 'page',
    pageSize: 100,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tsCode) params.ts_code = tsCode
      if (participantId) params.col_participant_id = participantId
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      return params
    },
    onBackfillDate: (dateStr) => {
      if (!tradeDate) setTradeDate(new Date(dateStr + 'T00:00:00'))
    },
    syncSuccessMessage: 'CCASS持股明细数据同步完成',
  })

  // 覆盖同步确认：需要额外传 syncTsCode / syncHkCode / syncTradeDate，且需要验证至少填写一个参数
  const handleCustomSyncConfirm = async () => {
    const hasTsCode = syncTsCode.trim() !== ''
    const hasHkCode = syncHkCode.trim() !== ''
    const hasTradeDate = syncTradeDate !== undefined
    const hasDateRange = dp.syncStartDate !== undefined || dp.syncEndDate !== undefined

    if (!hasTsCode && !hasHkCode && !hasTradeDate && !hasDateRange) {
      const { toast } = await import('sonner')
      toast.error('请至少填写股票代码、港交所代码、交易日期或日期范围中的一个')
      return
    }

    dp.setSyncDialogOpen(false)
    const params: Record<string, unknown> = {}
    if (syncTsCode.trim()) params.ts_code = syncTsCode.trim()
    if (syncHkCode.trim()) params.hk_code = syncHkCode.trim()
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
        label: '总记录数',
        value: formatNumber(s.total_records),
        subValue: '条',
        icon: Database,
        iconColor: 'text-blue-600',
      },
      {
        label: '交易日数',
        value: formatNumber(s.trading_days),
        subValue: '天',
        icon: Calendar,
        iconColor: 'text-orange-600',
      },
      {
        label: '股票数',
        value: formatNumber(s.stock_count),
        subValue: '只',
        icon: TrendingUp,
        iconColor: 'text-green-600',
      },
      {
        label: '机构数',
        value: formatNumber(s.participant_count),
        subValue: '个',
        icon: Users,
        iconColor: 'text-purple-600',
      },
    ]
  }, [dp.statistics])

  const columns = useMemo((): Column<CcassHoldDetailData>[] => [
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
      header: '股票名称',
      accessor: (row) => row.name || '-',
      key: 'name',
      width: 100
    },
    {
      header: '参与者编号',
      accessor: (row) => row.col_participant_id,
      key: 'col_participant_id',
      width: 110,
      cellClassName: 'whitespace-nowrap font-mono text-xs'
    },
    {
      header: '机构名称',
      accessor: (row) => row.col_participant_name || '-',
      key: 'col_participant_name',
      width: 160
    },
    {
      header: '持股量(股)',
      accessor: (row) => formatNumber(row.col_shareholding),
      key: 'col_shareholding',
      sortable: true,
      width: 130,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      header: '持股比例(%)',
      accessor: (row) => formatNumber(row.col_shareholding_percent, 2),
      key: 'col_shareholding_percent',
      sortable: true,
      width: 110,
      cellClassName: 'text-right whitespace-nowrap'
    }
  ], [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="中央结算系统持股明细"
        description="获取中央结算系统机构席位持股明细，数据覆盖全历史，根据交易所披露时间，当日数据在下一交易日早上9点前完成"
        details={<>
          <div>接口：ccass_hold_detail</div>
          <a href="https://tushare.pro/document/2?doc_id=274" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="CCASS持股明细"
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
                placeholder="如 00960.HK"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value.toUpperCase())}
                className="w-full sm:w-40"
              />
            </div>
            <div className="space-y-1 w-full sm:w-auto">
              <Label htmlFor="participant_id">参与者编号</Label>
              <Input
                id="participant_id"
                placeholder="如 C00001"
                value={participantId}
                onChange={(e) => setParticipantId(e.target.value)}
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
                  <div>
                    <div className="font-semibold text-sm">{row.name || row.ts_code}</div>
                    <div className="text-xs text-muted-foreground font-mono">{row.col_participant_id}{row.col_participant_name ? ` · ${row.col_participant_name}` : ''}</div>
                  </div>
                  <span className="text-xs text-muted-foreground">{row.trade_date}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">股票代码</span>
                  <span className="font-medium font-mono text-xs">{row.ts_code}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">持股量</span>
                  <span className="font-medium">{formatNumber(row.col_shareholding)} 股</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">持股比例</span>
                  <span className="font-medium">{formatNumber(row.col_shareholding_percent, 2)}%</span>
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
        onConfirm={handleCustomSyncConfirm}
        title="同步中央结算系统持股明细"
        description="请至少填写一个参数（股票代码、港交所代码、交易日期或日期范围）。消耗 8000 积分/次，单次最大 6000 条。"
        disabled={dp.syncing || (!syncTsCode.trim() && !syncHkCode.trim() && !syncTradeDate && !dp.syncStartDate && !dp.syncEndDate)}
      >
        <div className="space-y-4 py-4">
          <div className="space-y-1">
            <Label>股票代码</Label>
            <Input
              placeholder="如：00960.HK"
              value={syncTsCode}
              onChange={(e) => setSyncTsCode(e.target.value.toUpperCase())}
            />
            <p className="text-xs text-muted-foreground">港股代码格式，如：00960.HK</p>
          </div>
          <div className="space-y-1">
            <Label>港交所代码</Label>
            <Input
              placeholder="如：95009"
              value={syncHkCode}
              onChange={(e) => setSyncHkCode(e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label>交易日期（可选）</Label>
            <DatePicker date={syncTradeDate} onDateChange={setSyncTradeDate} placeholder="选择交易日期" />
          </div>
          <div className="space-y-1">
            <Label>日期范围（可选）</Label>
            <div className="flex gap-2 items-center">
              <DatePicker date={dp.syncStartDate} onDateChange={dp.setSyncStartDate} placeholder="开始日期" />
              <span className="text-muted-foreground">至</span>
              <DatePicker date={dp.syncEndDate} onDateChange={dp.setSyncEndDate} placeholder="结束日期" />
            </div>
          </div>
        </div>
      </SyncDialog>
    </div>
  )
}
