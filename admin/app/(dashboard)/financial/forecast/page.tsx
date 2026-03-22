'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { forecastApi, ForecastData, ForecastStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, Briefcase, TrendingDown, BarChart3 } from 'lucide-react'

export default function ForecastPage() {
  const [data, setData] = useState<ForecastData[]>([])
  const [statistics, setStatistics] = useState<ForecastStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [forecastType, setForecastType] = useState<string>('')
  const [period, setPeriod] = useState('')
  const [syncing, setSyncing] = useState(false)

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params: any = { limit: pageSize }
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]
      if (tsCode) params.ts_code = tsCode.trim()
      if (forecastType) params.type = forecastType
      if (period) params.period = period

      const [dataResponse, statsResponse] = await Promise.all([
        forecastApi.getData(params),
        forecastApi.getStatistics({
          start_date: params.start_date,
          end_date: params.end_date,
          ts_code: params.ts_code,
          type: params.type
        })
      ])

      if (dataResponse.code === 200) {
        setData(dataResponse.data?.items || [])
        setTotal(dataResponse.data?.total || 0)
      }

      if (statsResponse.code === 200) {
        setStatistics(statsResponse.data || null)
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast.error('加载失败', { description: err.message })
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, tsCode, forecastType, period, pageSize])

  useEffect(() => {
    loadData()
  }, [loadData])

  // 异步同步数据
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params: any = {}
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]
      if (period) params.period = period
      if (forecastType) params.type = forecastType

      const response = await forecastApi.syncAsync(params)

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
            toast.success('数据同步完成', { description: '业绩预告数据已更新' })
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
  }, [unregisterCompletionCallback])

  // 格式化金额
  const formatAmount = (amount: number | null | undefined) => {
    if (amount === null || amount === undefined) return '-'
    return `${amount.toLocaleString()} 万元`
  }

  // 格式化百分比
  const formatPercent = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '-'
    return `${value.toFixed(2)}%`
  }

  // 获取预告类型颜色
  const getTypeColor = (type: string) => {
    const positiveTypes = ['预增', '扭亏', '续盈', '略增']
    const negativeTypes = ['预减', '首亏', '续亏', '略减']

    if (positiveTypes.includes(type)) {
      return 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400'
    } else if (negativeTypes.includes(type)) {
      return 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
    }
    return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
  }

  // 表格列定义
  const columns: Column<ForecastData>[] = useMemo(() => [
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
      header: '报告期',
      accessor: (row) => row.end_date
    },
    {
      key: 'type',
      header: '预告类型',
      accessor: (row) => (
        <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getTypeColor(row.type)}`}>
          {row.type || '-'}
        </span>
      )
    },
    {
      key: 'p_change',
      header: '变动幅度 (%)',
      accessor: (row) => {
        if (row.p_change_min === null && row.p_change_max === null) return '-'
        if (row.p_change_min === row.p_change_max) return formatPercent(row.p_change_min)
        return `${formatPercent(row.p_change_min)} ~ ${formatPercent(row.p_change_max)}`
      },
      align: 'right'
    },
    {
      key: 'net_profit',
      header: '预告净利润',
      accessor: (row) => {
        if (row.net_profit_min === null && row.net_profit_max === null) return '-'
        if (row.net_profit_min === row.net_profit_max) return formatAmount(row.net_profit_min)
        return (
          <div className="text-right">
            <div>{formatAmount(row.net_profit_min)}</div>
            <div className="text-xs text-gray-500">~ {formatAmount(row.net_profit_max)}</div>
          </div>
        )
      },
      align: 'right'
    },
    {
      key: 'last_parent_net',
      header: '上年同期',
      accessor: (row) => formatAmount(row.last_parent_net),
      align: 'right'
    },
    {
      key: 'summary',
      header: '预告摘要',
      accessor: (row) => (
        <div className="max-w-xs truncate" title={row.summary || '-'}>
          {row.summary || '-'}
        </div>
      )
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: ForecastData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">股票代码</span>
        <span className="font-medium">{item.ts_code}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">公告日期</span>
        <span className="font-medium">{item.ann_date}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">报告期</span>
        <span className="font-medium">{item.end_date}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">预告类型</span>
        <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getTypeColor(item.type)}`}>
          {item.type || '-'}
        </span>
      </div>
      {(item.p_change_min !== null || item.p_change_max !== null) && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">变动幅度</span>
          <span className="font-medium">
            {item.p_change_min === item.p_change_max
              ? formatPercent(item.p_change_min)
              : `${formatPercent(item.p_change_min)} ~ ${formatPercent(item.p_change_max)}`
            }
          </span>
        </div>
      )}
      {(item.net_profit_min !== null || item.net_profit_max !== null) && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">预告净利润</span>
          <span className="font-medium text-blue-600">
            {item.net_profit_min === item.net_profit_max
              ? formatAmount(item.net_profit_min)
              : `${formatAmount(item.net_profit_min)} ~ ${formatAmount(item.net_profit_max)}`
            }
          </span>
        </div>
      )}
      {item.last_parent_net !== null && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">上年同期</span>
          <span className="font-medium">{formatAmount(item.last_parent_net)}</span>
        </div>
      )}
      {item.summary && (
        <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
          <span className="text-sm text-gray-600 dark:text-gray-400">预告摘要</span>
          <p className="text-sm mt-1 text-gray-700 dark:text-gray-300">{item.summary}</p>
        </div>
      )}
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="业绩预告"
        description="上市公司业绩预告数据，包括预告类型、净利润变动幅度等信息"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">总记录数</p>
                  <p className="text-2xl font-bold">{statistics.total_count}</p>
                </div>
                <BarChart3 className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">涉及股票数</p>
                  <p className="text-2xl font-bold">{statistics.stock_count}</p>
                </div>
                <Briefcase className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">正面预告比例</p>
                  <p className="text-2xl font-bold">{statistics.positive_ratio.toFixed(1)}%</p>
                  <p className="text-xs text-muted-foreground">{statistics.positive_count} 条</p>
                </div>
                <TrendingUp className="h-8 w-8 text-red-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">负面预告比例</p>
                  <p className="text-2xl font-bold">{statistics.negative_ratio.toFixed(1)}%</p>
                  <p className="text-xs text-muted-foreground">{statistics.negative_count} 条</p>
                </div>
                <TrendingDown className="h-8 w-8 text-green-500" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 查询控件 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">开始日期</label>
              <DatePicker date={startDate} onSelect={setStartDate} />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">结束日期</label>
              <DatePicker date={endDate} onSelect={setEndDate} />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">股票代码</label>
              <Input
                placeholder="如: 600000.SH"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">报告期</label>
              <Input
                placeholder="如: 2024-12-31"
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">预告类型</label>
              <Select value={forecastType || 'ALL'} onValueChange={(value) => setForecastType(value === 'ALL' ? '' : value)}>
                <SelectTrigger>
                  <SelectValue placeholder="全部" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="预增">预增</SelectItem>
                  <SelectItem value="预减">预减</SelectItem>
                  <SelectItem value="扭亏">扭亏</SelectItem>
                  <SelectItem value="首亏">首亏</SelectItem>
                  <SelectItem value="续亏">续亏</SelectItem>
                  <SelectItem value="续盈">续盈</SelectItem>
                  <SelectItem value="略增">略增</SelectItem>
                  <SelectItem value="略减">略减</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end gap-2">
              <Button variant="default" onClick={loadData} disabled={loading} className="flex-1">
                查询
              </Button>
              <Button variant="outline" onClick={handleSync} disabled={syncing} className="flex-1">
                {syncing ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                    同步中
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-1" />
                    同步
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
            <h3 className="text-sm font-medium">业绩预告列表</h3>
          </div>
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {!loading && !error && data.map((item, index) => (
              <div
                key={`${item.ts_code}-${item.ann_date}-${item.end_date}`}
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

        {/* 桌面端表格 */}
        <div className="hidden sm:block">
          <DataTable
            columns={columns}
            data={data}
            loading={loading}
            error={error}
            emptyMessage="暂无业绩预告数据"
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
    </div>
  )
}
