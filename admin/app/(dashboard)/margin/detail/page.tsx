'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { apiClient } from '@/lib/api-client'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

// 数据类型定义
interface MarginDetailData {
  trade_date: string
  ts_code: string
  name: string
  rzye: number          // 融资余额(元)
  rqye: number          // 融券余额(元)
  rzmre: number         // 融资买入额(元)
  rqyl: number          // 融券余量(股)
  rzche: number         // 融资偿还额(元)
  rqchl: number         // 融券偿还量(股)
  rqmcl: number         // 融券卖出量(股)
  rzrqye: number        // 融资融券余额(元)
}

interface Statistics {
  avg_rzrqye: number
  total_rzrqye: number
  max_rzrqye: number
  stock_count: number
}

export default function MarginDetailPage() {
  const [data, setData] = useState<MarginDetailData[]>([])
  const [topStocks, setTopStocks] = useState<any[]>([])
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 筛选状态
  const [tsCode, setTsCode] = useState('')
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
        page,
        page_size: pageSize
      }

      if (tsCode) params.ts_code = tsCode
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]

      const response = await apiClient.getMarginDetail(params)

      if (response.code === 200 && response.data) {
        setData(response.data.data || [])
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
  }, [page, pageSize, tsCode, startDate, endDate])

  // 加载统计数据
  const loadStatistics = useCallback(async () => {
    try {
      const params: any = {}
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]

      const response = await apiClient.getMarginDetailStatistics(params)
      if (response.code === 200 && response.data) {
        setStatistics(response.data)
      }
    } catch (err) {
      console.error('加载统计数据失败:', err)
    }
  }, [startDate, endDate])

  // 加载TOP股票
  const loadTopStocks = useCallback(async () => {
    try {
      const response = await apiClient.getMarginDetailTopStocks({ limit: 20 })
      if (response.code === 200 && response.data) {
        setTopStocks(response.data)
      }
    } catch (err) {
      console.error('加载TOP股票失败:', err)
    }
  }, [])

  // 初始加载
  useEffect(() => {
    loadData()
    loadStatistics()
    loadTopStocks()
  }, [loadData, loadStatistics, loadTopStocks])

  // 异步同步
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params: any = {}
      if (tsCode) params.ts_code = tsCode
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]

      const response = await apiClient.syncMarginDetailAsync(params)

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
            loadStatistics().catch(() => {})
            loadTopStocks().catch(() => {})
            toast.success('数据同步完成', { description: '融资融券交易明细数据已更新' })
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
    } finally {
      setSyncing(false)
    }
  }

  // 组件卸载清理
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

  // 格式化金额（元转万元）
  const formatAmount = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '-'
    return (value / 10000).toFixed(2)
  }

  // 格式化日期
  const formatDate = (dateStr: string) => {
    if (!dateStr || dateStr.length !== 8) return dateStr
    return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
  }

  // 表格列定义
  const columns: Column<MarginDetailData>[] = useMemo(
    () => [
      {
        key: 'trade_date',
        header: '日期',
        accessor: (row) => formatDate(row.trade_date),
        width: 100
      },
      {
        key: 'ts_code',
        header: '代码',
        accessor: (row) => row.ts_code,
        width: 90
      },
      {
        key: 'name',
        header: '名称',
        accessor: (row) => row.name || '-',
        width: 100
      },
      {
        key: 'rzrqye',
        header: (
          <>
            <span className="sm:hidden">融券余额</span>
            <span className="hidden sm:inline">融资融券余额</span>
          </>
        ),
        accessor: (row) => `${formatAmount(row.rzrqye)} 万`,
        align: 'right',
        width: 120
      },
      {
        key: 'rzye',
        header: '融资余额',
        accessor: (row) => `${formatAmount(row.rzye)} 万`,
        align: 'right',
        hideOnMobile: true,
        width: 120
      },
      {
        key: 'rqye',
        header: '融券余额',
        accessor: (row) => `${formatAmount(row.rqye)} 万`,
        align: 'right',
        hideOnMobile: true,
        width: 120
      },
      {
        key: 'rzmre',
        header: '融资买入',
        accessor: (row) => `${formatAmount(row.rzmre)} 万`,
        align: 'right',
        hideOnMobile: true,
        width: 110
      },
      {
        key: 'rzche',
        header: '融资偿还',
        accessor: (row) => `${formatAmount(row.rzche)} 万`,
        align: 'right',
        hideOnMobile: true,
        width: 110
      }
    ],
    []
  )

  // 移动端卡片视图
  const mobileCard = useCallback((item: MarginDetailData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <div>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{item.ts_code}</span>
          <span className="ml-2 text-xs text-gray-500">{item.name}</span>
        </div>
        <span className="text-xs text-gray-500">{formatDate(item.trade_date)}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">融资融券余额</span>
        <span className="font-medium">{formatAmount(item.rzrqye)} 万</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">融资余额</span>
        <span className="font-medium">{formatAmount(item.rzye)} 万</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">融券余额</span>
        <span className="font-medium">{formatAmount(item.rqye)} 万</span>
      </div>
    </div>
  ), [])

  // 准备图表数据
  const chartData = useMemo(() => {
    return topStocks.slice(0, 20).map((stock) => ({
      name: stock.name || stock.ts_code,
      融资融券余额: (stock.rzrqye / 100000000).toFixed(2),
      融资余额: (stock.rzye / 100000000).toFixed(2),
      融券余额: (stock.rqye / 100000000).toFixed(2)
    }))
  }, [topStocks])

  return (
    <div className="space-y-6">
      <PageHeader
        title="融资融券交易明细"
        description="个股融资融券交易明细数据（Tushare接口，2000积分/次，单次最大6000行）"
      />

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>平均融资融券余额</CardDescription>
            <CardTitle className="text-2xl">
              {statistics ? `${formatAmount(statistics.avg_rzrqye)} 万` : '-'}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardDescription>累计融资融券余额</CardDescription>
            <CardTitle className="text-2xl">
              {statistics ? `${(statistics.total_rzrqye / 100000000).toFixed(2)} 亿` : '-'}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardDescription>最大融资融券余额</CardDescription>
            <CardTitle className="text-2xl">
              {statistics ? `${(statistics.max_rzrqye / 100000000).toFixed(2)} 亿` : '-'}
            </CardTitle>
          </CardHeader>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardDescription>统计股票数量</CardDescription>
            <CardTitle className="text-2xl">
              {statistics ? `${statistics.stock_count} 只` : '-'}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* 趋势图表 */}
      {chartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>TOP 20 股票融资融券余额</CardTitle>
            <CardDescription>按融资融券余额排序（单位：亿元）</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[400px] overflow-x-auto">
              <ResponsiveContainer width="100%" height="100%" minWidth={chartData.length * 60}>
                <BarChart
                  data={chartData}
                  margin={{ top: 20, right: 30, left: 20, bottom: 80 }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="name"
                    angle={-45}
                    textAnchor="end"
                    height={100}
                    interval={0}
                  />
                  <YAxis label={{ value: '金额（亿元）', angle: -90, position: 'insideLeft' }} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="融资融券余额" fill="#8884d8" />
                  <Bar dataKey="融资余额" fill="#82ca9d" />
                  <Bar dataKey="融券余额" fill="#ffc658" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 筛选和同步 */}
      <Card>
        <CardHeader>
          <CardTitle>数据筛选与同步</CardTitle>
          <CardDescription>筛选条件和数据同步操作</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="flex flex-col gap-2">
                <Label>股票代码</Label>
                <Input
                  placeholder="如：000001.SZ"
                  value={tsCode}
                  onChange={(e) => setTsCode(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label>开始日期</Label>
                <DatePicker
                  date={startDate}
                  onDateChange={setStartDate}
                />
              </div>
              <div className="flex flex-col gap-2">
                <Label>结束日期</Label>
                <DatePicker
                  date={endDate}
                  onDateChange={setEndDate}
                />
              </div>
            </div>
            <div className="flex gap-2 flex-wrap">
              <Button
                variant="default"
                size="sm"
                onClick={() => {
                  setPage(1)
                  loadData()
                  loadStatistics()
                }}
              >
                <RefreshCw className="h-4 w-4 mr-1" />
                查询
              </Button>
              <Button
                variant="outline"
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
                    <TrendingUp className="h-4 w-4 mr-1" />
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
            <h3 className="text-sm font-medium">融资融券交易明细</h3>
          </div>
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {!loading && !error && data.map((item, index) => (
              <div
                key={`${item.trade_date}-${item.ts_code}`}
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
            emptyMessage="暂无融资融券交易明细数据"
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
