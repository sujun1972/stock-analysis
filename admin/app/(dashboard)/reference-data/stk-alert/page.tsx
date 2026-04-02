'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { toast } from 'sonner'
import { RefreshCw, AlertCircle, FileBarChart, Tag } from 'lucide-react'
import { stkAlertApi, type StkAlertData, type StkAlertStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'

export default function StkAlertPage() {
  const [data, setData] = useState<StkAlertData[]>([])
  const [statistics, setStatistics] = useState<StkAlertStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')

  // 同步弹窗状态
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncDate, setSyncDate] = useState<Date | undefined>(undefined)

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize] = useState(100)
  const [total, setTotal] = useState(0)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  // 从 task store 实时派生 syncing 状态
  const syncing = isTaskRunning('tasks.sync_stk_alert')

  // 构建本地时间日期字符串
  const toDateStr = (date: Date) =>
    `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params: any = { limit: pageSize }
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      if (tsCode.trim()) params.ts_code = tsCode.trim()

      const [dataResponse, statsResponse] = await Promise.all([
        stkAlertApi.getData(params),
        stkAlertApi.getStatistics({ trade_date: tradeDate ? toDateStr(tradeDate) : undefined })
      ])

      if (dataResponse.code === 200 && dataResponse.data) {
        setData(dataResponse.data.items || [])
        setTotal(dataResponse.data.total || 0)
        if (!tradeDate && dataResponse.data.trade_date) {
          setTradeDate(new Date(dataResponse.data.trade_date + 'T00:00:00'))
        }
      } else {
        throw new Error(dataResponse.message || '获取数据失败')
      }

      if (statsResponse.code === 200 && statsResponse.data) {
        setStatistics(statsResponse.data)
      }
    } catch (err: any) {
      const errorMsg = err.message || '加载数据失败'
      setError(errorMsg)
      toast.error('加载失败', { description: errorMsg })
    } finally {
      setLoading(false)
    }
  }, [tradeDate, tsCode, pageSize])

  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    try {
      const params: any = {}
      if (syncDate) params.trade_date = toDateStr(syncDate)

      const response = await stkAlertApi.syncAsync(params)

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
            toast.success('数据同步完成', { description: '交易所重点提示证券数据已更新' })
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

  useEffect(() => {
    loadData()
  }, [loadData])

  const columns: Column<StkAlertData>[] = useMemo(() => [
    { key: 'ts_code', header: '股票代码', accessor: (row) => row.ts_code },
    { key: 'name', header: '股票名称', accessor: (row) => row.name },
    { key: 'start_date', header: '起始日期', accessor: (row) => row.start_date },
    { key: 'end_date', header: '截至日期', accessor: (row) => row.end_date },
    { key: 'type', header: '提示类型', accessor: (row) => row.type }
  ], [])

  const mobileCard = useCallback((item: StkAlertData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium">{item.name}</span>
        <span className="text-xs text-gray-500">{item.ts_code}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">起始日期</span>
        <span>{item.start_date}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">截至日期</span>
        <span>{item.end_date}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">提示类型</span>
        <span className="text-orange-600 dark:text-orange-400">{item.type}</span>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="交易所重点提示证券"
        description="根据证券交易所交易规则的有关规定，交易所每日发布重点提示证券"
        details={<>
          <div>接口：stk_alert</div>
          <a href="https://tushare.pro/document/2?doc_id=453" target="_blank" rel="noopener noreferrer">查看文档</a>
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
            <DialogDescription>选择同步日期（留空则同步最新交易日数据）。</DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <label className="text-sm font-medium mb-2 block">交易日期（可选）</label>
            <DatePicker date={syncDate} onDateChange={setSyncDate} placeholder="留空同步最新交易日" />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncDialogOpen(false)}>取消</Button>
            <Button onClick={handleSyncConfirm} disabled={syncing}>确认同步</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">总记录数</p>
                  <p className="text-2xl font-bold">{statistics.total_count?.toLocaleString() || 0}</p>
                </div>
                <FileBarChart className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">股票数量</p>
                  <p className="text-2xl font-bold">{statistics.stock_count?.toLocaleString() || 0}</p>
                </div>
                <AlertCircle className="h-8 w-8 text-orange-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">提示类型数</p>
                  <p className="text-2xl font-bold">{statistics.type_count?.toLocaleString() || 0}</p>
                </div>
                <Tag className="h-8 w-8 text-purple-500" />
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
              <label className="text-sm font-medium mb-2 block">交易日期</label>
              <DatePicker date={tradeDate} onDateChange={setTradeDate} placeholder="选择交易日期" />
            </div>
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">股票代码（可选）</label>
              <Input
                placeholder="如：000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
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
