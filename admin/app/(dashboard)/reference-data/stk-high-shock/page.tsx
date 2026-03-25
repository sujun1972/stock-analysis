'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, Building2, AlertCircle } from 'lucide-react'
import { stkHighShockApi, type StkHighShockData, type StkHighShockStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'

export default function StkHighShockPage() {
  // 状态管理
  const [data, setData] = useState<StkHighShockData[]>([])
  const [statistics, setStatistics] = useState<StkHighShockStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [syncing, setSyncing] = useState(false)

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // 任务存储
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

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

      const response = await stkHighShockApi.getData(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setTotal(response.data.total || 0)
      } else {
        throw new Error(response.message || '加载数据失败')
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast.error('加载失败', {
        description: err.message || '无法加载数据'
      })
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, pageSize])

  // 加载统计数据
  const loadStatistics = useCallback(async () => {
    try {
      const params: any = {}

      if (startDate) {
        params.start_date = startDate.toISOString().split('T')[0]
      }
      if (endDate) {
        params.end_date = endDate.toISOString().split('T')[0]
      }

      const response = await stkHighShockApi.getStatistics(params)

      if (response.code === 200 && response.data) {
        setStatistics(response.data)
      }
    } catch (err) {
      console.error('加载统计数据失败:', err)
    }
  }, [startDate, endDate])

  // 初始加载
  useEffect(() => {
    loadData()
    loadStatistics()
  }, [loadData, loadStatistics])

  // 异步同步数据
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params: any = {}

      if (startDate) {
        params.start_date = startDate.toISOString().split('T')[0]
      }
      if (endDate) {
        params.end_date = endDate.toISOString().split('T')[0]
      }

      const response = await stkHighShockApi.syncAsync(params)

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
            loadStatistics().catch(() => {})
            toast.success('数据同步完成', {
              description: '个股严重异常波动数据已更新'
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
  }, [unregisterCompletionCallback])

  // 表格列定义
  const columns: Column<StkHighShockData>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '公告日期',
      accessor: (row) => row.trade_date,
      width: '120px'
    },
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code,
      width: '110px'
    },
    {
      key: 'name',
      header: '股票名称',
      accessor: (row) => row.name,
      width: '120px'
    },
    {
      key: 'trade_market',
      header: (
        <>
          <span className="sm:hidden">市场</span>
          <span className="hidden sm:inline">交易所</span>
        </>
      ),
      accessor: (row) => row.trade_market,
      width: '100px'
    },
    {
      key: 'reason',
      header: '异常说明',
      accessor: (row) => (
        <span className="text-sm" title={row.reason}>
          {row.reason}
        </span>
      )
    },
    {
      key: 'period',
      header: '异常期间',
      accessor: (row) => row.period,
      width: '200px'
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: StkHighShockData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">股票</span>
        <span className="font-medium">{item.name} ({item.ts_code})</span>
      </div>

      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">公告日期</span>
        <span className="font-medium">{item.trade_date}</span>
      </div>

      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">交易所</span>
        <span className="font-medium">{item.trade_market}</span>
      </div>

      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">异常期间</span>
        <span className="text-sm">{item.period}</span>
      </div>

      <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
        <div className="text-sm text-gray-600 dark:text-gray-400 mb-1">异常说明</div>
        <div className="text-sm">{item.reason}</div>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="个股严重异常波动"
        description="根据证券交易所交易规则的有关规定，交易所每日发布股票交易严重异常波动情况"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">总记录数</p>
                  <p className="text-2xl font-bold">{statistics.total_count}</p>
                </div>
                <AlertCircle className="h-8 w-8 text-orange-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">异常股票数</p>
                  <p className="text-2xl font-bold">{statistics.stock_count}</p>
                </div>
                <TrendingUp className="h-8 w-8 text-red-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">涉及交易所</p>
                  <p className="text-2xl font-bold">{statistics.market_count}</p>
                </div>
                <Building2 className="h-8 w-8 text-blue-500" />
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
              <label className="text-sm font-medium mb-2 block">开始日期</label>
              <DatePicker
                date={startDate}
                onDateChange={setStartDate}
              />
            </div>
            <div className="w-full sm:w-auto">
              <label className="text-sm font-medium mb-2 block">结束日期</label>
              <DatePicker
                date={endDate}
                onDateChange={setEndDate}
              />
            </div>
            <Button
              variant="outline"
              size="default"
              onClick={loadData}
              disabled={loading}
              className="w-full sm:w-auto"
            >
              查询
            </Button>
            <Button
              variant="default"
              size="default"
              onClick={handleSync}
              disabled={syncing}
              className="w-full sm:w-auto"
            >
              {syncing ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                  同步中...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4 mr-1" />
                  同步数据
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card className="p-0 sm:p-0 overflow-hidden">
        {/* 移动端视图 */}
        <div className="sm:hidden">
          <div className="px-4 py-3 border-b bg-muted/50">
            <h3 className="text-sm font-medium">异常波动数据</h3>
          </div>
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {!loading && !error && data.map((item, index) => (
              <div
                key={index}
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
            emptyMessage="暂无个股严重异常波动数据"
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
    </div>
  )
}
