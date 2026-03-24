'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DataTable, Column } from '@/components/common/DataTable'
import { ggtMonthlyApi, type GgtMonthlyData, type GgtMonthlyStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, TrendingDown, DollarSign, Activity } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'

export default function GgtMonthlyPage() {
  const [data, setData] = useState<GgtMonthlyData[]>([])
  const [statistics, setStatistics] = useState<GgtMonthlyStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [startMonth, setStartMonth] = useState('')
  const [endMonth, setEndMonth] = useState('')
  const [syncing, setSyncing] = useState(false)

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
      setLoading(true)
      setError(null)

      const response = await ggtMonthlyApi.getData({
        start_month: startMonth || undefined,
        end_month: endMonth || undefined,
        limit: pageSize
      })

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setTotal(response.data.total || 0)
        setStatistics(response.data.statistics || null)
      } else {
        throw new Error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast.error('加载失败', {
        description: err.message || '无法加载港股通每月成交统计数据'
      })
    } finally {
      setLoading(false)
    }
  }, [startMonth, endMonth, pageSize])

  // 初始加载
  useEffect(() => {
    loadData()
  }, [loadData])

  // 组件卸载时清理所有活跃的任务回调
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

  // 异步同步数据
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params: {
        start_month?: string
        end_month?: string
      } = {}

      if (startMonth) params.start_month = startMonth
      if (endMonth) params.end_month = endMonth

      const response = await ggtMonthlyApi.syncAsync(params)

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
              description: '港股通每月成交统计数据已更新'
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

  // 格式化数字
  const formatNumber = (num: number | null | undefined, decimals: number = 2) => {
    if (num === null || num === undefined) return '0.00'
    return num.toFixed(decimals)
  }

  // 准备图表数据
  const chartData = useMemo(() => {
    return data.slice(0, 12).reverse().map(item => ({
      month: item.month,
      日均买入: item.day_buy_amt,
      日均卖出: item.day_sell_amt,
      总买入: item.total_buy_amt,
      总卖出: item.total_sell_amt
    }))
  }, [data])

  // 表格列定义
  const columns: Column<GgtMonthlyData>[] = useMemo(() => [
    {
      key: 'month',
      header: '月度',
      accessor: (row) => row.month
    },
    {
      key: 'day_buy_amt',
      header: '日均买入(亿元)',
      accessor: (row) => formatNumber(row.day_buy_amt)
    },
    {
      key: 'day_buy_vol',
      header: '日均买入笔数(万笔)',
      accessor: (row) => formatNumber(row.day_buy_vol)
    },
    {
      key: 'day_sell_amt',
      header: '日均卖出(亿元)',
      accessor: (row) => formatNumber(row.day_sell_amt)
    },
    {
      key: 'day_sell_vol',
      header: '日均卖出笔数(万笔)',
      accessor: (row) => formatNumber(row.day_sell_vol)
    },
    {
      key: 'total_buy_amt',
      header: '总买入(亿元)',
      accessor: (row) => formatNumber(row.total_buy_amt)
    },
    {
      key: 'total_buy_vol',
      header: '总买入笔数(万笔)',
      accessor: (row) => formatNumber(row.total_buy_vol)
    },
    {
      key: 'total_sell_amt',
      header: '总卖出(亿元)',
      accessor: (row) => formatNumber(row.total_sell_amt)
    },
    {
      key: 'total_sell_vol',
      header: '总卖出笔数(万笔)',
      accessor: (row) => formatNumber(row.total_sell_vol)
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: GgtMonthlyData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">月度</span>
        <span className="font-medium">{item.month}</span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div className="flex justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-400">日均买入</span>
          <span className="font-medium">{formatNumber(item.day_buy_amt)}亿</span>
        </div>
        <div className="flex justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-400">日均卖出</span>
          <span className="font-medium">{formatNumber(item.day_sell_amt)}亿</span>
        </div>
        <div className="flex justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-400">总买入</span>
          <span className="font-medium">{formatNumber(item.total_buy_amt)}亿</span>
        </div>
        <div className="flex justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-400">总卖出</span>
          <span className="font-medium">{formatNumber(item.total_sell_amt)}亿</span>
        </div>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="港股通每月成交统计"
        description="港股通每月成交信息，数据从2014年开始（Tushare ggt_monthly接口，5000积分/次）"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">日均买入均值</p>
                  <p className="text-2xl font-bold">{formatNumber(statistics.avg_day_buy_amt)}亿</p>
                </div>
                <DollarSign className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">累计总买入</p>
                  <p className="text-2xl font-bold">{formatNumber(statistics.sum_total_buy_amt)}亿</p>
                </div>
                <TrendingUp className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">最大总买入</p>
                  <p className="text-2xl font-bold">{formatNumber(statistics.max_total_buy_amt)}亿</p>
                </div>
                <Activity className="h-8 w-8 text-orange-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">最大总卖出</p>
                  <p className="text-2xl font-bold">{formatNumber(statistics.max_total_sell_amt)}亿</p>
                </div>
                <TrendingDown className="h-8 w-8 text-red-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 趋势图表 */}
      {chartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>港股通每月成交趋势</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[400px] w-full overflow-x-auto">
              <div style={{ minWidth: '600px', height: '100%' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 40 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="month"
                      angle={-45}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis label={{ value: '金额(亿元)', angle: -90, position: 'insideLeft' }} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="日均买入" stroke="#3b82f6" strokeWidth={2} />
                    <Line type="monotone" dataKey="日均卖出" stroke="#ef4444" strokeWidth={2} />
                    <Line type="monotone" dataKey="总买入" stroke="#10b981" strokeWidth={2} />
                    <Line type="monotone" dataKey="总卖出" stroke="#f59e0b" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 筛选和操作区域 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="start-month">开始月度</Label>
                <Input
                  id="start-month"
                  type="month"
                  value={startMonth}
                  onChange={(e) => setStartMonth(e.target.value)}
                  placeholder="YYYY-MM"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="end-month">结束月度</Label>
                <Input
                  id="end-month"
                  type="month"
                  value={endMonth}
                  onChange={(e) => setEndMonth(e.target.value)}
                  placeholder="YYYY-MM"
                />
              </div>
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <Button
                variant="outline"
                size="sm"
                onClick={loadData}
                disabled={loading}
                className="flex-1 sm:flex-initial"
              >
                <RefreshCw className="h-4 w-4 mr-1" />
                查询
              </Button>
              <Button
                variant="default"
                size="sm"
                onClick={handleSync}
                disabled={syncing}
                className="flex-1 sm:flex-initial"
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
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card className="p-0 sm:p-0 overflow-hidden">
        {/* 移动端视图 */}
        <div className="sm:hidden">
          <div className="px-4 py-3 border-b bg-muted/50">
            <h3 className="text-sm font-medium">港股通每月成交数据</h3>
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

          {/* 移动端状态显示 */}
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
