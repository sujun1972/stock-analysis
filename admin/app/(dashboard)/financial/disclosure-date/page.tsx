'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { DatePicker } from '@/components/ui/date-picker'
import { toast } from 'sonner'
import { RefreshCw, FileText, Calendar, TrendingUp, CheckCircle, Clock } from 'lucide-react'
import { useDataBulkOps } from '@/hooks/useDataBulkOps'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { financialDataApi, type DisclosureDateData, type DisclosureDateStatistics } from '@/lib/api/financial-data'
import { useTaskStore } from '@/stores/task-store'

const toDateStr = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

const toDateStrYYYYMMDD = (d: Date) =>
  `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`

export default function DisclosureDatePage() {
  const [data, setData] = useState<DisclosureDateData[]>([])
  const [statistics, setStatistics] = useState<DisclosureDateStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 筛选条件
  const [tsCode, setTsCode] = useState('')
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)

  // 分页
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // 同步弹窗
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncTsCode, setSyncTsCode] = useState('')
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  // 任务回调存储
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()

  // 从 task store 派生 syncing 状态
  const syncing = isTaskRunning('tasks.sync_disclosure_date')

  // 加载数据
  const loadData = useCallback(async (currentPage = page, currentPageSize = pageSize) => {
    try {
      setLoading(true)
      setError(null)

      const response = await financialDataApi.getDisclosureDate({
        ts_code: tsCode || undefined,
        start_date: startDate ? toDateStr(startDate) : undefined,
        end_date: endDate ? toDateStr(endDate) : undefined,
        limit: currentPageSize,
        offset: (currentPage - 1) * currentPageSize
      })

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics)
        setTotal(response.data.total || 0)
      } else {
        throw new Error(response.message || '加载失败')
      }
    } catch (err: any) {
      const errorMsg = err.message || '加载数据失败'
      setError(errorMsg)
      toast.error('加载失败', { description: errorMsg })
    } finally {
      setLoading(false)
    }
  }, [tsCode, startDate, endDate, page, pageSize])

  // 初始加载
  useEffect(() => {
    loadData()
  }, [loadData])

  const {
    handleFullSync,
    handleClear,
    fullSyncing,
    isClearing,
    isClearDialogOpen,
    setIsClearDialogOpen,
    cleanup,
    earliestHistoryDate,
  } = useDataBulkOps({
    tableKey: 'disclosure_date',
    syncFn: (params) => financialDataApi.syncDisclosureDateFullHistoryAsync(params),
    taskName: 'tasks.sync_disclosure_date_full_history',
    onSuccess: loadData,
  })

  // 组件卸载时清理回调
  useEffect(() => {
    return () => {
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
      cleanup()
    }
  }, [unregisterCompletionCallback])

  // 同步确认
  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    try {
      const params: any = {}
      if (syncTsCode) params.ts_code = syncTsCode
      if (syncEndDate) params.end_date = toDateStrYYYYMMDD(syncEndDate)

      const response = await financialDataApi.syncDisclosureDateAsync(params)

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
            loadData(1, pageSize).catch(() => {})
            toast.success('数据同步完成', { description: '财报披露计划数据已更新' })
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

  // 表格列定义
  const columns: Column<DisclosureDateData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'end_date',
      header: '报告期',
      accessor: (row) => row.end_date
    },
    {
      key: 'ann_date',
      header: '公告日',
      accessor: (row) => row.ann_date
    },
    {
      key: 'pre_date',
      header: '预计披露日期',
      accessor: (row) => row.pre_date || '-'
    },
    {
      key: 'actual_date',
      header: '实际披露日期',
      accessor: (row) => row.actual_date || '-'
    },
    {
      key: 'status',
      header: '披露状态',
      accessor: (row) => (
        <span className={`px-2 py-1 rounded text-xs ${
          row.actual_date
            ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
            : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
        }`}>
          {row.actual_date ? '已披露' : '待披露'}
        </span>
      )
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: DisclosureDateData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">股票代码</span>
        <span className="font-medium">{item.ts_code}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">报告期</span>
        <span>{item.end_date}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">公告日</span>
        <span>{item.ann_date}</span>
      </div>
      {item.pre_date && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">预计披露日期</span>
          <span>{item.pre_date}</span>
        </div>
      )}
      {item.actual_date && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">实际披露日期</span>
          <span>{item.actual_date}</span>
        </div>
      )}
      <div className="flex justify-between items-center pt-2">
        <span className="text-sm text-gray-600 dark:text-gray-400">披露状态</span>
        <span className={`px-2 py-1 rounded text-xs ${
          item.actual_date
            ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
            : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400'
        }`}>
          {item.actual_date ? '已披露' : '待披露'}
        </span>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="财报披露计划"
        description="获取财报披露计划日期"
        details={<>
          <div>接口：disclosure_date</div>
          <a href="https://tushare.pro/document/2?doc_id=162" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <div className="flex gap-2">
            <Button onClick={() => setSyncDialogOpen(true)} disabled={syncing}>
              {syncing ? (
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
              ) : (
                <><RefreshCw className="h-4 w-4 mr-1" />同步数据</>
              )}
            </Button>
            <BulkOpsButtons
              onFullSync={handleFullSync}
              onClearConfirm={handleClear}
              isClearDialogOpen={isClearDialogOpen}
              setIsClearDialogOpen={setIsClearDialogOpen}
              fullSyncing={fullSyncing}
              isClearing={isClearing}
              earliestHistoryDate={earliestHistoryDate}
              tableName="财报披露计划"
            />
          </div>
        }
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">总记录数</p>
                  <p className="text-2xl font-bold">{statistics.total_count || 0}</p>
                </div>
                <FileText className="h-8 w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">股票数量</p>
                  <p className="text-2xl font-bold">{statistics.stock_count || 0}</p>
                </div>
                <TrendingUp className="h-8 w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">报告期数量</p>
                  <p className="text-2xl font-bold">{statistics.period_count || 0}</p>
                </div>
                <Calendar className="h-8 w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">已披露</p>
                  <p className="text-2xl font-bold text-green-600">{statistics.disclosed_count || 0}</p>
                </div>
                <CheckCircle className="h-8 w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">待披露</p>
                  <p className="text-2xl font-bold text-yellow-600">{statistics.pending_count || 0}</p>
                </div>
                <Clock className="h-8 w-8 text-yellow-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选和操作 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="flex-1 w-full sm:w-auto">
              <Label className="mb-2 block">股票代码</Label>
              <Input
                placeholder="如: 600000.SH"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <Label className="mb-2 block">开始日期（报告期）</Label>
              <DatePicker date={startDate} onDateChange={setStartDate} placeholder="选择开始日期" />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <Label className="mb-2 block">结束日期（报告期）</Label>
              <DatePicker date={endDate} onDateChange={setEndDate} placeholder="选择结束日期" />
            </div>
            <div className="flex gap-2">
              <Button onClick={loadData} disabled={loading}>
                查询
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card className="p-0 sm:p-0 overflow-hidden">
        {/* 移动端视图 */}
        <div className="sm:hidden">
          <div className="px-4 py-3 border-b bg-muted/50">
            <h3 className="text-sm font-medium">财报披露计划数据</h3>
          </div>
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {!loading && !error && data.map((item, index) => (
              <div
                key={`${item.ts_code}-${item.end_date}-${index}`}
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
              <p className="text-sm text-muted-foreground">暂无数据</p>
            </div>
          )}

          {/* 移动端分页 */}
          {!loading && !error && data.length > 0 && (
            <div className="p-4 border-t bg-muted/30">
              <div className="flex items-center justify-between">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => { const newPage = Math.max(1, page - 1); setPage(newPage); loadData(newPage, pageSize).catch(() => {}) }}
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
                  onClick={() => { const newPage = Math.min(Math.ceil(total / pageSize), page + 1); setPage(newPage); loadData(newPage, pageSize).catch(() => {}) }}
                  disabled={page >= Math.ceil(total / pageSize)}
                >
                  下一页
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* 桌面端表格 */}
        <div className="hidden sm:block">
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
              onPageChange: (newPage) => { setPage(newPage); loadData(newPage, pageSize).catch(() => {}) },
              onPageSizeChange: (newPageSize) => { setPageSize(newPageSize); setPage(1); loadData(1, newPageSize).catch(() => {}) },
              pageSizeOptions: [10, 20, 30, 50, 100]
            }}
          />
        </div>
      </Card>

      {/* 同步弹窗 */}
      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>同步财报披露计划数据</DialogTitle>
            <DialogDescription>
              选择同步范围（留空则同步最新数据）。500积分/次。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label className="mb-2 block">股票代码（可选）</Label>
              <Input
                placeholder="如: 600000.SH，留空同步全量"
                value={syncTsCode}
                onChange={(e) => setSyncTsCode(e.target.value)}
              />
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
