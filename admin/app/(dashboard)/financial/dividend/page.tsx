'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, TrendingDown, DollarSign, Users } from 'lucide-react'
import { financialDataApi } from '@/lib/api'
import type { DividendData, DividendStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'

export default function DividendPage() {
  const [data, setData] = useState<DividendData[]>([])
  const [statistics, setStatistics] = useState<DividendStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [tsCode, setTsCode] = useState('')
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [totalRecords, setTotalRecords] = useState(0)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const params: any = {
        limit: pageSize,
        offset: (currentPage - 1) * pageSize
      }

      if (tsCode) params.ts_code = tsCode
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]

      const response = await financialDataApi.getDividend(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics || null)
        setTotalRecords(response.data.total || 0)
      } else {
        throw new Error(response.message || '加载失败')
      }
    } catch (err: any) {
      toast.error('加载失败', { description: err.message })
      setData([])
      setStatistics(null)
      setTotalRecords(0)
    } finally {
      setLoading(false)
    }
  }, [tsCode, startDate, endDate, currentPage, pageSize])

  // 重置到第一页（当筛选条件变化时）
  const handleQuery = () => {
    setCurrentPage(1)
    loadData()
  }

  useEffect(() => {
    loadData()
  }, [loadData])

  // 异步同步处理
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params: any = {}
      if (tsCode) params.ts_code = tsCode
      if (startDate) params.ann_date = startDate.toISOString().split('T')[0]

      const response = await financialDataApi.syncDividendAsync(params)

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
              description: '分红送股数据已更新'
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

  // 清理回调
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

  // 表格列定义
  const columns: Column<DividendData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'end_date',
      header: '分红年度',
      accessor: (row) => row.end_date || '-'
    },
    {
      key: 'ann_date',
      header: '公告日期',
      accessor: (row) => row.ann_date || '-'
    },
    {
      key: 'div_proc',
      header: '实施进度',
      accessor: (row) => row.div_proc || '-'
    },
    {
      key: 'cash_div',
      header: '每股分红(税后)',
      accessor: (row) => row.cash_div !== null && row.cash_div !== undefined
        ? row.cash_div.toFixed(4)
        : '-',
      className: 'text-right'
    },
    {
      key: 'stk_div',
      header: '每股送转',
      accessor: (row) => row.stk_div !== null && row.stk_div !== undefined
        ? row.stk_div.toFixed(4)
        : '-',
      className: 'text-right'
    },
    {
      key: 'ex_date',
      header: '除权除息日',
      accessor: (row) => row.ex_date || '-'
    },
    {
      key: 'record_date',
      header: '股权登记日',
      accessor: (row) => row.record_date || '-'
    }
  ], [])

  // 移动端卡片
  const mobileCard = useCallback((item: DividendData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">股票代码</span>
        <span className="font-medium">{item.ts_code}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">分红年度</span>
        <span>{item.end_date || '-'}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">公告日期</span>
        <span>{item.ann_date || '-'}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">实施进度</span>
        <span>{item.div_proc || '-'}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">每股分红(税后)</span>
        <span className="font-medium text-green-600">
          {item.cash_div !== null && item.cash_div !== undefined ? item.cash_div.toFixed(4) : '-'}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">每股送转</span>
        <span className="font-medium text-blue-600">
          {item.stk_div !== null && item.stk_div !== undefined ? item.stk_div.toFixed(4) : '-'}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">除权除息日</span>
        <span>{item.ex_date || '-'}</span>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="分红送股数据"
        description="上市公司分红送股详细信息，包括现金分红、送股、转增等"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">总记录数</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.total_records?.toLocaleString() ?? 0}</div>
              <p className="text-xs text-muted-foreground mt-1">
                统计股票数: {statistics.stock_count?.toLocaleString() ?? 0}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">平均现金分红</CardTitle>
              <DollarSign className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {statistics.avg_cash_div?.toFixed(4) ?? '0.0000'}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                每股分红(税后)
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最高现金分红</CardTitle>
              <TrendingUp className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {statistics.max_cash_div?.toFixed(4) ?? '0.0000'}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                最大每股分红
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">平均送转比例</CardTitle>
              <TrendingDown className="h-4 w-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">
                {statistics.avg_stk_div?.toFixed(4) ?? '0.0000'}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                每股送转
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选和操作区域 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
          <CardDescription>
            查询上市公司分红送股数据（至少提供一个筛选条件）
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <Input
                placeholder="股票代码 (如: 600848.SH)"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="flex flex-col sm:flex-row gap-4 items-end">
              <DatePicker
                date={startDate}
                onDateChange={setStartDate}
                placeholder="开始日期"
              />
              <DatePicker
                date={endDate}
                onDateChange={setEndDate}
                placeholder="结束日期"
              />
              <Button onClick={handleQuery} disabled={loading}>
                {loading ? '查询中...' : '查询'}
              </Button>
              <Button
                variant="default"
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
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card className="p-0 sm:p-0 overflow-hidden">
        <DataTable
          columns={columns}
          data={data}
          loading={loading}
          emptyMessage="暂无数据"
          mobileCard={mobileCard}
          page={currentPage}
          pageSize={pageSize}
          total={totalRecords}
          onPageChange={setCurrentPage}
          onPageSizeChange={setPageSize}
          pageSizeOptions={[10, 20, 30, 50, 100]}
        />
      </Card>
    </div>
  )
}
