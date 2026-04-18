'use client'

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, Calendar, BarChart3, PieChart } from 'lucide-react'
import { newStockApi, axiosInstance } from '@/lib/api'
import type { NewStockData, NewStockStatistics } from '@/lib/api/new-stock-api'
import { useTaskStore } from '@/stores/task-store'
import { useDataBulkOps } from '@/hooks/useDataBulkOps'

export default function NewStocksPage() {
  const [data, setData] = useState<NewStockData[]>([])
  const [statistics, setStatistics] = useState<NewStockStatistics | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)

  // 分页
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncDays, setSyncDays] = useState<number>(90)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  // 从 task store 实时派生——不要用本地 useState(false)
  const syncing = isTaskRunning('sync.new_stocks')

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params: any = {
        limit: pageSize,
        offset: (currentPage - 1) * pageSize,
      }
      if (startDate) {
        const y = startDate.getFullYear()
        const m = String(startDate.getMonth() + 1).padStart(2, '0')
        const d = String(startDate.getDate()).padStart(2, '0')
        params.start_date = `${y}${m}${d}`
      }
      if (endDate) {
        const y = endDate.getFullYear()
        const m = String(endDate.getMonth() + 1).padStart(2, '0')
        const d = String(endDate.getDate()).padStart(2, '0')
        params.end_date = `${y}${m}${d}`
      }

      const [dataResp, statsResp] = await Promise.all([
        newStockApi.getData(params),
        newStockApi.getStatistics(),
      ])

      if (dataResp.code === 200) {
        setData(dataResp.data?.items || [])
        setTotal(dataResp.data?.total || 0)
      }
      if (statsResp.code === 200) {
        setStatistics(statsResp.data || null)
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast.error('加载失败', { description: err.message })
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, currentPage, pageSize])

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
    tableKey: 'new_stocks',
    syncFn: (params) => axiosInstance.post('/api/new-stocks/sync-async', null, { params }),
    taskName: 'sync.new_stocks',
    onSuccess: loadData,
  })

  useEffect(() => {
    loadData()
  }, [loadData])

  useEffect(() => {
    setCurrentPage(1)
  }, [startDate, endDate])

  // 组件卸载清理
  useEffect(() => {
    return () => {
      // eslint-disable-next-line react-hooks/exhaustive-deps
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((cb, taskId) => unregisterCompletionCallback(taskId, cb))
      callbacks.clear()
      cleanup()
    }
  }, [unregisterCompletionCallback, cleanup])

  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    try {
      const response = await newStockApi.syncAsync({ days: syncDays || 90 })
      if (response.code === 200 && response.data) {
        const taskId = response.data.celery_task_id
        addTask({
          taskId,
          taskName: response.data.task_name,
          displayName: response.data.display_name,
          taskType: 'data_sync',
          status: 'running',
          progress: 0,
          startTime: Date.now(),
        })
        const completionCallback = (task: any) => {
          if (task.status === 'success') {
            loadData().catch(() => {})
            toast.success('数据同步完成', { description: '新股列表已更新' })
          } else if (task.status === 'failure') {
            toast.error('数据同步失败', { description: task.error || '同步过程中发生错误' })
          }
          unregisterCompletionCallback(taskId, completionCallback)
          activeCallbacksRef.current.delete(taskId)
        }
        activeCallbacksRef.current.set(taskId, completionCallback)
        registerCompletionCallback(taskId, completionCallback)
        triggerPoll()
        toast.success('任务已提交', { description: `"${response.data.display_name}" 已开始执行` })
      } else {
        throw new Error(response.message || '同步失败')
      }
    } catch (err: any) {
      toast.error('同步失败', { description: err.message })
    }
  }

  const fmt = (v: number | string | null | undefined, decimals = 2) => {
    if (v == null || v === '') return '-'
    const n = typeof v === 'string' ? parseFloat(v) : v
    return isNaN(n) ? '-' : n.toFixed(decimals)
  }

  const columns: Column<NewStockData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code,
      cellClassName: 'font-mono',
    },
    {
      key: 'name',
      header: '股票名称',
      accessor: (row) => row.name,
    },
    {
      key: 'ipo_date',
      header: '上网发行日',
      accessor: (row) => row.ipo_date || '-',
    },
    {
      key: 'issue_date',
      header: '上市日期',
      accessor: (row) => row.issue_date || '-',
      cellClassName: 'hidden md:table-cell',
    },
    {
      key: 'price',
      header: '发行价(元)',
      accessor: (row) => fmt(row.price),
      cellClassName: 'text-right hidden sm:table-cell',
    },
    {
      key: 'pe',
      header: '发行市盈率',
      accessor: (row) => fmt(row.pe),
      cellClassName: 'text-right hidden lg:table-cell',
    },
    {
      key: 'amount',
      header: '发行量(万股)',
      accessor: (row) => fmt(row.amount, 0),
      cellClassName: 'text-right hidden lg:table-cell',
    },
    {
      key: 'funds',
      header: '募集资金(亿)',
      accessor: (row) => fmt(row.funds),
      cellClassName: 'text-right hidden xl:table-cell',
    },
    {
      key: 'ballot',
      header: '中签率(%)',
      accessor: (row) => { const b = row.ballot != null ? parseFloat(String(row.ballot)) : NaN; return isNaN(b) ? '-' : (b * 100).toFixed(4) },
      cellClassName: 'text-right hidden xl:table-cell',
    },
  ], [])

  const mobileCard = useCallback((item: NewStockData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="font-mono font-semibold">{item.ts_code}</span>
        <span className="font-medium">{item.name}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">上网发行日</span>
        <span>{item.ipo_date || '-'}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">上市日期</span>
        <span>{item.issue_date || '-'}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">发行价</span>
        <span className="font-medium">{fmt(item.price)} 元</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">募集资金</span>
        <span>{fmt(item.funds)} 亿元</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">中签率</span>
        <span>{ (() => { const b = item.ballot != null ? parseFloat(String(item.ballot)) : NaN; return isNaN(b) ? '-' : (b * 100).toFixed(4) + '%' })() }</span>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="IPO新股列表"
        description="获取新股上市列表数据，包含发行价、市盈率、募集资金、中签率等信息"
        details={<>
          <div>接口：new_share</div>
          <a href="https://tushare.pro/document/2?doc_id=123" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="新股列表"
            />
          </div>
        }
      />

      {/* 同步弹窗 */}
      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>同步新股列表</DialogTitle>
            <DialogDescription>选择同步天数范围（默认最近90天）。</DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <label className="text-sm font-medium mb-2 block">同步最近天数</label>
            <Input
              type="number"
              min="1"
              max="3650"
              value={syncDays}
              onChange={(e) => setSyncDays(parseInt(e.target.value) || 90)}
              placeholder="如：90"
            />
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
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">总数量</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.total_count.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground mt-1">库中全部记录</p>
                </div>
                <PieChart className="h-6 w-6 sm:h-8 sm:w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">最近7天</p>
                  <p className="text-xl sm:text-2xl font-bold text-green-600">{statistics.recent_7_days}</p>
                  <p className="text-xs text-muted-foreground mt-1">新上市</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">最近30天</p>
                  <p className="text-xl sm:text-2xl font-bold text-blue-600">{statistics.recent_30_days}</p>
                  <p className="text-xs text-muted-foreground mt-1">新上市</p>
                </div>
                <Calendar className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">最近90天</p>
                  <p className="text-xl sm:text-2xl font-bold text-purple-600">{statistics.recent_90_days}</p>
                  <p className="text-xs text-muted-foreground mt-1">新上市</p>
                </div>
                <BarChart3 className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选 */}
      <Card>
        <CardHeader><CardTitle>数据查询</CardTitle></CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">开始日期（上网发行）</label>
                <DatePicker date={startDate} onDateChange={setStartDate} placeholder="选择开始日期" />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">结束日期（上网发行）</label>
                <DatePicker date={endDate} onDateChange={setEndDate} placeholder="选择结束日期" />
              </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={() => loadData()} disabled={loading}>
                <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
                查询
              </Button>
              <Button
                variant="ghost"
                onClick={() => { setStartDate(undefined); setEndDate(undefined) }}
              >
                重置
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card className="p-0 sm:p-0 overflow-hidden">
        {/* 移动端 */}
        <div className="sm:hidden">
          <div className="px-4 py-3 border-b bg-muted/50">
            <h3 className="text-sm font-medium">新股数据</h3>
          </div>
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {!loading && !error && data.map((item, index) => (
              <div
                key={item.ts_code}
                className={`p-4 transition-colors ${
                  index % 2 === 0
                    ? 'bg-white dark:bg-gray-900 hover:bg-blue-50 dark:hover:bg-blue-950/20 active:bg-blue-100'
                    : 'bg-gray-50 dark:bg-gray-950 hover:bg-blue-50 dark:hover:bg-blue-950/20 active:bg-blue-100'
                }`}
              >
                {mobileCard(item)}
              </div>
            ))}
          </div>
          {loading && (
            <div className="p-8 text-center">
              <div className="flex flex-col items-center gap-2">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                <span className="text-sm text-muted-foreground">加载中...</span>
              </div>
            </div>
          )}
          {error && <div className="p-8 text-center"><p className="text-sm text-destructive">{error}</p></div>}
          {!loading && !error && data.length === 0 && (
            <div className="p-8 text-center"><p className="text-sm text-muted-foreground">暂无数据</p></div>
          )}
        </div>

        {/* 桌面端 */}
        <div className="hidden sm:block">
          <DataTable
            columns={columns}
            data={data}
            loading={loading}
            error={error}
            emptyMessage="暂无新股数据"
            mobileCard={mobileCard}
            pagination={{
              page: currentPage,
              pageSize,
              total,
              onPageChange: setCurrentPage,
              onPageSizeChange: (s) => { setPageSize(s); setCurrentPage(1) },
            }}
          />
        </div>
      </Card>
    </div>
  )
}
