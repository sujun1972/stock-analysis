'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { apiClient } from '@/lib/api-client'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, Database, TrendingUp, BarChart3, Package } from 'lucide-react'

interface DailyBasicData {
  ts_code: string
  trade_date: string
  close: number | null
  turnover_rate: number | null
  turnover_rate_f: number | null
  volume_ratio: number | null
  pe: number | null
  pe_ttm: number | null
  pb: number | null
  ps: number | null
  ps_ttm: number | null
  dv_ratio: number | null
  dv_ttm: number | null
  total_share: number | null
  float_share: number | null
  free_share: number | null
  total_mv: number | null
  circ_mv: number | null
}

interface DailyBasicStatistics {
  total_records: number
  date_range: {
    earliest_date: string
    latest_date: string
  }
  avg_turnover_rate: number
  avg_pe_ttm: number
  stock_count: number
}

export default function DailyBasicPage() {
  const [data, setData] = useState<DailyBasicData[]>([])
  const [statistics, setStatistics] = useState<DailyBasicStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [syncing, setSyncing] = useState(false)

  // 筛选条件
  const [tsCode, setTsCode] = useState('')
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)

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

      const params: any = { page, page_size: pageSize }
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (tradeDate) params.trade_date = tradeDate.toISOString().split('T')[0]
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]

      const response = await apiClient.get('/api/daily-basic', { params })

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setTotal(response.data.total || 0)
      } else {
        throw new Error(response.message || '获取数据失败')
      }

      // 加载统计信息
      const statsParams: any = {}
      if (startDate) statsParams.start_date = startDate.toISOString().split('T')[0]
      if (endDate) statsParams.end_date = endDate.toISOString().split('T')[0]

      const statsResponse = await apiClient.get('/api/daily-basic/statistics', { params: statsParams })
      if (statsResponse.code === 200 && statsResponse.data) {
        setStatistics(statsResponse.data)
      }
    } catch (err: any) {
      setError(err.message || '加载失败')
      toast.error('加载失败', { description: err.message })
    } finally {
      setLoading(false)
    }
  }, [tsCode, tradeDate, startDate, endDate, page, pageSize])

  // 初始加载
  useEffect(() => {
    loadData()
  }, [loadData])

  // 清理任务回调
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

  // 异步同步
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params: any = {}
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (tradeDate) params.trade_date = tradeDate.toISOString().split('T')[0]
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]

      const response = await apiClient.post('/api/daily-basic/sync-async', null, { params })

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

        // 注册任务完成回调
        const completionCallback = (task: any) => {
          if (task.status === 'success') {
            loadData().catch(() => {})
            toast.success('数据同步完成', {
              description: '每日指标数据已更新'
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

  // 表格列定义
  const columns: Column<DailyBasicData>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => row.trade_date
    },
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'close',
      header: '收盘价',
      accessor: (row) => row.close !== null ? `¥${row.close.toFixed(2)}` : '-'
    },
    {
      key: 'turnover_rate',
      header: '换手率',
      accessor: (row) => row.turnover_rate !== null ? `${row.turnover_rate.toFixed(2)}%` : '-'
    },
    {
      key: 'volume_ratio',
      header: '量比',
      accessor: (row) => row.volume_ratio !== null ? row.volume_ratio.toFixed(2) : '-'
    },
    {
      key: 'pe_ttm',
      header: '市盈率(TTM)',
      accessor: (row) => row.pe_ttm !== null ? row.pe_ttm.toFixed(2) : '-'
    },
    {
      key: 'pb',
      header: '市净率',
      accessor: (row) => row.pb !== null ? row.pb.toFixed(2) : '-'
    },
    {
      key: 'ps_ttm',
      header: '市销率(TTM)',
      accessor: (row) => row.ps_ttm !== null ? row.ps_ttm.toFixed(2) : '-'
    },
    {
      key: 'total_mv',
      header: '总市值(万元)',
      accessor: (row) => row.total_mv !== null ? row.total_mv.toFixed(0) : '-'
    },
    {
      key: 'circ_mv',
      header: '流通市值(万元)',
      accessor: (row) => row.circ_mv !== null ? row.circ_mv.toFixed(0) : '-'
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: DailyBasicData) => (
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
        <span className="text-sm text-gray-600 dark:text-gray-400">收盘价</span>
        <span className="font-medium">
          {item.close !== null ? `¥${item.close.toFixed(2)}` : '-'}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">换手率</span>
        <span className="font-medium">
          {item.turnover_rate !== null ? `${item.turnover_rate.toFixed(2)}%` : '-'}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">市盈率(TTM)</span>
        <span className="font-medium">
          {item.pe_ttm !== null ? item.pe_ttm.toFixed(2) : '-'}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">市净率</span>
        <span className="font-medium">
          {item.pb !== null ? item.pb.toFixed(2) : '-'}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">总市值</span>
        <span className="font-medium">
          {item.total_mv !== null ? `${item.total_mv.toFixed(0)}万元` : '-'}
        </span>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="每日指标"
        description="获取全部股票每日重要的基本面指标，可用于选股分析、报表展示等（2000积分/次，单次最大6000条）"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">总记录数</CardTitle>
              <Database className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.total_records?.toLocaleString() || 0}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">统计股票数</CardTitle>
              <Package className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.stock_count?.toLocaleString() || 0}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">平均换手率</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {statistics.avg_turnover_rate !== null && statistics.avg_turnover_rate !== undefined
                  ? `${statistics.avg_turnover_rate.toFixed(2)}%`
                  : '-'}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">平均市盈率(TTM)</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {statistics.avg_pe_ttm !== null && statistics.avg_pe_ttm !== undefined
                  ? statistics.avg_pe_ttm.toFixed(2)
                  : '-'}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 查询条件 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="space-y-2">
              <Label htmlFor="ts-code">股票代码</Label>
              <Input
                id="ts-code"
                placeholder="如：000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label>交易日期</Label>
              <DatePicker date={tradeDate} onSelect={setTradeDate} placeholder="选择日期" />
            </div>
            <div className="space-y-2">
              <Label>开始日期</Label>
              <DatePicker date={startDate} onSelect={setStartDate} placeholder="开始日期" />
            </div>
            <div className="space-y-2">
              <Label>结束日期</Label>
              <DatePicker date={endDate} onSelect={setEndDate} placeholder="结束日期" />
            </div>
            <div className="flex items-end gap-2">
              <Button onClick={loadData} className="flex-1">查询</Button>
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
        {/* 移动端视图 */}
        <div className="sm:hidden">
          <div className="px-4 py-3 border-b bg-muted/50">
            <h3 className="text-sm font-medium">每日指标数据</h3>
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
