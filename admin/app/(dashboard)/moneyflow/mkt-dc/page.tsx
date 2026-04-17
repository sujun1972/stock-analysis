'use client'

import { useState, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { useDataPage } from '@/hooks/useDataPage'
import { moneyflowApi } from '@/lib/api'
import { apiClient } from '@/lib/api-client'
import { toDateStr } from '@/lib/date-utils'
import { RefreshCw, TrendingUp, TrendingDown, Activity, DollarSign, ListFilter } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

// ============== 类型定义 ==============

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

// ============== 工具函数 ==============

const pctColor = (val: number | null | undefined) =>
  (val ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'

const formatDate = (dateStr: string) => {
  if (!dateStr || dateStr.length !== 8) return dateStr
  return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
}

// ============== 页面组件 ==============

export default function MoneyflowMktDcPage() {
  // 查询筛选状态（页面个性化）
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)

  const dp = useDataPage<MoneyflowMktDcData, Statistics>({
    apiCall: (params) => moneyflowApi.getMoneyflowMktDc(params),
    syncFn: (params) => moneyflowApi.syncMoneyflowMktDcAsync(params),
    taskName: 'tasks.sync_moneyflow_mkt_dc',
    bulkOps: {
      tableKey: 'moneyflow_mkt_dc',
      syncFn: (params) => apiClient.post('/api/moneyflow-mkt-dc/sync-full-history', null, { params }),
      taskName: 'tasks.sync_moneyflow_mkt_dc_full_history',
    },
    paginationMode: 'offset',
    pageSize: 30,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      return params
    },
    syncSuccessMessage: '大盘资金流向数据同步完成',
  })

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '主力净流入均值',
        value: (
          <span className={pctColor(s.avg_net)}>
            {(s.avg_net ?? 0) >= 0 ? '+' : ''}{(s.avg_net ?? 0).toFixed(2)}亿
          </span>
        ),
        subValue: `近${s.count}个交易日`,
        icon: Activity,
        iconColor: 'text-orange-600',
      },
      {
        label: '最大净流入',
        value: <span className="text-red-600">+{(s.max_net ?? 0).toFixed(2)}亿</span>,
        subValue: '单日最高',
        icon: TrendingUp,
        iconColor: 'text-green-600',
      },
      {
        label: '超大单均值',
        value: (
          <span className={pctColor(s.avg_elg)}>
            {(s.avg_elg ?? 0) >= 0 ? '+' : ''}{(s.avg_elg ?? 0).toFixed(2)}亿
          </span>
        ),
        subValue: '日均流入',
        icon: DollarSign,
        iconColor: 'text-purple-600',
      },
      {
        label: '累计净流入',
        value: (
          <span className={pctColor(s.total_net)}>
            {(s.total_net ?? 0) >= 0 ? '+' : ''}{(s.total_net ?? 0).toFixed(2)}亿
          </span>
        ),
        subValue: '期间总计',
        icon: TrendingDown,
        iconColor: 'text-blue-600',
      },
    ]
  }, [dp.statistics])

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

  // 趋势图数据（时序倒序 -> 正序）
  const chartData = useMemo(() => {
    return [...dp.data].reverse().map(item => ({
      date: formatDate(item.trade_date),
      主力净流入: item.net_amount,
      超大单: item.buy_elg_amount,
      大单: item.buy_lg_amount,
    }))
  }, [dp.data])

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
              tableName="大盘资金流向(DC)"
            />
          </div>
        }
      />

      <StatisticsCards items={statsCards} />

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
              <label className="text-sm font-medium mb-1 block">开始日期</label>
              <DatePicker date={startDate} onDateChange={setStartDate} placeholder="选择开始日期" />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">结束日期</label>
              <DatePicker date={endDate} onDateChange={setEndDate} placeholder="选择结束日期" />
            </div>
            <Button onClick={dp.handleQuery} disabled={dp.isLoading} className="w-full sm:w-auto">
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
            data={dp.data}
            loading={dp.isLoading}
            mobileCard={mobileCard}
            emptyMessage="暂无大盘资金流向数据"
            tableClassName="table-fixed w-full [&_th]:border-r [&_td]:border-r [&_th:last-child]:border-r-0 [&_td:last-child]:border-r-0 [&_th]:!text-center"
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
        title="同步大盘资金流向数据"
        description="选择同步日期范围（留空则同步最新交易日数据）。"
        disabled={dp.syncing}
        showDateRange
        startDate={dp.syncStartDate}
        onStartDateChange={dp.setSyncStartDate}
        endDate={dp.syncEndDate}
        onEndDateChange={dp.setSyncEndDate}
      />
    </div>
  )
}
