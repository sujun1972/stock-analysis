'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DataTable, Column } from '@/components/common/DataTable'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, TrendingDown, DollarSign, Activity } from 'lucide-react'
import { cashflowApi } from '@/lib/api'
import type { CashflowData, CashflowStatistics } from '@/lib/api/cashflow-api'
import { useTaskStore } from '@/stores/task-store'

export default function CashflowPage() {
  const [data, setData] = useState<CashflowData[]>([])
  const [statistics, setStatistics] = useState<CashflowStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [syncing, setSyncing] = useState(false)

  // 查询参数
  const [tsCode, setTsCode] = useState('')
  const [period, setPeriod] = useState('')

  // 分页
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // 任务存储
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await cashflowApi.getCashflowData({
        ts_code: tsCode || undefined,
        period: period || undefined,
        limit: pageSize
      })

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setTotal(response.data.total || 0)
      } else {
        throw new Error(response.message || '加载数据失败')
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast.error('加载失败', { description: err.message })
    } finally {
      setLoading(false)
    }
  }, [tsCode, period, pageSize])

  // 加载统计信息
  const loadStatistics = useCallback(async () => {
    try {
      const response = await cashflowApi.getStatistics({
        ts_code: tsCode || undefined
      })

      if (response.code === 200 && response.data) {
        setStatistics(response.data)
      }
    } catch (err: any) {
      console.error('加载统计信息失败:', err)
    }
  }, [tsCode])

  useEffect(() => {
    loadData()
    loadStatistics()
  }, [loadData, loadStatistics])

  // 异步同步
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params: any = {}
      if (tsCode) params.ts_code = tsCode
      if (period) params.period = period

      const response = await cashflowApi.syncAsync(params)

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

        // 注册完成回调
        const completionCallback = (task: any) => {
          if (task.status === 'success') {
            loadData().catch(() => {})
            loadStatistics().catch(() => {})
            toast.success('数据同步完成', {
              description: '现金流量表数据已更新'
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

  // 组件卸载时清理
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
  const columns: Column<CashflowData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'end_date',
      header: '报告期',
      accessor: (row) => row.end_date
    },
    {
      key: 'ann_date',
      header: '公告日期',
      accessor: (row) => row.ann_date
    },
    {
      key: 'n_cashflow_act',
      header: <span className="text-xs sm:text-sm">经营现金流(万)</span>,
      accessor: (row) => (
        <span className={row.n_cashflow_act && row.n_cashflow_act > 0 ? 'text-red-600' : 'text-green-600'}>
          {row.n_cashflow_act?.toFixed(2) || '0.00'}
        </span>
      )
    },
    {
      key: 'n_cashflow_inv_act',
      header: <span className="text-xs sm:text-sm">投资现金流(万)</span>,
      accessor: (row) => (
        <span className={row.n_cashflow_inv_act && row.n_cashflow_inv_act > 0 ? 'text-red-600' : 'text-green-600'}>
          {row.n_cashflow_inv_act?.toFixed(2) || '0.00'}
        </span>
      )
    },
    {
      key: 'n_cash_flows_fnc_act',
      header: <span className="text-xs sm:text-sm">筹资现金流(万)</span>,
      accessor: (row) => (
        <span className={row.n_cash_flows_fnc_act && row.n_cash_flows_fnc_act > 0 ? 'text-red-600' : 'text-green-600'}>
          {row.n_cash_flows_fnc_act?.toFixed(2) || '0.00'}
        </span>
      )
    },
    {
      key: 'free_cashflow',
      header: <span className="text-xs sm:text-sm">自由现金流(万)</span>,
      accessor: (row) => (
        <span className={row.free_cashflow && row.free_cashflow > 0 ? 'text-red-600' : 'text-green-600'}>
          {row.free_cashflow?.toFixed(2) || '0.00'}
        </span>
      )
    }
  ], [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="现金流量表"
        description="上市公司现金流量表数据查询（经营、投资、筹资活动现金流）"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">记录总数</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.total?.toLocaleString() || 0}</div>
              <p className="text-xs text-muted-foreground mt-1">
                覆盖 {statistics.stock_count || 0} 只股票
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">平均经营现金流</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.avg_operating_cf?.toFixed(2) || '0.00'}</div>
              <p className="text-xs text-muted-foreground mt-1">万元</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">平均自由现金流</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.avg_free_cf?.toFixed(2) || '0.00'}</div>
              <p className="text-xs text-muted-foreground mt-1">万元</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最大经营现金流</CardTitle>
              <TrendingDown className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.max_operating_cf?.toFixed(2) || '0.00'}</div>
              <p className="text-xs text-muted-foreground mt-1">万元</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 查询表单 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label htmlFor="ts_code">股票代码</Label>
              <Input
                id="ts_code"
                placeholder="如：600000.SH"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="period">报告期</Label>
              <Input
                id="period"
                type="date"
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
              />
            </div>
            <div className="flex items-end space-x-2">
              <Button onClick={loadData} disabled={loading}>
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
          error={error}
          emptyMessage="暂无现金流量表数据"
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
      </Card>
    </div>
  )
}
