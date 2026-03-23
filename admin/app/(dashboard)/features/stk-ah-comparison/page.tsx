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
import { RefreshCw, TrendingUp, TrendingDown, BarChart3, Calendar } from 'lucide-react'
import type { StkAhComparisonData, StkAhComparisonStatistics } from '@/lib/api/stk-ah-comparison'

export default function StkAhComparisonPage() {
  const [data, setData] = useState<StkAhComparisonData[]>([])
  const [statistics, setStatistics] = useState<StkAhComparisonStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [syncing, setSyncing] = useState(false)

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // 同步对话框状态
  const [showSyncDialog, setShowSyncDialog] = useState(false)
  const [syncHkCode, setSyncHkCode] = useState<string>('')
  const [syncTsCode, setSyncTsCode] = useState<string>('')
  const [syncTradeDate, setSyncTradeDate] = useState<Date | undefined>(undefined)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  // 存储活跃的任务回调
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params: any = {
        limit: pageSize
      }

      if (startDate) {
        params.start_date = startDate.toISOString().split('T')[0]
      }
      if (endDate) {
        params.end_date = endDate.toISOString().split('T')[0]
      }

      const response = await stkAhComparisonApi.getData(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics || null)
        setTotal(response.data.total || 0)
      } else {
        throw new Error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast.error('加载失败', {
        description: err.message || '无法加载AH股比价数据'
      })
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, pageSize])

  // 初始加载
  useEffect(() => {
    loadData()
  }, [loadData])

  // 打开同步对话框
  const openSyncDialog = () => {
    setShowSyncDialog(true)
  }

  // 关闭同步对话框
  const closeSyncDialog = () => {
    setShowSyncDialog(false)
    setSyncHkCode('')
    setSyncTsCode('')
    setSyncTradeDate(undefined)
    setSyncStartDate(undefined)
    setSyncEndDate(undefined)
  }

  // 异步同步数据
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params: any = {}
      if (syncHkCode.trim()) params.hk_code = syncHkCode.trim()
      if (syncTsCode.trim()) params.ts_code = syncTsCode.trim()
      if (syncTradeDate) params.trade_date = syncTradeDate.toISOString().split('T')[0]
      if (syncStartDate) params.start_date = syncStartDate.toISOString().split('T')[0]
      if (syncEndDate) params.end_date = syncEndDate.toISOString().split('T')[0]

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
            loadData().catch(() => {})
            toast.success('数据同步完成', {
              description: 'AH股比价数据已更新'
            })
          } else if (task.status === 'failure') {
            toast.error('数据同步失败', {
              description: task.error || '同步过程中发生错误'
            })
          }
          unregisterCompletionCallback(taskId, completionCallback)
          activeCallbacksRef.current.delete(taskId)
        }

        activeCallbacksRef.current.set(taskId, completionCallback)
        registerCompletionCallback(taskId, completionCallback)

        triggerPoll()

        closeSyncDialog()

        toast.success('任务已提交', {
          description: `"${response.data.display_name}" 已开始执行，可在任务面板查看进度`
        })
      } else {
        throw new Error(response.message || '同步失败')
      }
    } catch (err: any) {
      toast.error('同步失败', {
        description: err.message || '无法同步数据'
      })
    } finally {
      setSyncing(false)
    }
  }

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

  // 格式化日期
  const formatDate = (dateStr: string) => {
    if (!dateStr || dateStr.length !== 8) return dateStr
    return `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`
  }

  // 格式化数值
  const formatNumber = (num: number | null | undefined, decimals: number = 2) => {
    if (num === null || num === undefined) return '-'
    return num.toFixed(decimals)
  }

  // 格式化百分比
  const formatPercent = (num: number | null | undefined) => {
    if (num === null || num === undefined) return '-'
    const sign = num >= 0 ? '+' : ''
    return `${sign}${num.toFixed(2)}%`
  }

  // 表格列定义
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
      accessor: (row) => formatNumber(row.hk_close)
    },
    {
      key: 'close',
      header: 'A股收盘价',
      accessor: (row) => formatNumber(row.close)
    },
    {
      key: 'ah_comparison',
      header: 'AH比价',
      accessor: (row) => formatNumber(row.ah_comparison)
    },
    {
      key: 'ah_premium',
      header: (
        <>
          <span className="sm:hidden">溢价</span>
          <span className="hidden sm:inline">AH溢价率</span>
        </>
      ),
      accessor: (row) => (
        <span className={`font-medium ${
          (row.ah_premium ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'
        }`}>
          {formatPercent(row.ah_premium)}
        </span>
      )
    },
    {
      key: 'hk_pct_chg',
      header: '港股涨跌幅',
      accessor: (row) => (
        <span className={`font-medium ${
          (row.hk_pct_chg ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'
        }`}>
          {formatPercent(row.hk_pct_chg)}
        </span>
      )
    },
    {
      key: 'pct_chg',
      header: 'A股涨跌幅',
      accessor: (row) => (
        <span className={`font-medium ${
          (row.pct_chg ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'
        }`}>
          {formatPercent(row.pct_chg)}
        </span>
      )
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: StkAhComparisonData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <div>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {item.hk_name} / {item.name}
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
          <span className={`font-medium ${
            (item.ah_premium ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'
          }`}>
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
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">股票数量</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.stock_count}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">平均溢价率</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${
                statistics.avg_premium >= 0 ? 'text-red-600' : 'text-green-600'
              }`}>
                {formatPercent(statistics.avg_premium)}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最高溢价率</CardTitle>
              <TrendingUp className="h-4 w-4 text-red-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {formatPercent(statistics.max_premium)}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最低溢价率</CardTitle>
              <TrendingDown className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {formatPercent(statistics.min_premium)}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选和操作区域 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="w-full sm:w-auto">
              <Label>开始日期</Label>
              <DatePicker
                date={startDate}
                onSelect={setStartDate}
                placeholder="选择开始日期"
              />
            </div>
            <div className="w-full sm:w-auto">
              <Label>结束日期</Label>
              <DatePicker
                date={endDate}
                onSelect={setEndDate}
                placeholder="选择结束日期"
              />
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <Button onClick={loadData} disabled={loading} className="flex-1 sm:flex-none">
                <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
                查询
              </Button>
              <Button onClick={openSyncDialog} disabled={syncing} variant="default" className="flex-1 sm:flex-none">
                <Calendar className="h-4 w-4 mr-1" />
                同步数据
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
            <h3 className="text-sm font-medium">AH股比价数据</h3>
          </div>
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {!loading && !error && data.map((item, index) => (
              <div
                key={`${item.hk_code}-${item.ts_code}-${item.trade_date}`}
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

          {!loading && !error && data.length > 0 && (
            <div className="p-4 border-t bg-muted/30">
              <div className="flex items-center justify-between">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(Math.max(1, page - 1))}
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
                  onClick={() => setPage(Math.min(Math.ceil(total / pageSize), page + 1))}
                  disabled={page >= Math.ceil(total / pageSize)}
                >
                  下一页
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* 桌面端表格视图 */}
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
              onPageChange: (newPage) => {
                setPage(newPage)
              },
              onPageSizeChange: (newPageSize) => {
                setPageSize(newPageSize)
                setPage(1)
              },
              pageSizeOptions: [10, 20, 30, 50, 100]
            }}
          />
        </div>
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

            <div className="rounded-lg bg-amber-50 dark:bg-amber-950 p-3 border border-amber-200 dark:border-amber-800">
              <p className="text-sm text-amber-800 dark:text-amber-200">
                <strong>注意：</strong>此接口消耗 5000 积分起，单次最大返回 1000 条数据。数据从2025年8月12日开始，每天盘后17:00更新。
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
