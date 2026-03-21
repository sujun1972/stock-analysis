'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp } from 'lucide-react'
import { extendedDataApi } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'

interface PledgeStatData {
  ts_code: string
  end_date: string
  pledge_count: number
  unrest_pledge: number
  rest_pledge: number
  total_share: number
  pledge_ratio: number
  created_at?: string
  updated_at?: string
}

interface PledgeStatStatistics {
  avg_pledge_ratio: number
  max_pledge_ratio: number
  total_pledge_count: number
  stock_count: number
}

export default function PledgeStatPage() {
  // 数据状态
  const [data, setData] = useState<PledgeStatData[]>([])
  const [statistics, setStatistics] = useState<PledgeStatStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 筛选状态
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [syncing, setSyncing] = useState(false)

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

      if (startDate) {
        params.start_date = startDate.toISOString().split('T')[0]
      }
      if (endDate) {
        params.end_date = endDate.toISOString().split('T')[0]
      }
      if (tsCode.trim()) {
        params.ts_code = tsCode.trim()
      }

      const [dataResponse, statsResponse] = await Promise.all([
        extendedDataApi.getPledgeStat(params),
        extendedDataApi.getPledgeStatStatistics({
          start_date: startDate ? startDate.toISOString().split('T')[0] : undefined,
          end_date: endDate ? endDate.toISOString().split('T')[0] : undefined
        })
      ])

      if (dataResponse.code === 200 && dataResponse.data) {
        setData(dataResponse.data.items || [])
        setTotal(dataResponse.data.total || 0)
      } else {
        throw new Error(dataResponse.message || '获取数据失败')
      }

      if (statsResponse.code === 200 && statsResponse.data) {
        setStatistics(statsResponse.data)
      }
    } catch (err: any) {
      const errorMsg = err.message || '加载数据失败'
      setError(errorMsg)
      toast.error('加载失败', { description: errorMsg })
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, tsCode, pageSize])

  // 异步同步数据
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params: any = {}
      if (endDate) {
        params.trade_date = endDate.toISOString().split('T')[0]
      }
      if (tsCode.trim()) {
        params.ts_code = tsCode.trim()
      }

      const response = await extendedDataApi.syncPledgeStatAsync(params)

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
              description: '股权质押统计数据已更新'
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

  // 初始加载
  useEffect(() => {
    loadData()
  }, [loadData])

  // 表格列定义
  const columns: Column<PledgeStatData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'end_date',
      header: '截止日期',
      accessor: (row) => row.end_date
    },
    {
      key: 'pledge_count',
      header: '质押次数',
      accessor: (row) => row.pledge_count?.toLocaleString() || 0
    },
    {
      key: 'unrest_pledge',
      header: '无限售股质押(股)',
      accessor: (row) => row.unrest_pledge ? (row.unrest_pledge / 10000).toFixed(2) + '万' : '0'
    },
    {
      key: 'rest_pledge',
      header: '限售股质押(股)',
      accessor: (row) => row.rest_pledge ? (row.rest_pledge / 10000).toFixed(2) + '万' : '0'
    },
    {
      key: 'total_share',
      header: '总股本(股)',
      accessor: (row) => row.total_share ? (row.total_share / 10000).toFixed(2) + '万' : '0'
    },
    {
      key: 'pledge_ratio',
      header: '质押比例(%)',
      accessor: (row) => {
        const ratio = row.pledge_ratio || 0
        const color = ratio >= 50 ? 'text-red-600 dark:text-red-400' :
                     ratio >= 30 ? 'text-orange-600 dark:text-orange-400' :
                     'text-gray-900 dark:text-gray-100'
        return (
          <span className={`font-medium ${color}`}>
            {ratio.toFixed(2)}%
          </span>
        )
      }
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: PledgeStatData) => {
    const ratio = item.pledge_ratio || 0
    const ratioColor = ratio >= 50 ? 'text-red-600 dark:text-red-400' :
                       ratio >= 30 ? 'text-orange-600 dark:text-orange-400' :
                       'text-gray-900 dark:text-gray-100'

    return (
      <div className="space-y-2">
        <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">股票代码</span>
          <span className="font-medium">{item.ts_code}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">截止日期</span>
          <span>{item.end_date}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">质押次数</span>
          <span>{item.pledge_count?.toLocaleString() || 0}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">无限售股质押</span>
          <span>{item.unrest_pledge ? (item.unrest_pledge / 10000).toFixed(2) + '万股' : '0'}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">限售股质押</span>
          <span>{item.rest_pledge ? (item.rest_pledge / 10000).toFixed(2) + '万股' : '0'}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">总股本</span>
          <span>{item.total_share ? (item.total_share / 10000).toFixed(2) + '万股' : '0'}</span>
        </div>
        <div className="flex justify-between items-center pt-2 border-t border-gray-200 dark:border-gray-700">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">质押比例</span>
          <span className={`text-lg font-bold ${ratioColor}`}>
            {ratio.toFixed(2)}%
          </span>
        </div>
      </div>
    )
  }, [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="股权质押统计"
        description="上市公司股票质押统计数据，包含质押次数、质押股本、质押比例等信息"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                平均质押比例
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {statistics.avg_pledge_ratio?.toFixed(2) || 0}%
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                最高质押比例
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600 dark:text-red-400">
                {statistics.max_pledge_ratio?.toFixed(2) || 0}%
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                总质押次数
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {statistics.total_pledge_count?.toLocaleString() || 0}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                统计股票数
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {statistics.stock_count?.toLocaleString() || 0}
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
              <DatePicker
                date={startDate}
                onSelect={setStartDate}
                placeholder="开始日期"
              />
            </div>
            <div className="flex-1">
              <DatePicker
                date={endDate}
                onSelect={setEndDate}
                placeholder="截止日期"
              />
            </div>
            <div className="flex-1">
              <Input
                placeholder="股票代码（可选）"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <Button onClick={loadData} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
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
                  <TrendingUp className="h-4 w-4 mr-1" />
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
            <h3 className="text-sm font-medium">股权质押统计列表</h3>
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
