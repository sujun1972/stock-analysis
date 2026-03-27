'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { marginApi } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, TrendingDown, DollarSign, BarChart3 } from 'lucide-react'

// 数据类型定义
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

const toDateStr = (date: Date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

export default function MarginPage() {
  const [data, setData] = useState<MarginData[]>([])
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [exchangeId, setExchangeId] = useState<string>('')

  // 同步弹窗状态
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // 任务存储
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  // 从 task store 实时派生——不用本地 boolean
  const syncing = isTaskRunning('tasks.sync_margin')

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params: {
        start_date?: string
        end_date?: string
        exchange_id?: string
        page: number
        page_size: number
      } = { page, page_size: pageSize }

      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      if (exchangeId) params.exchange_id = exchangeId

      const response = await marginApi.getMargin(params)

      if (response.code === 200 && response.data) {
        setData(response.data.data)
        setTotal(response.data.total)
      } else {
        throw new Error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast.error('加载失败', { description: err.message || '无法加载融资融券交易汇总数据' })
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, startDate, endDate, exchangeId])

  // 加载统计数据
  const loadStatistics = useCallback(async () => {
    try {
      const params: { start_date?: string; end_date?: string } = {}
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)

      const response = await marginApi.getMarginStatistics(params)
      if (response.code === 200 && response.data) {
        setStatistics(response.data)
      }
    } catch (err: any) {
      console.error('加载统计数据失败:', err)
    }
  }, [startDate, endDate])

  // 初始加载
  useEffect(() => {
    loadData()
    loadStatistics()
  }, [loadData, loadStatistics])

  // 确认同步
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
            loadData().catch(() => {})
            loadStatistics().catch(() => {})
            toast.success('数据同步完成', { description: '融资融券交易汇总数据已更新' })
          } else if (task.status === 'failure') {
            toast.error('数据同步失败', { description: task.error || '同步过程中发生错误' })
          }
          unregisterCompletionCallback(taskId, completionCallback)
          activeCallbacksRef.current.delete(taskId)
        }

        activeCallbacksRef.current.set(taskId, completionCallback)
        registerCompletionCallback(taskId, completionCallback)
        triggerPoll()

        toast.success('任务已提交', {
          description: `"${response.data.display_name}" 已开始执行，可在任务面板查看进度`
        })
      } else {
        throw new Error(response.message || '同步失败')
      }
    } catch (err: any) {
      toast.error('同步失败', { description: err.message || '无法同步数据' })
    }
  }

  // 组件卸载时清理回调
  useEffect(() => {
    return () => {
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 格式化日期
  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-'
    return `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`
  }

  // 格式化金额（元转亿元）
  const formatAmount = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '-'
    return (value / 100000000).toFixed(2)
  }

  // 格式化数量（保留2位小数）
  const formatVolume = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '-'
    return value.toFixed(2)
  }

  // 表格列定义
  const columns: Column<MarginData>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => formatDate(row.trade_date)
    },
    {
      key: 'exchange_id',
      header: '交易所',
      accessor: (row) => row.exchange_id
    },
    {
      key: 'rzrqye',
      header: '融资融券余额(亿)',
      accessor: (row) => formatAmount(row.rzrqye),
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rzye',
      header: '融资余额(亿)',
      accessor: (row) => formatAmount(row.rzye),
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rzmre',
      header: '融资买入额(亿)',
      accessor: (row) => formatAmount(row.rzmre),
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rzche',
      header: '融资偿还额(亿)',
      accessor: (row) => formatAmount(row.rzche),
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rqye',
      header: '融券余额(亿)',
      accessor: (row) => formatAmount(row.rqye),
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rqmcl',
      header: '融券卖出量(万股)',
      accessor: (row) => formatVolume(row.rqmcl),
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rqyl',
      header: '融券余量(万股)',
      accessor: (row) => formatVolume(row.rqyl),
      cellClassName: 'text-right whitespace-nowrap'
    }
  ], [])

  // 移动端卡片渲染
  const mobileCard = useCallback((item: MarginData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">日期</span>
        <span className="font-medium">{formatDate(item.trade_date)}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">交易所</span>
        <span className="font-medium">{item.exchange_id}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">融资融券余额(亿)</span>
        <span className="font-medium">{formatAmount(item.rzrqye)}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">融资余额(亿)</span>
        <span>{formatAmount(item.rzye)}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">融券余额(亿)</span>
        <span>{formatAmount(item.rqye)}</span>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="融资融券交易汇总"
        description="查看和分析融资融券交易汇总数据（按交易所统计）"
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

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">平均融资融券余额</p>
                  <p className="text-2xl font-bold mt-1">{formatAmount(statistics.avg_rzrqye)}亿</p>
                  <p className="text-xs text-muted-foreground mt-1">所选时间段平均值</p>
                </div>
                <BarChart3 className="h-8 w-8 text-muted-foreground shrink-0" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">累计融资融券余额</p>
                  <p className="text-2xl font-bold mt-1">{formatAmount(statistics.total_rzrqye)}亿</p>
                  <p className="text-xs text-muted-foreground mt-1">所选时间段累计值</p>
                </div>
                <DollarSign className="h-8 w-8 text-muted-foreground shrink-0" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">最大融资余额</p>
                  <p className="text-2xl font-bold mt-1 text-green-600">{formatAmount(statistics.max_rzye)}亿</p>
                  <p className="text-xs text-muted-foreground mt-1">所选时间段最大值</p>
                </div>
                <TrendingUp className="h-8 w-8 text-green-600 shrink-0" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">最大融券余额</p>
                  <p className="text-2xl font-bold mt-1 text-red-600">{formatAmount(statistics.max_rqye)}亿</p>
                  <p className="text-xs text-muted-foreground mt-1">所选时间段最大值</p>
                </div>
                <TrendingDown className="h-8 w-8 text-red-600 shrink-0" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选区域 */}
      <Card>
        <CardHeader>
          <CardTitle>数据筛选</CardTitle>
          <CardDescription>选择日期范围和交易所查看融资融券交易汇总数据</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1 space-y-2">
              <label className="text-sm font-medium">开始日期</label>
              <DatePicker date={startDate} onDateChange={setStartDate} placeholder="选择开始日期" />
            </div>
            <div className="flex-1 space-y-2">
              <label className="text-sm font-medium">结束日期</label>
              <DatePicker date={endDate} onDateChange={setEndDate} placeholder="选择结束日期" />
            </div>
            <div className="flex-1 space-y-2">
              <label className="text-sm font-medium">交易所</label>
              <Select value={exchangeId || 'ALL'} onValueChange={(value) => setExchangeId(value === 'ALL' ? '' : value)}>
                <SelectTrigger>
                  <SelectValue placeholder="选择交易所" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="SSE">上交所(SSE)</SelectItem>
                  <SelectItem value="SZSE">深交所(SZSE)</SelectItem>
                  <SelectItem value="BSE">北交所(BSE)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end">
              <Button
                variant="outline"
                size="sm"
                onClick={() => { loadData(); loadStatistics() }}
              >
                <RefreshCw className="h-4 w-4 mr-1" />
                刷新
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card className="p-0 sm:p-0 overflow-hidden">
        <div className="sm:hidden">
          {/* 移动端视图 */}
          <div className="px-4 py-3 border-b bg-muted/50">
            <h3 className="text-sm font-medium">融资融券交易汇总数据</h3>
          </div>
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {!loading && !error && data.map((item, index) => (
              <div
                key={index}
                className={`p-4 transition-colors ${
                  index % 2 === 0
                    ? 'bg-white dark:bg-gray-900 hover:bg-blue-50 dark:hover:bg-blue-950/20 active:bg-blue-100 dark:active:bg-blue-900/30'
                    : 'bg-gray-50 dark:bg-gray-950 hover:bg-blue-50 dark:hover:bg-blue-950/20 active:bg-blue-100 dark:active:bg-blue-900/30'
                }`}
              >
                {mobileCard(item)}
              </div>
            ))}
          </div>
          {loading && (
            <div className="p-8 text-center">
              <div className="flex flex-col items-center justify-center gap-2">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                <span className="text-sm text-muted-foreground">加载中...</span>
              </div>
            </div>
          )}
          {error && (
            <div className="p-8 text-center">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}
          {!loading && !error && data.length === 0 && (
            <div className="p-8 text-center">
              <p className="text-sm text-muted-foreground">暂无融资融券数据</p>
            </div>
          )}

          {/* 移动端分页 */}
          {!loading && !error && data.length > 0 && (
            <div className="p-4 border-t bg-muted/30">
              <div className="flex items-center justify-between">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                >
                  上一页
                </Button>
                <span className="text-sm text-muted-foreground">
                  第 {page} / {Math.ceil(total / pageSize)} 页
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(Math.min(Math.ceil(total / pageSize), page + 1))}
                  disabled={page >= Math.ceil(total / pageSize)}
                >
                  下一页
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* 桌面端表格视图 */}
        <div className="hidden sm:block">
          <DataTable
            columns={columns}
            data={data}
            loading={loading}
            error={error}
            emptyMessage="暂无融资融券数据"
            tableClassName="[&_th]:border-r [&_td]:border-r [&_th:last-child]:border-r-0 [&_td:last-child]:border-r-0"
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: (newPage) => setPage(newPage),
              onPageSizeChange: (newPageSize) => { setPageSize(newPageSize); setPage(1) },
              pageSizeOptions: [10, 20, 30, 50, 100]
            }}
          />
        </div>
      </Card>
    </div>
  )
}
