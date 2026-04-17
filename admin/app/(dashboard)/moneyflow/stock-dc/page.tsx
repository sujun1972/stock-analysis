'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useDataPage } from '@/hooks/useDataPage'
import { moneyflowApi } from '@/lib/api'
import { formatStockCode, pctChangeColor } from '@/lib/utils'
import { useSystemConfig } from '@/contexts'
import { toDateStr } from '@/lib/date-utils'
import { TrendingUp, BarChart3, ListFilter, RefreshCw, DollarSign } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

// ============== 类型定义 ==============

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

// ============== 工具函数 ==============

const toYi = (val: number | null | undefined) => {
  if (val === null || val === undefined) return '-'
  return (val >= 0 ? '+' : '') + val.toFixed(2) + '亿'
}

const toYiNoSign = (val: number | null | undefined) => {
  if (val === null || val === undefined) return '-'
  return val.toFixed(2) + '亿'
}

// ============== 页面组件 ==============

export default function MoneyflowStockDcPage() {
  // 查询筛选状态
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')

  // TOP 股票图表数据（独立加载）
  const [topStocks, setTopStocks] = useState<MoneyflowStockDcItem[]>([])

  const { config } = useSystemConfig()

  const openStockAnalysis = useCallback((code: string) => {
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(code)), '_blank')
  }, [config])

  const dp = useDataPage<MoneyflowStockDcItem, Statistics>({
    apiCall: (params) => moneyflowApi.getMoneyflowStockDc(params),
    syncFn: (params) => moneyflowApi.syncMoneyflowStockDcAsync(params),
    taskName: 'tasks.sync_moneyflow_stock_dc',
    bulkOps: {
      tableKey: 'moneyflow_stock_dc',
      syncFn: (params) => moneyflowApi.syncMoneyflowStockDcFullHistoryAsync(params),
      taskName: 'tasks.sync_moneyflow_stock_dc_full_history',
    },
    paginationMode: 'page',
    pageSize: 100,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      if (tsCode) params.ts_code = tsCode
      return params
    },
    onBackfillDate: (dateStr) => setTradeDate(new Date(dateStr + 'T00:00:00')),
    syncSuccessMessage: '个股资金流向数据同步完成',
  })

  // 独立加载 TOP 股票
  const loadTopStocks = useCallback(async () => {
    try {
      const response = await moneyflowApi.getTopMoneyflowStocks({ limit: 20 })
      if (response.code === 200 && response.data) {
        setTopStocks(response.data.items || [])
      }
    } catch {
      // 图表加载失败不阻断主流程
    }
  }, [])

  useEffect(() => {
    loadTopStocks().catch(() => {})
  }, [loadTopStocks])

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '统计股票数',
        value: `${s.stock_count ?? 0}只`,
        icon: BarChart3,
        iconColor: 'text-blue-600',
      },
      {
        label: '主力资金均值(亿)',
        value: <span className={(s.avg_net_amount ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}>{(s.avg_net_amount ?? 0) >= 0 ? '+' : ''}{(s.avg_net_amount ?? 0).toFixed(2)}</span>,
        icon: TrendingUp,
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
        value: <span className={(s.avg_buy_elg_amount ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}>{(s.avg_buy_elg_amount ?? 0) >= 0 ? '+' : ''}{(s.avg_buy_elg_amount ?? 0).toFixed(2)}</span>,
        icon: DollarSign,
        iconColor: 'text-purple-600',
      },
    ]
  }, [dp.statistics])

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
        description="获取东方财富个股资金流向数据，每日盘后更新，数据开始于20230911"
        details={<>
          <div>接口：moneyflow_dc</div>
          <a href="https://tushare.pro/document/2?doc_id=349" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="个股资金流向(DC)"
            />
          </div>
        }
      />

      <StatisticsCards items={statsCards} />

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
            emptyMessage="暂无个股资金流向数据"
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

      {/* 同步弹窗 */}
      <SyncDialog
        open={dp.syncDialogOpen}
        onOpenChange={dp.setSyncDialogOpen}
        onConfirm={dp.handleSyncConfirm}
        title="同步个股资金流向数据"
        description="选择同步日期（留空则同步最新交易日数据）。"
        disabled={dp.syncing}
        showDateRange
        startDate={dp.syncStartDate}
        onStartDateChange={dp.setSyncStartDate}
        endDate={dp.syncEndDate}
        onEndDateChange={dp.setSyncEndDate}
        startDateLabel="开始日期"
        endDateLabel="结束日期"
      />
    </div>
  )
}
