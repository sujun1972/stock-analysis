'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { DatePicker } from '@/components/ui/date-picker'
import { stkHolderNumberApi } from '@/lib/api'
import type { StkHolderNumberData, StkHolderNumberStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, TrendingDown, Users, BarChart3 } from 'lucide-react'

export default function StkHolderNumberPage() {
  const [data, setData] = useState<StkHolderNumberData[]>([])
  const [statistics, setStatistics] = useState<StkHolderNumberStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [syncing, setSyncing] = useState(false)

  // 筛选条件
  const [tsCode, setTsCode] = useState('')
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // 任务管理
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

      if (tsCode.trim()) {
        params.ts_code = tsCode.trim()
      }
      if (startDate) {
        params.start_date = startDate.toISOString().split('T')[0]
      }
      if (endDate) {
        params.end_date = endDate.toISOString().split('T')[0]
      }

      const [dataResponse, statsResponse] = await Promise.all([
        stkHolderNumberApi.getData(params),
        stkHolderNumberApi.getStatistics({
          ts_code: params.ts_code,
          start_date: params.start_date,
          end_date: params.end_date
        })
      ])

      if (dataResponse.code === 200 && dataResponse.data) {
        setData(dataResponse.data.items || [])
        setTotal(dataResponse.data.total || 0)
      }

      if (statsResponse.code === 200 && statsResponse.data) {
        setStatistics(statsResponse.data)
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast.error('加载数据失败', { description: err.message })
    } finally {
      setLoading(false)
    }
  }, [tsCode, startDate, endDate, pageSize])

  // 初始加载
  useEffect(() => {
    loadData()
  }, [loadData])

  // 异步同步数据
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params: any = {}
      if (tsCode.trim()) {
        params.ts_code = tsCode.trim()
      }
      if (startDate) {
        params.start_date = startDate.toISOString().split('T')[0]
      }
      if (endDate) {
        params.end_date = endDate.toISOString().split('T')[0]
      }

      const response = await stkHolderNumberApi.syncAsync(params)

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

        // 注册完成回调
        const completionCallback = (task: any) => {
          if (task.status === 'success') {
            loadData().catch(() => {})
            toast.success('数据同步完成', {
              description: '股东人数数据已更新'
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
      }
    } catch (err: any) {
      toast.error('同步失败', {
        description: err.message || '无法同步数据'
      })
    } finally {
      setSyncing(false)
    }
  }

  // 清理回调
  useEffect(() => {
    return () => {
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
    }
  }, [unregisterCompletionCallback])

  // 格式化数字
  const formatNumber = (num: number | null | undefined) => {
    if (num === null || num === undefined) return '-'
    return num.toLocaleString()
  }

  // 表格列定义
  const columns: Column<StkHolderNumberData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'ann_date',
      header: '公告日期',
      accessor: (row) => row.ann_date
    },
    {
      key: 'end_date',
      header: '截止日期',
      accessor: (row) => row.end_date
    },
    {
      key: 'holder_num',
      header: '股东户数',
      accessor: (row) => (
        <span className="font-medium">
          {formatNumber(row.holder_num)}
        </span>
      )
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: StkHolderNumberData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">股票代码</span>
        <span className="font-medium">{item.ts_code}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">公告日期</span>
        <span>{item.ann_date}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">截止日期</span>
        <span>{item.end_date}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">股东户数</span>
        <span className="font-medium text-blue-600 dark:text-blue-400">
          {formatNumber(item.holder_num)}
        </span>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="股东人数"
        description="上市公司股东户数数据（数据不定期公布）"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">记录数</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(statistics.record_count)}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">平均股东户数</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(Math.round(statistics.avg_holder_num))}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最大股东户数</CardTitle>
              <TrendingUp className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {formatNumber(statistics.max_holder_num)}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最小股东户数</CardTitle>
              <TrendingDown className="h-4 w-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">
                {formatNumber(statistics.min_holder_num)}
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
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <Input
                placeholder="股票代码（如：000001.SZ）"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="flex-1 sm:flex-none">
              <DatePicker
                date={startDate}
                onDateChange={setStartDate}
                placeholder="开始日期"
              />
            </div>
            <div className="flex-1 sm:flex-none">
              <DatePicker
                date={endDate}
                onDateChange={setEndDate}
                placeholder="结束日期"
              />
            </div>
            <Button onClick={loadData} disabled={loading}>
              查询
            </Button>
            <Button onClick={handleSync} disabled={syncing} variant="default">
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
            <h3 className="text-sm font-medium">股东人数数据</h3>
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

          {/* 移动端状态 */}
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
