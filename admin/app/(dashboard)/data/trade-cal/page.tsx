'use client'

import { useState, useMemo } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useDataPage } from '@/hooks/useDataPage'
import { tradeCalApi } from '@/lib/api'
import type { TradeCalData, TradeCalStatistics } from '@/lib/api'
import { axiosInstance } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { RefreshCw, Calendar, TrendingUp, BarChart2, CheckCircle } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

const EXCHANGE_OPTIONS = [
  { value: 'SSE', label: 'SSE 上交所' },
  { value: 'SZSE', label: 'SZSE 深交所' },
  { value: 'CFFEX', label: 'CFFEX 中金所' },
  { value: 'SHFE', label: 'SHFE 上期所' },
  { value: 'CZCE', label: 'CZCE 郑商所' },
  { value: 'DCE', label: 'DCE 大商所' },
  { value: 'INE', label: 'INE 上能源' },
]

export default function TradeCalPage() {
  const [exchange, setExchange] = useState('SSE')
  const [isOpen, setIsOpen] = useState<string>('all')
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)

  // 同步弹窗独立参数（与查询筛选解耦）
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncExchange, setSyncExchange] = useState<string>('SSE')
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const dp = useDataPage<TradeCalData, TradeCalStatistics>({
    apiCall: (params) => tradeCalApi.getData(params),
    statisticsCall: (params) => tradeCalApi.getStatistics(params),
    syncFn: (params) => tradeCalApi.syncAsync(params),
    taskName: 'tasks.sync_trade_cal',
    bulkOps: {
      tableKey: 'trade_cal',
      syncFn: (params) => axiosInstance.post('/api/trade-cal/sync-async', null, { params }),
      taskName: 'tasks.sync_trade_cal',
    },
    paginationMode: 'page',
    pageSize: 30,
    buildParams: () => {
      const params: Record<string, unknown> = { exchange }
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      if (isOpen !== 'all') params.is_open = isOpen
      return params
    },
    syncSuccessMessage: '交易日历同步完成',
  })

  // 自定义同步处理（使用独立参数，不传查询筛选日期）
  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    const params: Record<string, unknown> = {}
    if (syncExchange) params.exchange = syncExchange
    if (syncStartDate) params.start_date = toDateStr(syncStartDate)
    if (syncEndDate) params.end_date = toDateStr(syncEndDate)
    await dp.handleSyncDirect(params)
  }

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      { label: '总天数', value: s.total_days ?? 0, subValue: `${s.year} 年`, icon: Calendar, iconColor: 'text-blue-600' },
      { label: '交易日', value: <span className="text-green-600">{s.trading_days ?? 0}</span>, subValue: '开市天数', icon: CheckCircle, iconColor: 'text-green-500' },
      { label: '休市天数', value: s.non_trading_days ?? 0, subValue: '含周末节假日', icon: BarChart2, iconColor: 'text-gray-500' },
      { label: '交易日占比', value: <span className="text-blue-600">{s.trading_day_ratio ?? 0}%</span>, subValue: '全年交易占比', icon: TrendingUp, iconColor: 'text-blue-500' },
    ]
  }, [dp.statistics])

  const columns: Column<TradeCalData>[] = [
    {
      key: 'exchange',
      header: '交易所',
      width: '100px',
      accessor: (row) => (
        <Badge variant="outline">{row.exchange}</Badge>
      )
    },
    {
      key: 'cal_date',
      header: '日期',
      width: '130px',
    },
    {
      key: 'is_open',
      header: '是否交易',
      width: '100px',
      accessor: (row) => (
        <Badge variant={row.is_open === 1 ? 'default' : 'secondary'}>
          {row.is_open === 1 ? '交易日' : '休市'}
        </Badge>
      )
    },
    {
      key: 'pretrade_date',
      header: '上一交易日',
      accessor: (row) => row.pretrade_date ?? '-'
    },
  ]

  const mobileCard = (item: TradeCalData) => (
    <div className="p-4 space-y-2">
      <div className="flex justify-between items-center">
        <span className="font-medium">{item.cal_date}</span>
        <span>{item.is_open === 1
          ? <span className="text-green-600 text-sm font-medium">交易日</span>
          : <span className="text-muted-foreground text-sm">休市</span>
        }</span>
      </div>
      <div className="flex justify-between text-sm text-muted-foreground">
        <span>交易所：{item.exchange}</span>
        <span>上一交易日：{item.pretrade_date ?? '-'}</span>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="交易日历"
        description="获取各大交易所交易日历数据，默认提取的是上交所"
        details={
          <>
            <div>接口：trade_cal</div>
            <a
              href="https://tushare.pro/document/2?doc_id=26"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-500 underline"
            >
              查看文档
            </a>
          </>
        }
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
              tableName="交易日历"
            />
          </div>
        }
      />

      {/* 同步弹窗（自定义，含交易所选择） */}
      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>同步交易日历</DialogTitle>
            <DialogDescription>选择要同步的交易所和日期范围（日期留空则同步当年数据）。</DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">交易所</label>
              <Select value={syncExchange} onValueChange={setSyncExchange}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {EXCHANGE_OPTIONS.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">开始日期（可选）</label>
              <DatePicker date={syncStartDate} onDateChange={setSyncStartDate} placeholder="留空同步当年数据" />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">结束日期（可选）</label>
              <DatePicker date={syncEndDate} onDateChange={setSyncEndDate} placeholder="留空同步当年数据" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncDialogOpen(false)}>取消</Button>
            <Button onClick={handleSyncConfirm} disabled={dp.syncing}>确认同步</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <StatisticsCards
        items={statsCards}
        className="grid grid-cols-2 sm:grid-cols-4 gap-4"
      />

      {/* 筛选区域 */}
      <Card>
        <CardHeader><CardTitle>数据查询</CardTitle></CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted-foreground">交易所</span>
              <Select value={exchange} onValueChange={(v) => { setExchange(v); setTimeout(() => dp.handleQuery(), 0) }}>
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {EXCHANGE_OPTIONS.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted-foreground">是否交易</span>
              <Select value={isOpen} onValueChange={setIsOpen}>
                <SelectTrigger className="w-28">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部</SelectItem>
                  <SelectItem value="1">交易日</SelectItem>
                  <SelectItem value="0">休市</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted-foreground">开始日期</span>
              <DatePicker date={startDate} onDateChange={setStartDate} />
            </div>
            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted-foreground">结束日期</span>
              <DatePicker date={endDate} onDateChange={setEndDate} />
            </div>
            <Button onClick={dp.handleQuery}>查询</Button>
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
    </div>
  )
}
