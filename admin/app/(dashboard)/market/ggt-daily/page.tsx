'use client'

import { useState, useMemo } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useDataPage } from '@/hooks/useDataPage'
import { ggtDailyApi, type GgtDailyData, type GgtDailyStatistics } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { RefreshCw, TrendingUp, TrendingDown, Activity, DollarSign } from 'lucide-react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'

// ============== 页面组件 ==============

export default function GgtDailyPage() {
  // 查询筛选状态
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)

  const dp = useDataPage<GgtDailyData, GgtDailyStatistics>({
    apiCall: (params) => ggtDailyApi.getGgtDaily(params),
    syncFn: (params) => ggtDailyApi.syncAsync(params),
    taskName: 'tasks.sync_ggt_daily',
    bulkOps: {
      tableKey: 'ggt_daily',
      syncFn: (params) => ggtDailyApi.syncFullHistory(params),
      taskName: 'tasks.sync_ggt_daily_full_history',
    },
    paginationMode: 'offset',
    pageSize: 30,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      return params
    },
    syncSuccessMessage: '港股通每日成交统计数据同步完成',
  })

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '平均买入金额',
        value: <span className="text-red-600">{s.avg_buy_amount?.toFixed(2) || '0.00'}</span>,
        subValue: '亿元',
        icon: TrendingUp,
        iconColor: 'text-red-600',
      },
      {
        label: '平均卖出金额',
        value: <span className="text-green-600">{s.avg_sell_amount?.toFixed(2) || '0.00'}</span>,
        subValue: '亿元',
        icon: TrendingDown,
        iconColor: 'text-green-600',
      },
      {
        label: '累计买入金额',
        value: `${s.total_buy_amount?.toFixed(2) || '0.00'}`,
        subValue: '亿元',
        icon: DollarSign,
        iconColor: 'text-blue-600',
      },
      {
        label: '统计天数',
        value: `${s.total_count || 0}`,
        subValue: '交易日',
        icon: Activity,
        iconColor: 'text-orange-600',
      },
    ]
  }, [dp.statistics])

  // 表格列定义
  const columns: Column<GgtDailyData>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => row.trade_date
    },
    {
      key: 'buy_amount',
      header: '买入金额',
      accessor: (row) => (
        <span className="text-red-600 font-medium">
          {row.buy_amount?.toFixed(2) || '0.00'} 亿
        </span>
      )
    },
    {
      key: 'buy_volume',
      header: '买入笔数',
      accessor: (row) => (
        <span>{row.buy_volume?.toFixed(2) || '0.00'} 万笔</span>
      )
    },
    {
      key: 'sell_amount',
      header: '卖出金额',
      accessor: (row) => (
        <span className="text-green-600 font-medium">
          {row.sell_amount?.toFixed(2) || '0.00'} 亿
        </span>
      )
    },
    {
      key: 'sell_volume',
      header: '卖出笔数',
      accessor: (row) => (
        <span>{row.sell_volume?.toFixed(2) || '0.00'} 万笔</span>
      )
    },
    {
      key: 'net_amount',
      header: '净额',
      accessor: (row) => {
        const netAmount = (row.buy_amount || 0) - (row.sell_amount || 0)
        return (
          <span className={netAmount >= 0 ? 'text-red-600 font-medium' : 'text-green-600 font-medium'}>
            {netAmount >= 0 ? '+' : ''}{netAmount.toFixed(2)} 亿
          </span>
        )
      }
    }
  ], [])

  // 图表数据
  const chartData = useMemo(() => {
    return dp.data.map(item => ({
      date: item.trade_date,
      买入金额: item.buy_amount || 0,
      卖出金额: item.sell_amount || 0,
      净额: (item.buy_amount || 0) - (item.sell_amount || 0)
    })).reverse()
  }, [dp.data])

  return (
    <div className="space-y-6">
      <PageHeader
        title="港股通每日成交统计"
        description="获取港股通每日成交信息，数据从2014年开始"
        details={<>
          <div>接口：ggt_daily</div>
          <a href="https://tushare.pro/document/2?doc_id=196" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="港股通每日成交"
            />
          </div>
        }
      />

      <StatisticsCards items={statsCards} />

      {/* 趋势图表 */}
      {chartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>成交金额趋势</CardTitle>
            <CardDescription>港股通买卖成交金额变化</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="date"
                    angle={-45}
                    textAnchor="end"
                    height={80}
                    tick={{ fontSize: 12 }}
                  />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="买入金额"
                    stroke="#ef4444"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="卖出金额"
                    stroke="#22c55e"
                    strokeWidth={2}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="净额"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 筛选和操作区域 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">开始日期</label>
              <DatePicker
                date={startDate}
                onDateChange={setStartDate}
                placeholder="选择开始日期"
              />
            </div>

            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">结束日期</label>
              <DatePicker
                date={endDate}
                onDateChange={setEndDate}
                placeholder="选择结束日期"
              />
            </div>

            <div className="flex gap-2">
              <Button onClick={dp.handleQuery} disabled={dp.isLoading} variant="outline">
                <RefreshCw className={`mr-2 h-4 w-4 ${dp.isLoading ? 'animate-spin' : ''}`} />
                查询
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="p-0">
          <DataTable
            columns={columns}
            data={dp.data}
            loading={dp.isLoading}
            emptyMessage="暂无数据"
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
        title="同步数据"
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
