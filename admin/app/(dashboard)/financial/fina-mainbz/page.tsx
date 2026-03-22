'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { financialDataApi, type FinaMainbzData, type FinaMainbzStatistics } from '@/lib/api/financial-data'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, PieChart, TrendingUp, DollarSign, Package } from 'lucide-react'

export default function FinaMainbzPage() {
  const [data, setData] = useState<FinaMainbzData[]>([])
  const [statistics, setStatistics] = useState<FinaMainbzStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [syncing, setSyncing] = useState(false)

  // 查询参数
  const [tsCode, setTsCode] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [period, setPeriod] = useState('')
  const [type, setType] = useState<string>('ALL')

  // 分页
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await financialDataApi.getFinaMainbz({
        ts_code: tsCode || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined,
        period: period || undefined,
        type: type === 'ALL' ? undefined : type,
        limit: pageSize
      })

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setTotal(response.data.total || 0)
      } else {
        throw new Error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast.error('加载失败', { description: err.message })
    } finally {
      setLoading(false)
    }
  }, [tsCode, startDate, endDate, period, type, pageSize])

  // 加载统计信息
  const loadStatistics = useCallback(async () => {
    try {
      const response = await financialDataApi.getFinaMainbzStatistics({
        ts_code: tsCode || undefined,
        start_date: startDate || undefined,
        end_date: endDate || undefined
      })

      if (response.code === 200 && response.data) {
        setStatistics(response.data)
      }
    } catch (err: any) {
      console.error('加载统计信息失败:', err)
    }
  }, [tsCode, startDate, endDate])

  // 初始化加载
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
      if (startDate) params.start_date = startDate
      if (endDate) params.end_date = endDate
      if (period) params.period = period
      if (type !== 'ALL') params.type = type

      const response = await financialDataApi.syncFinaMainbzAsync(params)

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
            toast.success('数据同步完成', { description: '主营业务构成数据已更新' })
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

  // 格式化金额（元转万元）
  const formatAmount = (amount: number | null | undefined) => {
    if (amount === null || amount === undefined) return '-'
    return (amount / 10000).toFixed(2)
  }

  // 表格列定义
  const columns: Column<FinaMainbzData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'end_date',
      header: '报告期',
      accessor: (row) => {
        const date = row.end_date
        return date ? `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}` : '-'
      }
    },
    {
      key: 'bz_item',
      header: '业务来源',
      accessor: (row) => row.bz_item || '-'
    },
    {
      key: 'bz_sales',
      header: <span>主营收入<br className="sm:hidden" /><span className="text-xs text-muted-foreground">(万元)</span></span>,
      accessor: (row) => formatAmount(row.bz_sales)
    },
    {
      key: 'bz_profit',
      header: <span>主营利润<br className="sm:hidden" /><span className="text-xs text-muted-foreground">(万元)</span></span>,
      accessor: (row) => formatAmount(row.bz_profit)
    },
    {
      key: 'bz_cost',
      header: <span>主营成本<br className="sm:hidden" /><span className="text-xs text-muted-foreground">(万元)</span></span>,
      accessor: (row) => formatAmount(row.bz_cost)
    },
    {
      key: 'curr_type',
      header: '货币',
      accessor: (row) => row.curr_type || '-'
    }
  ], [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="主营业务构成"
        description="上市公司主营业务构成数据，按产品/地区/行业分类"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">总记录数</CardTitle>
              <Package className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.total_count.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground mt-1">
                股票数: {statistics.stock_count}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">业务类型数</CardTitle>
              <PieChart className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.bz_item_count.toLocaleString()}</div>
              <p className="text-xs text-muted-foreground mt-1">
                报告期数: {statistics.period_count}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">平均收入</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatAmount(statistics.avg_bz_sales)}万</div>
              <p className="text-xs text-muted-foreground mt-1">
                总收入: {formatAmount(statistics.total_bz_sales)}万
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">收入范围</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatAmount(statistics.max_bz_sales)}万</div>
              <p className="text-xs text-muted-foreground mt-1">
                最小: {formatAmount(statistics.min_bz_sales)}万
              </p>
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
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <Label htmlFor="tsCode">股票代码</Label>
              <Input
                id="tsCode"
                placeholder="如: 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="startDate">开始日期</Label>
              <Input
                id="startDate"
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="endDate">结束日期</Label>
              <Input
                id="endDate"
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="period">报告期</Label>
              <Input
                id="period"
                type="date"
                placeholder="如: 2023-12-31"
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
              />
            </div>
            <div>
              <Label htmlFor="type">分类类型</Label>
              <Select value={type} onValueChange={setType}>
                <SelectTrigger id="type">
                  <SelectValue placeholder="选择类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="P">按产品</SelectItem>
                  <SelectItem value="D">按地区</SelectItem>
                  <SelectItem value="I">按行业</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <Button onClick={loadData} variant="default">
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
