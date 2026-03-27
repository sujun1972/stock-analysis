'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { moneyflowApi } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import {
  TrendingUp,
  TrendingDown,
  Activity,
  DollarSign,
  RefreshCw,
  ListFilter,
} from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'

interface MoneyflowData {
  trade_date: string
  ggt_ss: number      // 港股通（上海）
  ggt_sz: number      // 港股通（深圳）
  hgt: number         // 沪股通
  sgt: number         // 深股通
  north_money: number // 北向资金
  south_money: number // 南向资金
}

interface Statistics {
  avg_north: number
  max_north: number
  min_north: number
  total_north: number
  avg_south: number
  max_south: number
  min_south: number
  total_south: number
  latest_date: string
  earliest_date: string
  count: number
}

const PAGE_SIZE = 30

// 时区安全的日期字符串构建（避免 toISOString UTC 偏移）
const toDateStr = (date: Date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

// 百万元 → 亿元
const toYi = (value: number | null | undefined, decimals = 2) => {
  if (value === null || value === undefined) return '0.00'
  return (value / 100).toFixed(decimals)
}

const pctColor = (val: number | null | undefined) =>
  (val ?? 0) >= 0 ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400'

const formatDate = (dateStr: string) => {
  if (!dateStr || dateStr.length !== 8) return dateStr
  return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
}

export default function MoneyflowHsgtPage() {
  const [data, setData] = useState<MoneyflowData[]>([])
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  // 从 task store 实时派生——不用本地 useState
  const syncing = isTaskRunning('tasks.sync_moneyflow_hsgt')

  const loadData = useCallback(async (targetPage: number = 1) => {
    setIsLoading(true)
    try {
      const params: any = {
        limit: PAGE_SIZE,
        offset: (targetPage - 1) * PAGE_SIZE,
      }
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)

      const response = await moneyflowApi.getMoneyflowHsgt(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics || null)
        setTotal(response.data.total || 0)
        setPage(targetPage)
      } else {
        throw new Error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      toast.error(err.message || '加载数据失败')
    } finally {
      setIsLoading(false)
    }
  }, [startDate, endDate])

  // 仅在 mount 时加载，后续由用户点击查询按钮触发
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { loadData(1) }, [])

  const handleQuery = () => loadData(1)

  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    try {
      // 不传查询日期，仅传用户在弹窗中显式选择的日期
      const params: any = {}
      if (syncStartDate) params.start_date = toDateStr(syncStartDate)
      if (syncEndDate) params.end_date = toDateStr(syncEndDate)

      const response = await moneyflowApi.syncMoneyflowHsgtAsync(params)

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
            loadData(1)
            toast.success('沪深港通资金流向数据同步完成')
          } else if (task.status === 'failure') {
            toast.error('数据同步失败', { description: task.error || '同步过程中发生错误' })
          }
          unregisterCompletionCallback(taskId, completionCallback)
          activeCallbacksRef.current.delete(taskId)
        }
        activeCallbacksRef.current.set(taskId, completionCallback)
        registerCompletionCallback(taskId, completionCallback)
        triggerPoll()

        toast.success('同步任务已提交', {
          description: `"${response.data.display_name}" 已开始执行，可在任务面板查看进度`
        })
      } else {
        throw new Error(response.message || '提交同步任务失败')
      }
    } catch (err: any) {
      toast.error(err.message || '提交同步任务失败')
    }
  }

  // 组件卸载时清理所有活跃的任务回调
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
  const columns: Column<MoneyflowData>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '日期',
      accessor: (row) => formatDate(row.trade_date),
      width: 110,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'hgt',
      header: '沪股通(亿)',
      accessor: (row) => (
        <div className={`text-right font-medium ${pctColor(row.hgt)}`}>
          {(row.hgt ?? 0) >= 0 ? '+' : ''}{toYi(row.hgt)}
        </div>
      ),
      width: 100,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'sgt',
      header: '深股通(亿)',
      accessor: (row) => (
        <div className={`text-right font-medium ${pctColor(row.sgt)}`}>
          {(row.sgt ?? 0) >= 0 ? '+' : ''}{toYi(row.sgt)}
        </div>
      ),
      width: 100,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'north_money',
      header: '北向合计(亿)',
      accessor: (row) => (
        <div className={`text-right font-semibold ${pctColor(row.north_money)}`}>
          {(row.north_money ?? 0) >= 0 ? '+' : ''}{toYi(row.north_money)}
        </div>
      ),
      width: 120,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'ggt_ss',
      header: '港股通沪(亿)',
      accessor: (row) => (
        <div className="text-right text-gray-600 dark:text-gray-400">
          {toYi(row.ggt_ss)}
        </div>
      ),
      width: 110,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'ggt_sz',
      header: '港股通深(亿)',
      accessor: (row) => (
        <div className="text-right text-gray-600 dark:text-gray-400">
          {toYi(row.ggt_sz)}
        </div>
      ),
      width: 110,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'south_money',
      header: '南向合计(亿)',
      accessor: (row) => (
        <div className="text-right text-gray-600 dark:text-gray-400">
          {toYi(row.south_money)}
        </div>
      ),
      width: 120,
      cellClassName: 'whitespace-nowrap'
    },
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: MoneyflowData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700 mb-2">
        <span className="font-medium">{formatDate(item.trade_date)}</span>
        <span className={`font-bold text-base ${pctColor(item.north_money)}`}>
          北向 {(item.north_money ?? 0) >= 0 ? '+' : ''}{toYi(item.north_money)}亿
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm mb-2">
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">沪股通</span>
          <span className={pctColor(item.hgt)}>{(item.hgt ?? 0) >= 0 ? '+' : ''}{toYi(item.hgt)}亿</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">深股通</span>
          <span className={pctColor(item.sgt)}>{(item.sgt ?? 0) >= 0 ? '+' : ''}{toYi(item.sgt)}亿</span>
        </div>
      </div>
      <div className="border-t border-gray-100 dark:border-gray-800 pt-2 grid grid-cols-2 gap-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-500 dark:text-gray-500">南向合计</span>
          <span className="text-gray-600 dark:text-gray-400">{toYi(item.south_money)}亿</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500 dark:text-gray-500">港股通沪</span>
          <span className="text-gray-600 dark:text-gray-400">{toYi(item.ggt_ss)}亿</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500 dark:text-gray-500">港股通深</span>
          <span className="text-gray-600 dark:text-gray-400">{toYi(item.ggt_sz)}亿</span>
        </div>
      </div>
    </div>
  ), [])

  // 趋势图数据（时序倒序 → 正序）
  const chartData = useMemo(() => {
    return [...data].reverse().map(item => ({
      date: formatDate(item.trade_date),
      北向资金: item.north_money !== null ? item.north_money / 100 : null,
      南向资金: item.south_money !== null ? item.south_money / 100 : null,
    }))
  }, [data])

  return (
    <div className="space-y-6">
      <PageHeader
        title="沪深港通资金流向"
        description="查看沪深港通每日资金流向数据，包含北向（沪股通+深股通）和南向（港股通）资金"
        details={<>
          <div>接口：moneyflow_hsgt</div>
          <a href="https://tushare.pro/document/2?doc_id=47" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
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

      {/* 统计卡片 — 左文字右图标 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">北向资金均值</p>
                  <p className={`text-xl sm:text-2xl font-bold mt-1 ${pctColor(statistics.avg_north)}`}>
                    {(statistics.avg_north ?? 0) >= 0 ? '+' : ''}{toYi(statistics.avg_north)}亿
                  </p>
                  <p className="text-xs text-gray-500 mt-1">近{statistics.count}个交易日</p>
                </div>
                <Activity className="h-6 w-6 sm:h-8 sm:w-8 text-orange-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">累计净流入</p>
                  <p className={`text-xl sm:text-2xl font-bold mt-1 ${pctColor(statistics.total_north)}`}>
                    {(statistics.total_north ?? 0) >= 0 ? '+' : ''}{toYi(statistics.total_north)}亿
                  </p>
                  <p className="text-xs text-gray-500 mt-1">期间总计</p>
                </div>
                <TrendingDown className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">北向最大流入</p>
                  <p className="text-xl sm:text-2xl font-bold mt-1 text-red-600 dark:text-red-400">
                    +{toYi(statistics.max_north)}亿
                  </p>
                  <p className="text-xs text-gray-500 mt-1">单日最高</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">南向最大流出</p>
                  <p className="text-xl sm:text-2xl font-bold mt-1 text-green-600 dark:text-green-400">
                    {toYi(statistics.max_south)}亿
                  </p>
                  <p className="text-xs text-gray-500 mt-1">单日最高</p>
                </div>
                <DollarSign className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 趋势图 */}
      {chartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              资金流向趋势
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <div style={{ minWidth: '600px' }}>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 40 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="date"
                      angle={-45}
                      textAnchor="end"
                      height={80}
                      tick={{ fontSize: 12 }}
                    />
                    <YAxis tick={{ fontSize: 12 }} label={{ value: '亿元', angle: -90, position: 'insideLeft' }} />
                    <Tooltip formatter={(v) => typeof v === 'number' ? v.toFixed(2) + '亿' : '-'} />
                    <Legend />
                    <Line type="monotone" dataKey="北向资金" stroke="#ef4444" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="南向资金" stroke="#10b981" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 筛选区域（仅查询控件，同步按钮在 PageHeader） */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ListFilter className="h-5 w-5" />
            数据查询
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">开始日期</label>
              <DatePicker date={startDate} onDateChange={setStartDate} placeholder="选择开始日期" />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">结束日期</label>
              <DatePicker date={endDate} onDateChange={setEndDate} placeholder="选择结束日期" />
            </div>
            <Button onClick={handleQuery} disabled={isLoading} className="w-full sm:w-auto">
              查询
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="p-0 sm:p-6">
          <DataTable
            columns={columns}
            data={data}
            loading={isLoading}
            mobileCard={mobileCard}
            emptyMessage="暂无沪深港通资金流向数据"
            tableClassName="table-fixed w-full [&_th]:border-r [&_td]:border-r [&_th:last-child]:border-r-0 [&_td:last-child]:border-r-0 [&_th]:!text-center"
            pagination={{
              page,
              pageSize: PAGE_SIZE,
              total,
              onPageChange: (newPage) => loadData(newPage)
            }}
          />
        </CardContent>
      </Card>

      {/* 同步弹窗（不预填查询日期，让后端取最新交易日） */}
      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>同步沪深港通资金流向数据</DialogTitle>
            <DialogDescription>
              选择同步日期范围（留空则同步最新交易日数据）。
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">开始日期（可选）</label>
              <DatePicker
                date={syncStartDate}
                onDateChange={setSyncStartDate}
                placeholder="留空同步最新交易日"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">结束日期（可选）</label>
              <DatePicker
                date={syncEndDate}
                onDateChange={setSyncEndDate}
                placeholder="留空同步最新交易日"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncDialogOpen(false)}>取消</Button>
            <Button onClick={handleSyncConfirm} disabled={syncing}>
              {syncing ? (
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
              ) : '确认同步'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
