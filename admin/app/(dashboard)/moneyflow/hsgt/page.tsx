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
import { axiosInstance } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
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

// ============== 类型定义 ==============

interface MoneyflowData {
  trade_date: string
  ggt_ss: number
  ggt_sz: number
  hgt: number
  sgt: number
  north_money: number
  south_money: number
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

// ============== 工具函数 ==============

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

// ============== 页面组件 ==============

export default function MoneyflowHsgtPage() {
  // 查询筛选状态（页面个性化）
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)

  const dp = useDataPage<MoneyflowData, Statistics>({
    apiCall: (params) => moneyflowApi.getMoneyflowHsgt(params),
    syncFn: (params) => moneyflowApi.syncMoneyflowHsgtAsync(params),
    taskName: 'tasks.sync_moneyflow_hsgt',
    bulkOps: {
      tableKey: 'moneyflow_hsgt',
      syncFn: (params) => axiosInstance.post('/api/moneyflow-hsgt/sync-full-history', null, { params }),
      taskName: 'tasks.sync_moneyflow_hsgt_full_history',
    },
    paginationMode: 'offset',
    pageSize: 30,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      return params
    },
    syncSuccessMessage: '沪深港通资金流向数据同步完成',
  })

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '北向资金均值',
        value: <span className={pctColor(s.avg_north)}>{(s.avg_north ?? 0) >= 0 ? '+' : ''}{toYi(s.avg_north)}亿</span>,
        subValue: `近${s.count}个交易日`,
        icon: Activity,
        iconColor: 'text-orange-600',
      },
      {
        label: '累计净流入',
        value: <span className={pctColor(s.total_north)}>{(s.total_north ?? 0) >= 0 ? '+' : ''}{toYi(s.total_north)}亿</span>,
        subValue: '期间总计',
        icon: TrendingDown,
        iconColor: 'text-blue-600',
      },
      {
        label: '北向最大流入',
        value: <span className="text-red-600 dark:text-red-400">+{toYi(s.max_north)}亿</span>,
        subValue: '单日最高',
        icon: TrendingUp,
        iconColor: 'text-green-600',
      },
      {
        label: '南向最大流出',
        value: <span className="text-green-600 dark:text-green-400">{toYi(s.max_south)}亿</span>,
        subValue: '单日最高',
        icon: DollarSign,
        iconColor: 'text-purple-600',
      },
    ]
  }, [dp.statistics])

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
    return [...dp.data].reverse().map(item => ({
      date: formatDate(item.trade_date),
      北向资金: item.north_money !== null ? item.north_money / 100 : null,
      南向资金: item.south_money !== null ? item.south_money / 100 : null,
    }))
  }, [dp.data])

  return (
    <div className="space-y-6">
      <PageHeader
        title="沪深港通资金流向"
        description="获取沪股通、深股通、港股通每日资金流向数据，每次最多返回300条记录，总量不限制。"
        details={<>
          <div>接口：moneyflow_hsgt</div>
          <a href="https://tushare.pro/document/2?doc_id=47" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="沪深港通资金流向"
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
            emptyMessage="暂无沪深港通资金流向数据"
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
        title="同步沪深港通资金流向数据"
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
