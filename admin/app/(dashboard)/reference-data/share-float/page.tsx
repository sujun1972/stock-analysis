'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { shareFloatApi } from '@/lib/api'
import type { ShareFloatData, ShareFloatStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, Users, Calendar, Package } from 'lucide-react'

export default function ShareFloatPage() {
  const [data, setData] = useState<ShareFloatData[]>([])
  const [statistics, setStatistics] = useState<ShareFloatStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 筛选条件
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')

  // 同步弹窗状态
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize] = useState(100)
  const [total, setTotal] = useState(0)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  // 从 task store 实时派生 syncing 状态
  const syncing = isTaskRunning('tasks.sync_share_float')

  // 构建本地时间日期字符串
  const toDateStr = (date: Date) =>
    `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params: any = { limit: pageSize }
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      if (tsCode.trim()) params.ts_code = tsCode.trim()

      const [dataResponse, statsResponse] = await Promise.all([
        shareFloatApi.getData(params),
        shareFloatApi.getStatistics({
          start_date: startDate ? toDateStr(startDate) : undefined,
          end_date: endDate ? toDateStr(endDate) : undefined,
          ts_code: tsCode.trim() || undefined
        })
      ])

      if (dataResponse.code === 200 && dataResponse.data) {
        setData(dataResponse.data.items || [])
        setTotal(dataResponse.data.total || 0)
      } else {
        throw new Error(dataResponse.message || '加载数据失败')
      }

      if (statsResponse.code === 200 && statsResponse.data) {
        setStatistics(statsResponse.data)
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast.error('加载失败', { description: err.message })
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, tsCode, pageSize])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    try {
      const params: any = {}
      if (syncStartDate) params.start_date = toDateStr(syncStartDate)
      if (syncEndDate) params.end_date = toDateStr(syncEndDate)

      const response = await shareFloatApi.syncAsync(params)

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
            toast.success('数据同步完成', { description: '限售股解禁数据已更新' })
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

  const columns: Column<ShareFloatData>[] = useMemo(() => [
    { key: 'ts_code', header: '股票代码', accessor: (row) => row.ts_code, width: '120px' },
    { key: 'holder_name', header: '股东名称', accessor: (row) => row.holder_name, width: '150px' },
    { key: 'ann_date', header: '公告日期', accessor: (row) => row.ann_date, width: '120px' },
    { key: 'float_date', header: '解禁日期', accessor: (row) => row.float_date, width: '120px' },
    {
      key: 'float_share',
      header: '流通股份(股)',
      accessor: (row) => row.float_share !== null ? row.float_share.toLocaleString() : '-',
      width: '140px',
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'float_ratio',
      header: '流通比率(%)',
      accessor: (row) => row.float_ratio !== null ? (row.float_ratio * 100).toFixed(2) + '%' : '-',
      width: '120px',
      cellClassName: 'text-right'
    },
    { key: 'share_type', header: '股份类型', accessor: (row) => row.share_type, width: '120px' }
  ], [])

  const mobileCard = useCallback((item: ShareFloatData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium">{item.ts_code}</span>
        <span className="text-xs text-gray-500">{item.share_type}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">股东名称</span>
        <span className="font-medium text-right">{item.holder_name}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">公告日期</span>
        <span>{item.ann_date}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">解禁日期</span>
        <span>{item.float_date}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">流通股份</span>
        <span className="font-medium">{item.float_share !== null ? item.float_share.toLocaleString() + ' 股' : '-'}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">流通比率</span>
        <span className="font-medium">{item.float_ratio !== null ? (item.float_ratio * 100).toFixed(2) + '%' : '-'}</span>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="限售股解禁"
        description="获取限售股解禁"
        details={<>
          <div>接口：share_float</div>
          <a href="https://tushare.pro/document/2?doc_id=160" target="_blank" rel="noopener noreferrer">查看文档</a>
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
                  <p className="text-sm text-muted-foreground">记录总数</p>
                  <p className="text-2xl font-bold">{statistics.total_records}</p>
                  <p className="text-xs text-muted-foreground">涉及 {statistics.total_stocks} 只股票</p>
                </div>
                <Package className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">总流通股份</p>
                  <p className="text-2xl font-bold">{statistics.total_float_share_yi.toFixed(2)}</p>
                  <p className="text-xs text-muted-foreground">亿股</p>
                </div>
                <TrendingUp className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">平均流通比率</p>
                  <p className="text-2xl font-bold">{statistics.avg_float_ratio_percent.toFixed(2)}%</p>
                  <p className="text-xs text-muted-foreground">占总股本比率</p>
                </div>
                <Users className="h-8 w-8 text-purple-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">最大流通比率</p>
                  <p className="text-2xl font-bold">{statistics.max_float_ratio_percent.toFixed(2)}%</p>
                  <p className="text-xs text-muted-foreground">单次最大解禁比率</p>
                </div>
                <Calendar className="h-8 w-8 text-orange-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选区域 */}
      <Card>
        <CardHeader><CardTitle>数据查询</CardTitle></CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">股票代码（可选）</label>
              <Input placeholder="如：000001.SZ" value={tsCode} onChange={(e) => setTsCode(e.target.value)} />
            </div>
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">解禁开始日期</label>
              <DatePicker date={startDate} onDateChange={setStartDate} />
            </div>
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">解禁结束日期</label>
              <DatePicker date={endDate} onDateChange={setEndDate} />
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
            emptyMessage="暂无数据"
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
