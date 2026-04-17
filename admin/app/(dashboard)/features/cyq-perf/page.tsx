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
import { cyqPerfApi, type CyqPerfData, type CyqPerfStatistics } from '@/lib/api'
import { apiClient } from '@/lib/api-client'
import { toDateStr } from '@/lib/date-utils'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { RefreshCw, TrendingUp, TrendingDown, BarChart3, DollarSign, ListFilter } from 'lucide-react'

// ============== 页面组件 ==============

export default function CyqPerfPage() {
  // 查询条件
  const [tsCode, setTsCode] = useState('')
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)

  // 同步弹窗额外字段
  const [syncTsCode, setSyncTsCode] = useState('')

  const dp = useDataPage<CyqPerfData, CyqPerfStatistics>({
    apiCall: (params) => cyqPerfApi.getData(params),
    syncFn: (params) => cyqPerfApi.syncAsync(params as { ts_code: string }),
    taskName: 'tasks.sync_cyq_perf',
    bulkOps: {
      tableKey: 'cyq_perf',
      syncFn: (params) => apiClient.post('/api/cyq-perf/sync-async', null, { params }),
      taskName: 'tasks.sync_cyq_perf',
    },
    paginationMode: 'page',
    pageSize: 100,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tsCode) params.ts_code = tsCode
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      return params
    },
    onBackfillDate: (dateStr) => {
      if (!tradeDate) setTradeDate(new Date(dateStr + 'T00:00:00'))
    },
    syncSuccessMessage: '筹码及胜率数据同步完成',
  })

  // 覆盖同步确认：需要额外传 syncTsCode（必填）
  const handleCustomSyncConfirm = async () => {
    if (!syncTsCode) {
      const { toast } = await import('sonner')
      toast.error('请输入股票代码')
      return
    }
    dp.setSyncDialogOpen(false)
    const params: Record<string, unknown> = { ts_code: syncTsCode }
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
        label: '平均胜率',
        value: `${s.avg_winner_rate?.toFixed(2) ?? 0}%`,
        subValue: '筛选范围内平均',
        icon: BarChart3,
        iconColor: 'text-muted-foreground',
      },
      {
        label: '最高胜率',
        value: <span className="text-red-600">{s.max_winner_rate?.toFixed(2) ?? 0}%</span>,
        subValue: '胜率最高值',
        icon: TrendingUp,
        iconColor: 'text-red-600',
      },
      {
        label: '最低胜率',
        value: <span className="text-green-600">{s.min_winner_rate?.toFixed(2) ?? 0}%</span>,
        subValue: '胜率最低值',
        icon: TrendingDown,
        iconColor: 'text-green-600',
      },
      {
        label: '加权均成本',
        value: `${s.avg_cost?.toFixed(2) ?? 0}`,
        subValue: '平均加权成本',
        icon: DollarSign,
        iconColor: 'text-muted-foreground',
      },
    ]
  }, [dp.statistics])

  const columns = useMemo((): Column<CyqPerfData>[] => [
    {
      header: '股票代码',
      accessor: (row) => row.ts_code,
      key: 'ts_code',
      width: 110,
      cellClassName: 'whitespace-nowrap font-mono text-xs'
    },
    {
      header: '交易日期',
      accessor: (row) => {
        const d = row.trade_date
        if (!d || d.length !== 8) return d
        return `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`
      },
      key: 'trade_date',
      sortable: true,
      width: 100,
      cellClassName: 'whitespace-nowrap'
    },
    {
      header: '历史最低',
      accessor: (row) => row.his_low?.toFixed(2) ?? '-',
      key: 'his_low',
      width: 85,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      header: '历史最高',
      accessor: (row) => row.his_high?.toFixed(2) ?? '-',
      key: 'his_high',
      width: 85,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      header: '5%成本',
      accessor: (row) => row.cost_5pct?.toFixed(2) ?? '-',
      key: 'cost_5pct',
      width: 75,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      header: '15%成本',
      accessor: (row) => row.cost_15pct?.toFixed(2) ?? '-',
      key: 'cost_15pct',
      width: 80,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      header: '50%成本',
      accessor: (row) => row.cost_50pct?.toFixed(2) ?? '-',
      key: 'cost_50pct',
      sortable: true,
      width: 80,
      cellClassName: 'text-right whitespace-nowrap font-semibold'
    },
    {
      header: '85%成本',
      accessor: (row) => row.cost_85pct?.toFixed(2) ?? '-',
      key: 'cost_85pct',
      width: 80,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      header: '95%成本',
      accessor: (row) => row.cost_95pct?.toFixed(2) ?? '-',
      key: 'cost_95pct',
      width: 80,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      header: '加权均成本',
      accessor: (row) => row.weight_avg?.toFixed(2) ?? '-',
      key: 'weight_avg',
      sortable: true,
      width: 95,
      cellClassName: 'text-right whitespace-nowrap font-semibold'
    },
    {
      header: '胜率(%)',
      accessor: (row) => {
        const rate = row.winner_rate
        if (rate === null || rate === undefined) return <span>-</span>
        const cls = rate >= 60 ? 'text-red-600 font-semibold' : rate <= 40 ? 'text-green-600 font-semibold' : 'font-semibold'
        return <span className={cls}>{rate.toFixed(2)}%</span>
      },
      key: 'winner_rate',
      sortable: true,
      width: 85,
      cellClassName: 'text-right whitespace-nowrap'
    }
  ], [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="每日筹码及胜率"
        description="获取A股每日筹码平均成本和胜率情况，每天18~19点左右更新，数据从2018年开始"
        details={<>
          <div>接口：cyq_perf</div>
          <a href="https://tushare.pro/document/2?doc_id=293" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="每日筹码及胜率"
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
                  <span className="font-semibold text-sm">{row.ts_code}</span>
                  <span className="text-xs text-muted-foreground">
                    {row.trade_date?.length === 8
                      ? `${row.trade_date.slice(0,4)}-${row.trade_date.slice(4,6)}-${row.trade_date.slice(6,8)}`
                      : row.trade_date}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                  <div className="flex justify-between"><span className="text-muted-foreground">50%成本</span><span className="font-medium">{row.cost_50pct?.toFixed(2) ?? '-'}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">加权均</span><span className="font-medium">{row.weight_avg?.toFixed(2) ?? '-'}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">胜率</span>
                    <span className={`font-semibold ${(row.winner_rate ?? 0) >= 60 ? 'text-red-600' : (row.winner_rate ?? 0) <= 40 ? 'text-green-600' : ''}`}>
                      {row.winner_rate?.toFixed(2) ?? '-'}%
                    </span>
                  </div>
                  <div className="flex justify-between"><span className="text-muted-foreground">历史区间</span><span>{row.his_low?.toFixed(2) ?? '-'} - {row.his_high?.toFixed(2) ?? '-'}</span></div>
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
        title="同步筹码及胜率数据"
        description="从Tushare接口同步数据（5000积分/次）。股票代码必填。"
        disabled={dp.syncing || !syncTsCode}
      >
        <div className="space-y-4 py-4">
          <div className="space-y-1">
            <Label>股票代码 *</Label>
            <Input
              placeholder="如 000001.SZ"
              value={syncTsCode}
              onChange={(e) => setSyncTsCode(e.target.value.toUpperCase())}
            />
          </div>
          <div className="space-y-1">
            <Label>开始日期（可选）</Label>
            <DatePicker date={dp.syncStartDate} onDateChange={dp.setSyncStartDate} placeholder="留空从最早日期开始" />
          </div>
          <div className="space-y-1">
            <Label>结束日期（可选）</Label>
            <DatePicker date={dp.syncEndDate} onDateChange={dp.setSyncEndDate} placeholder="留空同步到最新日期" />
          </div>
        </div>
      </SyncDialog>
    </div>
  )
}
