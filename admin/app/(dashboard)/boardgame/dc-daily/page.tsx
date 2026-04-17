'use client'

import { useState, useMemo } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useDataPage } from '@/hooks/useDataPage'
import { dcDailyApi, type DcDailyData, type DcDailyStatistics } from '@/lib/api'
import { apiClient } from '@/lib/api-client'
import { toDateStr } from '@/lib/date-utils'
import { pctChangeColor } from '@/lib/utils'
import { RefreshCw, Database, Calendar, Layers, TrendingUp, AlertTriangle, ListFilter } from 'lucide-react'

const IDX_TYPE_OPTIONS = [
  { value: '概念板块', label: '概念板块' },
  { value: '行业板块', label: '行业板块' },
  { value: '地域板块', label: '地域板块' },
]

export default function DcDailyPage() {
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)

  // 同步对话框状态（自定义，不使用 SyncDialog）
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncTsCode, setSyncTsCode] = useState<string>('')
  const [syncIdxType, setSyncIdxType] = useState<string>('')
  const [syncTradeDate, setSyncTradeDate] = useState<Date | undefined>(undefined)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const dp = useDataPage<DcDailyData, DcDailyStatistics>({
    apiCall: (params) => dcDailyApi.getData(params),
    statisticsCall: (params) => dcDailyApi.getStatistics(params),
    syncFn: (params) => dcDailyApi.syncAsync(params),
    taskName: 'tasks.sync_dc_daily',
    bulkOps: {
      tableKey: 'dc_daily',
      syncFn: (params) => apiClient.post('/api/dc-daily/sync-async', null, { params }),
      taskName: 'tasks.sync_dc_daily',
    },
    paginationMode: 'page',
    pageSize: 100,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      return params
    },
    onBackfillDate: (dateStr) => setTradeDate(new Date(dateStr + 'T00:00:00')),
  })

  // 自定义同步处理（弹窗有额外字段 ts_code, idx_type 等）
  const handleSync = async () => {
    setSyncDialogOpen(false)
    try {
      const params: Record<string, unknown> = {}
      if (syncTsCode.trim()) params.ts_code = syncTsCode.trim()
      if (syncIdxType) params.idx_type = syncIdxType
      if (syncTradeDate) params.trade_date = toDateStr(syncTradeDate)
      if (syncStartDate) params.start_date = toDateStr(syncStartDate)
      if (syncEndDate) params.end_date = toDateStr(syncEndDate)

      await dp.handleSyncDirect(params)
    } catch (err: any) {
      // handleSyncDirect already handles errors via toast
    }
  }

  const formatPct = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '-'
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  const formatAmount = (value: number | null | undefined) =>
    value == null ? '-' : (value / 100000000).toFixed(2) + '亿'

  const formatVol = (value: number | null | undefined) =>
    value == null ? '-' : (value / 10000).toFixed(0) + '万手'

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      { label: '总记录数', value: (s.total_records ?? 0).toLocaleString(), icon: Database, iconColor: 'text-blue-600' },
      { label: '板块数量', value: (s.board_count ?? 0).toLocaleString(), icon: Layers, iconColor: 'text-purple-600' },
      { label: '交易日数', value: (s.date_count ?? 0).toLocaleString(), icon: Calendar, iconColor: 'text-orange-600' },
      {
        label: '平均涨跌幅',
        value: <span className={pctChangeColor(s.avg_pct_change)}>{s.avg_pct_change != null ? formatPct(s.avg_pct_change) : '-'}</span>,
        subValue: `最新: ${s.latest_date || '-'}`,
        icon: TrendingUp,
        iconColor: 'text-green-600',
      },
    ]
  }, [dp.statistics])

  const columns: Column<DcDailyData>[] = [
    {
      key: 'ts_code',
      header: '板块',
      accessor: (row) => row.board_name ? `${row.board_name}[${row.ts_code}]` : row.ts_code,
      width: 200,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'close',
      header: '收盘',
      accessor: (row) => (
        <span className={pctChangeColor(row.pct_change)}>
          {row.close != null ? row.close.toFixed(2) : '-'}
        </span>
      ),
      width: 80,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'pct_change',
      header: '涨跌幅%',
      accessor: (row) => (
        <span className={pctChangeColor(row.pct_change)}>
          {formatPct(row.pct_change)}
        </span>
      ),
      width: 100,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'change',
      header: '涨跌点',
      accessor: (row) => (
        <span className={pctChangeColor(row.change)}>
          {row.change != null ? (row.change >= 0 ? '+' : '') + row.change.toFixed(2) : '-'}
        </span>
      ),
      width: 90,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'open',
      header: '开盘',
      accessor: (row) => row.open != null ? row.open.toFixed(2) : '-',
      width: 80,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'high',
      header: '最高',
      accessor: (row) => (
        <span className="text-red-600">{row.high != null ? row.high.toFixed(2) : '-'}</span>
      ),
      width: 80,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'low',
      header: '最低',
      accessor: (row) => (
        <span className="text-green-600">{row.low != null ? row.low.toFixed(2) : '-'}</span>
      ),
      width: 80,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'amount',
      header: '成交额',
      accessor: (row) => (
        <span className={pctChangeColor(row.pct_change)}>{formatAmount(row.amount)}</span>
      ),
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'vol',
      header: '成交量',
      accessor: (row) => formatVol(row.vol),
      width: 100,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'swing',
      header: '振幅%',
      accessor: (row) => row.swing != null ? `${row.swing.toFixed(2)}%` : '-',
      width: 80,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'turnover_rate',
      header: '换手率%',
      accessor: (row) => (
        <span className={pctChangeColor(row.pct_change)}>
          {row.turnover_rate != null ? `${row.turnover_rate.toFixed(2)}%` : '-'}
        </span>
      ),
      width: 90,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
  ]

  const mobileCard = (item: DcDailyData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div className="font-semibold text-base">
          {item.board_name ? `${item.board_name}[${item.ts_code}]` : item.ts_code}
        </div>
        <div className="text-right">
          <div className={`font-bold ${pctChangeColor(item.pct_change)}`}>
            {formatPct(item.pct_change)}
          </div>
          <div className="text-sm text-gray-500">{item.trade_date}</div>
        </div>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">收盘/开盘:</span>
          <span className={pctChangeColor(item.pct_change)}>
            {item.close != null ? item.close.toFixed(2) : '-'} / {item.open != null ? item.open.toFixed(2) : '-'}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">最高/最低:</span>
          <span>
            <span className="text-red-600">{item.high != null ? item.high.toFixed(2) : '-'}</span>
            <span className="text-gray-400 mx-1">/</span>
            <span className="text-green-600">{item.low != null ? item.low.toFixed(2) : '-'}</span>
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">成交额:</span>
          <span>{formatAmount(item.amount)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">换手率:</span>
          <span>{item.turnover_rate != null ? `${item.turnover_rate.toFixed(2)}%` : '-'}</span>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="东财概念板块行情"
        description="获取东财概念板块、行业指数板块、地域板块行情数据，历史数据开始于2020年"
        details={<>
          <div>接口：dc_daily</div>
          <a href="https://tushare.pro/document/2?doc_id=382" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <div className="flex gap-2">
            <Button onClick={() => setSyncDialogOpen(true)} disabled={dp.syncing}>
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
              tableName="东财概念板块行情"
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

      {/* 同步参数对话框（自定义） */}
      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>同步东财概念板块行情</DialogTitle>
            <DialogDescription>
              配置同步参数后提交后台任务。所有参数均为可选。
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="flex items-start gap-2 p-3 bg-yellow-50 dark:bg-yellow-950/20 rounded-md border border-yellow-200 dark:border-yellow-800">
              <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-yellow-700 dark:text-yellow-400">
                每次调用消耗 <strong>6000</strong> 积分，单次最大返回 2000 条数据，请谨慎操作。
              </p>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">板块类型（可选）</label>
              <Select value={syncIdxType || 'ALL'} onValueChange={(v) => setSyncIdxType(v === 'ALL' ? '' : v)}>
                <SelectTrigger>
                  <SelectValue placeholder="全部类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部类型</SelectItem>
                  {IDX_TYPE_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">板块代码（可选）</label>
              <Input
                placeholder="如：BK0001"
                value={syncTsCode}
                onChange={(e) => setSyncTsCode(e.target.value)}
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">指定交易日期（可选）</label>
              <DatePicker date={syncTradeDate} onDateChange={setSyncTradeDate} />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">开始日期（可选）</label>
                <DatePicker date={syncStartDate} onDateChange={setSyncStartDate} />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">结束日期（可选）</label>
                <DatePicker date={syncEndDate} onDateChange={setSyncEndDate} />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncDialogOpen(false)}>取消</Button>
            <Button onClick={handleSync} disabled={dp.syncing}>
              {dp.syncing ? (
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />提交中...</>
              ) : '提交同步任务'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
