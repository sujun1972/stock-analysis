'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { toast } from 'sonner'
import { stkAuctionOApi } from '@/lib/api'
import type { StkAuctionOData, StkAuctionOStatistics } from '@/lib/api/stk-auction-o'
import { useTaskStore } from '@/stores/task-store'
import { RefreshCw, TrendingUp, TrendingDown, DollarSign } from 'lucide-react'

export default function StkAuctionOPage() {
  const [data, setData] = useState<StkAuctionOData[]>([])
  const [statistics, setStatistics] = useState<StkAuctionOStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [syncing, setSyncing] = useState(false)
  const [showSyncDialog, setShowSyncDialog] = useState(false)
  const [syncTsCode, setSyncTsCode] = useState<string>('')
  const [syncTradeDate, setSyncTradeDate] = useState<Date | undefined>(undefined)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params: any = { limit: 100 }
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]

      const response = await stkAuctionOApi.getData(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics)
      } else {
        throw new Error(response.message || '加载失败')
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast.error('加载失败', { description: err.message })
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate])

  useEffect(() => {
    loadData()
  }, [loadData])

  useEffect(() => {
    return () => {
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
    }
  }, [unregisterCompletionCallback])

  const openSyncDialog = () => setShowSyncDialog(true)
  const closeSyncDialog = () => {
    setShowSyncDialog(false)
    setSyncTsCode('')
    setSyncTradeDate(undefined)
    setSyncStartDate(undefined)
    setSyncEndDate(undefined)
  }

  const handleSync = async () => {
    setSyncing(true)

    const params: any = {}
    if (syncTsCode.trim()) params.ts_code = syncTsCode.trim()
    if (syncTradeDate) params.trade_date = syncTradeDate.toISOString().split('T')[0]
    if (syncStartDate) params.start_date = syncStartDate.toISOString().split('T')[0]
    if (syncEndDate) params.end_date = syncEndDate.toISOString().split('T')[0]

    try {
      const response = await stkAuctionOApi.syncAsync(params)

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
            toast.success('数据同步完成', { description: '开盘集合竞价数据已更新' })
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

        closeSyncDialog()
      } else {
        throw new Error(response.message || '同步失败')
      }
    } catch (err: any) {
      toast.error('同步失败', { description: err.message || '无法同步数据' })
    } finally {
      setSyncing(false)
    }
  }

  const formatDate = (dateStr: string) => {
    if (!dateStr || dateStr.length !== 8) return dateStr
    return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
  }

  const formatNumber = (num: number | null | undefined) => {
    if (num === null || num === undefined) return '0.00'
    return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  const columns: Column<StkAuctionOData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => formatDate(row.trade_date)
    },
    {
      key: 'close',
      header: '收盘价',
      accessor: (row) => formatNumber(row.close)
    },
    {
      key: 'open',
      header: '开盘价',
      accessor: (row) => formatNumber(row.open)
    },
    {
      key: 'high',
      header: '最高价',
      accessor: (row) => formatNumber(row.high)
    },
    {
      key: 'low',
      header: '最低价',
      accessor: (row) => formatNumber(row.low)
    },
    {
      key: 'vol',
      header: '成交量',
      accessor: (row) => formatNumber(row.vol)
    },
    {
      key: 'amount',
      header: '成交额',
      accessor: (row) => formatNumber(row.amount)
    },
    {
      key: 'vwap',
      header: '均价',
      accessor: (row) => formatNumber(row.vwap)
    }
  ], [])

  const mobileCard = useCallback((item: StkAuctionOData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">股票代码</span>
        <span className="font-medium">{item.ts_code}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">交易日期</span>
        <span>{formatDate(item.trade_date)}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">开盘价</span>
        <span>{formatNumber(item.open)}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">收盘价</span>
        <span>{formatNumber(item.close)}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">成交量</span>
        <span>{formatNumber(item.vol)}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">成交额</span>
        <span>{formatNumber(item.amount)}</span>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="股票开盘集合竞价"
        description="股票开盘9:30集合竞价数据，每天盘后更新"
      />

      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">股票数量</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.stock_count || 0}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">平均成交量</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(statistics.avg_vol)}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最大成交量</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(statistics.max_vol)}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最大成交额</CardTitle>
              <TrendingDown className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(statistics.max_amount)}</div>
            </CardContent>
          </Card>
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="flex-1 space-y-2">
              <Label>开始日期</Label>
              <DatePicker date={startDate} onSelect={setStartDate} placeholder="选择开始日期" />
            </div>
            <div className="flex-1 space-y-2">
              <Label>结束日期</Label>
              <DatePicker date={endDate} onSelect={setEndDate} placeholder="选择结束日期" />
            </div>
            <Button onClick={loadData} disabled={loading} className="w-full sm:w-auto">
              {loading ? <RefreshCw className="h-4 w-4 mr-1 animate-spin" /> : <RefreshCw className="h-4 w-4 mr-1" />}
              查询
            </Button>
            <Button variant="default" onClick={openSyncDialog} disabled={syncing} className="w-full sm:w-auto">
              <RefreshCw className="h-4 w-4 mr-1" />
              同步数据
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="p-0 sm:p-0 overflow-hidden">
        <div className="sm:hidden">
          <div className="px-4 py-3 border-b bg-muted/50">
            <h3 className="text-sm font-medium">集合竞价数据</h3>
          </div>
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {!loading && !error && data.map((item, index) => (
              <div
                key={index}
                className={`p-4 transition-colors ${
                  index % 2 === 0
                    ? 'bg-white dark:bg-gray-900 hover:bg-blue-50 dark:hover:bg-blue-950/20'
                    : 'bg-gray-50 dark:bg-gray-950 hover:bg-blue-50 dark:hover:bg-blue-950/20'
                }`}
              >
                {mobileCard(item)}
              </div>
            ))}
          </div>

          {loading && <div className="p-8 text-center"><div className="flex flex-col items-center justify-center gap-2"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" /><span className="text-sm text-muted-foreground">加载中...</span></div></div>}
          {error && <div className="p-8 text-center"><p className="text-sm text-destructive">{error}</p></div>}
          {!loading && !error && data.length === 0 && <div className="p-8 text-center"><p className="text-sm text-muted-foreground">暂无数据</p></div>}
        </div>

        <div className="hidden sm:block">
          <DataTable
            columns={columns}
            data={data}
            loading={loading}
            error={error}
            emptyMessage="暂无数据"
          />
        </div>
      </Card>

      <Dialog open={showSyncDialog} onOpenChange={setShowSyncDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>同步开盘集合竞价数据</DialogTitle>
            <DialogDescription>
              所有参数均为可选，不填写参数将同步最近交易日数据
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="sync-ts-code">股票代码</Label>
              <Input
                id="sync-ts-code"
                placeholder="如：600000.SH"
                value={syncTsCode}
                onChange={(e) => setSyncTsCode(e.target.value)}
              />
            </div>

            <div className="grid gap-2">
              <Label>交易日期</Label>
              <DatePicker
                date={syncTradeDate}
                onSelect={setSyncTradeDate}
                placeholder="选择交易日期"
              />
            </div>

            <div className="grid gap-2">
              <Label>日期范围（可选）</Label>
              <div className="flex gap-2 items-center">
                <DatePicker
                  date={syncStartDate}
                  onSelect={setSyncStartDate}
                  placeholder="开始日期"
                />
                <span className="text-muted-foreground">至</span>
                <DatePicker
                  date={syncEndDate}
                  onSelect={setSyncEndDate}
                  placeholder="结束日期"
                />
              </div>
            </div>

            <div className="rounded-lg bg-blue-50 dark:bg-blue-950 p-3 border border-blue-200 dark:border-blue-800">
              <p className="text-sm text-blue-800 dark:text-blue-200">
                <strong>说明：</strong>需要开通股票分钟权限，每次最大返回10000行数据
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={closeSyncDialog} disabled={syncing}>
              取消
            </Button>
            <Button onClick={handleSync} disabled={syncing}>
              {syncing ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                  同步中...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4 mr-1" />
                  开始同步
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
