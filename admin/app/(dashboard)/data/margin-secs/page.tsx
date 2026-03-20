'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { marginSecsApi } from '@/lib/api'
import type { MarginSecsItem, MarginSecsStatistics } from '@/lib/api/margin-secs'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'

// 交易所常量
const EXCHANGES = [
  { value: 'ALL', label: '全部' },
  { value: 'SSE', label: '上交所' },
  { value: 'SZSE', label: '深交所' },
  { value: 'BSE', label: '北交所' }
]

const EXCHANGE_COLORS: Record<string, string> = {
  'SSE': '#8884d8',
  'SZSE': '#82ca9d',
  'BSE': '#ffc658'
}

export default function MarginSecsPage() {
  const [data, setData] = useState<MarginSecsItem[]>([])
  const [statistics, setStatistics] = useState<MarginSecsStatistics | null>(null)
  const [exchangeDistribution, setExchangeDistribution] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 筛选状态
  const [tsCode, setTsCode] = useState('')
  const [exchange, setExchange] = useState('ALL')
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [syncing, setSyncing] = useState(false)

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // 任务回调引用
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

      if (tsCode) params.ts_code = tsCode
      if (exchange && exchange !== 'ALL') params.exchange = exchange
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]

      const response = await marginSecsApi.getMarginSecs(params)

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
      setLoading(false)
    }
  }, [pageSize, tsCode, exchange, startDate, endDate])

  // 加载最新数据和交易所分布
  const loadLatestData = useCallback(async () => {
    try {
      const response = await marginSecsApi.getLatestMarginSecs()
      if (response.code === 200 && response.data) {
        setExchangeDistribution(response.data.statistics.exchange_distribution || [])
      }
    } catch (err) {
      console.error('加载最新数据失败:', err)
    }
  }, [])

  // 初始加载
  useEffect(() => {
    loadData()
    loadLatestData()
  }, [loadData, loadLatestData])

  // 异步同步
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params: any = {}
      if (exchange && exchange !== 'ALL') params.exchange = exchange
      if (startDate) {
        params.trade_date = startDate.toISOString().split('T')[0].replace(/-/g, '')
      }

      const response = await marginSecsApi.syncMarginSecsAsync(params)

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

        triggerPoll()

        // 注册回调
        const callback = (task: any) => {
          if (task.status === 'completed') {
            toast.success('同步完成', { description: '融资融券标的数据已更新' })
            setTimeout(() => {
              loadData().catch(() => {})
              loadLatestData().catch(() => {})
            }, 2000)
          } else if (task.status === 'failed') {
            toast.error('同步失败', { description: task.error || '请查看任务详情' })
          }
          activeCallbacksRef.current.delete(taskId)
          unregisterCompletionCallback(taskId, callback)
        }

        activeCallbacksRef.current.set(taskId, callback)
        registerCompletionCallback(taskId, callback)

        toast.success('任务已提交', { description: '正在同步融资融券标的数据...' })

        // 保险性刷新：5秒后自动刷新数据（即使回调未触发）
        setTimeout(() => {
          loadData().catch(() => {})
          loadLatestData().catch(() => {})
        }, 5000)
      } else {
        throw new Error(response.message || '提交任务失败')
      }
    } catch (err: any) {
      toast.error('同步失败', { description: err.message || '提交任务失败' })
    } finally {
      setSyncing(false)
    }
  }

  // 清理回调
  useEffect(() => {
    return () => {
      activeCallbacksRef.current.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      activeCallbacksRef.current.clear()
    }
  }, [unregisterCompletionCallback])

  // 数据表列定义
  const columns: Column<MarginSecsItem>[] = [
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => row.trade_date,
      width: '120px'
    },
    {
      key: 'ts_code',
      header: '标的代码',
      accessor: (row) => row.ts_code,
      width: '120px'
    },
    {
      key: 'name',
      header: '标的名称',
      accessor: (row) => row.name,
      width: '150px'
    },
    {
      key: 'exchange',
      header: '交易所',
      accessor: (row) => {
        const exchangeMap: Record<string, string> = {
          'SSE': '上交所',
          'SZSE': '深交所',
          'BSE': '北交所'
        }
        return exchangeMap[row.exchange] || row.exchange
      },
      width: '100px'
    }
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="融资融券标的"
        description="查询和管理融资融券标的数据（盘前更新）"
      />

      {/* 统计卡片 */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总记录数</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {statistics?.total_count?.toLocaleString() || '0'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              融资融券标的总数
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">标的数量</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {statistics?.unique_stocks?.toLocaleString() || '0'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              不同标的数量
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">交易日数</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {statistics?.trading_days?.toLocaleString() || '0'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              数据覆盖天数
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">交易所数</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {statistics?.exchange_count?.toLocaleString() || '0'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              涵盖交易所数量
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 交易所分布图表 */}
      {exchangeDistribution.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>交易所分布</CardTitle>
            <CardDescription>各交易所融资融券标的数量分布</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={exchangeDistribution}
                    dataKey="count"
                    nameKey="exchange"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label={(entry) => {
                      const exchangeMap: Record<string, string> = {
                        'SSE': '上交所',
                        'SZSE': '深交所',
                        'BSE': '北交所'
                      }
                      return `${exchangeMap[entry.exchange] || entry.exchange}: ${entry.count}`
                    }}
                  >
                    {exchangeDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={EXCHANGE_COLORS[entry.exchange] || '#999999'} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: any) => `${value} 只`} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 筛选和同步控制 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
          <CardDescription>筛选和同步融资融券标的数据</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5 items-end">
            <div className="space-y-2">
              <Label htmlFor="ts_code">标的代码</Label>
              <Input
                id="ts_code"
                placeholder="例如: 510050.SH"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="exchange">交易所</Label>
              <Select value={exchange} onValueChange={setExchange}>
                <SelectTrigger id="exchange">
                  <SelectValue placeholder="选择交易所" />
                </SelectTrigger>
                <SelectContent>
                  {EXCHANGES.map((ex) => (
                    <SelectItem key={ex.value} value={ex.value}>
                      {ex.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>开始日期</Label>
              <DatePicker
                date={startDate}
                onSelect={setStartDate}
                placeholder="选择开始日期"
              />
            </div>

            <div className="space-y-2">
              <Label>结束日期</Label>
              <DatePicker
                date={endDate}
                onSelect={setEndDate}
                placeholder="选择结束日期"
              />
            </div>

            <div className="flex gap-2">
              <Button onClick={loadData} disabled={loading} className="flex-1">
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                查询
              </Button>
              <Button onClick={handleSync} disabled={syncing} variant="outline" className="flex-1">
                <RefreshCw className={`h-4 w-4 mr-2 ${syncing ? 'animate-spin' : ''}`} />
                同步
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardHeader>
          <CardTitle>数据列表</CardTitle>
          <CardDescription>共 {total} 条记录</CardDescription>
        </CardHeader>
        <CardContent>
          {error ? (
            <div className="text-center py-8 text-red-500">{error}</div>
          ) : (
            <DataTable
              columns={columns}
              data={data}
              loading={loading}
              pagination={{
                total,
                pageSize,
                currentPage: page,
                onPageChange: setPage,
                onPageSizeChange: setPageSize
              }}
            />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
