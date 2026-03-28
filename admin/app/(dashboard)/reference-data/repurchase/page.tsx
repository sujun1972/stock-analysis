'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { repurchaseApi, RepurchaseData, RepurchaseStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, Briefcase, DollarSign, BarChart3 } from 'lucide-react'

export default function RepurchasePage() {
  const [data, setData] = useState<RepurchaseData[]>([])
  const [statistics, setStatistics] = useState<RepurchaseStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [proc, setProc] = useState<string>('')

  // 同步弹窗状态
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize] = useState(100)
  const [total, setTotal] = useState(0)

  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()

  // 从 task store 实时派生 syncing 状态
  const syncing = isTaskRunning('tasks.sync_repurchase')

  // 构建本地时间日期字符串
  const toDateStr = (date: Date) =>
    `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params: any = { limit: pageSize }
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      if (tsCode) params.ts_code = tsCode.trim()
      if (proc) params.proc = proc

      const [dataResponse, statsResponse] = await Promise.all([
        repurchaseApi.getData(params),
        repurchaseApi.getStatistics({
          start_date: startDate ? toDateStr(startDate) : undefined,
          end_date: endDate ? toDateStr(endDate) : undefined,
          ts_code: tsCode.trim() || undefined
        })
      ])

      if (dataResponse.code === 200) {
        setData(dataResponse.data?.items || [])
        setTotal(dataResponse.data?.total || 0)
      }

      if (statsResponse.code === 200) {
        setStatistics(statsResponse.data || null)
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast.error('加载失败', { description: err.message })
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, tsCode, proc, pageSize])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    try {
      const params: any = {}
      if (syncStartDate) params.start_date = toDateStr(syncStartDate)
      if (syncEndDate) params.end_date = toDateStr(syncEndDate)

      const response = await repurchaseApi.syncAsync(params)

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
            toast.success('数据同步完成', { description: '股票回购数据已更新' })
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

  useEffect(() => {
    return () => {
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
    }
  }, [])

  // 格式化金额
  const formatAmount = (amount: number | null | undefined) => {
    if (amount === null || amount === undefined) return '-'
    return `${amount.toLocaleString()} 万元`
  }

  // 格式化数量
  const formatVolume = (vol: number | null | undefined) => {
    if (vol === null || vol === undefined) return '-'
    return vol.toLocaleString() + ' 股'
  }

  const columns: Column<RepurchaseData>[] = useMemo(() => [
    { key: 'ts_code', header: '股票代码', accessor: (row) => row.ts_code },
    { key: 'ann_date', header: '公告日期', accessor: (row) => row.ann_date },
    {
      key: 'proc',
      header: '进度',
      accessor: (row) => (
        <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
          row.proc === '完成' ? 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400' :
          row.proc === '实施' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400' :
          'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
        }`}>
          {row.proc || '-'}
        </span>
      )
    },
    { key: 'vol', header: '回购数量', accessor: (row) => formatVolume(row.vol), cellClassName: 'text-right whitespace-nowrap' },
    { key: 'amount', header: '回购金额', accessor: (row) => formatAmount(row.amount), cellClassName: 'text-right whitespace-nowrap' },
    { key: 'high_limit', header: '最高价', accessor: (row) => row.high_limit ? `${row.high_limit} 元` : '-', cellClassName: 'text-right' },
    { key: 'low_limit', header: '最低价', accessor: (row) => row.low_limit ? `${row.low_limit} 元` : '-', cellClassName: 'text-right' },
    { key: 'end_date', header: '截止日期', accessor: (row) => row.end_date || '-' }
  ], [])

  const mobileCard = useCallback((item: RepurchaseData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium">{item.ts_code}</span>
        <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${
          item.proc === '完成' ? 'bg-green-100 text-green-700' :
          item.proc === '实施' ? 'bg-blue-100 text-blue-700' :
          'bg-gray-100 text-gray-700'
        }`}>
          {item.proc || '-'}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">公告日期</span>
        <span className="font-medium">{item.ann_date}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">回购金额</span>
        <span className="font-medium text-blue-600">{formatAmount(item.amount)}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">回购数量</span>
        <span>{formatVolume(item.vol)}</span>
      </div>
      {(item.high_limit || item.low_limit) && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">价格区间</span>
          <span>{item.low_limit || '-'} ~ {item.high_limit || '-'} 元</span>
        </div>
      )}
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="股票回购"
        description="上市公司回购股票数据，包括回购公告、进度、金额等信息"
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
            <DialogTitle>同步数据</DialogTitle>
            <DialogDescription>选择同步日期范围（留空则同步最新数据）。</DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">开始日期（可选）</label>
              <DatePicker date={syncStartDate} onDateChange={setSyncStartDate} placeholder="留空同步最新数据" />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">结束日期（可选）</label>
              <DatePicker date={syncEndDate} onDateChange={setSyncEndDate} placeholder="留空同步最新数据" />
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
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">总记录数</p>
                  <p className="text-2xl font-bold">{statistics.total_count}</p>
                </div>
                <BarChart3 className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">涉及股票数</p>
                  <p className="text-2xl font-bold">{statistics.stock_count}</p>
                </div>
                <Briefcase className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">回购总金额</p>
                  <p className="text-2xl font-bold">{statistics.total_amount?.toLocaleString() || 0}</p>
                  <p className="text-xs text-muted-foreground">万元</p>
                </div>
                <DollarSign className="h-8 w-8 text-yellow-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">平均金额</p>
                  <p className="text-2xl font-bold">{statistics.avg_amount?.toLocaleString() || 0}</p>
                  <p className="text-xs text-muted-foreground">万元</p>
                </div>
                <TrendingUp className="h-8 w-8 text-purple-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选区域 */}
      <Card>
        <CardHeader><CardTitle>数据查询</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 items-end">
            <div>
              <label className="text-sm font-medium mb-2 block">开始日期</label>
              <DatePicker date={startDate} onDateChange={setStartDate} />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">结束日期</label>
              <DatePicker date={endDate} onDateChange={setEndDate} />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">股票代码（可选）</label>
              <Input placeholder="如: 600000.SH" value={tsCode} onChange={(e) => setTsCode(e.target.value)} />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">回购进度</label>
              <Select value={proc || 'ALL'} onValueChange={(value) => setProc(value === 'ALL' ? '' : value)}>
                <SelectTrigger>
                  <SelectValue placeholder="全部" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="完成">完成</SelectItem>
                  <SelectItem value="实施">实施</SelectItem>
                  <SelectItem value="股东大会通过">股东大会通过</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button onClick={loadData} disabled={loading}>查询</Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="pt-6">
          <DataTable
            columns={columns}
            data={data}
            loading={loading}
            error={error}
            emptyMessage="暂无股票回购数据"
            mobileCard={mobileCard}
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: setPage,
              onPageSizeChange: () => {},
              pageSizeOptions: [100]
            }}
          />
        </CardContent>
      </Card>
    </div>
  )
}
