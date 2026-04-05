'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, TrendingDown, DollarSign, Users } from 'lucide-react'
import { useDataBulkOps } from '@/hooks/useDataBulkOps'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { financialDataApi } from '@/lib/api'
import type { DividendData, DividendStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'

const toDateStr = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

export default function DividendPage() {
  const [data, setData] = useState<DividendData[]>([])
  const [statistics, setStatistics] = useState<DividendStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [tsCode, setTsCode] = useState('')
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)

  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [totalRecords, setTotalRecords] = useState(0)

  // 同步弹窗状态
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncTsCode, setSyncTsCode] = useState('')
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  const syncing = isTaskRunning('tasks.sync_dividend')

  const loadData = useCallback(async (pg = currentPage, ps = pageSize) => {
    try {
      setLoading(true)
      const params: any = { limit: ps, offset: (pg - 1) * ps }
      if (tsCode) params.ts_code = tsCode
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)

      const response = await financialDataApi.getDividend(params)
      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics || null)
        setTotalRecords(response.data.total || 0)
      } else {
        throw new Error(response.message || '加载失败')
      }
    } catch (err: any) {
      toast.error('加载失败', { description: err.message })
      setData([])
      setStatistics(null)
      setTotalRecords(0)
    } finally {
      setLoading(false)
    }
  }, [tsCode, startDate, endDate, currentPage, pageSize])

  const handleQuery = () => {
    setCurrentPage(1)
    loadData()
  }

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
    tableKey: 'dividend',
    syncFn: (params) => financialDataApi.syncDividendFullHistoryAsync(params),
    taskName: 'tasks.sync_dividend_full_history',
    onSuccess: loadData,
  })

  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    try {
      const params: any = {}
      if (syncTsCode) params.ts_code = syncTsCode
      if (syncStartDate) params.ann_date = toDateStr(syncStartDate)
      if (syncEndDate) params.end_date = toDateStr(syncEndDate)

      const response = await financialDataApi.syncDividendAsync(params)
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
            toast.success('数据同步完成', { description: '分红送股数据已更新' })
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
      cleanup()
    }
  }, [])

  const columns: Column<DividendData>[] = useMemo(() => [
    { key: 'ts_code', header: '股票代码', accessor: (row) => row.ts_code },
    { key: 'end_date', header: '分红年度', accessor: (row) => row.end_date || '-' },
    { key: 'ann_date', header: '公告日期', accessor: (row) => row.ann_date || '-' },
    { key: 'div_proc', header: '实施进度', accessor: (row) => row.div_proc || '-' },
    {
      key: 'cash_div',
      header: '每股分红(税后)',
      accessor: (row) => row.cash_div !== null && row.cash_div !== undefined ? row.cash_div.toFixed(4) : '-',
      cellClassName: 'text-right'
    },
    {
      key: 'stk_div',
      header: '每股送转',
      accessor: (row) => row.stk_div !== null && row.stk_div !== undefined ? row.stk_div.toFixed(4) : '-',
      cellClassName: 'text-right'
    },
    { key: 'ex_date', header: '除权除息日', accessor: (row) => row.ex_date || '-' },
    { key: 'record_date', header: '股权登记日', accessor: (row) => row.record_date || '-' }
  ], [])

  const mobileCard = useCallback((item: DividendData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">股票代码</span>
        <span className="font-medium">{item.ts_code}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">分红年度</span>
        <span>{item.end_date || '-'}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">公告日期</span>
        <span>{item.ann_date || '-'}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">实施进度</span>
        <span>{item.div_proc || '-'}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">每股分红(税后)</span>
        <span className="font-medium text-green-600">
          {item.cash_div !== null && item.cash_div !== undefined ? item.cash_div.toFixed(4) : '-'}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">每股送转</span>
        <span className="font-medium text-blue-600">
          {item.stk_div !== null && item.stk_div !== undefined ? item.stk_div.toFixed(4) : '-'}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">除权除息日</span>
        <span>{item.ex_date || '-'}</span>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="分红送股"
        description="获取上市公司分红送股数据"
        details={<>
          <div>接口：dividend</div>
          <a href="https://tushare.pro/document/2?doc_id=103" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="分红送股"
            />
          </div>
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
                  <p className="text-xl sm:text-2xl font-bold">{statistics.total_records?.toLocaleString() ?? 0}</p>
                  <p className="text-xs text-muted-foreground mt-1">统计股票数: {statistics.stock_count?.toLocaleString() ?? 0}</p>
                </div>
                <Users className="h-6 w-6 sm:h-8 sm:w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">平均现金分红</p>
                  <p className="text-xl sm:text-2xl font-bold text-green-600">{statistics.avg_cash_div?.toFixed(4) ?? '0.0000'}</p>
                  <p className="text-xs text-muted-foreground mt-1">每股分红(税后)</p>
                </div>
                <DollarSign className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">最高现金分红</p>
                  <p className="text-xl sm:text-2xl font-bold text-green-600">{statistics.max_cash_div?.toFixed(4) ?? '0.0000'}</p>
                  <p className="text-xs text-muted-foreground mt-1">最大每股分红</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">平均送转比例</p>
                  <p className="text-xl sm:text-2xl font-bold text-blue-600">{statistics.avg_stk_div?.toFixed(4) ?? '0.0000'}</p>
                  <p className="text-xs text-muted-foreground mt-1">每股送转</p>
                </div>
                <TrendingDown className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 查询 Card */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
          <CardDescription>查询上市公司分红送股数据</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <Input
                placeholder="股票代码 (如: 600848.SH)"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="flex flex-col sm:flex-row gap-4 items-end">
              <DatePicker date={startDate} onDateChange={setStartDate} placeholder="开始日期" />
              <DatePicker date={endDate} onDateChange={setEndDate} placeholder="结束日期" />
              <Button onClick={handleQuery} disabled={loading}>
                {loading ? '查询中...' : '查询'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="p-0 sm:p-0 overflow-hidden">
        <DataTable
          columns={columns}
          data={data}
          loading={loading}
          emptyMessage="暂无数据"
          mobileCard={mobileCard}
          page={currentPage}
          pageSize={pageSize}
          total={totalRecords}
          onPageChange={(newPage) => { setCurrentPage(newPage); loadData(newPage, pageSize).catch(() => {}) }}
          onPageSizeChange={(newSize) => { setPageSize(newSize); setCurrentPage(1); loadData(1, newSize).catch(() => {}) }}
          pageSizeOptions={[10, 20, 30, 50, 100]}
        />
      </Card>

      {/* 同步弹窗 */}
      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>同步分红送股数据</DialogTitle>
            <DialogDescription>
              选择同步条件（均可留空），留空时同步最新数据。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">股票代码（可选）</label>
              <Input
                placeholder="如 600848.SH，留空同步全部"
                value={syncTsCode}
                onChange={(e) => setSyncTsCode(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">开始公告日期（可选）</label>
              <DatePicker
                date={syncStartDate}
                onDateChange={setSyncStartDate}
                placeholder="留空不限制"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">结束日期（可选）</label>
              <DatePicker
                date={syncEndDate}
                onDateChange={setSyncEndDate}
                placeholder="留空不限制"
              />
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
