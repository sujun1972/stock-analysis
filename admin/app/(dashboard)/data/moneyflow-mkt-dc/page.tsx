'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { apiClient } from '@/lib/api-client'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, TrendingDown, Activity, DollarSign } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

// 数据类型定义
interface MoneyflowMktDcData {
  trade_date: string
  close_sh: number
  pct_change_sh: number
  close_sz: number
  pct_change_sz: number
  net_amount: number
  net_amount_rate: number
  buy_elg_amount: number
  buy_elg_amount_rate: number
  buy_lg_amount: number
  buy_lg_amount_rate: number
  buy_md_amount: number
  buy_md_amount_rate: number
  buy_sm_amount: number
  buy_sm_amount_rate: number
}

interface Statistics {
  avg_net: number
  max_net: number
  min_net: number
  total_net: number
  avg_elg: number
  max_elg: number
  avg_lg: number
  max_lg: number
  avg_pct_sh: number
  avg_pct_sz: number
  latest_date: string
  earliest_date: string
  count: number
}

export default function MoneyflowMktDcPage() {
  const [data, setData] = useState<MoneyflowMktDcData[]>([])
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [syncing, setSyncing] = useState(false)

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // 存储活跃的任务回调（用于组件卸载时清理）
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  // 任务存储Hook
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params: {
        start_date?: string
        end_date?: string
        limit: number
        offset: number
      } = {
        limit: pageSize,
        offset: (page - 1) * pageSize
      }

      if (startDate) {
        params.start_date = startDate.toISOString().split('T')[0]
      }
      if (endDate) {
        params.end_date = endDate.toISOString().split('T')[0]
      }

      const response = await apiClient.getMoneyflowMktDc(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics)
        setTotal(response.data.total || 0)
      } else {
        throw new Error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast.error('加载失败', {
        description: err.message || '无法加载大盘资金流向数据'
      })
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, startDate, endDate])

  // 初始加载和翻页时重新加载
  useEffect(() => {
    loadData()
  }, [loadData])

  // 异步同步数据
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params: {
        start_date?: string
        end_date?: string
      } = {}

      if (startDate) {
        params.start_date = startDate.toISOString().split('T')[0]
      }
      if (endDate) {
        params.end_date = endDate.toISOString().split('T')[0]
      }

      const response = await apiClient.syncMoneyflowMktDcAsync(params)

      if (response.code === 200 && response.data) {
        const taskId = response.data.celery_task_id

        // 添加到任务存储
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
              description: '大盘资金流向数据已更新'
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

        // 立即触发轮询
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

  // 日期格式化函数
  const formatDate = (dateStr: string) => {
    if (!dateStr || dateStr.length !== 8) return dateStr
    return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
  }

  // 数值格式化（亿元）
  const formatAmount = (value: number) => {
    return (value / 100000000).toFixed(2)
  }

  // 百分比格式化
  const formatPercent = (value: number) => {
    return value.toFixed(2)
  }

  // 表格列定义
  const columns: Column<MoneyflowMktDcData>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '日期',
      accessor: (row) => formatDate(row.trade_date),
      sortable: true
    },
    {
      key: 'close_sh',
      header: '上证',
      accessor: (row) => (
        <div className="text-right">
          <div>{row.close_sh.toFixed(2)}</div>
          <div className={`text-xs ${row.pct_change_sh >= 0 ? 'text-red-600' : 'text-green-600'}`}>
            {row.pct_change_sh >= 0 ? '+' : ''}{formatPercent(row.pct_change_sh)}%
          </div>
        </div>
      )
    },
    {
      key: 'close_sz',
      header: '深证',
      accessor: (row) => (
        <div className="text-right">
          <div>{row.close_sz.toFixed(2)}</div>
          <div className={`text-xs ${row.pct_change_sz >= 0 ? 'text-red-600' : 'text-green-600'}`}>
            {row.pct_change_sz >= 0 ? '+' : ''}{formatPercent(row.pct_change_sz)}%
          </div>
        </div>
      )
    },
    {
      key: 'net_amount',
      header: '主力净流入',
      accessor: (row) => (
        <div className="text-right">
          <div className={row.net_amount >= 0 ? 'text-red-600' : 'text-green-600'}>
            {formatAmount(row.net_amount)}亿
          </div>
          <div className="text-xs text-gray-500">
            {formatPercent(row.net_amount_rate)}%
          </div>
        </div>
      ),
      sortable: true
    },
    {
      key: 'buy_elg_amount',
      header: '超大单',
      accessor: (row) => (
        <div className="text-right">
          <div className={row.buy_elg_amount >= 0 ? 'text-red-600' : 'text-green-600'}>
            {formatAmount(row.buy_elg_amount)}亿
          </div>
        </div>
      )
    },
    {
      key: 'buy_lg_amount',
      header: '大单',
      accessor: (row) => (
        <div className="text-right">
          <div className={row.buy_lg_amount >= 0 ? 'text-red-600' : 'text-green-600'}>
            {formatAmount(row.buy_lg_amount)}亿
          </div>
        </div>
      )
    },
    {
      key: 'buy_md_amount',
      header: '中单',
      accessor: (row) => (
        <div className="text-right">
          <div className={row.buy_md_amount >= 0 ? 'text-red-600' : 'text-green-600'}>
            {formatAmount(row.buy_md_amount)}亿
          </div>
        </div>
      )
    },
    {
      key: 'buy_sm_amount',
      header: '小单',
      accessor: (row) => (
        <div className="text-right">
          <div className={row.buy_sm_amount >= 0 ? 'text-red-600' : 'text-green-600'}>
            {formatAmount(row.buy_sm_amount)}亿
          </div>
        </div>
      )
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: MoneyflowMktDcData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">日期</span>
        <span className="font-medium">{formatDate(item.trade_date)}</span>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="flex flex-col">
          <span className="text-xs text-gray-600 dark:text-gray-400">上证</span>
          <span>{item.close_sh.toFixed(2)}</span>
          <span className={`text-xs ${item.pct_change_sh >= 0 ? 'text-red-600' : 'text-green-600'}`}>
            {item.pct_change_sh >= 0 ? '+' : ''}{formatPercent(item.pct_change_sh)}%
          </span>
        </div>

        <div className="flex flex-col">
          <span className="text-xs text-gray-600 dark:text-gray-400">深证</span>
          <span>{item.close_sz.toFixed(2)}</span>
          <span className={`text-xs ${item.pct_change_sz >= 0 ? 'text-red-600' : 'text-green-600'}`}>
            {item.pct_change_sz >= 0 ? '+' : ''}{formatPercent(item.pct_change_sz)}%
          </span>
        </div>
      </div>

      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">主力净流入</span>
        <div className="text-right">
          <div className={`font-medium ${item.net_amount >= 0 ? 'text-red-600' : 'text-green-600'}`}>
            {formatAmount(item.net_amount)}亿
          </div>
          <div className="text-xs text-gray-500">
            {formatPercent(item.net_amount_rate)}%
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">超大单</span>
          <span className={item.buy_elg_amount >= 0 ? 'text-red-600' : 'text-green-600'}>
            {formatAmount(item.buy_elg_amount)}亿
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">大单</span>
          <span className={item.buy_lg_amount >= 0 ? 'text-red-600' : 'text-green-600'}>
            {formatAmount(item.buy_lg_amount)}亿
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">中单</span>
          <span className={item.buy_md_amount >= 0 ? 'text-red-600' : 'text-green-600'}>
            {formatAmount(item.buy_md_amount)}亿
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">小单</span>
          <span className={item.buy_sm_amount >= 0 ? 'text-red-600' : 'text-green-600'}>
            {formatAmount(item.buy_sm_amount)}亿
          </span>
        </div>
      </div>
    </div>
  ), [])

  // 趋势图数据
  const chartData = useMemo(() => {
    return [...data].reverse().map(item => ({
      date: formatDate(item.trade_date),
      主力净流入: parseFloat(formatAmount(item.net_amount)),
      超大单: parseFloat(formatAmount(item.buy_elg_amount)),
      大单: parseFloat(formatAmount(item.buy_lg_amount))
    }))
  }, [data])

  return (
    <div className="space-y-6">
      <PageHeader
        title="大盘资金流向"
        description="查看大盘主力资金、超大单、大单、中单、小单的流入流出情况"
        actions={
          <div className="flex flex-col sm:flex-row gap-2 w-full sm:w-auto">
            <Button
              variant="default"
              size="sm"
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
                  同步数据
                </>
              )}
            </Button>
          </div>
        }
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">主力净流入均值</CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${statistics.avg_net >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                {formatAmount(statistics.avg_net)}亿
              </div>
              <div className="text-xs text-gray-500 mt-1">
                <Activity className="inline h-3 w-3 mr-1" />
                近{statistics.count}个交易日
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">最大净流入</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {formatAmount(statistics.max_net)}亿
              </div>
              <div className="text-xs text-gray-500 mt-1">
                <TrendingUp className="inline h-3 w-3 mr-1" />
                单日最高
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">超大单均值</CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${statistics.avg_elg >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                {formatAmount(statistics.avg_elg)}亿
              </div>
              <div className="text-xs text-gray-500 mt-1">
                <DollarSign className="inline h-3 w-3 mr-1" />
                日均流入
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">累计净流入</CardTitle>
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${statistics.total_net >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                {formatAmount(statistics.total_net)}亿
              </div>
              <div className="text-xs text-gray-500 mt-1">
                <TrendingDown className="inline h-3 w-3 mr-1" />
                期间总计
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选器 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="flex-1 min-w-0">
              <label className="text-sm font-medium mb-2 block">开始日期</label>
              <DatePicker
                date={startDate}
                onDateChange={setStartDate}
                placeholder="选择开始日期"
              />
            </div>
            <div className="flex-1 min-w-0">
              <label className="text-sm font-medium mb-2 block">结束日期</label>
              <DatePicker
                date={endDate}
                onDateChange={setEndDate}
                placeholder="选择结束日期"
              />
            </div>
            <Button onClick={loadData} variant="default" className="w-full sm:w-auto">
              查询
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 趋势图 */}
      {!loading && !error && data.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>资金流向趋势</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="w-full overflow-x-auto">
              <div style={{ minWidth: '600px' }}>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 40 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="date"
                      angle={-45}
                      textAnchor="end"
                      height={80}
                      tick={{ fontSize: 12 }}
                    />
                    <YAxis tick={{ fontSize: 12 }} label={{ value: '亿元', angle: -90, position: 'insideLeft' }} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="主力净流入" stroke="#8884d8" strokeWidth={2} />
                    <Line type="monotone" dataKey="超大单" stroke="#82ca9d" strokeWidth={2} />
                    <Line type="monotone" dataKey="大单" stroke="#ffc658" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 桌面端表格 */}
      <div className="hidden sm:block">
        <DataTable
          columns={columns}
          data={data}
          loading={loading}
          error={error}
          page={page}
          pageSize={pageSize}
          total={total}
          onPageChange={setPage}
          onPageSizeChange={setPageSize}
        />
      </div>

      {/* 移动端卡片列表 */}
      <div className="sm:hidden">
        <Card>
          <div className="px-4 py-3 border-b bg-muted/50">
            <h3 className="text-sm font-medium">大盘资金流向数据</h3>
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
        </Card>
      </div>
    </div>
  )
}
