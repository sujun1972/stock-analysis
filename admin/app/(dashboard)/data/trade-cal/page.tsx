'use client'

import { useState, useEffect, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { toast } from 'sonner'
import { RefreshCw, Calendar, TrendingUp, BarChart2, CheckCircle } from 'lucide-react'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { tradeCalApi } from '@/lib/api'
import type { TradeCalData, TradeCalStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'

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
  const [data, setData] = useState<TradeCalData[]>([])
  const [statistics, setStatistics] = useState<TradeCalStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const pageSize = 30

  const [exchange, setExchange] = useState('SSE')
  const [isOpen, setIsOpen] = useState<string>('all')
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)

  // 同步弹窗独立参数（与查询筛选解耦）
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncExchange, setSyncExchange] = useState<string>('SSE')
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  const syncing = isTaskRunning('tasks.sync_trade_cal')

  const loadData = async (currentPage = page) => {
    setIsLoading(true)
    try {
      const params: any = {
        exchange,
        page: currentPage,
        page_size: pageSize,
      }
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]
      if (isOpen !== 'all') params.is_open = isOpen

      const response = await tradeCalApi.getData(params)
      if (response.code === 200 && response.data) {
        setData(response.data.items)
        setTotal(response.data.total)
      }
    } catch {
      toast.error('加载数据失败')
    } finally {
      setIsLoading(false)
    }
  }

  const loadStatistics = async () => {
    try {
      const response = await tradeCalApi.getStatistics({ exchange })
      if (response.code === 200 && response.data) {
        setStatistics(response.data)
      }
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    loadData(1)
    setPage(1)
    loadStatistics()
  }, [exchange])

  const handleQuery = () => {
    setPage(1)
    loadData(1)
  }

  const handlePageChange = (newPage: number) => {
    setPage(newPage)
    loadData(newPage)
  }

  const toDateStr = (date: Date) => {
    const y = date.getFullYear()
    const m = String(date.getMonth() + 1).padStart(2, '0')
    const d = String(date.getDate()).padStart(2, '0')
    return `${y}-${m}-${d}`
  }

  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    try {
      // 使用同步弹窗独立参数，不传查询筛选日期
      const params: any = {}
      if (syncExchange) params.exchange = syncExchange
      if (syncStartDate) params.start_date = toDateStr(syncStartDate)
      if (syncEndDate) params.end_date = toDateStr(syncEndDate)

      const response = await tradeCalApi.syncAsync(params)
      if (response.code === 200 && response.data) {
        const taskId = response.data.celery_task_id
        addTask({
          taskId,
          taskName: response.data.task_name,
          displayName: response.data.display_name,
          taskType: 'data_sync',
          status: 'running',
          progress: 0,
          startTime: Date.now()
        })

        const completionCallback = (task: any) => {
          if (task.status === 'success') {
            loadData(1).catch(() => {})
            loadStatistics().catch(() => {})
            setPage(1)
            toast.success('交易日历同步完成')
          }
          unregisterCompletionCallback(taskId, completionCallback)
          activeCallbacksRef.current.delete(taskId)
        }
        activeCallbacksRef.current.set(taskId, completionCallback)
        registerCompletionCallback(taskId, completionCallback)

        triggerPoll()
        toast.success('同步任务已提交')
      }
    } catch {
      toast.error('提交同步任务失败')
    }
  }

  useEffect(() => {
    return () => {
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
    }
  }, [])

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
          <Button onClick={() => setSyncDialogOpen(true)} disabled={syncing}>
            {syncing ? (
              <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
            ) : (
              <><RefreshCw className="h-4 w-4 mr-1" />同步数据</>
            )}
          </Button>
        }
      />

      {/* 同步弹窗 */}
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
            <Button onClick={handleSyncConfirm} disabled={syncing}>确认同步</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">总天数</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.total_days ?? 0}</p>
                  <p className="text-xs text-muted-foreground mt-1">{statistics.year} 年</p>
                </div>
                <Calendar className="h-6 w-6 sm:h-8 sm:w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">交易日</p>
                  <p className="text-xl sm:text-2xl font-bold text-green-600">{statistics.trading_days ?? 0}</p>
                  <p className="text-xs text-muted-foreground mt-1">开市天数</p>
                </div>
                <CheckCircle className="h-6 w-6 sm:h-8 sm:w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">休市天数</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.non_trading_days ?? 0}</p>
                  <p className="text-xs text-muted-foreground mt-1">含周末节假日</p>
                </div>
                <BarChart2 className="h-6 w-6 sm:h-8 sm:w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">交易日占比</p>
                  <p className="text-xl sm:text-2xl font-bold text-blue-600">{statistics.trading_day_ratio ?? 0}%</p>
                  <p className="text-xs text-muted-foreground mt-1">全年交易占比</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选区域 */}
      <Card>
        <CardHeader><CardTitle>数据查询</CardTitle></CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3 items-end">
            <div className="flex flex-col gap-1">
              <span className="text-xs text-muted-foreground">交易所</span>
              <Select value={exchange} onValueChange={setExchange}>
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
            <Button onClick={handleQuery}>查询</Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="pt-4">
          <DataTable
            columns={columns}
            data={data}
            loading={isLoading}
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: handlePageChange
            }}
            mobileCard={(item) => (
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
            )}
          />
        </CardContent>
      </Card>
    </div>
  )
}
