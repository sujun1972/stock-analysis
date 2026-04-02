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
import { RefreshCw, TrendingUp, TrendingDown, Activity, DollarSign, ListFilter } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

// 数据类型定义
interface MoneyflowMktDcData {
  trade_date: string
  close_sh: number
  pct_change_sh: number
  close_sz: number
  pct_change_sz: number
  net_amount: number
  net_amount_rate: number
  buy_elg_amount: number
  buy_elg_amount_rate: number
  buy_lg_amount: number
  buy_lg_amount_rate: number
  buy_md_amount: number
  buy_md_amount_rate: number
  buy_sm_amount: number
  buy_sm_amount_rate: number
}

interface Statistics {
  avg_net: number
  max_net: number
  min_net: number
  total_net: number
  avg_elg: number
  max_elg: number
  avg_lg: number
  max_lg: number
  avg_pct_sh: number
  avg_pct_sz: number
  latest_date: string
  earliest_date: string
  count: number
}

const PAGE_SIZE = 30

// 时区安全的日期字符串构建
const toDateStr = (date: Date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

const pctColor = (val: number | null | undefined) =>
  (val ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'

const formatDate = (dateStr: string) => {
  if (!dateStr || dateStr.length !== 8) return dateStr
  return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
}

export default function MoneyflowMktDcPage() {
  const [data, setData] = useState<MoneyflowMktDcData[]>([])
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
  const syncing = isTaskRunning('tasks.sync_moneyflow_mkt_dc')

  const loadData = useCallback(async (targetPage: number = 1) => {
    setIsLoading(true)
    try {
      const params: any = {
        limit: PAGE_SIZE,
        offset: (targetPage - 1) * PAGE_SIZE,
      }
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)

      const response = await moneyflowApi.getMoneyflowMktDc(params)

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

      const response = await moneyflowApi.syncMoneyflowMktDcAsync(params)

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
            toast.success('大盘资金流向数据同步完成')
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
  const columns: Column<MoneyflowMktDcData>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '日期',
      accessor: (row) => formatDate(row.trade_date),
      width: 110,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'close_sh',
      header: '上证',
      accessor: (row) => (
        <div className="text-right">
          <div>{row.close_sh?.toFixed(2) ?? '-'}</div>
          <div className={`text-xs ${pctColor(row.pct_change_sh)}`}>
            {row.pct_change_sh >= 0 ? '+' : ''}{row.pct_change_sh?.toFixed(2) ?? '-'}%
          </div>
        </div>
      ),
      width: 90,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'close_sz',
      header: '深证',
      accessor: (row) => (
        <div className="text-right">
          <div>{row.close_sz?.toFixed(2) ?? '-'}</div>
          <div className={`text-xs ${pctColor(row.pct_change_sz)}`}>
            {row.pct_change_sz >= 0 ? '+' : ''}{row.pct_change_sz?.toFixed(2) ?? '-'}%
          </div>
        </div>
      ),
      width: 90,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'net_amount',
      header: '主力净流入',
      accessor: (row) => (
        <div className="text-right">
          <div className={`font-semibold ${pctColor(row.net_amount)}`}>
            {row.net_amount >= 0 ? '+' : ''}{row.net_amount?.toFixed(2) ?? '-'}亿
          </div>
          <div className="text-xs text-gray-500">{row.net_amount_rate?.toFixed(2) ?? '-'}%</div>
        </div>
      ),
      width: 120,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'buy_elg_amount',
      header: '超大单',
      accessor: (row) => (
        <div className={`text-right ${pctColor(row.buy_elg_amount)}`}>
          {row.buy_elg_amount >= 0 ? '+' : ''}{row.buy_elg_amount?.toFixed(2) ?? '-'}亿
        </div>
      ),
      width: 100,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'buy_lg_amount',
      header: '大单',
      accessor: (row) => (
        <div className={`text-right ${pctColor(row.buy_lg_amount)}`}>
          {row.buy_lg_amount >= 0 ? '+' : ''}{row.buy_lg_amount?.toFixed(2) ?? '-'}亿
        </div>
      ),
      width: 100,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'buy_md_amount',
      header: '中单',
      accessor: (row) => (
        <div className={`text-right ${pctColor(row.buy_md_amount)}`}>
          {row.buy_md_amount >= 0 ? '+' : ''}{row.buy_md_amount?.toFixed(2) ?? '-'}亿
        </div>
      ),
      width: 100,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'buy_sm_amount',
      header: '小单',
      accessor: (row) => (
        <div className={`text-right ${pctColor(row.buy_sm_amount)}`}>
          {row.buy_sm_amount >= 0 ? '+' : ''}{row.buy_sm_amount?.toFixed(2) ?? '-'}亿
        </div>
      ),
      width: 100,
      cellClassName: 'whitespace-nowrap'
    },
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: MoneyflowMktDcData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700 mb-2">
        <span className="font-medium">{formatDate(item.trade_date)}</span>
        <div className="flex gap-3 text-sm">
          <span>上证 <span className={pctColor(item.pct_change_sh)}>{item.pct_change_sh >= 0 ? '+' : ''}{item.pct_change_sh?.toFixed(2)}%</span></span>
          <span>深证 <span className={pctColor(item.pct_change_sz)}>{item.pct_change_sz >= 0 ? '+' : ''}{item.pct_change_sz?.toFixed(2)}%</span></span>
        </div>
      </div>
      <div className="flex justify-between items-center mb-2">
        <span className="text-sm text-gray-600">主力净流入</span>
        <div className="text-right">
          <div className={`font-semibold ${pctColor(item.net_amount)}`}>
            {item.net_amount >= 0 ? '+' : ''}{item.net_amount?.toFixed(2)}亿
          </div>
          <div className="text-xs text-gray-500">{item.net_amount_rate?.toFixed(2)}%</div>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">超大单</span>
          <span className={pctColor(item.buy_elg_amount)}>{item.buy_elg_amount >= 0 ? '+' : ''}{item.buy_elg_amount?.toFixed(2)}亿</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">大单</span>
          <span className={pctColor(item.buy_lg_amount)}>{item.buy_lg_amount >= 0 ? '+' : ''}{item.buy_lg_amount?.toFixed(2)}亿</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">中单</span>
          <span className={pctColor(item.buy_md_amount)}>{item.buy_md_amount >= 0 ? '+' : ''}{item.buy_md_amount?.toFixed(2)}亿</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">小单</span>
          <span className={pctColor(item.buy_sm_amount)}>{item.buy_sm_amount >= 0 ? '+' : ''}{item.buy_sm_amount?.toFixed(2)}亿</span>
        </div>
      </div>
    </div>
  ), [])

  // 趋势图数据（时序倒序 → 正序）
  const chartData = useMemo(() => {
    return [...data].reverse().map(item => ({
      date: formatDate(item.trade_date),
      主力净流入: item.net_amount,
      超大单: item.buy_elg_amount,
      大单: item.buy_lg_amount,
    }))
  }, [data])

  return (
    <div className="space-y-6">
      <PageHeader
        title="大盘资金流向（DC）"
        description="获取东方财富大盘资金流向数据，每日盘后更新"
        details={<>
          <div>接口：moneyflow_mkt_dc</div>
          <a href="https://tushare.pro/document/2?doc_id=345" target="_blank" rel="noopener noreferrer">查看文档</a>
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
                  <p className="text-xs sm:text-sm text-gray-600">主力净流入均值</p>
                  <p className={`text-xl sm:text-2xl font-bold ${pctColor(statistics.avg_net)}`}>
                    {(statistics.avg_net ?? 0) >= 0 ? '+' : ''}{(statistics.avg_net ?? 0).toFixed(2)}亿
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
                  <p className="text-xs sm:text-sm text-gray-600">最大净流入</p>
                  <p className="text-xl sm:text-2xl font-bold text-red-600">
                    +{(statistics.max_net ?? 0).toFixed(2)}亿
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
                  <p className="text-xs sm:text-sm text-gray-600">超大单均值</p>
                  <p className={`text-xl sm:text-2xl font-bold ${pctColor(statistics.avg_elg)}`}>
                    {(statistics.avg_elg ?? 0) >= 0 ? '+' : ''}{(statistics.avg_elg ?? 0).toFixed(2)}亿
                  </p>
                  <p className="text-xs text-gray-500 mt-1">日均流入</p>
                </div>
                <DollarSign className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">累计净流入</p>
                  <p className={`text-xl sm:text-2xl font-bold ${pctColor(statistics.total_net)}`}>
                    {(statistics.total_net ?? 0) >= 0 ? '+' : ''}{(statistics.total_net ?? 0).toFixed(2)}亿
                  </p>
                  <p className="text-xs text-gray-500 mt-1">期间总计</p>
                </div>
                <TrendingDown className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
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
              主力资金流向趋势
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
                    <Line type="monotone" dataKey="主力净流入" stroke="#8884d8" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="超大单" stroke="#82ca9d" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="大单" stroke="#ffc658" strokeWidth={2} dot={false} />
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
            emptyMessage="暂无大盘资金流向数据"
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
            <DialogTitle>同步大盘资金流向数据</DialogTitle>
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
