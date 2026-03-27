'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { toast } from 'sonner'
import { moneyflowApi } from '@/lib/api'
import { formatStockCode, pctChangeColor } from '@/lib/utils'
import { useTaskStore } from '@/stores/task-store'
import { useSystemConfig } from '@/contexts'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { TrendingUp, BarChart3, ListFilter, RefreshCw, DollarSign } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

// 数据类型定义
interface MoneyflowStockDcItem {
  trade_date: string
  ts_code: string
  name: string
  pct_change: number | null
  close: number | null
  net_amount: number | null
  net_amount_rate: number | null
  buy_elg_amount: number | null
  buy_elg_amount_rate: number | null
  buy_lg_amount: number | null
  buy_lg_amount_rate: number | null
  buy_md_amount: number | null
  buy_md_amount_rate: number | null
  buy_sm_amount: number | null
  buy_sm_amount_rate: number | null
}

interface Statistics {
  avg_net_amount: number
  total_net_amount: number
  max_net_amount: number
  min_net_amount: number
  avg_buy_elg_amount: number
  max_buy_elg_amount: number
  avg_buy_lg_amount: number
  max_buy_lg_amount: number
  stock_count: number
  count: number
  latest_date: string
  earliest_date: string
}

const PAGE_SIZE = 100

