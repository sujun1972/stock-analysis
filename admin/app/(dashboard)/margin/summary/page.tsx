'use client'

import { useState, useEffect, useMemo, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { marginApi } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, TrendingDown, DollarSign, BarChart3, ListFilter } from 'lucide-react'

// ============== 类型定义 ==============

interface MarginData {
  trade_date: string
  exchange_id: string
  rzye: number | null
  rzmre: number | null
  rzche: number | null
  rqye: number | null
  rqmcl: number | null
  rzrqye: number | null
  rqyl: number | null
}

interface Statistics {
  avg_rzrqye: number
  total_rzrqye: number
  max_rzye: number
  max_rqye: number
}

const PAGE_SIZE = 100

const toDateStr = (date: Date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

// ============== 页面组件 ==============

export default function MarginSummaryPage() {
  const [data, setData] = useState<MarginData[]>([])
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [exchangeId, setExchangeId] = useState<string>('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc' | null>(null)

  // 同步弹窗状态
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()

  // 从 task store 实时派生——不用本地 useState
  const syncing = isTaskRunning('tasks.sync_margin')

  // 加载主数据（含统计，一次返回）
  const loadData = async (
    targetPage: number = page,
    overrideSortKey?: string | null,
    overrideSortDir?: 'asc' | 'desc' | null
  ) => {
    setIsLoading(true)
    try {
      const params: any = {
        page: targetPage,
        page_size: PAGE_SIZE,
        sort_by: (overrideSortKey !== undefined ? overrideSortKey : sortKey) ?? undefined,
        sort_order: (overrideSortDir !== undefined ? overrideSortDir : sortDirection) ?? undefined,
      }
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      if (exchangeId) params.exchange_id = exchangeId

      const response = await marginApi.getMargin(params)

      if (response.code === 200 && response.data) {
        setData(response.data.data || [])
        setTotal(response.data.total || 0)
        setStatistics(response.data.statistics || null)
        setPage(targetPage)
      } else {
        toast.error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      toast.error(err.message || '加载数据失败')
    } finally {
      setIsLoading(false)
    }
  }

  // 初始加载：只跑一次
  useEffect(() => {
    loadData(1).catch(() => {})
  }, [])

  const handleQuery = () => {
    loadData(1).catch(() => {})
  }

  // 同步确认
  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    try {
      const params: { start_date?: string; end_date?: string } = {}
      if (syncStartDate) params.start_date = toDateStr(syncStartDate)
      if (syncEndDate) params.end_date = toDateStr(syncEndDate)

      const response = await marginApi.syncMarginAsync(params)

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
            toast.success('数据同步完成')
          }
          unregisterCompletionCallback(taskId, completionCallback)
          activeCallbacksRef.current.delete(taskId)
        }
        activeCallbacksRef.current.set(taskId, completionCallback)
        registerCompletionCallback(taskId, completionCallback)

        triggerPoll()
        toast.success(response.message || '同步任务已提交')
      } else {
        toast.error(response.message || '提交同步任务失败')
      }
    } catch (err: any) {
      toast.error(err.message || '同步失败')
    }
  }

  // 组件卸载时清理回调
  useEffect(() => {
    return () => {
      // eslint-disable-next-line react-hooks/exhaustive-deps
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
    }
  }, [unregisterCompletionCallback])

  // 格式化日期
  const formatDate = (dateStr: string) => {
    if (!dateStr || dateStr.length !== 8) return dateStr || '-'
    return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
  }

  // 格式化金额（元转亿元）
  const toYi = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '-'
    return (value / 100000000).toFixed(2) + '亿'
  }

  // 格式化数量
  const toWan = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '-'
    return value.toFixed(2) + '万股'
  }

  // 表格列定义
  const columns: Column<MarginData>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => formatDate(row.trade_date),
      width: 110,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'exchange_id',
      header: '交易所',
      accessor: (row) => row.exchange_id,
      width: 90,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'rzrqye',
      header: '融资融券余额',
      accessor: (row) => toYi(row.rzrqye),
      width: 130,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rzye',
      header: '融资余额',
      accessor: (row) => toYi(row.rzye),
      width: 120,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rzmre',
      header: '融资买入',
      accessor: (row) => toYi(row.rzmre),
      hideOnMobile: true,
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rzche',
      header: '融资偿还',
      accessor: (row) => toYi(row.rzche),
      hideOnMobile: true,
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rqye',
      header: '融券余额',
      accessor: (row) => toYi(row.rqye),
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rqmcl',
      header: '融券卖出量',
      accessor: (row) => toWan(row.rqmcl),
      hideOnMobile: true,
      width: 120,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rqyl',
      header: '融券余量',
      accessor: (row) => toWan(row.rqyl),
      hideOnMobile: true,
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
  ], [])

  // 移动端卡片视图
  const mobileCard = (item: MarginData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-center mb-2">
        <span className="font-semibold text-base">{formatDate(item.trade_date)}</span>
        <span className="text-sm font-medium text-blue-600 dark:text-blue-400">{item.exchange_id}</span>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">融资融券余额</span>
          <span className="font-medium">{toYi(item.rzrqye)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">融资余额</span>
          <span>{toYi(item.rzye)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">融券余额</span>
          <span>{toYi(item.rqye)}</span>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="融资融券交易汇总"
        description="按交易所统计的融资融券交易汇总数据"
        details={<>
          <div>接口：margin</div>
          <a href="https://tushare.pro/document/2?doc_id=58" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
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
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>同步融资融券汇总数据</DialogTitle>
            <DialogDescription>选择同步日期范围（留空则同步最新交易日数据）。</DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">开始日期（可选）</label>
              <DatePicker date={syncStartDate} onDateChange={setSyncStartDate} placeholder="留空同步最新交易日" />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">结束日期（可选）</label>
              <DatePicker date={syncEndDate} onDateChange={setSyncEndDate} placeholder="留空同步最新交易日" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncDialogOpen(false)}>取消</Button>
            <Button onClick={handleSyncConfirm} disabled={syncing}>确认同步</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 统计卡片 — 左文字右图标 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">平均融资融券余额</p>
                  <p className="text-xl sm:text-2xl font-bold mt-1">{toYi(statistics.avg_rzrqye)}</p>
                  <p className="text-xs text-muted-foreground mt-1">所选时间段平均值</p>
                </div>
                <BarChart3 className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600 shrink-0" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">累计融资融券余额</p>
                  <p className="text-xl sm:text-2xl font-bold mt-1">{toYi(statistics.total_rzrqye)}</p>
                  <p className="text-xs text-muted-foreground mt-1">所选时间段累计值</p>
                </div>
                <DollarSign className="h-6 w-6 sm:h-8 sm:w-8 text-orange-600 shrink-0" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">最大融资余额</p>
                  <p className="text-xl sm:text-2xl font-bold mt-1 text-red-600">{toYi(statistics.max_rzye)}</p>
                  <p className="text-xs text-muted-foreground mt-1">所选时间段最大值</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-red-600 shrink-0" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">最大融券余额</p>
                  <p className="text-xl sm:text-2xl font-bold mt-1 text-green-600">{toYi(statistics.max_rqye)}</p>
                  <p className="text-xs text-muted-foreground mt-1">所选时间段最大值</p>
                </div>
                <TrendingDown className="h-6 w-6 sm:h-8 sm:w-8 text-green-600 shrink-0" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

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
              <label className="text-sm font-medium mb-1 block">开始日期</label>
              <DatePicker date={startDate} onDateChange={setStartDate} placeholder="选择开始日期" />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">结束日期</label>
              <DatePicker date={endDate} onDateChange={setEndDate} placeholder="选择结束日期" />
            </div>
            <div className="w-full sm:w-44">
              <label className="text-sm font-medium mb-1 block">交易所</label>
              <Select value={exchangeId || 'ALL'} onValueChange={(v) => setExchangeId(v === 'ALL' ? '' : v)}>
                <SelectTrigger>
                  <SelectValue placeholder="选择交易所" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="SSE">上交所 (SSE)</SelectItem>
                  <SelectItem value="SZSE">深交所 (SZSE)</SelectItem>
                  <SelectItem value="BSE">北交所 (BSE)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <Button onClick={handleQuery} disabled={isLoading} className="flex-1 sm:flex-none">
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
            data={data}
            loading={isLoading}
            mobileCard={mobileCard}
            emptyMessage="暂无融资融券汇总数据"
            tableClassName="table-fixed w-full [&_th]:border-r [&_td]:border-r [&_th:last-child]:border-r-0 [&_td:last-child]:border-r-0 [&_th]:!text-center"
            sort={{
              key: sortKey,
              direction: sortDirection,
              onSort: (key, direction) => {
                const newKey = direction ? key : null
                setSortKey(newKey)
                setSortDirection(direction)
                loadData(1, newKey, direction)
              }
            }}
            pagination={{
              page,
              pageSize: PAGE_SIZE,
              total,
              onPageChange: (newPage) => loadData(newPage)
            }}
          />
        </CardContent>
      </Card>
    </div>
  )
}
