'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { DatePicker } from '@/components/ui/date-picker'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { financialDataApi, type FinaIndicatorData, type FinaIndicatorStatistics } from '@/lib/api/financial-data'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, Percent, PieChart, Activity } from 'lucide-react'

const toDateStr = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

export default function FinaIndicatorPage() {
  const [data, setData] = useState<FinaIndicatorData[]>([])
  const [statistics, setStatistics] = useState<FinaIndicatorStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 查询参数
  const [tsCode, setTsCode] = useState('')
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [period, setPeriod] = useState<Date | undefined>(undefined)

  // 分页
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // 同步弹窗状态
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncTsCode, setSyncTsCode] = useState('')
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)
  const [syncPeriod, setSyncPeriod] = useState<Date | undefined>(undefined)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  const syncing = isTaskRunning('tasks.sync_fina_indicator')

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await financialDataApi.getFinaIndicator({
        ts_code: tsCode || undefined,
        start_date: startDate ? toDateStr(startDate) : undefined,
        end_date: endDate ? toDateStr(endDate) : undefined,
        period: period ? toDateStr(period) : undefined,
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
  }, [tsCode, startDate, endDate, period, pageSize])

  // 加载统计信息
  const loadStatistics = useCallback(async () => {
    try {
      const response = await financialDataApi.getFinaIndicatorStatistics({
        ts_code: tsCode || undefined,
        start_date: startDate ? toDateStr(startDate) : undefined,
        end_date: endDate ? toDateStr(endDate) : undefined
      })

      if (response.code === 200 && response.data) {
        setStatistics(response.data)
      }
    } catch {
      // 统计信息加载失败不影响主要数据展示
    }
  }, [tsCode, startDate, endDate])

  // 初始化加载
  useEffect(() => {
    loadData()
    loadStatistics()
  }, [loadData, loadStatistics])

  // 异步同步
  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    try {
      const params: any = {}
      if (syncTsCode) params.ts_code = syncTsCode
      if (syncStartDate) params.start_date = toDateStr(syncStartDate)
      if (syncEndDate) params.end_date = toDateStr(syncEndDate)
      if (syncPeriod) params.period = toDateStr(syncPeriod)

      const response = await financialDataApi.syncFinaIndicatorAsync(params)

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
            toast.success('数据同步完成', { description: '财务指标数据已更新' })
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

  // 格式化日期
  const formatDate = (dateStr: string) => {
    if (!dateStr || dateStr.length !== 8) return dateStr
    return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
  }

  // 格式化数字
  const formatNumber = (value: number | null | undefined, decimals: number = 2) => {
    if (value === null || value === undefined) return '-'
    return value.toFixed(decimals)
  }

  // 格式化百分比
  const formatPercent = (value: number | null | undefined, decimals: number = 2) => {
    if (value === null || value === undefined) return '-'
    return `${value.toFixed(decimals)}%`
  }

  // 桌面端表格列定义
  const columns: Column<FinaIndicatorData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'ann_date',
      header: '公告日期',
      accessor: (row) => formatDate(row.ann_date)
    },
    {
      key: 'end_date',
      header: '报告期',
      accessor: (row) => formatDate(row.end_date)
    },
    {
      key: 'eps',
      header: 'EPS(元)',
      accessor: (row) => formatNumber(row.eps, 4)
    },
    {
      key: 'roe',
      header: 'ROE(%)',
      accessor: (row) => (
        <span className={row.roe && row.roe >= 15 ? 'text-red-600 font-semibold' : ''}>
          {formatNumber(row.roe)}
        </span>
      )
    },
    {
      key: 'debt_to_assets',
      header: '资产负债率(%)',
      accessor: (row) => (
        <span className={row.debt_to_assets && row.debt_to_assets >= 70 ? 'text-orange-600' : ''}>
          {formatNumber(row.debt_to_assets)}
        </span>
      )
    },
    {
      key: 'grossprofit_margin',
      header: '毛利率(%)',
      accessor: (row) => formatNumber(row.grossprofit_margin)
    },
    {
      key: 'netprofit_margin',
      header: '净利率(%)',
      accessor: (row) => formatNumber(row.netprofit_margin)
    },
    {
      key: 'roa',
      header: 'ROA(%)',
      accessor: (row) => formatNumber(row.roa)
    },
    {
      key: 'current_ratio',
      header: '流动比率',
      accessor: (row) => formatNumber(row.current_ratio)
    },
    {
      key: 'basic_eps_yoy',
      header: 'EPS增长率(%)',
      accessor: (row) => (
        <span className={row.basic_eps_yoy && row.basic_eps_yoy >= 0 ? 'text-red-600' : 'text-green-600'}>
          {formatNumber(row.basic_eps_yoy)}
        </span>
      )
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = (item: FinaIndicatorData) => (
    <div className="p-4 space-y-3 border-b last:border-b-0 hover:bg-blue-50 active:bg-blue-100 transition-colors">
      <div className="flex justify-between items-start">
        <div>
          <div className="font-semibold text-base">{item.ts_code}</div>
          <div className="text-sm text-muted-foreground">
            报告期: {formatDate(item.end_date)}
          </div>
        </div>
        <div className="text-sm text-muted-foreground">
          {formatDate(item.ann_date)}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <span className="text-muted-foreground">EPS: </span>
          <span className="font-medium">{formatNumber(item.eps, 4)}元</span>
        </div>
        <div>
          <span className="text-muted-foreground">ROE: </span>
          <span className={`font-medium ${item.roe && item.roe >= 15 ? 'text-red-600' : ''}`}>
            {formatPercent(item.roe)}
          </span>
        </div>
        <div>
          <span className="text-muted-foreground">资产负债率: </span>
          <span className={`font-medium ${item.debt_to_assets && item.debt_to_assets >= 70 ? 'text-orange-600' : ''}`}>
            {formatPercent(item.debt_to_assets)}
          </span>
        </div>
        <div>
          <span className="text-muted-foreground">毛利率: </span>
          <span className="font-medium">{formatPercent(item.grossprofit_margin)}</span>
        </div>
        <div>
          <span className="text-muted-foreground">净利率: </span>
          <span className="font-medium">{formatPercent(item.netprofit_margin)}</span>
        </div>
        <div>
          <span className="text-muted-foreground">ROA: </span>
          <span className="font-medium">{formatPercent(item.roa)}</span>
        </div>
        <div>
          <span className="text-muted-foreground">流动比率: </span>
          <span className="font-medium">{formatNumber(item.current_ratio)}</span>
        </div>
        <div>
          <span className="text-muted-foreground">EPS增长: </span>
          <span className={`font-medium ${item.basic_eps_yoy && item.basic_eps_yoy >= 0 ? 'text-red-600' : 'text-green-600'}`}>
            {formatPercent(item.basic_eps_yoy)}
          </span>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="财务指标"
        description="上市公司财务指标数据，包括EPS、ROE、资产负债率、毛利率、净利率等核心财务指标"
        actions={
          <Button onClick={() => setSyncDialogOpen(true)} disabled={syncing}>
            {syncing ? (
              <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
            ) : (
              <><RefreshCw className="h-4 w-4 mr-1" />同步数据</>
            )}
          </Button>
        }
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">平均EPS</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.avg_eps, 4)} 元</p>
                  <p className="text-xs text-muted-foreground mt-1">每股收益平均值</p>
                </div>
                <Activity className="h-6 w-6 sm:h-8 sm:w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">平均ROE</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.avg_roe)}%</p>
                  <p className="text-xs text-muted-foreground mt-1">净资产收益率平均值</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">平均资产负债率</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.avg_debt_ratio)}%</p>
                  <p className="text-xs text-muted-foreground mt-1">负债占资产比例</p>
                </div>
                <PieChart className="h-6 w-6 sm:h-8 sm:w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">平均净利率</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.avg_netprofit_margin)}%</p>
                  <p className="text-xs text-muted-foreground mt-1">净利润占营收比例</p>
                </div>
                <Percent className="h-6 w-6 sm:h-8 sm:w-8 text-muted-foreground" />
              </div>
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
              <Label>开始日期</Label>
              <DatePicker date={startDate} onDateChange={setStartDate} placeholder="选择开始日期" />
            </div>
            <div className="space-y-2">
              <Label>结束日期</Label>
              <DatePicker date={endDate} onDateChange={setEndDate} placeholder="选择结束日期" />
            </div>
            <div className="space-y-2">
              <Label>报告期</Label>
              <DatePicker date={period} onDateChange={setPeriod} placeholder="选择报告期" />
            </div>
          </div>
          <div className="flex gap-2 mt-4">
            <Button onClick={loadData} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
              查询
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="pt-6">
          <DataTable
            columns={columns}
            data={data}
            loading={loading}
            error={error}
            emptyMessage="暂无财务指标数据"
            mobileCard={mobileCard}
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: setPage,
              onPageSizeChange: (newSize) => {
                setPageSize(newSize)
                setPage(1)
              },
              pageSizeOptions: [10, 20, 30, 50, 100]
            }}
          />
        </CardContent>
      </Card>

      {/* 同步弹窗 */}
      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>同步财务指标数据</DialogTitle>
            <DialogDescription>
              选择同步条件（均可留空），留空时同步最新数据。每次最多100条记录（2000积分/次）。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">股票代码（可选）</label>
              <Input
                placeholder="如 600000.SH，留空同步全部"
                value={syncTsCode}
                onChange={(e) => setSyncTsCode(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">开始日期（可选）</label>
              <DatePicker
                date={syncStartDate}
                onDateChange={setSyncStartDate}
                placeholder="留空不限制"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">结束日期（可选）</label>
              <DatePicker
                date={syncEndDate}
                onDateChange={setSyncEndDate}
                placeholder="留空不限制"
              />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">报告期（可选）</label>
              <DatePicker
                date={syncPeriod}
                onDateChange={setSyncPeriod}
                placeholder="留空不限制"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncDialogOpen(false)}>取消</Button>
            <Button onClick={handleSyncConfirm} disabled={syncing}>确认同步</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
