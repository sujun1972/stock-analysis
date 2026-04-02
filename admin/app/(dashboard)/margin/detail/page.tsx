'use client'

import { useState, useEffect, useMemo, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { marginApi } from '@/lib/api'
import { formatStockCode } from '@/lib/utils'
import { useTaskStore } from '@/stores/task-store'
import { useSystemConfig } from '@/contexts'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, BarChart3, DollarSign, ListFilter } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

// 数据类型定义
interface MarginDetailData {
  trade_date: string
  ts_code: string
  name: string
  rzye: number | null    // 融资余额(元)
  rqye: number | null    // 融券余额(元)
  rzmre: number | null   // 融资买入额(元)
  rqyl: number | null    // 融券余量(股)
  rzche: number | null   // 融资偿还额(元)
  rqchl: number | null   // 融券偿还量(股)
  rqmcl: number | null   // 融券卖出量(股)
  rzrqye: number | null  // 融资融券余额(元)
}

interface Statistics {
  avg_rzrqye: number
  total_rzrqye: number
  max_rzrqye: number
  stock_count: number
}

const PAGE_SIZE = 100

export default function MarginDetailPage() {
  const [data, setData] = useState<MarginDetailData[]>([])
  const [topStocks, setTopStocks] = useState<any[]>([])
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc' | null>(null)

  // 同步弹窗状态
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncDate, setSyncDate] = useState<Date | undefined>(undefined)

  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const { config } = useSystemConfig()

  // 从 task store 实时派生——不用本地 useState
  const syncing = isTaskRunning('tasks.sync_margin_detail')

  // 时区安全的日期字符串构建
  const toDateStr = (date: Date) =>
    `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

  // 判断是否为股票（可跳转分析页面），ETF/基金不跳转
  const isStock = (tsCode: string) => {
    const code = tsCode.split('.')[0]
    // 上海ETF/基金：5xxxxx，深圳ETF/基金：1xxxxx
    return !code.startsWith('5') && !code.startsWith('1')
  }

  const openStockAnalysis = (code: string) => {
    if (!isStock(code)) return
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(code)), '_blank')
  }

  // 加载主数据（含统计）
  const loadData = async (
    targetPage: number = page,
    overrideSortKey?: string | null,
    overrideSortDir?: 'asc' | 'desc' | null
  ) => {
    setIsLoading(true)
    try {
      const tradeDateStr = tradeDate ? toDateStr(tradeDate) : undefined
      const params: any = {
        page: targetPage,
        page_size: PAGE_SIZE,
        sort_by: (overrideSortKey !== undefined ? overrideSortKey : sortKey) ?? undefined,
        sort_order: (overrideSortDir !== undefined ? overrideSortDir : sortDirection) ?? undefined,
      }
      if (tsCode) params.ts_code = tsCode
      if (tradeDateStr) params.trade_date = tradeDateStr

      const response = await marginApi.getMarginDetail(params)

      if (response.code === 200 && response.data) {
        setData(response.data.data || [])
        setTotal(response.data.total || 0)
        setStatistics(response.data.statistics || null)
        setPage(targetPage)
        // 回填后端解析的实际日期
        if (!tradeDate && response.data.trade_date) {
          setTradeDate(new Date(response.data.trade_date + 'T00:00:00'))
        }
      } else {
        toast.error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      toast.error(err.message || '加载数据失败')
    } finally {
      setIsLoading(false)
    }
  }

  // 加载TOP股票（图表，独立不阻断主流程）
  const loadTopStocks = async () => {
    try {
      const response = await marginApi.getMarginDetailTopStocks({ limit: 20 })
      if (response.code === 200 && response.data) {
        setTopStocks(response.data)
      }
    } catch {
      // 图表加载失败不阻断主流程
    }
  }

  // 初始加载：只跑一次
  useEffect(() => {
    loadData(1).catch(() => {})
    loadTopStocks().catch(() => {})
  }, [])

  const handleQuery = () => {
    loadData(1).catch(() => {})
  }

  // 同步确认
  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    try {
      const syncDateStr = syncDate ? toDateStr(syncDate) : undefined
      const response = await marginApi.syncMarginDetailAsync(
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
            toast.success('数据同步完成', { description: '融资融券交易明细数据已更新' })
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
    } catch (err: any) {
      toast.error('同步失败', { description: err.message || '无法同步数据' })
    }
  }

  // 组件卸载清理
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

  // 格式化金额（元转亿元）
  const toYi = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '-'
    return (value / 100000000).toFixed(2) + '亿'
  }

  // 格式化日期
  const formatDate = (dateStr: string) => {
    if (!dateStr || dateStr.length !== 8) return dateStr
    return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
  }

  // 表格列定义
  const columns: Column<MarginDetailData>[] = useMemo(() => [
    {
      key: 'name',
      header: '股票',
      accessor: (row) => (
        <span
          className={`whitespace-nowrap${isStock(row.ts_code) ? ' cursor-pointer hover:underline' : ''}`}
          onClick={() => isStock(row.ts_code) && openStockAnalysis(row.ts_code)}
        >
          {row.name || '-'}[{formatStockCode(row.ts_code)}]
        </span>
      ),
      width: 160,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'rzrqye',
      header: '融资融券余额',
      accessor: (row) => toYi(row.rzrqye),
      width: 130,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rzye',
      header: '融资余额',
      accessor: (row) => toYi(row.rzye),
      hideOnMobile: true,
      width: 120,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rqye',
      header: '融券余额',
      accessor: (row) => toYi(row.rqye),
      hideOnMobile: true,
      width: 120,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rzmre',
      header: '融资买入',
      accessor: (row) => toYi(row.rzmre),
      hideOnMobile: true,
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rzche',
      header: '融资偿还',
      accessor: (row) => toYi(row.rzche),
      hideOnMobile: true,
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rqmcl',
      header: '融券卖出量',
      accessor: (row) => row.rqmcl !== null && row.rqmcl !== undefined ? row.rqmcl.toFixed(0) + '股' : '-',
      hideOnMobile: true,
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
  ], [config])

  // 移动端卡片视图
  const mobileCard = (item: MarginDetailData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div
            className={`font-semibold text-base${isStock(item.ts_code) ? ' cursor-pointer hover:underline' : ''}`}
            onClick={() => isStock(item.ts_code) && openStockAnalysis(item.ts_code)}
          >
            {item.name || '-'}
          </div>
          <div className="text-sm text-gray-500">{item.ts_code}</div>
        </div>
        <span className="text-xs text-gray-500">{formatDate(item.trade_date)}</span>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">融资融券余额</span>
          <span className="font-medium">{toYi(item.rzrqye)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">融资余额</span>
          <span className="font-medium">{toYi(item.rzye)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">融券余额</span>
          <span className="font-medium">{toYi(item.rqye)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">融资买入</span>
          <span className="font-medium">{toYi(item.rzmre)}</span>
        </div>
      </div>
    </div>
  )

  // 图表数据
  const chartData = useMemo(() => topStocks.slice(0, 20).map((stock) => ({
    name: stock.name || stock.ts_code,
    融资融券余额: Number((stock.rzrqye / 100000000).toFixed(2)),
    融资余额: Number((stock.rzye / 100000000).toFixed(2)),
    融券余额: Number((stock.rqye / 100000000).toFixed(2)),
  })), [topStocks])

  return (
    <div className="space-y-6">
      <PageHeader
        title="融资融券交易明细"
        description="获取沪深两市每日融资融券明细"
        details={<>
          <div>接口：margin_detail</div>
          <a href="https://tushare.pro/document/2?doc_id=59" target="_blank" rel="noopener noreferrer">查看文档</a>
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

      {/* 统计卡片 — 左文字右图标，统一亿元 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">统计股票数</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.stock_count ?? 0} 只</p>
                </div>
                <BarChart3 className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">平均融资融券余额</p>
                  <p className="text-xl sm:text-2xl font-bold">
                    {toYi(statistics.avg_rzrqye)}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">当日各股均值</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-orange-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">最大融资融券余额</p>
                  <p className="text-xl sm:text-2xl font-bold text-red-600">
                    {toYi(statistics.max_rzrqye)}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">单股最大值</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">合计融资融券余额</p>
                  <p className="text-xl sm:text-2xl font-bold">
                    {toYi(statistics.total_rzrqye)}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">当日全市场合计</p>
                </div>
                <DollarSign className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* TOP 20 图表 */}
      {chartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              融资融券余额 TOP 20
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
                    <Bar dataKey="融资融券余额" fill="#8884d8" />
                    <Bar dataKey="融资余额" fill="#82ca9d" />
                    <Bar dataKey="融券余额" fill="#ffc658" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </CardContent>
        </Card>
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
            emptyMessage="暂无融资融券交易明细数据"
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
            <DialogTitle>同步融资融券交易明细</DialogTitle>
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
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
              ) : '确认同步'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
