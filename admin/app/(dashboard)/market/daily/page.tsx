'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { stockDailyApi } from '@/lib/api'
import type { StockDailyData, StockDailyStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, Database, Calendar, BarChart3 } from 'lucide-react'

export default function StockDailyPage() {
  const [data, setData] = useState<StockDailyData[]>([])
  const [statistics, setStatistics] = useState<StockDailyStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 筛选参数
  const [code, setCode] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')

  // 同步参数（独立于查询筛选，留在"数据同步"卡片中）
  const [syncCode, setSyncCode] = useState('')
  const [syncStartDate, setSyncStartDate] = useState('')
  const [syncEndDate, setSyncEndDate] = useState('')
  const [syncYears, setSyncYears] = useState(5)

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [totalRecords, setTotalRecords] = useState(0)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  // 从 task store 派生 syncing 状态
  const syncing = isTaskRunning('tasks.sync_daily_single')

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params = {
        code: code || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        page: currentPage,
        page_size: pageSize
      }

      const [dataResp, statsResp] = await Promise.all([
        stockDailyApi.getData(params),
        stockDailyApi.getStatistics(code || undefined, startDate || undefined, endDate || undefined)
      ])

      if (dataResp.code === 200) {
        setData(dataResp.data?.items || [])
        setTotalRecords(dataResp.data?.total || 0)
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
  }, [code, startDate, endDate, currentPage, pageSize])

  useEffect(() => {
    loadData()
  }, [loadData])

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

  const handleSync = async () => {
    try {
      const params = {
        code: syncCode || undefined,
        start_date: syncStartDate || undefined,
        end_date: syncEndDate || undefined,
        years: syncYears
      }

      const response = await stockDailyApi.syncAsync(params)

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
            toast.success('数据同步完成', { description: '日线数据已更新' })
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
    }
  }

  // 表格列定义
  const columns: Column<StockDailyData>[] = useMemo(() => [
    {
      key: 'code',
      header: '代码',
      accessor: (row) => row.code
    },
    {
      key: 'name',
      header: '名称',
      accessor: (row) => row.name
    },
    {
      key: 'date',
      header: '日期',
      accessor: (row) => row.date
    },
    {
      key: 'close',
      header: '收盘价',
      accessor: (row) => row.close?.toFixed(2) || '-'
    },
    {
      key: 'pct_change',
      header: '涨跌幅',
      accessor: (row) => (
        <span className={
          (row.pct_change ?? 0) > 0 ? 'text-red-600 font-medium' :
          (row.pct_change ?? 0) < 0 ? 'text-green-600 font-medium' :
          'text-gray-600'
        }>
          {row.pct_change !== null && row.pct_change !== undefined
            ? `${row.pct_change > 0 ? '+' : ''}${row.pct_change.toFixed(2)}%`
            : '-'}
        </span>
      )
    },
    {
      key: 'open',
      header: '开盘',
      accessor: (row) => row.open?.toFixed(2) || '-'
    },
    {
      key: 'high',
      header: '最高',
      accessor: (row) => row.high?.toFixed(2) || '-'
    },
    {
      key: 'low',
      header: '最低',
      accessor: (row) => row.low?.toFixed(2) || '-'
    },
    {
      key: 'volume',
      header: '成交量',
      accessor: (row) => row.volume !== null ? (row.volume / 10000).toFixed(2) + '万手' : '-'
    },
    {
      key: 'amount',
      header: '成交额',
      accessor: (row) => row.amount !== null ? (row.amount / 100000000).toFixed(2) + '亿' : '-'
    },
    {
      key: 'amplitude',
      header: '振幅',
      accessor: (row) => row.amplitude !== null ? row.amplitude.toFixed(2) + '%' : '-'
    },
    {
      key: 'turnover',
      header: '换手率',
      accessor: (row) => row.turnover !== null ? row.turnover.toFixed(2) + '%' : '-'
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: StockDailyData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">股票</span>
        <span className="font-medium">{item.code} {item.name}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">日期</span>
        <span>{item.date}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">收盘价</span>
        <span className="font-medium">{item.close?.toFixed(2) || '-'}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">涨跌幅</span>
        <span className={`font-medium ${
          (item.pct_change ?? 0) > 0 ? 'text-red-600' :
          (item.pct_change ?? 0) < 0 ? 'text-green-600' :
          'text-gray-600'
        }`}>
          {item.pct_change !== null && item.pct_change !== undefined
            ? `${item.pct_change > 0 ? '+' : ''}${item.pct_change.toFixed(2)}%`
            : '-'}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">成交额</span>
        <span>{item.amount !== null ? (item.amount / 100000000).toFixed(2) + '亿' : '-'}</span>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="股票日线数据"
        description="查询和同步股票日线行情数据，使用Tushare daily接口"
        actions={
          <Button onClick={handleSync} disabled={syncing}>
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
        }
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">股票数量</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.stock_count.toLocaleString()}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">记录总数</CardTitle>
              <Database className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.record_count.toLocaleString()}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">平均涨跌幅</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${
                statistics.avg_pct_change > 0 ? 'text-red-600' :
                statistics.avg_pct_change < 0 ? 'text-green-600' :
                'text-gray-600'
              }`}>
                {statistics.avg_pct_change > 0 ? '+' : ''}{statistics.avg_pct_change.toFixed(2)}%
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最新日期</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.latest_date || '-'}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 数据查询 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">股票代码</label>
                <Input
                  placeholder="如：000001"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">开始日期</label>
                <Input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">结束日期</label>
                <Input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                />
              </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={loadData} disabled={loading}>
                <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
                查询
              </Button>
              <Button
                onClick={() => {
                  setCode('')
                  setStartDate('')
                  setEndDate('')
                }}
                variant="outline"
              >
                重置
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据同步 */}
      <Card>
        <CardHeader>
          <CardTitle>数据同步</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">股票代码（可选）</label>
                <Input
                  placeholder="如：000001.SZ（留空则同步全市场）"
                  value={syncCode}
                  onChange={(e) => setSyncCode(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">开始日期</label>
                <Input
                  type="date"
                  value={syncStartDate}
                  onChange={(e) => setSyncStartDate(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">结束日期</label>
                <Input
                  type="date"
                  value={syncEndDate}
                  onChange={(e) => setSyncEndDate(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">或者年数</label>
                <Input
                  type="number"
                  min={1}
                  max={20}
                  value={syncYears}
                  onChange={(e) => setSyncYears(Number(e.target.value))}
                />
              </div>
            </div>
            <div className="text-sm text-gray-500">
              提示：留空股票代码将同步全市场数据（使用最近交易日）。指定股票代码可同步该股票的历史数据（默认{syncYears}年）
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <DataTable
          columns={columns}
          data={data}
          loading={loading}
          error={error}
          emptyMessage="暂无日线数据"
          mobileCard={mobileCard}
          pagination={{
            page: currentPage,
            pageSize: pageSize,
            total: totalRecords,
            onPageChange: setCurrentPage,
            onPageSizeChange: setPageSize,
            pageSizeOptions: [10, 20, 30, 50, 100]
          }}
        />
      </Card>
    </div>
  )
}
