'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { DatePicker } from '@/components/ui/date-picker'
import { financialDataApi, type FinaMainbzData, type FinaMainbzStatistics } from '@/lib/api/financial-data'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, PieChart, TrendingUp, DollarSign, Package } from 'lucide-react'

const toDateStr = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

const toDateStrYYYYMMDD = (d: Date) =>
  `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`

export default function FinaMainbzPage() {
  const [data, setData] = useState<FinaMainbzData[]>([])
  const [statistics, setStatistics] = useState<FinaMainbzStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 查询参数
  const [tsCode, setTsCode] = useState('')
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [period, setPeriod] = useState<Date | undefined>(undefined)
  const [type, setType] = useState<string>('ALL')

  // 分页
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // 同步弹窗
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncTsCode, setSyncTsCode] = useState('')
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  // 从 task store 派生 syncing 状态
  const syncing = isTaskRunning('tasks.sync_fina_mainbz')

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await financialDataApi.getFinaMainbz({
        ts_code: tsCode || undefined,
        start_date: startDate ? toDateStr(startDate) : undefined,
        end_date: endDate ? toDateStr(endDate) : undefined,
        period: period ? toDateStr(period) : undefined,
        type: type === 'ALL' ? undefined : type,
        limit: pageSize
      })

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setTotal(response.data.total || 0)
      } else {
        throw new Error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast.error('加载失败', { description: err.message })
    } finally {
      setLoading(false)
    }
  }, [tsCode, startDate, endDate, period, type, pageSize])

  // 加载统计信息
  const loadStatistics = useCallback(async () => {
    try {
      const response = await financialDataApi.getFinaMainbzStatistics({
        ts_code: tsCode || undefined,
        start_date: startDate ? toDateStr(startDate) : undefined,
        end_date: endDate ? toDateStr(endDate) : undefined
      })

      if (response.code === 200 && response.data) {
        setStatistics(response.data)
      }
    } catch {
      // 统计信息加载失败不影响主要数据展示
    }
  }, [tsCode, startDate, endDate])

  // 初始化加载
  useEffect(() => {
    loadData()
    loadStatistics()
  }, [loadData, loadStatistics])

  // 同步确认
  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    try {
      const params: any = {}
      if (syncTsCode) params.ts_code = syncTsCode
      if (syncStartDate) params.start_date = toDateStrYYYYMMDD(syncStartDate)
      if (syncEndDate) params.end_date = toDateStrYYYYMMDD(syncEndDate)

      const response = await financialDataApi.syncFinaMainbzAsync(params)

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
            toast.success('数据同步完成', { description: '主营业务构成数据已更新' })
          } else if (task.status === 'failure') {
            toast.error('数据同步失败', { description: task.error || '同步过程中发生错误' })
          }
          unregisterCompletionCallback(taskId, completionCallback)
          activeCallbacksRef.current.delete(taskId)
        }

        activeCallbacksRef.current.set(taskId, completionCallback)
        registerCompletionCallback(taskId, completionCallback)
        triggerPoll()

        toast.success('同步任务已提交', { description: '可在任务面板查看进度' })
      } else {
        throw new Error(response.message || '同步失败')
      }
    } catch (err: any) {
      toast.error('同步失败', { description: err.message || '无法同步数据' })
    }
  }

  // 组件卸载清理
  useEffect(() => {
    return () => {
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
    }
  }, [unregisterCompletionCallback])

  // 格式化金额（元转万元）
  const formatAmount = (amount: number | null | undefined) => {
    if (amount === null || amount === undefined) return '-'
    return (amount / 10000).toFixed(2)
  }

  // 表格列定义
  const columns: Column<FinaMainbzData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'end_date',
      header: '报告期',
      accessor: (row) => {
        const date = row.end_date
        return date ? `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}` : '-'
      }
    },
    {
      key: 'bz_item',
      header: '业务来源',
      accessor: (row) => row.bz_item || '-'
    },
    {
      key: 'bz_sales',
      header: <span>主营收入<br className="sm:hidden" /><span className="text-xs text-muted-foreground">(万元)</span></span>,
      accessor: (row) => formatAmount(row.bz_sales)
    },
    {
      key: 'bz_profit',
      header: <span>主营利润<br className="sm:hidden" /><span className="text-xs text-muted-foreground">(万元)</span></span>,
      accessor: (row) => formatAmount(row.bz_profit)
    },
    {
      key: 'bz_cost',
      header: <span>主营成本<br className="sm:hidden" /><span className="text-xs text-muted-foreground">(万元)</span></span>,
      accessor: (row) => formatAmount(row.bz_cost)
    },
    {
      key: 'curr_type',
      header: '货币',
      accessor: (row) => row.curr_type || '-'
    }
  ], [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="主营业务构成"
        description="上市公司主营业务构成数据，按产品/地区/行业分类"
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

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">总记录数</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.total_count.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground mt-1">股票数: {statistics.stock_count}</p>
                </div>
                <Package className="h-6 w-6 sm:h-8 sm:w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">业务类型数</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.bz_item_count.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground mt-1">报告期数: {statistics.period_count}</p>
                </div>
                <PieChart className="h-6 w-6 sm:h-8 sm:w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">平均收入</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatAmount(statistics.avg_bz_sales)}万</p>
                  <p className="text-xs text-muted-foreground mt-1">总收入: {formatAmount(statistics.total_bz_sales)}万</p>
                </div>
                <DollarSign className="h-6 w-6 sm:h-8 sm:w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">收入范围</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatAmount(statistics.max_bz_sales)}万</p>
                  <p className="text-xs text-muted-foreground mt-1">最小: {formatAmount(statistics.min_bz_sales)}万</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选区域 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <Label htmlFor="tsCode">股票代码</Label>
              <Input
                id="tsCode"
                placeholder="如: 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div>
              <Label className="mb-2 block">开始日期</Label>
              <DatePicker date={startDate} onDateChange={setStartDate} placeholder="选择开始日期" />
            </div>
            <div>
              <Label className="mb-2 block">结束日期</Label>
              <DatePicker date={endDate} onDateChange={setEndDate} placeholder="选择结束日期" />
            </div>
            <div>
              <Label className="mb-2 block">报告期</Label>
              <DatePicker date={period} onDateChange={setPeriod} placeholder="选择报告期" />
            </div>
            <div>
              <Label htmlFor="type">分类类型</Label>
              <Select value={type} onValueChange={setType}>
                <SelectTrigger id="type">
                  <SelectValue placeholder="选择类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="P">按产品</SelectItem>
                  <SelectItem value="D">按地区</SelectItem>
                  <SelectItem value="I">按行业</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <Button onClick={loadData} variant="default">查询</Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card className="p-0 sm:p-0 overflow-hidden">
        <DataTable
          columns={columns}
          data={data}
          loading={loading}
          error={error}
          emptyMessage="暂无数据"
          pagination={{
            page,
            pageSize,
            total,
            onPageChange: (newPage) => setPage(newPage),
            onPageSizeChange: (newPageSize) => {
              setPageSize(newPageSize)
              setPage(1)
            },
            pageSizeOptions: [10, 20, 30, 50, 100]
          }}
        />
      </Card>

      {/* 同步弹窗 */}
      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>同步主营业务构成数据</DialogTitle>
            <DialogDescription>
              选择同步范围（留空则同步最新数据）。2000积分/次。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label className="mb-2 block">股票代码（可选）</Label>
              <Input
                placeholder="如: 000001.SZ，留空同步全量"
                value={syncTsCode}
                onChange={(e) => setSyncTsCode(e.target.value)}
              />
            </div>
            <div>
              <Label className="mb-2 block">开始日期（可选）</Label>
              <DatePicker date={syncStartDate} onDateChange={setSyncStartDate} placeholder="留空同步最新数据" />
            </div>
            <div>
              <Label className="mb-2 block">结束日期（可选）</Label>
              <DatePicker date={syncEndDate} onDateChange={setSyncEndDate} placeholder="留空同步最新数据" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncDialogOpen(false)}>取消</Button>
            <Button onClick={handleSyncConfirm} disabled={syncing}>确认同步</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
