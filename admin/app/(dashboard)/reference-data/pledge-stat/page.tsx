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
import { RefreshCw, TrendingUp, BarChart3, Users, Percent } from 'lucide-react'
import { extendedDataApi } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'

interface PledgeStatData {
  ts_code: string
  end_date: string
  pledge_count: number
  unrest_pledge: number
  rest_pledge: number
  total_share: number
  pledge_ratio: number
  created_at?: string
  updated_at?: string
}

interface PledgeStatStatistics {
  avg_pledge_ratio: number
  max_pledge_ratio: number
  total_pledge_count: number
  stock_count: number
}

export default function PledgeStatPage() {
  const [data, setData] = useState<PledgeStatData[]>([])
  const [statistics, setStatistics] = useState<PledgeStatStatistics | null>(null)
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
  const syncing = isTaskRunning('tasks.sync_pledge_stat')

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
        extendedDataApi.getPledgeStat(params),
        extendedDataApi.getPledgeStatStatistics({
          trade_date: tradeDate ? toDateStr(tradeDate) : undefined
        })
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

      const response = await extendedDataApi.syncPledgeStatAsync(params)

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
            toast.success('数据同步完成', { description: '股权质押统计数据已更新' })
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

  const columns: Column<PledgeStatData>[] = useMemo(() => [
    { key: 'ts_code', header: '股票代码', accessor: (row) => row.ts_code },
    { key: 'end_date', header: '截止日期', accessor: (row) => row.end_date },
    { key: 'pledge_count', header: '质押次数', accessor: (row) => row.pledge_count?.toLocaleString() || 0 },
    {
      key: 'unrest_pledge',
      header: '无限售股质押(万股)',
      accessor: (row) => row.unrest_pledge ? (row.unrest_pledge / 10000).toFixed(2) : '0',
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rest_pledge',
      header: '限售股质押(万股)',
      accessor: (row) => row.rest_pledge ? (row.rest_pledge / 10000).toFixed(2) : '0',
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'total_share',
      header: '总股本(万股)',
      accessor: (row) => row.total_share ? (row.total_share / 10000).toFixed(2) : '0',
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'pledge_ratio',
      header: '质押比例(%)',
      accessor: (row) => {
        const ratio = row.pledge_ratio || 0
        const color = ratio >= 50 ? 'text-red-600 dark:text-red-400' :
                     ratio >= 30 ? 'text-orange-600 dark:text-orange-400' :
                     'text-gray-900 dark:text-gray-100'
        return <span className={`font-medium ${color}`}>{ratio.toFixed(2)}%</span>
      }
    }
  ], [])

  const mobileCard = useCallback((item: PledgeStatData) => {
    const ratio = item.pledge_ratio || 0
    const ratioColor = ratio >= 50 ? 'text-red-600 dark:text-red-400' :
                       ratio >= 30 ? 'text-orange-600 dark:text-orange-400' :
                       'text-gray-900 dark:text-gray-100'
    return (
      <div className="space-y-2">
        <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
          <span className="text-sm font-medium">{item.ts_code}</span>
          <span className={`text-lg font-bold ${ratioColor}`}>{ratio.toFixed(2)}%</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">截止日期</span>
          <span>{item.end_date}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">质押次数</span>
          <span>{item.pledge_count?.toLocaleString() || 0}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">无限售股质押</span>
          <span>{item.unrest_pledge ? (item.unrest_pledge / 10000).toFixed(2) + '万股' : '0'}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">限售股质押</span>
          <span>{item.rest_pledge ? (item.rest_pledge / 10000).toFixed(2) + '万股' : '0'}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">总股本</span>
          <span>{item.total_share ? (item.total_share / 10000).toFixed(2) + '万股' : '0'}</span>
        </div>
      </div>
    )
  }, [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="股权质押统计"
        description="上市公司股票质押统计数据，包含质押次数、质押股本、质押比例等信息"
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
            <label className="text-sm font-medium mb-2 block">截止日期（可选）</label>
            <DatePicker date={syncDate} onDateChange={setSyncDate} placeholder="留空同步最新数据" />
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
                  <p className="text-sm text-muted-foreground">平均质押比例</p>
                  <p className="text-2xl font-bold">{statistics.avg_pledge_ratio?.toFixed(2) || 0}%</p>
                </div>
                <Percent className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">最高质押比例</p>
                  <p className="text-2xl font-bold text-red-600 dark:text-red-400">
                    {statistics.max_pledge_ratio?.toFixed(2) || 0}%
                  </p>
                </div>
                <TrendingUp className="h-8 w-8 text-red-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">总质押次数</p>
                  <p className="text-2xl font-bold">{statistics.total_pledge_count?.toLocaleString() || 0}</p>
                </div>
                <BarChart3 className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">统计股票数</p>
                  <p className="text-2xl font-bold">{statistics.stock_count?.toLocaleString() || 0}</p>
                </div>
                <Users className="h-8 w-8 text-purple-500" />
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
              <label className="text-sm font-medium mb-2 block">截止日期</label>
              <DatePicker date={tradeDate} onDateChange={setTradeDate} placeholder="选择截止日期" />
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
