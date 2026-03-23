'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { hkHoldApi, type HkHoldQueryParams, type HkHoldData, type HkHoldStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, Users, Calendar, Database } from 'lucide-react'

export default function HkHoldPage() {
  const [data, setData] = useState<HkHoldData[]>([])
  const [statistics, setStatistics] = useState<HkHoldStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState<string>('')
  const [code, setCode] = useState<string>('')
  const [syncing, setSyncing] = useState(false)

  // 同步弹窗状态
  const [showSyncDialog, setShowSyncDialog] = useState(false)
  const [syncCode, setSyncCode] = useState<string>('')
  const [syncTsCode, setSyncTsCode] = useState<string>('')
  const [syncTradeDate, setSyncTradeDate] = useState<Date | undefined>(undefined)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)
  const [syncExchange, setSyncExchange] = useState<string>('')

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // 存储活跃的任务回调
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)

      const params: HkHoldQueryParams = {
        limit: pageSize
      }

      if (startDate) {
        params.start_date = startDate.toISOString().split('T')[0]
      }
      if (endDate) {
        params.end_date = endDate.toISOString().split('T')[0]
      }
      if (tsCode.trim()) {
        params.ts_code = tsCode.trim()
      }
      if (code.trim()) {
        params.code = code.trim()
      }

      const response = await hkHoldApi.getData(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics || null)
        setTotal(response.data.total || 0)
      } else {
        throw new Error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      const errorMsg = err.message || '加载数据失败'
      setError(errorMsg)
      toast.error('加载失败', { description: errorMsg })
    } finally {
      setIsLoading(false)
    }
  }, [startDate, endDate, tsCode, code, pageSize])

  // 初始加载
  useEffect(() => {
    loadData()
  }, [loadData])

  // 打开同步弹窗
  const openSyncDialog = () => {
    setShowSyncDialog(true)
  }

  // 关闭同步弹窗
  const closeSyncDialog = () => {
    setShowSyncDialog(false)
    setSyncCode('')
    setSyncTsCode('')
    setSyncTradeDate(undefined)
    setSyncStartDate(undefined)
    setSyncEndDate(undefined)
    setSyncExchange('')
  }

  // 异步同步数据
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params: any = {}
      if (syncCode.trim()) params.code = syncCode.trim()
      if (syncTsCode.trim()) params.ts_code = syncTsCode.trim()
      if (syncTradeDate) params.trade_date = syncTradeDate.toISOString().split('T')[0]
      if (syncStartDate) params.start_date = syncStartDate.toISOString().split('T')[0]
      if (syncEndDate) params.end_date = syncEndDate.toISOString().split('T')[0]
      if (syncExchange.trim()) params.exchange = syncExchange.trim()

      const response = await hkHoldApi.syncAsync(params)

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

        // 注册任务完成回调
        const completionCallback = (task: any) => {
          if (task.status === 'success') {
            loadData().catch(() => {})
            toast.success('数据同步完成', {
              description: '北向资金持股数据已更新'
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

        toast.success('任务已提交', {
          description: `"${response.data.display_name}" 已开始执行，可在任务面板查看进度`
        })

        // 关闭弹窗
        closeSyncDialog()
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

  // 格式化数字
  const formatNumber = (value: number | null | undefined, decimals: number = 0): string => {
    if (value === null || value === undefined) return '-'
    return value.toLocaleString('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
  }

  // 移动端卡片视图
  const mobileCard = useCallback((item: HkHoldData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">日期</span>
        <span className="font-medium">{item.trade_date}</span>
      </div>

      {item.ts_code && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">A股代码</span>
          <span className="font-medium">{item.ts_code}</span>
        </div>
      )}

      {item.code && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">港股代码</span>
          <span className="font-medium">{item.code}</span>
        </div>
      )}

      {item.name && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">股票名称</span>
          <span className="font-medium">{item.name}</span>
        </div>
      )}

      {item.exchange && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">交易所</span>
          <span className="font-medium">{item.exchange}</span>
        </div>
      )}

      {item.vol !== null && item.vol !== undefined && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">持股数(万股)</span>
          <span className="font-medium">{formatNumber(item.vol)}</span>
        </div>
      )}

      {item.amount !== null && item.amount !== undefined && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">持股额(百万元)</span>
          <span className="font-medium">{formatNumber(item.amount, 2)}</span>
        </div>
      )}

      {item.ratio !== null && item.ratio !== undefined && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">持股比例(%)</span>
          <span className="font-medium">{formatNumber(item.ratio, 2)}</span>
        </div>
      )}
    </div>
  ), [])

  // 桌面端表格列定义
  const columns: Column<HkHoldData>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => row.trade_date
    },
    {
      key: 'ts_code',
      header: 'A股代码',
      accessor: (row) => row.ts_code || '-'
    },
    {
      key: 'code',
      header: '港股代码',
      accessor: (row) => row.code || '-'
    },
    {
      key: 'name',
      header: '股票名称',
      accessor: (row) => row.name || '-'
    },
    {
      key: 'exchange',
      header: '交易所',
      accessor: (row) => row.exchange || '-'
    },
    {
      key: 'vol',
      header: '持股数(万股)',
      accessor: (row) => formatNumber(row.vol),
      className: 'text-right'
    },
    {
      key: 'amount',
      header: '持股额(百万元)',
      accessor: (row) => formatNumber(row.amount, 2),
      className: 'text-right'
    },
    {
      key: 'ratio',
      header: '持股比例(%)',
      accessor: (row) => formatNumber(row.ratio, 2),
      className: 'text-right'
    }
  ], [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="北向资金持股"
        description="查询北向资金（沪港通、深港通）持股数据，覆盖全部历史数据"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">总记录数</CardTitle>
              <Database className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(statistics.total_count)}</div>
              <p className="text-xs text-muted-foreground">条</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">股票数</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(statistics.stock_count)}</div>
              <p className="text-xs text-muted-foreground">只</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">平均持股数</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(statistics.avg_vol)}</div>
              <p className="text-xs text-muted-foreground">万股</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最高持股比例</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(statistics.max_ratio, 2)}</div>
              <p className="text-xs text-muted-foreground">%</p>
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
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">A股代码</label>
              <Input
                placeholder="如：000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>

            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">港股代码</label>
              <Input
                placeholder="如：00700.HK"
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
            </div>

            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">开始日期</label>
              <DatePicker date={startDate} onSelect={setStartDate} />
            </div>

            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">结束日期</label>
              <DatePicker date={endDate} onSelect={setEndDate} />
            </div>

            <Button onClick={loadData} disabled={isLoading}>
              {isLoading ? '查询中...' : '查询'}
            </Button>

            <Button
              variant="default"
              onClick={openSyncDialog}
              disabled={syncing}
            >
              <RefreshCw className="h-4 w-4 mr-1" />
              同步数据
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card className="p-0 sm:p-0 overflow-hidden">
        {/* 移动端视图 */}
        <div className="sm:hidden">
          <div className="px-4 py-3 border-b bg-muted/50">
            <h3 className="text-sm font-medium">持股数据</h3>
          </div>
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {!isLoading && !error && data.map((item, index) => (
              <div
                key={`${item.trade_date}-${item.ts_code}-${item.code}`}
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

          {/* 移动端状态显示 */}
          {isLoading && (
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
          {!isLoading && !error && data.length === 0 && (
            <div className="p-8 text-center">
              <p className="text-sm text-muted-foreground">暂无数据</p>
            </div>
          )}

          {/* 移动端分页 */}
          {!isLoading && !error && data.length > 0 && (
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
            loading={isLoading}
            error={error}
            emptyMessage="暂无数据"
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: (newPage) => setPage(newPage),
              onPageSizeChange: (newPageSize) => {
                setPageSize(newPageSize)
                setPage(1)
              },
              pageSizeOptions: [10, 20, 30, 50, 100]
            }}
          />
        </div>
      </Card>

      {/* 同步参数弹窗 */}
      <Dialog open={showSyncDialog} onOpenChange={setShowSyncDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>同步北向资金持股数据</DialogTitle>
            <DialogDescription>
              所有参数均为可选，不填写参数将同步所有可用数据
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="sync-code">港股代码</Label>
              <Input
                id="sync-code"
                placeholder="如：00700.HK"
                value={syncCode}
                onChange={(e) => setSyncCode(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                港股代码格式，如：00700.HK
              </p>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="sync-ts-code">A股代码</Label>
              <Input
                id="sync-ts-code"
                placeholder="如：000001.SZ"
                value={syncTsCode}
                onChange={(e) => setSyncTsCode(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                A股代码，如：000001.SZ
              </p>
            </div>

            <div className="grid gap-2">
              <Label>交易日期</Label>
              <DatePicker
                date={syncTradeDate}
                onSelect={setSyncTradeDate}
                placeholder="选择交易日期"
              />
              <p className="text-xs text-muted-foreground">
                查询指定交易日的数据
              </p>
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
              <p className="text-xs text-muted-foreground">
                查询日期范围内的数据
              </p>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="sync-exchange">交易所</Label>
              <Input
                id="sync-exchange"
                placeholder="如：HK"
                value={syncExchange}
                onChange={(e) => setSyncExchange(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                交易所代码，如：HK
              </p>
            </div>

            <div className="rounded-lg bg-amber-50 dark:bg-amber-950 p-3 border border-amber-200 dark:border-amber-800">
              <p className="text-sm text-amber-800 dark:text-amber-200">
                <strong>注意：</strong>此接口消耗 2000 积分/次
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={closeSyncDialog}
              disabled={syncing}
            >
              取消
            </Button>
            <Button
              onClick={handleSync}
              disabled={syncing}
            >
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
