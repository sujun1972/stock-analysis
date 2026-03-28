'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { stkAhComparisonApi } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, TrendingDown, BarChart3, Activity } from 'lucide-react'
import type { StkAhComparisonData, StkAhComparisonStatistics } from '@/lib/api/stk-ah-comparison'

const toDateStr = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

export default function StkAhComparisonPage() {
  const [data, setData] = useState<StkAhComparisonData[]>([])
  const [statistics, setStatistics] = useState<StkAhComparisonStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // 同步对话框状态
  const [showSyncDialog, setShowSyncDialog] = useState(false)
  const [syncHkCode, setSyncHkCode] = useState('')
  const [syncTsCode, setSyncTsCode] = useState('')
  const [syncTradeDate, setSyncTradeDate] = useState<Date | undefined>(undefined)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()

  // 从 task store 实时派生 syncing 状态
  const syncing = isTaskRunning('tasks.sync_stk_ah_comparison')

  const loadData = useCallback(async (targetPage: number = 1) => {
    try {
      setLoading(true)

      const params: any = {
        page: targetPage,
        page_size: pageSize
      }
      if (tradeDate) params.trade_date = toDateStr(tradeDate)

      const response = await stkAhComparisonApi.getData(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics || null)
        setTotal(response.data.total || 0)
        setPage(targetPage)

        // 未传日期时，用返回的最近有数据日期回填
        if (!tradeDate && response.data.resolved_date) {
          setTradeDate(new Date(response.data.resolved_date + 'T00:00:00'))
        }
      } else {
        throw new Error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      toast.error('加载失败', { description: err.message || '无法加载AH股比价数据' })
    } finally {
      setLoading(false)
    }
  }, [tradeDate, pageSize])

  useEffect(() => {
    loadData(1).catch(() => {})
  }, [])

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

  const handleSyncConfirm = async () => {
    setShowSyncDialog(false)

    try {
      const params: any = {}
      if (syncHkCode.trim()) params.hk_code = syncHkCode.trim()
      if (syncTsCode.trim()) params.ts_code = syncTsCode.trim()
      if (syncTradeDate) params.trade_date = toDateStr(syncTradeDate)
      if (syncStartDate) params.start_date = toDateStr(syncStartDate)
      if (syncEndDate) params.end_date = toDateStr(syncEndDate)

      const response = await stkAhComparisonApi.syncAsync(params)

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
            loadData(1).catch(() => {})
            toast.success('数据同步完成', { description: 'AH股比价数据已更新' })
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

  const formatDate = (dateStr: string) => {
    if (!dateStr || dateStr.length !== 8) return dateStr
    return `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`
  }

  const formatNumber = (num: number | null | undefined, decimals: number = 2) => {
    if (num === null || num === undefined) return '-'
    return num.toFixed(decimals)
  }

  const formatPercent = (num: number | null | undefined) => {
    if (num === null || num === undefined) return '-'
    const sign = num >= 0 ? '+' : ''
    return `${sign}${num.toFixed(2)}%`
  }

  const columns: Column<StkAhComparisonData>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => formatDate(row.trade_date)
    },
    {
      key: 'hk_code',
      header: '港股代码',
      accessor: (row) => row.hk_code
    },
    {
      key: 'hk_name',
      header: '港股名称',
      accessor: (row) => row.hk_name || '-'
    },
    {
      key: 'ts_code',
      header: 'A股代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'name',
      header: 'A股名称',
      accessor: (row) => row.name || '-'
    },
    {
      key: 'hk_close',
      header: '港股收盘价',
      accessor: (row) => formatNumber(row.hk_close),
      cellClassName: 'text-right'
    },
    {
      key: 'close',
      header: 'A股收盘价',
      accessor: (row) => formatNumber(row.close),
      cellClassName: 'text-right'
    },
    {
      key: 'ah_comparison',
      header: 'AH比价',
      accessor: (row) => formatNumber(row.ah_comparison),
      cellClassName: 'text-right'
    },
    {
      key: 'ah_premium',
      header: 'AH溢价率',
      accessor: (row) => (
        <span className={`font-medium ${(row.ah_premium ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
          {formatPercent(row.ah_premium)}
        </span>
      ),
      cellClassName: 'text-right'
    },
    {
      key: 'hk_pct_chg',
      header: '港股涨跌幅',
      accessor: (row) => (
        <span className={`font-medium ${(row.hk_pct_chg ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
          {formatPercent(row.hk_pct_chg)}
        </span>
      ),
      cellClassName: 'text-right'
    },
    {
      key: 'pct_chg',
      header: 'A股涨跌幅',
      accessor: (row) => (
        <span className={`font-medium ${(row.pct_chg ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
          {formatPercent(row.pct_chg)}
        </span>
      ),
      cellClassName: 'text-right'
    }
  ], [])

  const mobileCard = useCallback((item: StkAhComparisonData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <div>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {item.hk_name || item.hk_code} / {item.name || item.ts_code}
          </span>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
            {item.hk_code} / {item.ts_code}
          </div>
        </div>
        <span className="text-xs text-gray-600 dark:text-gray-400">{formatDate(item.trade_date)}</span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">港股价格:</span>
          <span className="font-medium">{formatNumber(item.hk_close)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">A股价格:</span>
          <span className="font-medium">{formatNumber(item.close)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">AH比价:</span>
          <span className="font-medium">{formatNumber(item.ah_comparison)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">溢价率:</span>
          <span className={`font-medium ${(item.ah_premium ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
            {formatPercent(item.ah_premium)}
          </span>
        </div>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="AH股比价"
        description="同时在A股和港股上市的股票价格比价数据，用于分析估值差异和溢价情况"
        details={
          <>
            <div>接口：stk_ah_comparison</div>
            <div>积分：5000积分/次，单次最大1000行</div>
            <div>数据起始：2025-08-12，每日盘后17:00更新</div>
          </>
        }
        actions={
          <Button onClick={() => setShowSyncDialog(true)} disabled={syncing}>
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
                  <p className="text-sm font-medium text-muted-foreground">股票数量</p>
                  <p className="text-2xl font-bold mt-1">{statistics.stock_count}</p>
                  <p className="text-xs text-muted-foreground mt-1">AH同时上市</p>
                </div>
                <BarChart3 className="h-8 w-8 text-muted-foreground shrink-0" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">平均溢价率</p>
                  <p className={`text-2xl font-bold mt-1 ${(statistics.avg_premium ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {formatPercent(statistics.avg_premium)}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">A股相对港股溢价</p>
                </div>
                <Activity className="h-8 w-8 text-muted-foreground shrink-0" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">最高溢价率</p>
                  <p className="text-2xl font-bold mt-1 text-red-600">{formatPercent(statistics.max_premium)}</p>
                  <p className="text-xs text-muted-foreground mt-1">溢价最大的股票</p>
                </div>
                <TrendingUp className="h-8 w-8 text-red-400 shrink-0" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">最低溢价率</p>
                  <p className="text-2xl font-bold mt-1 text-green-600">{formatPercent(statistics.min_premium)}</p>
                  <p className="text-xs text-muted-foreground mt-1">溢价最小的股票</p>
                </div>
                <TrendingDown className="h-8 w-8 text-green-400 shrink-0" />
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
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="w-full sm:w-auto">
              <Label>交易日期</Label>
              <DatePicker date={tradeDate} onDateChange={setTradeDate} placeholder="留空默认最近有数据日期" />
            </div>
            <Button onClick={() => loadData(1)} disabled={loading} className="w-full sm:w-auto">
              <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
              查询
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="p-0">
          <DataTable
            columns={columns}
            data={data}
            loading={loading}
            emptyMessage="暂无数据"
            mobileCard={mobileCard}
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: (newPage) => loadData(newPage),
              onPageSizeChange: () => {},
              pageSizeOptions: [30]
            }}
          />
        </CardContent>
      </Card>

      {/* 同步对话框 */}
      <Dialog open={showSyncDialog} onOpenChange={setShowSyncDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>同步AH股比价数据</DialogTitle>
            <DialogDescription>
              所有参数均为可选，不填写参数将同步最近30天数据
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="sync-hk-code">港股代码</Label>
              <Input
                id="sync-hk-code"
                placeholder="如：02068.HK"
                value={syncHkCode}
                onChange={(e) => setSyncHkCode(e.target.value)}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="sync-ts-code">A股代码</Label>
              <Input
                id="sync-ts-code"
                placeholder="如：601068.SH"
                value={syncTsCode}
                onChange={(e) => setSyncTsCode(e.target.value)}
              />
            </div>

            <div className="grid gap-2">
              <Label>交易日期</Label>
              <DatePicker date={syncTradeDate} onDateChange={setSyncTradeDate} placeholder="选择交易日期" />
            </div>

            <div className="grid gap-2">
              <Label>日期范围（可选）</Label>
              <div className="flex gap-2 items-center">
                <DatePicker date={syncStartDate} onDateChange={setSyncStartDate} placeholder="开始日期" />
                <span className="text-muted-foreground">至</span>
                <DatePicker date={syncEndDate} onDateChange={setSyncEndDate} placeholder="结束日期" />
              </div>
            </div>

            <div className="rounded-lg bg-amber-50 dark:bg-amber-950 p-3 border border-amber-200 dark:border-amber-800">
              <p className="text-sm text-amber-800 dark:text-amber-200">
                <strong>注意：</strong>此接口消耗 5000 积分起，单次最大返回 1000 条数据。数据从2025年8月12日开始，每天盘后17:00更新。
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSyncDialog(false)}>取消</Button>
            <Button onClick={handleSyncConfirm} disabled={syncing}>
              {syncing ? (
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
              ) : (
                <><RefreshCw className="h-4 w-4 mr-1" />开始同步</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
