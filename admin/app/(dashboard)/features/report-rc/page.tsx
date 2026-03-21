'use client'

import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Input } from '@/components/ui/input'
import { reportRcApi, type ReportRcData, type ReportRcStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, Building2, FileText, BarChart3 } from 'lucide-react'

export default function ReportRcPage() {
  const [data, setData] = useState<ReportRcData[]>([])
  const [statistics, setStatistics] = useState<ReportRcStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [orgName, setOrgName] = useState('')
  const [syncing, setSyncing] = useState(false)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params: any = { limit: 100 }
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (orgName.trim()) params.org_name = orgName.trim()

      const response = await reportRcApi.getData(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics || null)
      } else {
        throw new Error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast.error('加载数据失败', {
        description: err.message || '无法获取卖方盈利预测数据'
      })
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, tsCode, orgName])

  // 初始加载
  useEffect(() => {
    loadData()
  }, [loadData])

  // 异步同步处理
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params: any = {}
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]
      if (tsCode.trim()) params.ts_code = tsCode.trim()

      const response = await reportRcApi.syncAsync(params)

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
              description: '卖方盈利预测数据已更新'
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
  }, [unregisterCompletionCallback])

  // 格式化日期
  const formatDate = (dateStr: string) => {
    if (!dateStr || dateStr.length !== 8) return dateStr
    return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
  }

  // 表格列定义
  const columns: Column<ReportRcData>[] = useMemo(() => [
    {
      key: 'report_date',
      header: '研报日期',
      accessor: (row) => formatDate(row.report_date),
      width: 100
    },
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code,
      width: 100
    },
    {
      key: 'name',
      header: '股票名称',
      accessor: (row) => row.name,
      width: 100
    },
    {
      key: 'org_name',
      header: '机构',
      accessor: (row) => row.org_name,
      width: 120
    },
    {
      key: 'quarter',
      header: '预测期',
      accessor: (row) => row.quarter,
      width: 80
    },
    {
      key: 'eps',
      header: 'EPS(元)',
      accessor: (row) => row.eps !== null ? row.eps.toFixed(2) : '-',
      width: 80,
      align: 'right'
    },
    {
      key: 'pe',
      header: 'PE',
      accessor: (row) => row.pe !== null ? row.pe.toFixed(2) : '-',
      width: 70,
      align: 'right'
    },
    {
      key: 'roe',
      header: 'ROE(%)',
      accessor: (row) => row.roe !== null ? (row.roe * 100).toFixed(2) : '-',
      width: 80,
      align: 'right'
    },
    {
      key: 'rating',
      header: '评级',
      accessor: (row) => row.rating || '-',
      width: 100
    },
    {
      key: 'max_price',
      header: '目标价(元)',
      accessor: (row) => row.max_price !== null ? row.max_price.toFixed(2) : '-',
      width: 100,
      align: 'right'
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: ReportRcData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <div>
          <span className="font-medium text-base">{item.name}</span>
          <span className="text-sm text-gray-500 ml-2">{item.ts_code}</span>
        </div>
        <span className="text-sm text-gray-600 dark:text-gray-400">{formatDate(item.report_date)}</span>
      </div>

      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">机构:</span>
          <span className="font-medium">{item.org_name}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">预测期:</span>
          <span className="font-medium">{item.quarter}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">EPS:</span>
          <span className="font-medium">{item.eps !== null ? `${item.eps.toFixed(2)}元` : '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">PE:</span>
          <span className="font-medium">{item.pe !== null ? item.pe.toFixed(2) : '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">ROE:</span>
          <span className="font-medium">{item.roe !== null ? `${(item.roe * 100).toFixed(2)}%` : '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">评级:</span>
          <span className="font-medium text-blue-600">{item.rating || '-'}</span>
        </div>
      </div>

      {item.max_price !== null && (
        <div className="flex justify-between items-center pt-2 border-t border-gray-100 dark:border-gray-800">
          <span className="text-sm text-gray-600 dark:text-gray-400">目标价:</span>
          <span className="font-medium text-green-600">{item.max_price.toFixed(2)} 元</span>
        </div>
      )}
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="卖方盈利预测数据"
        description="券商研报盈利预测数据，包含EPS、PE、ROE等关键指标和评级信息"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">研报数量</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.total_count.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground mt-1">条研报记录</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">覆盖股票</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.stock_count.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground mt-1">只股票</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">参与机构</CardTitle>
              <Building2 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.org_count.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground mt-1">家券商</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">平均EPS</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.avg_eps.toFixed(2)}</div>
              <p className="text-xs text-muted-foreground mt-1">元/股</p>
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">股票代码</label>
              <Input
                placeholder="如: 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">机构名称</label>
              <Input
                placeholder="如: 安信证券"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">开始日期</label>
              <DatePicker date={startDate} onSelect={setStartDate} />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">结束日期</label>
              <DatePicker date={endDate} onSelect={setEndDate} />
            </div>
          </div>

          <div className="flex gap-2 mt-4">
            <Button onClick={loadData} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
              查询
            </Button>
            <Button onClick={handleSync} disabled={syncing} variant="outline">
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
            <h3 className="text-sm font-medium">研报数据</h3>
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

        {/* 桌面端表格视图 */}
        <div className="hidden sm:block">
          <DataTable
            columns={columns}
            data={data}
            loading={loading}
            error={error}
            emptyMessage="暂无数据"
          />
        </div>
      </Card>
    </div>
  )
}
