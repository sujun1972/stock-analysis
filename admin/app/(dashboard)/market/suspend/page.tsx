'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { suspendApi } from '@/lib/api'
import type { SuspendData, SuspendStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, TrendingDown, Calendar, BarChart3 } from 'lucide-react'

export default function SuspendPage() {
  const [data, setData] = useState<SuspendData[]>([])
  const [statistics, setStatistics] = useState<SuspendStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState<string>('')
  const [suspendType, setSuspendType] = useState<string>('ALL')
  const [syncing, setSyncing] = useState(false)

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [totalRecords, setTotalRecords] = useState(0)
  const [totalPages, setTotalPages] = useState(0)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params: any = {}
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (suspendType !== 'ALL') params.suspend_type = suspendType
      params.page = currentPage
      params.page_size = pageSize

      const [dataResp, statsResp] = await Promise.all([
        suspendApi.getData(params),
        suspendApi.getStatistics({
          start_date: params.start_date,
          end_date: params.end_date
        })
      ])

      if (dataResp.code === 200) {
        setData(dataResp.data?.items || [])
        setTotalRecords(dataResp.data?.total || 0)
        setTotalPages(dataResp.data?.total_pages || 0)
      }

      if (statsResp.code === 200) {
        setStatistics(statsResp.data || null)
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast.error('加载失败', { description: err.message })
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, tsCode, suspendType, currentPage, pageSize])

  useEffect(() => {
    loadData()
  }, [loadData])

  // 当筛选条件变化时，重置到第一页
  useEffect(() => {
    setCurrentPage(1)
  }, [startDate, endDate, tsCode, suspendType])

  // 异步同步数据
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params: any = {}
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (suspendType !== 'ALL') params.suspend_type = suspendType

      const response = await suspendApi.syncAsync(params)

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
            toast.success('数据同步完成', { description: '停复牌信息已更新' })
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
  }, [unregisterCompletionCallback])

  // 表格列定义
  const columns: Column<SuspendData>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '日期',
      accessor: (row) => row.trade_date
    },
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'suspend_type',
      header: '类型',
      accessor: (row) => (
        <span className={row.suspend_type === 'S' ? 'text-red-600' : 'text-green-600'}>
          {row.suspend_type === 'S' ? '停牌' : '复牌'}
        </span>
      )
    },
    {
      key: 'suspend_timing',
      header: '停牌时段',
      accessor: (row) => row.suspend_timing || '-'
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: SuspendData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">日期</span>
        <span className="font-medium">{item.trade_date}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">股票代码</span>
        <span className="font-medium">{item.ts_code}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">类型</span>
        <span className={`font-medium ${item.suspend_type === 'S' ? 'text-red-600' : 'text-green-600'}`}>
          {item.suspend_type === 'S' ? '停牌' : '复牌'}
        </span>
      </div>
      {item.suspend_timing && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">停牌时段</span>
          <span>{item.suspend_timing}</span>
        </div>
      )}
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="每日停复牌信息"
        description="查询股票每日停复牌情况，包括停牌时间段和复牌信息"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">总记录数</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.total_count.toLocaleString()}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">涉及股票</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.stock_count.toLocaleString()}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">停牌次数</CardTitle>
              <TrendingDown className="h-4 w-4 text-red-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{statistics.suspend_count.toLocaleString()}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">复牌次数</CardTitle>
              <TrendingUp className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{statistics.resume_count.toLocaleString()}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选和操作 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">开始日期</label>
                <DatePicker date={startDate} onDateChange={setStartDate} placeholder="选择开始日期" />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">结束日期</label>
                <DatePicker date={endDate} onDateChange={setEndDate} placeholder="选择结束日期" />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">股票代码</label>
                <Input
                  placeholder="如：000001.SZ"
                  value={tsCode}
                  onChange={(e) => setTsCode(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">类型</label>
                <Select value={suspendType} onValueChange={setSuspendType}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">全部</SelectItem>
                    <SelectItem value="S">停牌</SelectItem>
                    <SelectItem value="R">复牌</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex gap-2">
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
            <h3 className="text-sm font-medium">停复牌数据</h3>
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
        </div>

        {/* 桌面端表格 */}
        <div className="hidden sm:block">
          <DataTable
            columns={columns}
            data={data}
            loading={loading}
            error={error}
            emptyMessage="暂无停复牌数据"
            pagination={{
              page: currentPage,
              pageSize: pageSize,
              total: totalRecords,
              onPageChange: setCurrentPage,
              onPageSizeChange: (newSize) => {
                setPageSize(newSize)
                setCurrentPage(1) // 重置到第一页
              }
            }}
          />
        </div>
      </Card>
    </div>
  )
}
