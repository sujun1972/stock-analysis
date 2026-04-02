'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { moneyflowApi } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { useSystemConfig } from '@/contexts'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, BarChart3, TrendingDown, ListFilter } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { formatStockCode } from '@/lib/utils'

// 数据类型定义
interface MoneyflowData {
  trade_date: string
  ts_code: string
  name?: string
  buy_sm_amount: number
  sell_sm_amount: number
  buy_md_amount: number
  sell_md_amount: number
  buy_lg_amount: number
  sell_lg_amount: number
  buy_elg_amount: number
  sell_elg_amount: number
  net_mf_amount: number
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
  latest_date: string
  earliest_date: string
  count: number
  stock_count: number
}

const PAGE_SIZE = 100

const toDateStr = (date: Date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

export default function MoneyflowPage() {
  const [data, setData] = useState<MoneyflowData[]>([])
  const [topStocks, setTopStocks] = useState<MoneyflowData[]>([])
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  // 筛选状态 — 改为单日期模式，初始为空等待后端回填
  const [tsCode, setTsCode] = useState('')
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)

  // 分页状态
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  // 任务回调引用
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const { config } = useSystemConfig()

  // 从 task store 实时派生 — 不用 useState(false)
  const syncing = isTaskRunning('tasks.sync_moneyflow')

  const openStockAnalysis = (tsCode: string) => {
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(tsCode)), '_blank')
  }

  // 加载数据
  const loadData = useCallback(async (targetPage: number = 1) => {
    setIsLoading(true)
    try {
      const params: any = {
        limit: PAGE_SIZE,
        offset: (targetPage - 1) * PAGE_SIZE
      }
      if (tsCode) params.ts_code = tsCode
      if (tradeDate) params.trade_date = toDateStr(tradeDate)

      const response = await moneyflowApi.getMoneyflow(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics || null)
        setTotal(response.data.total || 0)
        setPage(targetPage)
        // 后端回填最近有数据的交易日
        if (!tradeDate && response.data.trade_date) {
          setTradeDate(new Date(response.data.trade_date + 'T00:00:00'))
        }
      } else {
        throw new Error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      toast.error('加载失败', { description: err.message || '加载数据失败' })
    } finally {
      setIsLoading(false)
    }
  }, [tsCode, tradeDate])

  // 加载TOP排名图表数据
  const loadTopStocks = useCallback(async () => {
    try {
      const response = await moneyflowApi.getTopMoneyflowTushare({ limit: 20 })
      if (response.code === 200 && response.data) {
        setTopStocks(response.data.items || [])
      }
    } catch (err) {
      console.error('加载TOP排名失败:', err)
    }
  }, [])

  // 初始加载
  useEffect(() => {
    loadData(1)
    loadTopStocks()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleQuery = () => {
    loadData(1).catch(() => {})
  }

  // 异步同步 — 不传日期，让后端从交易日历自动取最新交易日
  const handleSync = async () => {
    try {
      const params: any = {}
      if (tsCode) params.ts_code = tsCode
      // 注意：不传 trade_date，避免把查询筛选日期误传给同步，导致重复同步旧日期

      const response = await moneyflowApi.syncMoneyflowAsync(params)

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
            toast.success('数据同步完成', { description: '个股资金流向数据已更新' })
          } else if (task.status === 'failure') {
            toast.error('数据同步失败', { description: task.error || '同步过程中发生错误' })
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

  // 表格列定义
  const columns: Column<MoneyflowData>[] = useMemo(() => [
    {
      key: 'name',
      header: '股票',
      width: 160,
      cellClassName: 'whitespace-nowrap',
      accessor: (row) => (
        <span
          className="cursor-pointer hover:underline text-blue-600"
          onClick={() => openStockAnalysis(row.ts_code)}
        >
          {row.name ? `${row.name}[${formatStockCode(row.ts_code)}]` : row.ts_code}
        </span>
      )
    },
    {
      key: 'trade_date',
      header: '日期',
      width: 100,
      cellClassName: 'whitespace-nowrap',
      accessor: (row) => {
        const d = row.trade_date
        return d.length === 8 ? `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}` : d
      }
    },
    {
      key: 'net_mf_amount',
      header: '净流入(万)',
      width: 120,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap',
      accessor: (row) => {
        const val = row.net_mf_amount ?? 0
        return (
          <span className={val >= 0 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'}>
            {val >= 0 ? '+' : ''}{val.toFixed(2)}
          </span>
        )
      }
    },
    {
      key: 'buy_elg_amount',
      header: '特大单买(万)',
      width: 120,
      cellClassName: 'text-right whitespace-nowrap',
      accessor: (row) => (row.buy_elg_amount ?? 0).toFixed(2)
    },
    {
      key: 'sell_elg_amount',
      header: '特大单卖(万)',
      width: 120,
      cellClassName: 'text-right whitespace-nowrap',
      accessor: (row) => (row.sell_elg_amount ?? 0).toFixed(2)
    },
    {
      key: 'buy_lg_amount',
      header: '大单买(万)',
      width: 110,
      cellClassName: 'text-right whitespace-nowrap',
      accessor: (row) => (row.buy_lg_amount ?? 0).toFixed(2)
    },
    {
      key: 'sell_lg_amount',
      header: '大单卖(万)',
      width: 110,
      cellClassName: 'text-right whitespace-nowrap',
      accessor: (row) => (row.sell_lg_amount ?? 0).toFixed(2)
    },
    {
      key: 'buy_md_amount',
      header: '中单买(万)',
      width: 110,
      cellClassName: 'text-right whitespace-nowrap',
      accessor: (row) => (row.buy_md_amount ?? 0).toFixed(2)
    },
    {
      key: 'sell_md_amount',
      header: '中单卖(万)',
      width: 110,
      cellClassName: 'text-right whitespace-nowrap',
      accessor: (row) => (row.sell_md_amount ?? 0).toFixed(2)
    },
    {
      key: 'buy_sm_amount',
      header: '小单买(万)',
      width: 110,
      cellClassName: 'text-right whitespace-nowrap',
      accessor: (row) => (row.buy_sm_amount ?? 0).toFixed(2)
    },
    {
      key: 'sell_sm_amount',
      header: '小单卖(万)',
      width: 110,
      cellClassName: 'text-right whitespace-nowrap',
      accessor: (row) => (row.sell_sm_amount ?? 0).toFixed(2)
    }
  ], [openStockAnalysis])

  // 图表数据
  const chartData = useMemo(() => topStocks.map(item => ({
    code: item.name || formatStockCode(item.ts_code),
    净流入额: parseFloat((item.net_mf_amount ?? 0).toFixed(2)),
    特大单买: parseFloat((item.buy_elg_amount ?? 0).toFixed(2)),
    大单买: parseFloat((item.buy_lg_amount ?? 0).toFixed(2))
  })), [topStocks])

  // 移动端卡片视图
  const mobileCard = (item: MoneyflowData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div
            className="font-semibold text-base cursor-pointer hover:underline text-blue-600"
            onClick={() => openStockAnalysis(item.ts_code)}
          >
            {item.name || item.ts_code}
          </div>
          <div className="text-sm text-gray-500">{item.ts_code}</div>
        </div>
        <div className="text-right text-sm text-gray-500">
          {item.trade_date.length === 8
            ? `${item.trade_date.slice(0, 4)}-${item.trade_date.slice(4, 6)}-${item.trade_date.slice(6, 8)}`
            : item.trade_date}
        </div>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">净流入:</span>
          <span className={(item.net_mf_amount ?? 0) >= 0 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'}>
            {(item.net_mf_amount ?? 0) >= 0 ? '+' : ''}{(item.net_mf_amount ?? 0).toFixed(2)}万
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">特大单买:</span>
          <span>{(item.buy_elg_amount ?? 0).toFixed(2)}万</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">特大单卖:</span>
          <span>{(item.sell_elg_amount ?? 0).toFixed(2)}万</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">大单买:</span>
          <span>{(item.buy_lg_amount ?? 0).toFixed(2)}万</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">大单卖:</span>
          <span>{(item.sell_lg_amount ?? 0).toFixed(2)}万</span>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="个股资金流向"
        description="获取沪深A股票资金流向数据，分析大单小单成交情况，用于判别资金动向，数据开始于2010年。"
        details={<>
          <div>接口：moneyflow</div>
          <a href="https://tushare.pro/document/2?doc_id=170" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <Button onClick={handleSync} disabled={syncing}>
            {syncing ? (
              <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
            ) : (
              <><RefreshCw className="h-4 w-4 mr-1" />同步数据</>
            )}
          </Button>
        }
      />

      {/* 统计卡片 — 左文字右图标布局 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">平均净流入</p>
                  <p className={`text-xl sm:text-2xl font-bold ${(statistics.avg_net ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {statistics.avg_net != null ? `${statistics.avg_net >= 0 ? '+' : ''}${statistics.avg_net.toFixed(2)}` : '-'}万
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
                  <p className="text-xs sm:text-sm text-gray-600">累计净流入</p>
                  <p className={`text-xl sm:text-2xl font-bold ${(statistics.total_net ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {statistics.total_net != null ? `${statistics.total_net >= 0 ? '+' : ''}${statistics.total_net.toFixed(2)}` : '-'}万
                  </p>
                </div>
                <BarChart3 className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">最大净流入</p>
                  <p className="text-xl sm:text-2xl font-bold text-red-600">
                    {statistics.max_net != null ? `+${statistics.max_net.toFixed(2)}` : '-'}万
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
                  <p className="text-xs sm:text-sm text-gray-600">统计股票数</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.stock_count ?? 0}只</p>
                </div>
                <TrendingDown className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
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
              净流入额TOP 20
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <div style={{ minWidth: '600px' }}>
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="code"
                      angle={-45}
                      textAnchor="end"
                      height={80}
                      interval={0}
                      tick={{ fontSize: 12 }}
                    />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="净流入额" fill="#8884d8" />
                    <Bar dataKey="特大单买" fill="#82ca9d" />
                    <Bar dataKey="大单买" fill="#ffc658" />
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
            <div className="space-y-1 w-full sm:w-48">
              <Label>股票代码</Label>
              <Input
                placeholder="如 000001 或 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="space-y-1 w-full sm:w-auto">
              <Label>交易日期</Label>
              <DatePicker date={tradeDate} onDateChange={setTradeDate} />
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <Button onClick={handleQuery} disabled={isLoading} className="flex-1 sm:flex-none">
                查询
              </Button>
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-2">
            小单&lt;5万 | 中单5-20万 | 大单20-100万 | 特大单≥100万
          </p>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="p-0 sm:p-6">
          <DataTable
            columns={columns}
            data={data}
            loading={isLoading}
            emptyMessage="暂无个股资金流向数据"
            mobileCard={mobileCard}
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
    </div>
  )
}