export default function MoneyflowStockDcPage() {
  const [data, setData] = useState<MoneyflowStockDcItem[]>([])
  const [topStocks, setTopStocks] = useState<MoneyflowStockDcItem[]>([])
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc' | null>(null)
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncDate, setSyncDate] = useState<Date | undefined>(undefined)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  // 从 task store 实时派生——不用本地 useState
  const syncing = isTaskRunning('tasks.sync_moneyflow_stock_dc')
  const { config } = useSystemConfig()

  const openStockAnalysis = useCallback((tsCode: string) => {
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(tsCode)), '_blank')
  }, [config])

  useEffect(() => {
    loadData(1).catch(() => {})
    loadTopStocks().catch(() => {})
  }, [])

  const loadData = async (
    targetPage: number = page,
    overrideSortKey?: string | null,
    overrideSortDir?: 'asc' | 'desc' | null
  ) => {
    setIsLoading(true)
    try {
      const tradeDateStr = tradeDate
        ? `${tradeDate.getFullYear()}-${String(tradeDate.getMonth() + 1).padStart(2, '0')}-${String(tradeDate.getDate()).padStart(2, '0')}`
        : undefined

      const params: any = {
        trade_date: tradeDateStr,
        page: targetPage,
        page_size: PAGE_SIZE,
        sort_by: (overrideSortKey !== undefined ? overrideSortKey : sortKey) ?? undefined,
        sort_order: (overrideSortDir !== undefined ? overrideSortDir : sortDirection) ?? undefined,
      }
      if (tsCode) params.ts_code = tsCode

      const response = await moneyflowApi.getMoneyflowStockDc(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setTotal(response.data.total || 0)
        setStatistics(response.data.statistics || null)
        setPage(targetPage)
        // 回填后端解析的实际日期
        if (!tradeDate && response.data.trade_date) {
          setTradeDate(new Date(response.data.trade_date + 'T00:00:00'))
        }
      }
    } catch (error: any) {
      toast.error(error.message || '加载数据失败')
    } finally {
      setIsLoading(false)
    }
  }

  const loadTopStocks = async () => {
    try {
      const response = await moneyflowApi.getTopMoneyflowStocks({ limit: 20 })
      if (response.code === 200 && response.data) {
        setTopStocks(response.data.items || [])
      }
    } catch {
      // 图表加载失败不阻断主流程
    }
  }

  const handleQuery = () => {
    loadData(1).catch(() => {})
  }

  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    try {
      const syncDateStr = syncDate
        ? `${syncDate.getFullYear()}-${String(syncDate.getMonth() + 1).padStart(2, '0')}-${String(syncDate.getDate()).padStart(2, '0')}`
        : undefined

      const response = await moneyflowApi.syncMoneyflowStockDcAsync(
        syncDateStr ? { trade_date: syncDateStr } : {}
      )

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
            loadData(1).catch(() => {})
            loadTopStocks().catch(() => {})
            toast.success('数据同步完成')
          }
          unregisterCompletionCallback(taskId, completionCallback)
          activeCallbacksRef.current.delete(taskId)
        }
        activeCallbacksRef.current.set(taskId, completionCallback)
        registerCompletionCallback(taskId, completionCallback)

        triggerPoll()
        toast.success(response.message || '同步任务已提交')
      } else {
        toast.error(response.message || '提交同步任务失败')
      }
    } catch (error: any) {
      toast.error(error.message || '提交同步任务失败')
    }
  }

  useEffect(() => {
    return () => {
      // eslint-disable-next-line react-hooks/exhaustive-deps
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
    }
  }, [unregisterCompletionCallback])

  // 格式化金额（已是亿元）
  const toYi = (val: number | null | undefined) => {
    if (val === null || val === undefined) return '-'
    return (val >= 0 ? '+' : '') + val.toFixed(2) + '亿'
  }

  const toYiNoSign = (val: number | null | undefined) => {
    if (val === null || val === undefined) return '-'
    return val.toFixed(2) + '亿'
  }

  // 表格列定义
  const columns: Column<MoneyflowStockDcItem>[] = useMemo(() => [
    {
      key: 'name',
      header: '股票',
      accessor: (row) => (
        <span
          className={`cursor-pointer hover:underline ${pctChangeColor(row.pct_change)}`}
          onClick={() => openStockAnalysis(row.ts_code)}
        >
          {row.name || '-'}[{formatStockCode(row.ts_code)}]
        </span>
      ),
      width: 160,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'close',
      header: '最新价',
      accessor: (row) => (
        <span className={pctChangeColor(row.pct_change)}>
          {row.close !== null && row.close !== undefined ? row.close.toFixed(2) : '-'}
        </span>
      ),
      width: 80,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'pct_change',
      header: '涨跌幅%',
      accessor: (row) => {
        if (row.pct_change === null || row.pct_change === undefined) return '-'
        const v = row.pct_change
        return (
          <span className={pctChangeColor(v)}>
            {v >= 0 ? '+' : ''}{v.toFixed(2)}%
          </span>
        )
      },
      width: 100,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'net_amount',
      header: '主力净流入',
      accessor: (row) => {
        if (row.net_amount === null || row.net_amount === undefined) return '-'
        return (
          <span className={row.net_amount >= 0 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'}>
            {toYi(row.net_amount)}
          </span>
        )
      },
      width: 120,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'net_amount_rate',
      header: '主力净占比%',
      accessor: (row) => {
        if (row.net_amount_rate === null || row.net_amount_rate === undefined) return '-'
        const v = row.net_amount_rate
        return <span className={pctChangeColor(v)}>{v >= 0 ? '+' : ''}{v.toFixed(2)}%</span>
      },
      width: 115,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'buy_elg_amount',
      header: '超大单净流入',
      accessor: (row) => {
        if (row.buy_elg_amount === null || row.buy_elg_amount === undefined) return '-'
        return (
          <span className={row.buy_elg_amount >= 0 ? 'text-red-600' : 'text-green-600'}>
            {toYi(row.buy_elg_amount)}
          </span>
        )
      },
      width: 120,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'buy_lg_amount',
      header: '大单净流入',
      accessor: (row) => {
        if (row.buy_lg_amount === null || row.buy_lg_amount === undefined) return '-'
        return (
          <span className={row.buy_lg_amount >= 0 ? 'text-red-600' : 'text-green-600'}>
            {toYi(row.buy_lg_amount)}
          </span>
        )
      },
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'buy_md_amount',
      header: '中单净流入',
      accessor: (row) => {
        if (row.buy_md_amount === null || row.buy_md_amount === undefined) return '-'
        return (
          <span className={row.buy_md_amount >= 0 ? 'text-red-600' : 'text-green-600'}>
            {toYi(row.buy_md_amount)}
          </span>
        )
      },
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'buy_sm_amount',
      header: '小单净流入',
      accessor: (row) => {
        if (row.buy_sm_amount === null || row.buy_sm_amount === undefined) return '-'
        return (
          <span className={row.buy_sm_amount >= 0 ? 'text-red-600' : 'text-green-600'}>
            {toYi(row.buy_sm_amount)}
          </span>
        )
      },
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
  ], [openStockAnalysis])

  // 移动端卡片视图
  const mobileCard = (item: MoneyflowStockDcItem) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div
            className={`font-semibold text-base cursor-pointer hover:underline ${pctChangeColor(item.pct_change)}`}
            onClick={() => openStockAnalysis(item.ts_code)}
          >
            {item.name || '-'}
          </div>
          <div className="text-sm text-gray-500">{item.ts_code}</div>
        </div>
        <div className="text-right">
          <div className="font-semibold">{item.close !== null ? `¥${item.close.toFixed(2)}` : '-'}</div>
          {item.pct_change !== null && (
            <div className={item.pct_change >= 0 ? 'text-red-600' : 'text-green-600'}>
              {item.pct_change >= 0 ? '+' : ''}{item.pct_change.toFixed(2)}%
            </div>
          )}
        </div>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">主力净流入:</span>
          {item.net_amount !== null && (
            <span className={item.net_amount >= 0 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'}>
              {toYi(item.net_amount)}
            </span>
          )}
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">超大单净流入:</span>
          <span className={item.buy_elg_amount !== null && item.buy_elg_amount >= 0 ? 'text-red-600' : 'text-green-600'}>
            {toYiNoSign(item.buy_elg_amount)}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">大单净流入:</span>
          <span className={item.buy_lg_amount !== null && item.buy_lg_amount >= 0 ? 'text-red-600' : 'text-green-600'}>
            {toYiNoSign(item.buy_lg_amount)}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">主力净占比:</span>
          <span>{item.net_amount_rate !== null ? `${item.net_amount_rate.toFixed(2)}%` : '-'}</span>
        </div>
      </div>
    </div>
  )

  // 图表数据
  const chartData = useMemo(() => topStocks.map(item => ({
    name: item.name,
    主力净流入: item.net_amount ?? 0,
    超大单: item.buy_elg_amount ?? 0,
    大单: item.buy_lg_amount ?? 0,
  })), [topStocks])

  return (
    <div className="space-y-6">
      <PageHeader
        title="个股资金流向(DC)"
        description="东方财富个股资金流向数据，包含主力资金、超大单、大单、中单、小单流入流出情况"
        details={<>
          <div>接口：moneyflow_dc</div>
          <a href="https://tushare.pro/document/2?doc_id=349" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <Button onClick={() => setSyncDialogOpen(true)} disabled={syncing}>
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

      {/* 统计卡片 — 左文字右图标 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">统计股票数</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.stock_count ?? 0}只</p>
                </div>
                <BarChart3 className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">主力资金均值(亿)</p>
                  <p className={`text-xl sm:text-2xl font-bold ${(statistics.avg_net_amount ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {(statistics.avg_net_amount ?? 0) >= 0 ? '+' : ''}{(statistics.avg_net_amount ?? 0).toFixed(2)}
                  </p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-orange-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">最大净流入(亿)</p>
                  <p className="text-xl sm:text-2xl font-bold text-red-600">
                    +{(statistics.max_net_amount ?? 0).toFixed(2)}
                  </p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">超大单均值(亿)</p>
                  <p className={`text-xl sm:text-2xl font-bold ${(statistics.avg_buy_elg_amount ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {(statistics.avg_buy_elg_amount ?? 0) >= 0 ? '+' : ''}{(statistics.avg_buy_elg_amount ?? 0).toFixed(2)}
                  </p>
                </div>
                <DollarSign className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* TOP 20 图表 */}
      {topStocks.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              主力资金流入 TOP 20
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <div style={{ minWidth: '600px' }}>
                <ResponsiveContainer width="100%" height={360}>
                  <BarChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 60 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="name"
                      angle={-45}
                      textAnchor="end"
                      height={80}
                      interval={0}
                      tick={{ fontSize: 11 }}
                    />
                    <YAxis tickFormatter={(v) => v.toFixed(1)} />
                    <Tooltip formatter={(v) => typeof v === 'number' ? v.toFixed(2) + '亿' : '-'} />
                    <Legend />
                    <Bar dataKey="主力净流入" fill="#8884d8" />
                    <Bar dataKey="超大单" fill="#82ca9d" />
                    <Bar dataKey="大单" fill="#ffc658" />
                  </BarChart>
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
            <div className="w-full sm:w-48">
              <label className="text-sm font-medium mb-1 block">股票代码</label>
              <Input
                placeholder="如 000001 或 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
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
            emptyMessage="暂无个股资金流向数据"
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

      {/* 同步日期选择弹窗 */}
      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>同步个股资金流向数据</DialogTitle>
            <DialogDescription>
              选择同步日期（留空则同步最新交易日数据）。
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <label className="text-sm font-medium mb-2 block">交易日期（可选）</label>
            <DatePicker
              date={syncDate}
              onDateChange={setSyncDate}
              placeholder="留空同步最新交易日"
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSyncConfirm} disabled={syncing}>
              {syncing ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                  同步中...
                </>
              ) : '确认同步'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
