'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { apiClient } from '@/lib/api-client'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, TrendingDown, Activity, BarChart3 } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

// 数据类型定义
interface MoneyflowIndDcData {
  trade_date: string
  content_type: string
  ts_code: string
  name: string
  pct_change: number
  close: number
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
  buy_sm_amount_stock: string
  rank: number
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
  avg_pct: number
  latest_date: string
  earliest_date: string
  count: number
  type_count: number
  sector_count: number
}

export default function MoneyflowIndDcPage() {
  const [data, setData] = useState<MoneyflowIndDcData[]>([])
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [contentType, setContentType] = useState<string>('all')
  const [syncing, setSyncing] = useState(false)

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(50)
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
        content_type?: string
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
      if (contentType && contentType !== 'all') {
        params.content_type = contentType
      }

      const response = await apiClient.getMoneyflowIndDc(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics)
        setTotal(response.data.total || 0)
      } else {
        throw new Error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      console.error('加载数据失败:', err)
      setError(err.message || '加载数据失败')
      toast.error('加载数据失败', {
        description: err.message
      })
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, startDate, endDate, contentType])

  // 初始加载和分页/筛选变化时重新加载
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
        content_type?: string
      } = {}

      if (startDate) {
        params.start_date = startDate.toISOString().split('T')[0]
      }
      if (endDate) {
        params.end_date = endDate.toISOString().split('T')[0]
      }
      if (contentType && contentType !== 'all') {
        params.content_type = contentType
      }

      const response = await apiClient.syncMoneyflowIndDcAsync(params)

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
              description: '板块资金流向数据已更新'
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
    return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
  }

  // 格式化金额（元 -> 亿元）
  const formatAmount = (amount: number) => {
    return (amount / 100000000).toFixed(2)
  }

  // 格式化百分比
  const formatPercent = (value: number) => {
    return `${value.toFixed(2)}%`
  }

  // 表格列定义
  // 注意：DataTable 组件使用 'header' 属性显示列标题（不是 'title'）
  const columns: Column<MoneyflowIndDcData>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '日期',
      accessor: (row) => formatDate(row.trade_date),
      width: 110
    },
    {
      key: 'content_type',
      header: '类型',
      accessor: (row) => row.content_type,
      width: 80
    },
    {
      key: 'name',
      header: '板块名称',
      accessor: (row) => row.name,
      width: 150
    },
    {
      key: 'pct_change',
      header: '涨跌幅',
      accessor: (row) => (
        <span className={row.pct_change >= 0 ? 'text-red-600' : 'text-green-600'}>
          {formatPercent(row.pct_change)}
        </span>
      ),
      width: 100
    },
    {
      key: 'net_amount',
      header: '主力净流入',
      accessor: (row) => (
        <span className={row.net_amount >= 0 ? 'text-red-600' : 'text-green-600'}>
          {formatAmount(row.net_amount)}亿
        </span>
      ),
      width: 120
    },
    {
      key: 'net_amount_rate',
      header: '主力净占比',
      accessor: (row) => formatPercent(row.net_amount_rate),
      width: 110
    },
    {
      key: 'buy_elg_amount',
      header: '超大单',
      accessor: (row) => (
        <span className={row.buy_elg_amount >= 0 ? 'text-red-600' : 'text-green-600'}>
          {formatAmount(row.buy_elg_amount)}亿
        </span>
      ),
      width: 110
    },
    {
      key: 'buy_lg_amount',
      header: '大单',
      accessor: (row) => (
        <span className={row.buy_lg_amount >= 0 ? 'text-red-600' : 'text-green-600'}>
          {formatAmount(row.buy_lg_amount)}亿
        </span>
      ),
      width: 110
    },
    {
      key: 'rank',
      header: '排名',
      accessor: (row) => row.rank,
      width: 70
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: MoneyflowIndDcData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">板块</span>
        <span className="font-medium">{item.name}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">日期</span>
        <span>{formatDate(item.trade_date)}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">类型</span>
        <span>{item.content_type}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">涨跌幅</span>
        <span className={item.pct_change >= 0 ? 'text-red-600' : 'text-green-600'}>
          {formatPercent(item.pct_change)}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">主力净流入</span>
        <span className={item.net_amount >= 0 ? 'text-red-600 font-medium' : 'text-green-600 font-medium'}>
          {formatAmount(item.net_amount)}亿
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">排名</span>
        <span className="font-medium">#{item.rank}</span>
      </div>
    </div>
  ), [])

  // 图表数据（前10名）
  const chartData = useMemo(() => {
    return data.slice(0, 10).map(item => ({
      name: item.name.length > 6 ? item.name.slice(0, 6) + '...' : item.name,
      主力净流入: parseFloat(formatAmount(item.net_amount)),
      超大单: parseFloat(formatAmount(item.buy_elg_amount)),
      大单: parseFloat(formatAmount(item.buy_lg_amount))
    }))
  }, [data])

  return (
    <div className="space-y-6">
      <PageHeader
        title="板块资金流向（DC）"
        description="东方财富板块资金流向数据，包含行业、概念、地域板块的主力资金流向情况"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">主力资金均值</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${statistics.avg_net >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                {formatAmount(statistics.avg_net)}亿
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                板块数: {statistics.sector_count}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最大净流入</CardTitle>
              <TrendingUp className="h-4 w-4 text-red-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {formatAmount(statistics.max_net)}亿
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                最高涨幅: {formatPercent(statistics.avg_pct)}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最小净流出</CardTitle>
              <TrendingDown className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {formatAmount(statistics.min_net)}亿
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                数据类型: {statistics.type_count}种
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">超大单均值</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${statistics.avg_elg >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                {formatAmount(statistics.avg_elg)}亿
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                记录数: {statistics.count}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 趋势图表 */}
      {chartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>TOP 10 板块资金流向</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] overflow-x-auto">
              <div style={{ minWidth: '600px' }}>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 40 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} />
                    <YAxis label={{ value: '金额（亿元）', angle: -90, position: 'insideLeft' }} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="主力净流入" fill="#8884d8" />
                    <Bar dataKey="超大单" fill="#82ca9d" />
                    <Bar dataKey="大单" fill="#ffc658" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 筛选和同步 */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="flex-1 space-y-2">
              <label className="text-sm font-medium">开始日期</label>
              <DatePicker date={startDate} onDateChange={setStartDate} />
            </div>
            <div className="flex-1 space-y-2">
              <label className="text-sm font-medium">结束日期</label>
              <DatePicker date={endDate} onDateChange={setEndDate} />
            </div>
            <div className="flex-1 space-y-2">
              <label className="text-sm font-medium">板块类型</label>
              <Select value={contentType} onValueChange={setContentType}>
                <SelectTrigger>
                  <SelectValue placeholder="选择类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部</SelectItem>
                  <SelectItem value="行业">行业</SelectItem>
                  <SelectItem value="概念">概念</SelectItem>
                  <SelectItem value="地域">地域</SelectItem>
                </SelectContent>
              </Select>
            </div>
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
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardHeader>
          <CardTitle>板块资金流向数据</CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={columns}
            data={data}
            loading={loading}
            error={error}
            emptyMessage="暂无板块资金流向数据"
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: (newPage) => {
                setPage(newPage)
              },
              onPageSizeChange: (newPageSize) => {
                setPageSize(newPageSize)
                setPage(1) // 重置到第一页
              }
            }}
            mobileCard={mobileCard}
          />
        </CardContent>
      </Card>
    </div>
  )
}
