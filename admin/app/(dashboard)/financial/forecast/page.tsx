'use client'

import { useState, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { useDataPage } from '@/hooks/useDataPage'
import { forecastApi } from '@/lib/api'
import type { ForecastData, ForecastStatistics } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { RefreshCw, TrendingUp, Briefcase, TrendingDown, BarChart3 } from 'lucide-react'

// ============== 工具函数 ==============

const formatAmount = (amount: number | null | undefined) => {
  if (amount === null || amount === undefined) return '-'
  return `${amount.toLocaleString()} 万元`
}

const formatPercent = (value: number | null | undefined) => {
  if (value === null || value === undefined) return '-'
  return `${value.toFixed(2)}%`
}

const getTypeColor = (type: string) => {
  const positiveTypes = ['预增', '扭亏', '续盈', '略增']
  const negativeTypes = ['预减', '首亏', '续亏', '略减']

  if (positiveTypes.includes(type)) {
    return 'bg-red-100 text-red-700 dark:bg-red-900/20 dark:text-red-400'
  } else if (negativeTypes.includes(type)) {
    return 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400'
  }
  return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
}

// ============== 页面组件 ==============

export default function ForecastPage() {
  // 查询筛选状态
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [forecastType, setForecastType] = useState<string>('')
  const [period, setPeriod] = useState('')

  const dp = useDataPage<ForecastData, ForecastStatistics>({
    apiCall: (params) => forecastApi.getData(params),
    statisticsCall: (params) => forecastApi.getStatistics(params),
    syncFn: () => forecastApi.syncAsync(),
    taskName: ['tasks.sync_forecast', 'tasks.sync_forecast_full_history'],
    bulkOps: {
      tableKey: 'forecast',
      syncFn: (params) => forecastApi.syncFullHistoryAsync(params),
      taskName: 'tasks.sync_forecast_full_history',
    },
    paginationMode: 'offset',
    pageSize: 30,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      if (tsCode) params.ts_code = tsCode.trim()
      if (forecastType) params.type = forecastType
      if (period) params.period = period
      return params
    },
    syncSuccessMessage: '业绩预告数据同步完成',
  })

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '总记录数',
        value: s.total_count.toLocaleString(),
        icon: BarChart3,
        iconColor: 'text-blue-500',
      },
      {
        label: '涉及股票数',
        value: s.stock_count.toLocaleString(),
        icon: Briefcase,
        iconColor: 'text-green-500',
      },
      {
        label: '正面预告比例',
        value: `${s.positive_ratio.toFixed(1)}%`,
        subValue: `${s.positive_count} 条`,
        icon: TrendingUp,
        iconColor: 'text-red-500',
      },
      {
        label: '负面预告比例',
        value: `${s.negative_ratio.toFixed(1)}%`,
        subValue: `${s.negative_count} 条`,
        icon: TrendingDown,
        iconColor: 'text-green-500',
      },
    ]
  }, [dp.statistics])

  // 表格列定义
  const columns: Column<ForecastData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'ann_date',
      header: '公告日期',
      accessor: (row) => row.ann_date
    },
    {
      key: 'end_date',
      header: '报告期',
      accessor: (row) => row.end_date
    },
    {
      key: 'type',
      header: '预告类型',
      accessor: (row) => (
        <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getTypeColor(row.type)}`}>
          {row.type || '-'}
        </span>
      )
    },
    {
      key: 'p_change',
      header: '变动幅度 (%)',
      accessor: (row) => {
        if (row.p_change_min === null && row.p_change_max === null) return '-'
        if (row.p_change_min === row.p_change_max) return formatPercent(row.p_change_min)
        return `${formatPercent(row.p_change_min)} ~ ${formatPercent(row.p_change_max)}`
      },
      align: 'right'
    },
    {
      key: 'net_profit',
      header: '预告净利润',
      accessor: (row) => {
        if (row.net_profit_min === null && row.net_profit_max === null) return '-'
        if (row.net_profit_min === row.net_profit_max) return formatAmount(row.net_profit_min)
        return (
          <div className="text-right">
            <div>{formatAmount(row.net_profit_min)}</div>
            <div className="text-xs text-gray-500">~ {formatAmount(row.net_profit_max)}</div>
          </div>
        )
      },
      align: 'right'
    },
    {
      key: 'last_parent_net',
      header: '上年同期',
      accessor: (row) => formatAmount(row.last_parent_net),
      align: 'right'
    },
    {
      key: 'summary',
      header: '预告摘要',
      accessor: (row) => (
        <div className="max-w-xs truncate" title={row.summary || '-'}>
          {row.summary || '-'}
        </div>
      )
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: ForecastData) => (
    <div className="p-4 space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{item.ts_code}</span>
        <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${getTypeColor(item.type)}`}>
          {item.type || '-'}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">公告日期</span>
        <span className="font-medium">{item.ann_date}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">报告期</span>
        <span className="font-medium">{item.end_date}</span>
      </div>
      {(item.p_change_min !== null || item.p_change_max !== null) && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">变动幅度</span>
          <span className="font-medium">
            {item.p_change_min === item.p_change_max
              ? formatPercent(item.p_change_min)
              : `${formatPercent(item.p_change_min)} ~ ${formatPercent(item.p_change_max)}`
            }
          </span>
        </div>
      )}
      {(item.net_profit_min !== null || item.net_profit_max !== null) && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">预告净利润</span>
          <span className="font-medium text-blue-600">
            {item.net_profit_min === item.net_profit_max
              ? formatAmount(item.net_profit_min)
              : `${formatAmount(item.net_profit_min)} ~ ${formatAmount(item.net_profit_max)}`
            }
          </span>
        </div>
      )}
      {item.last_parent_net !== null && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">上年同期</span>
          <span className="font-medium">{formatAmount(item.last_parent_net)}</span>
        </div>
      )}
      {item.summary && (
        <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
          <span className="text-sm text-gray-600 dark:text-gray-400">预告摘要</span>
          <p className="text-sm mt-1 text-gray-700 dark:text-gray-300">{item.summary}</p>
        </div>
      )}
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="业绩预告"
        description="获取业绩预告数据"
        details={<>
          <div>接口：forecast</div>
          <a href="https://tushare.pro/document/2?doc_id=45" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="业绩预告"
            />
          </div>
        }
      />

      <StatisticsCards items={statsCards} />

      {/* 查询控件 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">开始日期</label>
              <DatePicker date={startDate} onDateChange={setStartDate} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">结束日期</label>
              <DatePicker date={endDate} onDateChange={setEndDate} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">股票代码</label>
              <Input placeholder="如: 600000.SH" value={tsCode} onChange={(e) => setTsCode(e.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">报告期</label>
              <Input placeholder="如: 2024-12-31" value={period} onChange={(e) => setPeriod(e.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">预告类型</label>
              <Select value={forecastType || 'ALL'} onValueChange={(value) => setForecastType(value === 'ALL' ? '' : value)}>
                <SelectTrigger><SelectValue placeholder="全部" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="预增">预增</SelectItem>
                  <SelectItem value="预减">预减</SelectItem>
                  <SelectItem value="扭亏">扭亏</SelectItem>
                  <SelectItem value="首亏">首亏</SelectItem>
                  <SelectItem value="续亏">续亏</SelectItem>
                  <SelectItem value="续盈">续盈</SelectItem>
                  <SelectItem value="略增">略增</SelectItem>
                  <SelectItem value="略减">略减</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-end">
              <Button onClick={dp.handleQuery} disabled={dp.isLoading} className="w-full">
                {dp.isLoading ? '查询中...' : '查询'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="pt-6">
          <DataTable
            columns={columns}
            data={dp.data}
            loading={dp.isLoading}
            emptyMessage="暂无业绩预告数据"
            pagination={{
              page: dp.page,
              pageSize: dp.pageSize,
              total: dp.total,
              onPageChange: dp.handlePageChange,
              onPageSizeChange: dp.handlePageSizeChange,
              pageSizeOptions: [10, 20, 30, 50, 100]
            }}
            mobileCard={mobileCard}
          />
        </CardContent>
      </Card>

      {/* 同步弹窗 */}
      <SyncDialog
        open={dp.syncDialogOpen}
        onOpenChange={dp.setSyncDialogOpen}
        onConfirm={dp.handleSyncConfirm}
        title="同步业绩预告"
        description="将从 Tushare 增量同步最新业绩预告数据，无需选择日期。"
        disabled={dp.syncing}
      />
    </div>
  )
}
