'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { useDataPage } from '@/hooks/useDataPage'
import { moneyflowApi } from '@/lib/api'
import { axiosInstance } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { RefreshCw, TrendingUp, BarChart3, ListFilter, DollarSign, Activity } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { toast } from 'sonner'
import { useTaskStore } from '@/stores/task-store'

// ============== 类型定义 ==============

interface MoneyflowIndDcData {
  trade_date: string
  content_type: string
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
  buy_sm_amount_stock: string
  rank: number | null
}

interface Statistics {
  avg_net_amount: number
  max_net_amount: number
  min_net_amount: number
  total_net_amount: number
  avg_buy_elg_amount: number
  max_buy_elg_amount: number
  avg_buy_lg_amount: number
  max_buy_lg_amount: number
  latest_date: string
  earliest_date: string
  count: number
  sector_count: number
}

// ============== 工具函数 ==============

const toYi = (val: number | null | undefined) => {
  if (val === null || val === undefined) return '-'
  return (val >= 0 ? '+' : '') + val.toFixed(2) + '亿'
}

const pctColor = (val: number | null | undefined) =>
  (val ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'

// ============== 页面组件 ==============

export default function MoneyflowIndDcPage() {
  // 查询筛选状态（页面个性化）
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [contentType, setContentType] = useState<string>('all')

  // 同步弹窗额外状态（该页面同步弹窗含自定义字段）
  const [syncDate, setSyncDate] = useState<Date | undefined>(undefined)
  const [syncContentType, setSyncContentType] = useState<string>('all')

  // TOP 板块图表数据（独立加载，不走 useDataPage）
  const [topSectors, setTopSectors] = useState<MoneyflowIndDcData[]>([])

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()

  const dp = useDataPage<MoneyflowIndDcData, Statistics>({
    apiCall: (params) => moneyflowApi.getMoneyflowIndDc(params),
    taskName: 'tasks.sync_moneyflow_ind_dc',
    bulkOps: {
      tableKey: 'moneyflow_ind_dc',
      syncFn: (params) => axiosInstance.post('/api/moneyflow-ind-dc/sync-full-history', null, { params }),
      taskName: 'tasks.sync_moneyflow_ind_dc_full_history',
    },
    paginationMode: 'page',
    pageSize: 100,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      if (contentType && contentType !== 'all') params.content_type = contentType
      return params
    },
    onBackfillDate: (dateStr) => setTradeDate(new Date(dateStr + 'T00:00:00')),
  })

  // 独立加载 TOP 板块
  const loadTopSectors = useCallback(async () => {
    try {
      const response = await moneyflowApi.getTopMoneyflowIndustries({ limit: 20 })
      if (response.code === 200 && response.data) {
        setTopSectors(Array.isArray(response.data) ? response.data : response.data.items || [])
      }
    } catch {
      // 图表加载失败不阻断主流程
    }
  }, [])

  useEffect(() => {
    loadTopSectors().catch(() => {})
  }, [loadTopSectors])

  // 自定义同步确认（该页面同步逻辑特殊：全部时提交三个任务）
  const handleSyncConfirm = async () => {
    dp.setSyncDialogOpen(false)
    try {
      const syncDateStr = syncDate ? toDateStr(syncDate) : undefined
      const ct = syncContentType !== 'all' ? syncContentType : undefined

      const types = ct ? [ct] : ['行业', '概念', '地域']

      for (const type of types) {
        const response = await moneyflowApi.syncMoneyflowIndDcAsync(
          syncDateStr ? { trade_date: syncDateStr, content_type: type } : { content_type: type }
        )

        if (response.code === 200 && response.data) {
          const taskId = response.data.celery_task_id
          addTask({
            taskId,
            taskName: response.data.task_name,
            displayName: response.data.display_name + `(${type})`,
            taskType: 'data_sync',
            status: 'running',
            progress: 0,
            startTime: Date.now()
          })

          const completionCallback = (task: { status: string }) => {
            if (task.status === 'success') {
              dp.loadData(1)
              loadTopSectors().catch(() => {})
              toast.success(`${type}数据同步完成`)
            }
            unregisterCompletionCallback(taskId, completionCallback)
          }
          registerCompletionCallback(taskId, completionCallback)
          triggerPoll()
        } else {
          toast.error(response.message || `提交${type}同步任务失败`)
        }
      }

      toast.success(ct ? '同步任务已提交' : '已提交行业/概念/地域三个同步任务')
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '提交同步任务失败'
      toast.error(message)
    }
  }

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '板块数',
        value: `${s.sector_count ?? 0}个`,
        icon: BarChart3,
        iconColor: 'text-blue-600',
      },
      {
        label: '主力资金均值(亿)',
        value: <span className={pctColor(s.avg_net_amount)}>{(s.avg_net_amount ?? 0) >= 0 ? '+' : ''}{(s.avg_net_amount ?? 0).toFixed(2)}</span>,
        icon: Activity,
        iconColor: 'text-orange-600',
      },
      {
        label: '最大净流入(亿)',
        value: <span className="text-red-600">+{(s.max_net_amount ?? 0).toFixed(2)}</span>,
        icon: TrendingUp,
        iconColor: 'text-green-600',
      },
      {
        label: '超大单均值(亿)',
        value: <span className={pctColor(s.avg_buy_elg_amount)}>{(s.avg_buy_elg_amount ?? 0) >= 0 ? '+' : ''}{(s.avg_buy_elg_amount ?? 0).toFixed(2)}</span>,
        icon: DollarSign,
        iconColor: 'text-purple-600',
      },
    ]
  }, [dp.statistics])

  // 表格列定义
  const columns: Column<MoneyflowIndDcData>[] = useMemo(() => [
    {
      key: 'name',
      header: '板块',
      accessor: (row) => row.name ? `${row.name}[${row.ts_code}]` : row.ts_code,
      width: 200,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'content_type',
      header: '类型',
      accessor: (row) => row.content_type,
      width: 70,
      cellClassName: 'text-center whitespace-nowrap'
    },
    {
      key: 'pct_change',
      header: '涨跌幅%',
      accessor: (row) => {
        if (row.pct_change === null || row.pct_change === undefined) return '-'
        const v = row.pct_change
        return <span className={pctColor(v)}>{v >= 0 ? '+' : ''}{v.toFixed(2)}%</span>
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
        return <span className={row.net_amount >= 0 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'}>{toYi(row.net_amount)}</span>
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
        return <span className={pctColor(v)}>{v >= 0 ? '+' : ''}{v.toFixed(2)}%</span>
      },
      width: 115,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'buy_elg_amount',
      header: '超大单净流入',
      accessor: (row) => {
        if (row.buy_elg_amount === null || row.buy_elg_amount === undefined) return '-'
        return <span className={row.buy_elg_amount >= 0 ? 'text-red-600' : 'text-green-600'}>{toYi(row.buy_elg_amount)}</span>
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
        return <span className={row.buy_lg_amount >= 0 ? 'text-red-600' : 'text-green-600'}>{toYi(row.buy_lg_amount)}</span>
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
        return <span className={row.buy_md_amount >= 0 ? 'text-red-600' : 'text-green-600'}>{toYi(row.buy_md_amount)}</span>
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
        return <span className={row.buy_sm_amount >= 0 ? 'text-red-600' : 'text-green-600'}>{toYi(row.buy_sm_amount)}</span>
      },
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rank',
      header: '排名',
      accessor: (row) => row.rank !== null && row.rank !== undefined ? `#${row.rank}` : '-',
      width: 70,
      cellClassName: 'text-center whitespace-nowrap'
    },
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: MoneyflowIndDcData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div className="font-semibold text-base">{item.name || item.ts_code}</div>
          <div className="text-sm text-gray-500">{item.ts_code} · {item.content_type}</div>
        </div>
        <div className="text-right">
          {item.pct_change !== null && (
            <div className={pctColor(item.pct_change)}>
              {item.pct_change >= 0 ? '+' : ''}{item.pct_change.toFixed(2)}%
            </div>
          )}
          {item.rank !== null && <div className="text-xs text-gray-500">#{item.rank}</div>}
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
          <span className={pctColor(item.buy_elg_amount)}>{toYi(item.buy_elg_amount)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">大单净流入:</span>
          <span className={pctColor(item.buy_lg_amount)}>{toYi(item.buy_lg_amount)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">主力净占比:</span>
          <span>{item.net_amount_rate !== null ? `${item.net_amount_rate.toFixed(2)}%` : '-'}</span>
        </div>
      </div>
    </div>
  ), [])

  // 图表数据（TOP 20）
  const chartData = useMemo(() => topSectors.map(item => ({
    name: item.name || item.ts_code,
    主力净流入: item.net_amount ?? 0,
    超大单: item.buy_elg_amount ?? 0,
    大单: item.buy_lg_amount ?? 0,
  })), [topSectors])

  return (
    <div className="space-y-6">
      <PageHeader
        title="板块资金流向（DC）"
        description="获取东方财富板块资金流向，每天盘后更新"
        details={<>
          <div>接口：moneyflow_ind_dc</div>
          <a href="https://tushare.pro/document/2?doc_id=344" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <div className="flex gap-2">
            <Button onClick={() => dp.setSyncDialogOpen(true)} disabled={dp.syncing}>
              {dp.syncing ? (
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
              ) : (
                <><RefreshCw className="h-4 w-4 mr-1" />同步数据</>
              )}
            </Button>
            <BulkOpsButtons
              onFullSync={dp.handleFullSync}
              onClearConfirm={dp.handleClear}
              isClearDialogOpen={dp.isClearDialogOpen}
              setIsClearDialogOpen={dp.setIsClearDialogOpen}
              fullSyncing={dp.fullSyncing}
              isClearing={dp.isClearing}
              earliestHistoryDate={dp.earliestHistoryDate}
              tableName="板块资金流向(DC)"
            />
          </div>
        }
      />

      <StatisticsCards items={statsCards} />

      {/* TOP 20 图表 */}
      {chartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              主力资金流入 TOP 20 板块
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
            <div className="w-full sm:w-40">
              <label className="text-sm font-medium mb-1 block">板块类型</label>
              <Select value={contentType} onValueChange={setContentType}>
                <SelectTrigger>
                  <SelectValue placeholder="选择类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部</SelectItem>
                  <SelectItem value="行业">行业</SelectItem>
                  <SelectItem value="概念">概念</SelectItem>
                  <SelectItem value="地域">地域</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <Button onClick={dp.handleQuery} disabled={dp.isLoading} className="flex-1 sm:flex-none">
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
            data={dp.data}
            loading={dp.isLoading}
            mobileCard={mobileCard}
            emptyMessage="暂无板块资金流向数据"
            tableClassName="table-fixed w-full [&_th]:border-r [&_td]:border-r [&_th:last-child]:border-r-0 [&_td:last-child]:border-r-0 [&_th]:!text-center"
            sort={{
              key: dp.sortKey,
              direction: dp.sortDirection,
              onSort: dp.handleSort,
            }}
            pagination={{
              page: dp.page,
              pageSize: dp.pageSize,
              total: dp.total,
              onPageChange: dp.handlePageChange,
            }}
          />
        </CardContent>
      </Card>

      {/* 同步日期选择弹窗（自定义内容，不用 SyncDialog） */}
      <Dialog open={dp.syncDialogOpen} onOpenChange={dp.setSyncDialogOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>同步板块资金流向数据</DialogTitle>
            <DialogDescription>
              选择同步日期和板块类型（日期留空则同步最新交易日；&ldquo;全部&rdquo;将依次提交行业/概念/地域三个任务，共消耗约 18000 积分）。
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">交易日期（可选）</label>
              <DatePicker
                date={syncDate}
                onDateChange={setSyncDate}
                placeholder="留空同步最新交易日"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">板块类型</label>
              <Select value={syncContentType} onValueChange={setSyncContentType}>
                <SelectTrigger>
                  <SelectValue placeholder="选择类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部（行业+概念+地域）</SelectItem>
                  <SelectItem value="行业">行业</SelectItem>
                  <SelectItem value="概念">概念</SelectItem>
                  <SelectItem value="地域">地域</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => dp.setSyncDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSyncConfirm} disabled={dp.syncing}>
              {dp.syncing ? (
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
              ) : '确认同步'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
