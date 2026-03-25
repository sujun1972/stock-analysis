'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { stockRealtimeApi } from '@/lib/api'
import type { StockRealtimeData, StockRealtimeStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, TrendingDown, Activity, BarChart3 } from 'lucide-react'

export default function StockRealtimePage() {
  const [data, setData] = useState<StockRealtimeData[]>([])
  const [statistics, setStatistics] = useState<StockRealtimeStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [syncing, setSyncing] = useState(false)
  const [batchSize, setBatchSize] = useState(100)
  const [updateMode, setUpdateMode] = useState<'full' | 'incremental'>('incremental')
  const [dataSource, setDataSource] = useState<string>('tushare')

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

      const [dataResp, statsResp] = await Promise.all([
        stockRealtimeApi.getData(currentPage, pageSize),
        stockRealtimeApi.getStatistics()
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
  }, [currentPage, pageSize])

  useEffect(() => {
    loadData()
  }, [loadData])

  // 异步同步数据
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params = {
        batch_size: batchSize,
        update_oldest: updateMode === 'incremental',
        data_source: dataSource
      }

      const response = await stockRealtimeApi.syncAsync(params)

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
            toast.success('数据同步完成', { description: '实时行情已更新' })
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
  const columns: Column<StockRealtimeData>[] = useMemo(() => [
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
      key: 'latest_price',
      header: '最新价',
      accessor: (row) => row.latest_price?.toFixed(2) || '-'
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
      key: 'change_amount',
      header: '涨跌额',
      accessor: (row) => row.change_amount !== null ? row.change_amount.toFixed(2) : '-'
    },
    {
      key: 'volume',
      header: '成交量',
      accessor: (row) => row.volume !== null ? (row.volume / 10000).toFixed(2) + '万' : '-'
    },
    {
      key: 'amount',
      header: '成交额',
      accessor: (row) => row.amount !== null ? (row.amount / 100000000).toFixed(2) + '亿' : '-'
    },
    {
      key: 'turnover',
      header: '换手率',
      accessor: (row) => row.turnover !== null ? row.turnover.toFixed(2) + '%' : '-'
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: StockRealtimeData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">股票</span>
        <span className="font-medium">{item.code} {item.name}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">最新价</span>
        <span className="font-medium">{item.latest_price?.toFixed(2) || '-'}</span>
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
        title="实时行情同步"
        description="获取最新的实时行情快照，使用Tushare daily接口（120积分/次）"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">总股票数</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.total_count.toLocaleString()}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">上涨</CardTitle>
              <TrendingUp className="h-4 w-4 text-red-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{statistics.rising_count.toLocaleString()}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">下跌</CardTitle>
              <TrendingDown className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{statistics.falling_count.toLocaleString()}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">平均涨跌幅</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
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
        </div>
      )}

      {/* 筛选和操作 */}
      <Card>
        <CardHeader>
          <CardTitle>数据同步</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-4">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">更新模式</label>
                <Select value={updateMode} onValueChange={(val) => setUpdateMode(val as 'full' | 'incremental')}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="incremental">渐进式更新（推荐）</SelectItem>
                    <SelectItem value="full">全量更新</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">批次大小</label>
                <Select value={String(batchSize)} onValueChange={(val) => setBatchSize(Number(val))}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="50">50只</SelectItem>
                    <SelectItem value="100">100只</SelectItem>
                    <SelectItem value="200">200只</SelectItem>
                    <SelectItem value="500">500只</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-sm font-medium">数据源</label>
                <Select value={dataSource} onValueChange={setDataSource}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="tushare">Tushare（推荐）</SelectItem>
                    <SelectItem value="akshare">AkShare</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex gap-2">
              <Button onClick={loadData} disabled={loading}>
                <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
                刷新
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
        <DataTable
          columns={columns}
          data={data}
          loading={loading}
          error={error}
          emptyMessage="暂无实时行情数据"
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
