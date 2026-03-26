'use client'

import { useState, useEffect, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { dcDailyApi, type DcDailyData, type DcDailyStatistics } from '@/lib/api'
import { pctChangeColor } from '@/lib/utils'
import { useTaskStore, type Task } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, Database, Calendar, Layers, TrendingUp, AlertTriangle, ListFilter } from 'lucide-react'

const PAGE_SIZE = 100

const IDX_TYPE_OPTIONS = [
  { value: '概念板块', label: '概念板块' },
  { value: '行业板块', label: '行业板块' },
  { value: '地域板块', label: '地域板块' },
]

export default function DcDailyPage() {
  const [data, setData] = useState<DcDailyData[]>([])
  const [statistics, setStatistics] = useState<DcDailyStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc' | null>(null)

  // 同步对话框状态
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncTsCode, setSyncTsCode] = useState<string>('')
  const [syncIdxType, setSyncIdxType] = useState<string>('')
  const [syncTradeDate, setSyncTradeDate] = useState<Date | undefined>(undefined)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const syncing = isTaskRunning('tasks.sync_dc_daily')

  useEffect(() => {
    loadData(1).catch(() => {})
  }, [])

  const toDateStr = (date: Date) =>
    `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

  const loadData = async (
    targetPage: number = page,
    overrideSortKey?: string | null,
    overrideSortDir?: 'asc' | 'desc' | null
  ) => {
    setIsLoading(true)
    try {
      const tradeDateStr = tradeDate ? toDateStr(tradeDate) : undefined
      const params = {
        trade_date: tradeDateStr,
        page: targetPage,
        page_size: PAGE_SIZE,
        sort_by: (overrideSortKey !== undefined ? overrideSortKey : sortKey) ?? undefined,
        sort_order: (overrideSortDir !== undefined ? overrideSortDir : sortDirection) ?? undefined
      }

      const [dataResponse, statsResponse] = await Promise.all([
        dcDailyApi.getData(params),
        dcDailyApi.getStatistics({ trade_date: tradeDateStr })
      ])

      if (dataResponse.code === 200 && dataResponse.data) {
        setData(dataResponse.data.items)
        setTotal(dataResponse.data.total)
        setPage(targetPage)
        // 回填后端解析的实际日期
        if (!tradeDate && dataResponse.data.trade_date) {
          setTradeDate(new Date(dataResponse.data.trade_date + 'T00:00:00'))
        }
      }

      if (statsResponse.code === 200 && statsResponse.data) {
        setStatistics(statsResponse.data)
      }
    } catch (error: any) {
      toast.error(error.message || '加载数据失败')
    } finally {
      setIsLoading(false)
    }
  }

  const handleQuery = () => {
    loadData(1).catch(() => {})
  }

  const handleSync = async () => {
    try {
      setSyncDialogOpen(false)

      const params: any = {}
      if (syncTsCode.trim()) params.ts_code = syncTsCode.trim()
      if (syncIdxType) params.idx_type = syncIdxType
      if (syncTradeDate) params.trade_date = toDateStr(syncTradeDate)
      if (syncStartDate) params.start_date = toDateStr(syncStartDate)
      if (syncEndDate) params.end_date = toDateStr(syncEndDate)

      const response = await dcDailyApi.syncAsync(params)

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

        const completionCallback = (task: Task) => {
          if (task.status === 'success') {
            loadData(1).catch(() => {})
            toast.success('数据同步完成')
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
        throw new Error(response.message || '同步失败')
      }
    } catch (err: any) {
      toast.error('同步失败', { description: err.message || '无法同步数据' })
    }
  }

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

  const formatPct = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '-'
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  const formatAmount = (value: number | null | undefined) =>
    value == null ? '-' : (value / 100000000).toFixed(2) + '亿'

  const formatVol = (value: number | null | undefined) =>
    value == null ? '-' : (value / 10000).toFixed(0) + '万手'

  const columns: Column<DcDailyData>[] = [
    {
      key: 'ts_code',
      header: '板块',
      accessor: (row) => row.board_name ? `${row.board_name}[${row.ts_code}]` : row.ts_code,
      width: 200,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'close',
      header: '收盘',
      accessor: (row) => (
        <span className={pctChangeColor(row.pct_change)}>
          {row.close != null ? row.close.toFixed(2) : '-'}
        </span>
      ),
      width: 80,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'pct_change',
      header: '涨跌幅%',
      accessor: (row) => (
        <span className={pctChangeColor(row.pct_change)}>
          {formatPct(row.pct_change)}
        </span>
      ),
      width: 100,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'change',
      header: '涨跌点',
      accessor: (row) => (
        <span className={pctChangeColor(row.change)}>
          {row.change != null ? (row.change >= 0 ? '+' : '') + row.change.toFixed(2) : '-'}
        </span>
      ),
      width: 90,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'open',
      header: '开盘',
      accessor: (row) => row.open != null ? row.open.toFixed(2) : '-',
      width: 80,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'high',
      header: '最高',
      accessor: (row) => (
        <span className="text-red-600">{row.high != null ? row.high.toFixed(2) : '-'}</span>
      ),
      width: 80,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'low',
      header: '最低',
      accessor: (row) => (
        <span className="text-green-600">{row.low != null ? row.low.toFixed(2) : '-'}</span>
      ),
      width: 80,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'amount',
      header: '成交额',
      accessor: (row) => (
        <span className={pctChangeColor(row.pct_change)}>{formatAmount(row.amount)}</span>
      ),
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'vol',
      header: '成交量',
      accessor: (row) => formatVol(row.vol),
      width: 100,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'swing',
      header: '振幅%',
      accessor: (row) => row.swing != null ? `${row.swing.toFixed(2)}%` : '-',
      width: 80,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'turnover_rate',
      header: '换手率%',
      accessor: (row) => (
        <span className={pctChangeColor(row.pct_change)}>
          {row.turnover_rate != null ? `${row.turnover_rate.toFixed(2)}%` : '-'}
        </span>
      ),
      width: 90,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
  ]

  const mobileCard = (item: DcDailyData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div className="font-semibold text-base">
          {item.board_name ? `${item.board_name}[${item.ts_code}]` : item.ts_code}
        </div>
        <div className="text-right">
          <div className={`font-bold ${pctChangeColor(item.pct_change)}`}>
            {formatPct(item.pct_change)}
          </div>
          <div className="text-sm text-gray-500">{item.trade_date}</div>
        </div>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">收盘/开盘:</span>
          <span className={pctChangeColor(item.pct_change)}>
            {item.close != null ? item.close.toFixed(2) : '-'} / {item.open != null ? item.open.toFixed(2) : '-'}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">最高/最低:</span>
          <span>
            <span className="text-red-600">{item.high != null ? item.high.toFixed(2) : '-'}</span>
            <span className="text-gray-400 mx-1">/</span>
            <span className="text-green-600">{item.low != null ? item.low.toFixed(2) : '-'}</span>
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">成交额:</span>
          <span>{formatAmount(item.amount)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">换手率:</span>
          <span>{item.turnover_rate != null ? `${item.turnover_rate.toFixed(2)}%` : '-'}</span>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="东财概念板块行情"
        description="获取东财概念板块、行业指数板块、地域板块行情数据，历史数据开始于2020年"
        details={<>
          <div>接口：dc_daily</div>
          <a href="https://tushare.pro/document/2?doc_id=382" target="_blank" rel="noopener noreferrer">查看文档</a>
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

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">总记录数</p>
                  <p className="text-xl sm:text-2xl font-bold">{(statistics.total_records ?? 0).toLocaleString()}</p>
                </div>
                <Database className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">板块数量</p>
                  <p className="text-xl sm:text-2xl font-bold">{(statistics.board_count ?? 0).toLocaleString()}</p>
                </div>
                <Layers className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">交易日数</p>
                  <p className="text-xl sm:text-2xl font-bold">{(statistics.date_count ?? 0).toLocaleString()}</p>
                </div>
                <Calendar className="h-6 w-6 sm:h-8 sm:w-8 text-orange-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">平均涨跌幅</p>
                  <p className={`text-xl sm:text-2xl font-bold ${pctChangeColor(statistics.avg_pct_change)}`}>
                    {statistics.avg_pct_change != null ? formatPct(statistics.avg_pct_change) : '-'}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    最新: {statistics.latest_date || '-'}
                  </p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选区域 */}
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
              <label className="text-sm font-medium mb-1 block">交易日期</label>
              <DatePicker date={tradeDate} onDateChange={setTradeDate} />
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <Button onClick={handleQuery} disabled={isLoading} className="flex-1 sm:flex-none">
                查询
              </Button>
            </div>
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
            tableClassName="table-fixed w-full [&_th]:border-r [&_td]:border-r [&_th:last-child]:border-r-0 [&_td:last-child]:border-r-0 [&_th]:!text-center"
            sort={{
              key: sortKey,
              direction: sortDirection,
              onSort: (key, direction) => {
                const newKey = direction ? key : null
                setSortKey(newKey)
                setSortDirection(direction)
                loadData(1, newKey, direction)
              }
            }}
            pagination={{
              page,
              pageSize: PAGE_SIZE,
              total,
              onPageChange: (newPage) => loadData(newPage)
            }}
          />
        </CardContent>
      </Card>

      {/* 同步参数对话框 */}
      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>同步东财概念板块行情</DialogTitle>
            <DialogDescription>
              配置同步参数后提交后台任务。所有参数均为可选。
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="flex items-start gap-2 p-3 bg-yellow-50 dark:bg-yellow-950/20 rounded-md border border-yellow-200 dark:border-yellow-800">
              <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-yellow-700 dark:text-yellow-400">
                每次调用消耗 <strong>6000</strong> 积分，单次最大返回 2000 条数据，请谨慎操作。
              </p>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">板块类型（可选）</label>
              <Select value={syncIdxType || 'ALL'} onValueChange={(v) => setSyncIdxType(v === 'ALL' ? '' : v)}>
                <SelectTrigger>
                  <SelectValue placeholder="全部类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部类型</SelectItem>
                  {IDX_TYPE_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">板块代码（可选）</label>
              <Input
                placeholder="如：BK0001"
                value={syncTsCode}
                onChange={(e) => setSyncTsCode(e.target.value)}
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">指定交易日期（可选）</label>
              <DatePicker date={syncTradeDate} onDateChange={setSyncTradeDate} />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">开始日期（可选）</label>
                <DatePicker date={syncStartDate} onDateChange={setSyncStartDate} />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">结束日期（可选）</label>
                <DatePicker date={syncEndDate} onDateChange={setSyncEndDate} />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncDialogOpen(false)}>取消</Button>
            <Button onClick={handleSync} disabled={syncing}>
              {syncing ? (
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />提交中...</>
              ) : '提交同步任务'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
