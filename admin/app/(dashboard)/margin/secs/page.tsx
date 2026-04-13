'use client'

import { useState, useEffect, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { marginSecsApi } from '@/lib/api'
import type { MarginSecsItem, MarginSecsStatistics } from '@/lib/api/margin-secs'
import { apiClient } from '@/lib/api-client'
import { formatStockCode } from '@/lib/utils'
import { useTaskStore } from '@/stores/task-store'
import { useDataBulkOps } from '@/hooks/useDataBulkOps'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useSystemConfig } from '@/contexts'
import { toast } from 'sonner'
import { RefreshCw, BarChart3, TrendingUp, Building2, CalendarDays } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'

// 交易所常量
const EXCHANGES = [
  { value: 'ALL', label: '全部' },
  { value: 'SSE', label: '上交所' },
  { value: 'SZSE', label: '深交所' },
  { value: 'BSE', label: '北交所' },
]

const EXCHANGE_LABEL: Record<string, string> = {
  SSE: '上交所',
  SZSE: '深交所',
  BSE: '北交所',
}

const EXCHANGE_COLORS: Record<string, string> = {
  SSE: '#8884d8',
  SZSE: '#82ca9d',
  BSE: '#ffc658',
}

const PAGE_SIZE = 100

export default function MarginSecsPage() {
  const [data, setData] = useState<MarginSecsItem[]>([])
  const [statistics, setStatistics] = useState<MarginSecsStatistics | null>(null)
  const [exchangeDistribution, setExchangeDistribution] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)

  // 筛选状态
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [exchange, setExchange] = useState('ALL')

  // 同步弹窗
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)

  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const { config } = useSystemConfig()

  // 从 task store 实时派生——不用本地 useState
  const syncing = isTaskRunning('extended.sync_margin_secs') || isTaskRunning('tasks.sync_margin_secs_full_history')

  // 判断是否为股票（ETF/基金/债券不跳转）
  // 5xxxxx = 上海ETF/基金，1xxxxx = 深圳ETF/基金，821xxx = 北交所债券
  const isStock = (tsCode: string) => {
    const code = tsCode.split('.')[0]
    return !code.startsWith('5') && !code.startsWith('1') && !code.startsWith('821')
  }

  const openStockAnalysis = (tsCode: string) => {
    if (!isStock(tsCode)) return
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(tsCode)), '_blank')
  }

  // 时区安全的日期字符串构建
  const toDateStr = (date: Date) =>
    `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

  // 加载主数据
  const loadData = async (targetPage: number = page) => {
    setIsLoading(true)
    try {
      const params: any = {
        page: targetPage,
        page_size: PAGE_SIZE,
      }
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      if (tsCode) params.ts_code = tsCode
      if (exchange && exchange !== 'ALL') params.exchange = exchange

      const response = await marginSecsApi.getMarginSecs(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics || null)
        setTotal(response.data.total || 0)
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

  // 加载交易所分布图表（独立，不阻断主流程）
  const loadExchangeDistribution = async () => {
    try {
      const response = await marginSecsApi.getLatestMarginSecs()
      if (response.code === 200 && response.data) {
        setExchangeDistribution(response.data.statistics.exchange_distribution || [])
      }
    } catch {
      // 图表加载失败不阻断主流程
    }
  }

  const {
    handleFullSync,
    handleClear,
    fullSyncing,
    isClearing,
    isClearDialogOpen,
    setIsClearDialogOpen,
    cleanup,
    earliestHistoryDate,
  } = useDataBulkOps({
    tableKey: 'margin_secs',
    syncFn: (params) => apiClient.post('/api/margin-secs/sync-full-history', null, { params }),
    taskName: 'tasks.sync_margin_secs_full_history',
    onSuccess: loadData,
  })

  // 初始加载：只跑一次
  useEffect(() => {
    loadData(1).catch(() => {})
    loadExchangeDistribution().catch(() => {})
  }, [])

  const handleQuery = () => {
    loadData(1).catch(() => {})
  }

  // 同步确认
  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    try {
      // 不传日期参数，由后端从 sync_configs 自动计算
      const response = await marginSecsApi.syncMarginSecsAsync()

      if (response.code === 200 && response.data) {
        const taskId = response.data.celery_task_id

        addTask({
          taskId,
          taskName: response.data.task_name,
          displayName: response.data.display_name,
          taskType: 'data_sync',
          status: 'running',
          progress: 0,
          startTime: Date.now(),
        })

        const completionCallback = (task: any) => {
          if (task.status === 'success') {
            loadData(1).catch(() => {})
            loadExchangeDistribution().catch(() => {})
            toast.success('数据同步完成', { description: '融资融券标的数据已更新' })
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
      cleanup()
    }
  }, [unregisterCompletionCallback])

  // 表格列定义
  const columns: Column<MarginSecsItem>[] = [
    {
      key: 'name',
      header: '标的',
      accessor: (row) => (
        <span
          className={`whitespace-nowrap${isStock(row.ts_code) ? ' cursor-pointer hover:underline' : ''}`}
          onClick={() => isStock(row.ts_code) && openStockAnalysis(row.ts_code)}
        >
          {row.name || '-'}[{formatStockCode(row.ts_code)}]
        </span>
      ),
      width: 180,
      cellClassName: 'whitespace-nowrap',
    },
    {
      key: 'exchange',
      header: '交易所',
      accessor: (row) => EXCHANGE_LABEL[row.exchange] || row.exchange,
      width: 90,
      cellClassName: 'text-center',
    },
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => row.trade_date,
      width: 120,
      cellClassName: 'whitespace-nowrap text-center',
    },
  ]

  // 移动端卡片视图
  const mobileCard = (item: MarginSecsItem) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start">
        <div>
          <div
            className={`font-semibold text-base${isStock(item.ts_code) ? ' cursor-pointer hover:underline' : ''}`}
            onClick={() => isStock(item.ts_code) && openStockAnalysis(item.ts_code)}
          >
            {item.name || '-'}
          </div>
          <div className="text-sm text-gray-500">{item.ts_code}</div>
        </div>
        <div className="text-right">
          <div className="text-sm font-medium">{EXCHANGE_LABEL[item.exchange] || item.exchange}</div>
          <div className="text-xs text-gray-500 mt-0.5">{item.trade_date}</div>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="融资融券标的"
        description="获取沪深京三大交易所融资融券标的（包括ETF），每天盘前更新"
        details={<>
          <div>接口：margin_secs</div>
          <a href="https://tushare.pro/document/2?doc_id=326" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <div className="flex gap-2">
            <Button onClick={() => setSyncDialogOpen(true)} disabled={syncing}>
              {syncing ? (
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
              ) : (
                <><RefreshCw className="h-4 w-4 mr-1" />同步数据</>
              )}
            </Button>
            <BulkOpsButtons
              onFullSync={handleFullSync}
              onClearConfirm={handleClear}
              isClearDialogOpen={isClearDialogOpen}
              setIsClearDialogOpen={setIsClearDialogOpen}
              fullSyncing={fullSyncing}
              isClearing={isClearing}
              earliestHistoryDate={earliestHistoryDate}
              tableName="融资融券标的"
            />
          </div>
        }
      />

      {/* 统计卡片 — 左文字右图标 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">标的数量</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.unique_stocks ?? 0} 只</p>
                  <p className="text-xs text-gray-400 mt-0.5">当日不重复标的数</p>
                </div>
                <BarChart3 className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">总记录数</p>
                  <p className="text-xl sm:text-2xl font-bold">{(statistics.total_count ?? 0).toLocaleString()}</p>
                  <p className="text-xs text-gray-400 mt-0.5">当前筛选范围内</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-orange-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">交易所数</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.exchange_count ?? 0} 个</p>
                  <p className="text-xs text-gray-400 mt-0.5">涵盖交易所数量</p>
                </div>
                <Building2 className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">数据天数</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.trading_days ?? 0} 天</p>
                  <p className="text-xs text-gray-400 mt-0.5">数据覆盖交易日数</p>
                </div>
                <CalendarDays className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 交易所分布图表 */}
      {exchangeDistribution.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>最新交易日标的交易所分布</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[260px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={exchangeDistribution}
                    dataKey="count"
                    nameKey="exchange"
                    cx="50%"
                    cy="50%"
                    outerRadius={90}
                    label={(entry: any) =>
                      `${EXCHANGE_LABEL[entry.exchange] || entry.exchange}: ${entry.count}`
                    }
                  >
                    {exchangeDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={EXCHANGE_COLORS[entry.exchange] || '#999999'} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: any) => `${value} 只`} />
                  <Legend
                    formatter={(value) => EXCHANGE_LABEL[value] || value}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 筛选区域 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            数据查询
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="w-full sm:w-48">
              <label className="text-sm font-medium mb-1 block">标的代码</label>
              <Input
                placeholder="如 510050 或 510050.SH"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="w-full sm:w-36">
              <label className="text-sm font-medium mb-1 block">交易所</label>
              <Select value={exchange} onValueChange={setExchange}>
                <SelectTrigger>
                  <SelectValue placeholder="全部" />
                </SelectTrigger>
                <SelectContent>
                  {EXCHANGES.map((ex) => (
                    <SelectItem key={ex.value} value={ex.value}>
                      {ex.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
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
            emptyMessage="暂无融资融券标的数据"
            pagination={{
              page,
              pageSize: PAGE_SIZE,
              total,
              onPageChange: (newPage) => loadData(newPage),
            }}
          />
        </CardContent>
      </Card>

      {/* 同步日期选择弹窗 */}
      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>同步融资融券标的</DialogTitle>
            <DialogDescription>
              将从 Tushare 增量同步最新融资融券标的数据，无需选择日期。
            </DialogDescription>
          </DialogHeader>
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
