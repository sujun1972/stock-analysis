'use client'

import { useState, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DataTable, Column } from '@/components/common/DataTable'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useDataPage } from '@/hooks/useDataPage'
import { ggtMonthlyApi, type GgtMonthlyData, type GgtMonthlyStatistics } from '@/lib/api'
import { RefreshCw, TrendingUp, TrendingDown, DollarSign, Activity } from 'lucide-react'
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

// ============== 工具函数 ==============

const formatNumber = (num: number | null | undefined, decimals: number = 2) => {
  if (num === null || num === undefined) return '0.00'
  return num.toFixed(decimals)
}

// ============== 页面组件 ==============

export default function GgtMonthlyPage() {
  // 查询筛选状态
  const [startMonth, setStartMonth] = useState('')
  const [endMonth, setEndMonth] = useState('')

  // 同步弹窗额外状态（月度范围用 Input 而非 DatePicker）
  const [syncStartMonth, setSyncStartMonth] = useState('')
  const [syncEndMonth, setSyncEndMonth] = useState('')

  const dp = useDataPage<GgtMonthlyData, GgtMonthlyStatistics>({
    apiCall: (params) => ggtMonthlyApi.getData(params),
    syncFn: (params) => ggtMonthlyApi.syncAsync(params),
    taskName: 'tasks.sync_ggt_monthly',
    bulkOps: {
      tableKey: 'ggt_monthly',
      syncFn: () => ggtMonthlyApi.syncAsync({}),
      taskName: 'tasks.sync_ggt_monthly',
    },
    paginationMode: 'offset',
    pageSize: 30,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (startMonth) params.start_month = startMonth
      if (endMonth) params.end_month = endMonth
      return params
    },
    syncSuccessMessage: '港股通每月成交统计数据同步完成',
  })

  // 自定义同步确认（月度参数，不用标准的 date 弹窗）
  const handleCustomSyncConfirm = async () => {
    const params: Record<string, unknown> = {}
    if (syncStartMonth) params.start_month = syncStartMonth
    if (syncEndMonth) params.end_month = syncEndMonth
    dp.setSyncDialogOpen(false)
    await dp.handleSyncDirect(params)
  }

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '日均买入均值',
        value: `${formatNumber(s.avg_day_buy_amt)}亿`,
        icon: DollarSign,
        iconColor: 'text-blue-500',
      },
      {
        label: '累计总买入',
        value: `${formatNumber(s.sum_total_buy_amt)}亿`,
        icon: TrendingUp,
        iconColor: 'text-green-500',
      },
      {
        label: '最大总买入',
        value: `${formatNumber(s.max_total_buy_amt)}亿`,
        icon: Activity,
        iconColor: 'text-orange-500',
      },
      {
        label: '最大总卖出',
        value: `${formatNumber(s.max_total_sell_amt)}亿`,
        icon: TrendingDown,
        iconColor: 'text-red-500',
      },
    ]
  }, [dp.statistics])

  // 表格列定义
  const columns: Column<GgtMonthlyData>[] = useMemo(() => [
    {
      key: 'month',
      header: '月度',
      accessor: (row) => row.month
    },
    {
      key: 'day_buy_amt',
      header: '日均买入(亿元)',
      accessor: (row) => formatNumber(row.day_buy_amt)
    },
    {
      key: 'day_buy_vol',
      header: '日均买入笔数(万笔)',
      accessor: (row) => formatNumber(row.day_buy_vol)
    },
    {
      key: 'day_sell_amt',
      header: '日均卖出(亿元)',
      accessor: (row) => formatNumber(row.day_sell_amt)
    },
    {
      key: 'day_sell_vol',
      header: '日均卖出笔数(万笔)',
      accessor: (row) => formatNumber(row.day_sell_vol)
    },
    {
      key: 'total_buy_amt',
      header: '总买入(亿元)',
      accessor: (row) => formatNumber(row.total_buy_amt)
    },
    {
      key: 'total_buy_vol',
      header: '总买入笔数(万笔)',
      accessor: (row) => formatNumber(row.total_buy_vol)
    },
    {
      key: 'total_sell_amt',
      header: '总卖出(亿元)',
      accessor: (row) => formatNumber(row.total_sell_amt)
    },
    {
      key: 'total_sell_vol',
      header: '总卖出笔数(万笔)',
      accessor: (row) => formatNumber(row.total_sell_vol)
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: GgtMonthlyData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">月度</span>
        <span className="font-medium">{item.month}</span>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div className="flex justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-400">日均买入</span>
          <span className="font-medium">{formatNumber(item.day_buy_amt)}亿</span>
        </div>
        <div className="flex justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-400">日均卖出</span>
          <span className="font-medium">{formatNumber(item.day_sell_amt)}亿</span>
        </div>
        <div className="flex justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-400">总买入</span>
          <span className="font-medium">{formatNumber(item.total_buy_amt)}亿</span>
        </div>
        <div className="flex justify-between">
          <span className="text-sm text-gray-600 dark:text-gray-400">总卖出</span>
          <span className="font-medium">{formatNumber(item.total_sell_amt)}亿</span>
        </div>
      </div>
    </div>
  ), [])

  // 准备图表数据
  const chartData = useMemo(() => {
    return dp.data.slice(0, 12).reverse().map(item => ({
      month: item.month,
      日均买入: item.day_buy_amt,
      日均卖出: item.day_sell_amt,
      总买入: item.total_buy_amt,
      总卖出: item.total_sell_amt
    }))
  }, [dp.data])

  return (
    <div className="space-y-6">
      <PageHeader
        title="港股通每月成交统计"
        description="港股通每月成交信息，数据从2014年开始"
        details={<>
          <div>接口：ggt_monthly</div>
          <a href="https://tushare.pro/document/2?doc_id=197" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="港股通每月成交"
            />
          </div>
        }
      />

      <StatisticsCards items={statsCards} />

      {/* 趋势图表 */}
      {chartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>港股通每月成交趋势</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[400px] w-full overflow-x-auto">
              <div style={{ minWidth: '600px', height: '100%' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 40 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="month"
                      angle={-45}
                      textAnchor="end"
                      height={60}
                    />
                    <YAxis label={{ value: '金额(亿元)', angle: -90, position: 'insideLeft' }} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="日均买入" stroke="#3b82f6" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="日均卖出" stroke="#ef4444" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="总买入" stroke="#10b981" strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="总卖出" stroke="#f59e0b" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
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
            <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="start-month">开始月度</Label>
                <Input
                  id="start-month"
                  type="month"
                  value={startMonth}
                  onChange={(e) => setStartMonth(e.target.value)}
                  placeholder="YYYY-MM"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="end-month">结束月度</Label>
                <Input
                  id="end-month"
                  type="month"
                  value={endMonth}
                  onChange={(e) => setEndMonth(e.target.value)}
                  placeholder="YYYY-MM"
                />
              </div>
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <Button
                variant="outline"
                onClick={dp.handleQuery}
                disabled={dp.isLoading}
                className="flex-1 sm:flex-initial"
              >
                <RefreshCw className={`h-4 w-4 mr-1 ${dp.isLoading ? 'animate-spin' : ''}`} />
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
            mobileCard={mobileCard}
            pagination={{
              page: dp.page,
              pageSize: dp.pageSize,
              total: dp.total,
              onPageChange: dp.handlePageChange,
            }}
          />
        </CardContent>
      </Card>

      {/* 同步弹窗（自定义月度输入） */}
      <SyncDialog
        open={dp.syncDialogOpen}
        onOpenChange={dp.setSyncDialogOpen}
        onConfirm={handleCustomSyncConfirm}
        title="同步数据"
        description="选择同步月度范围（留空则同步最新月度数据）。"
        disabled={dp.syncing}
      >
        <div className="py-4 space-y-4">
          <div className="space-y-2">
            <Label htmlFor="sync-start-month">开始月度（可选）</Label>
            <Input
              id="sync-start-month"
              type="month"
              value={syncStartMonth}
              onChange={(e) => setSyncStartMonth(e.target.value)}
              placeholder="YYYY-MM"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="sync-end-month">结束月度（可选）</Label>
            <Input
              id="sync-end-month"
              type="month"
              value={syncEndMonth}
              onChange={(e) => setSyncEndMonth(e.target.value)}
              placeholder="YYYY-MM"
            />
          </div>
        </div>
      </SyncDialog>
    </div>
  )
}
