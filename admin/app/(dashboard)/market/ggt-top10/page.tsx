'use client'

import { useState, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useDataPage } from '@/hooks/useDataPage'
import { ggtTop10Api, type GgtTop10Data, type GgtTop10Statistics } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { RefreshCw, TrendingUp, TrendingDown, Activity, DollarSign } from 'lucide-react'

// ============== 页面组件 ==============

export default function GgtTop10Page() {
  // 查询筛选状态
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [marketType, setMarketType] = useState<string>('ALL')

  const dp = useDataPage<GgtTop10Data, GgtTop10Statistics>({
    apiCall: (params) => ggtTop10Api.getGgtTop10(params),
    statisticsCall: (params) => ggtTop10Api.getStatistics(params),
    syncFn: (params) => ggtTop10Api.syncAsync(params),
    taskName: 'tasks.sync_ggt_top10',
    bulkOps: {
      tableKey: 'ggt_top10',
      syncFn: (params) => ggtTop10Api.syncFullHistory(params),
      taskName: 'tasks.sync_ggt_top10_full_history',
    },
    paginationMode: 'offset',
    pageSize: 30,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (marketType && marketType !== 'ALL') params.market_type = marketType
      return params
    },
    syncSuccessMessage: '港股通十大成交股数据同步完成',
  })

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '平均成交金额',
        value: `${s.avg_amount_yi.toFixed(2)}`,
        subValue: '亿元',
        icon: DollarSign,
        iconColor: 'text-blue-600',
      },
      {
        label: '平均净成交金额',
        value: <span className={s.avg_net_amount_yi >= 0 ? 'text-red-600' : 'text-green-600'}>{s.avg_net_amount_yi >= 0 ? '+' : ''}{s.avg_net_amount_yi.toFixed(2)}</span>,
        subValue: '亿元',
        icon: TrendingUp,
        iconColor: 'text-orange-600',
      },
      {
        label: '最大成交金额',
        value: `${s.max_amount_yi.toFixed(2)}`,
        subValue: '亿元',
        icon: Activity,
        iconColor: 'text-green-600',
      },
      {
        label: '统计股票数',
        value: `${s.stock_count}`,
        subValue: `${s.trading_days} 个交易日`,
        icon: TrendingDown,
        iconColor: 'text-purple-600',
      },
    ]
  }, [dp.statistics])

  // 表格列定义
  const columns: Column<GgtTop10Data>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => row.trade_date
    },
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'name',
      header: '股票名称',
      accessor: (row) => row.name
    },
    {
      key: 'market_type',
      header: (
        <>
          <span className="sm:hidden">市</span>
          <span className="hidden sm:inline">市场类型</span>
        </>
      ),
      accessor: (row) => row.market_type === '1' ? '沪市' : row.market_type === '3' ? '深市' : row.market_type
    },
    {
      key: 'rank',
      header: '排名',
      accessor: (row) => row.rank
    },
    {
      key: 'close',
      header: '收盘价',
      accessor: (row) => row.close?.toFixed(2) || '-'
    },
    {
      key: 'change',
      header: '涨跌额',
      accessor: (row) => {
        const change = row.change
        if (change === null || change === undefined) return '-'
        const color = change >= 0 ? 'text-red-600' : 'text-green-600'
        return <span className={color}>{change >= 0 ? '+' : ''}{change.toFixed(2)}</span>
      }
    },
    {
      key: 'amount',
      header: (
        <>
          <span className="sm:hidden">成交额</span>
          <span className="hidden sm:inline">成交金额(万元)</span>
        </>
      ),
      accessor: (row) => (row.amount / 10000).toFixed(2)
    },
    {
      key: 'net_amount',
      header: (
        <>
          <span className="sm:hidden">净额</span>
          <span className="hidden sm:inline">净成交金额(万元)</span>
        </>
      ),
      accessor: (row) => {
        const netAmount = row.net_amount / 10000
        const color = netAmount >= 0 ? 'text-red-600' : 'text-green-600'
        return <span className={color}>{netAmount >= 0 ? '+' : ''}{netAmount.toFixed(2)}</span>
      }
    },
    {
      key: 'buy',
      header: (
        <>
          <span className="sm:hidden">买</span>
          <span className="hidden sm:inline">买入金额(万元)</span>
        </>
      ),
      accessor: (row) => (row.buy / 10000).toFixed(2)
    },
    {
      key: 'sell',
      header: (
        <>
          <span className="sm:hidden">卖</span>
          <span className="hidden sm:inline">卖出金额(万元)</span>
        </>
      ),
      accessor: (row) => (row.sell / 10000).toFixed(2)
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: GgtTop10Data) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <div>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{item.ts_code}</span>
          <span className="ml-2 text-xs text-gray-500">{item.name}</span>
        </div>
        <span className="text-xs px-2 py-1 rounded bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200">
          排名 {item.rank}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">交易日期</span>
          <span className="font-medium text-sm">{item.trade_date}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">市场类型</span>
          <span className="font-medium text-sm">
            {item.market_type === '1' ? '沪市' : item.market_type === '3' ? '深市' : item.market_type}
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">收盘价</span>
          <span className="font-medium text-sm">{item.close?.toFixed(2) || '-'}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">涨跌额</span>
          <span className={`font-medium text-sm ${(item.change ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
            {(item.change ?? 0) >= 0 ? '+' : ''}{item.change?.toFixed(2) || '-'}
          </span>
        </div>
        <div className="flex justify-between items-center col-span-2">
          <span className="text-sm text-gray-600 dark:text-gray-400">成交金额</span>
          <span className="font-medium text-sm">{(item.amount / 10000).toFixed(2)} 万元</span>
        </div>
        <div className="flex justify-between items-center col-span-2">
          <span className="text-sm text-gray-600 dark:text-gray-400">净成交金额</span>
          <span className={`font-medium text-sm ${(item.net_amount ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
            {(item.net_amount ?? 0) >= 0 ? '+' : ''}{(item.net_amount / 10000).toFixed(2)} 万元
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">买入</span>
          <span className="font-medium text-sm">{(item.buy / 10000).toFixed(2)} 万元</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">卖出</span>
          <span className="font-medium text-sm">{(item.sell / 10000).toFixed(2)} 万元</span>
        </div>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="港股通十大成交股"
        description="获取港股通每日成交数据，其中包括沪市、深市详细数据，每天18~20点之间完成当日更新"
        details={<>
          <div>接口：ggt_top10</div>
          <a href="https://tushare.pro/document/2?doc_id=49" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="港股通十大成交股"
            />
          </div>
        }
      />

      <StatisticsCards items={statsCards} />

      {/* 筛选和操作区域 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 items-end">
            <div className="space-y-2">
              <Label htmlFor="start-date">开始日期</Label>
              <DatePicker
                date={startDate}
                onDateChange={setStartDate}
                placeholder="选择开始日期"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="end-date">结束日期</Label>
              <DatePicker
                date={endDate}
                onDateChange={setEndDate}
                placeholder="选择结束日期"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ts-code">股票代码</Label>
              <Input
                id="ts-code"
                placeholder="如：600519.SH"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="market-type">市场类型</Label>
              <Select value={marketType} onValueChange={setMarketType}>
                <SelectTrigger>
                  <SelectValue placeholder="选择市场" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="1">沪市</SelectItem>
                  <SelectItem value="3">深市</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2">
              <Button onClick={dp.handleQuery} disabled={dp.isLoading} className="flex-1">
                查询
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
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
