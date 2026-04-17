'use client'

import { useState, useMemo } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { useDataPage } from '@/hooks/useDataPage'
import { financialDataApi } from '@/lib/api/financial-data'
import type { FinaIndicatorData, FinaIndicatorStatistics } from '@/lib/api/financial-data'
import { toDateStr } from '@/lib/date-utils'
import { RefreshCw, TrendingUp, Percent, PieChart, Activity } from 'lucide-react'

// ============== 工具函数 ==============

const formatDate8 = (dateStr: string) => {
  if (!dateStr || dateStr.length !== 8) return dateStr
  return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
}

const formatNumber = (value: number | null | undefined, decimals: number = 2) => {
  if (value === null || value === undefined) return '-'
  return value.toFixed(decimals)
}

const formatPercent = (value: number | null | undefined, decimals: number = 2) => {
  if (value === null || value === undefined) return '-'
  return `${value.toFixed(decimals)}%`
}

// ============== 页面组件 ==============

export default function FinaIndicatorPage() {
  // 查询筛选状态
  const [tsCode, setTsCode] = useState('')
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [period, setPeriod] = useState<Date | undefined>(undefined)

  const dp = useDataPage<FinaIndicatorData, FinaIndicatorStatistics>({
    apiCall: (params) => financialDataApi.getFinaIndicator(params),
    syncFn: () => financialDataApi.syncFinaIndicatorAsync(),
    taskName: ['tasks.sync_fina_indicator', 'tasks.sync_fina_indicator_full_history'],
    bulkOps: {
      tableKey: 'fina_indicator',
      syncFn: (params) => financialDataApi.syncFinaIndicatorFullHistoryAsync(params),
      taskName: 'tasks.sync_fina_indicator_full_history',
    },
    paginationMode: 'offset',
    pageSize: 30,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tsCode) params.ts_code = tsCode
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      if (period) params.period = toDateStr(period)
      return params
    },
    syncSuccessMessage: '财务指标数据同步完成',
  })

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '平均EPS',
        value: `${formatNumber(s.avg_eps, 4)} 元`,
        subValue: '每股收益平均值',
        icon: Activity,
        iconColor: 'text-muted-foreground',
      },
      {
        label: '平均ROE',
        value: `${formatNumber(s.avg_roe)}%`,
        subValue: '净资产收益率平均值',
        icon: TrendingUp,
        iconColor: 'text-muted-foreground',
      },
      {
        label: '平均资产负债率',
        value: `${formatNumber(s.avg_debt_ratio)}%`,
        subValue: '负债占资产比例',
        icon: PieChart,
        iconColor: 'text-muted-foreground',
      },
      {
        label: '平均净利率',
        value: `${formatNumber(s.avg_netprofit_margin)}%`,
        subValue: '净利润占营收比例',
        icon: Percent,
        iconColor: 'text-muted-foreground',
      },
    ]
  }, [dp.statistics])

  // 表格列定义
  const columns: Column<FinaIndicatorData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'ann_date',
      header: '公告日期',
      accessor: (row) => formatDate8(row.ann_date)
    },
    {
      key: 'end_date',
      header: '报告期',
      accessor: (row) => formatDate8(row.end_date)
    },
    {
      key: 'eps',
      header: 'EPS(元)',
      accessor: (row) => formatNumber(row.eps, 4)
    },
    {
      key: 'roe',
      header: 'ROE(%)',
      accessor: (row) => (
        <span className={row.roe && row.roe >= 15 ? 'text-red-600 font-semibold' : ''}>
          {formatNumber(row.roe)}
        </span>
      )
    },
    {
      key: 'debt_to_assets',
      header: '资产负债率(%)',
      accessor: (row) => (
        <span className={row.debt_to_assets && row.debt_to_assets >= 70 ? 'text-orange-600' : ''}>
          {formatNumber(row.debt_to_assets)}
        </span>
      )
    },
    {
      key: 'grossprofit_margin',
      header: '毛利率(%)',
      accessor: (row) => formatNumber(row.grossprofit_margin)
    },
    {
      key: 'netprofit_margin',
      header: '净利率(%)',
      accessor: (row) => formatNumber(row.netprofit_margin)
    },
    {
      key: 'roa',
      header: 'ROA(%)',
      accessor: (row) => formatNumber(row.roa)
    },
    {
      key: 'current_ratio',
      header: '流动比率',
      accessor: (row) => formatNumber(row.current_ratio)
    },
    {
      key: 'basic_eps_yoy',
      header: 'EPS增长率(%)',
      accessor: (row) => (
        <span className={row.basic_eps_yoy && row.basic_eps_yoy >= 0 ? 'text-red-600' : 'text-green-600'}>
          {formatNumber(row.basic_eps_yoy)}
        </span>
      )
    }
  ], [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="财务指标"
        description="获取上市公司财务指标数据，为避免服务器压力，现阶段每次请求最多返回100条记录，可通过设置日期多次请求获取更多数据。"
        details={<>
          <div>接口：fina_indicator</div>
          <a href="https://tushare.pro/document/2?doc_id=79" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="财务指标"
            />
          </div>
        }
      />

      <StatisticsCards items={statsCards} />

      {/* 查询表单 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label htmlFor="ts_code">股票代码</Label>
              <Input id="ts_code" placeholder="如：600000.SH" value={tsCode} onChange={(e) => setTsCode(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>开始日期</Label>
              <DatePicker date={startDate} onDateChange={setStartDate} placeholder="选择开始日期" />
            </div>
            <div className="space-y-2">
              <Label>结束日期</Label>
              <DatePicker date={endDate} onDateChange={setEndDate} placeholder="选择结束日期" />
            </div>
            <div className="space-y-2">
              <Label>报告期</Label>
              <DatePicker date={period} onDateChange={setPeriod} placeholder="选择报告期" />
            </div>
          </div>
          <div className="flex gap-2">
            <Button onClick={dp.handleQuery} disabled={dp.isLoading}>
              <RefreshCw className={`h-4 w-4 mr-1 ${dp.isLoading ? 'animate-spin' : ''}`} />
              {dp.isLoading ? '查询中...' : '查询'}
            </Button>
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
            emptyMessage="暂无财务指标数据"
            mobileCard={(item) => (
              <div className="p-4 space-y-3">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-semibold text-base">{item.ts_code}</div>
                    <div className="text-sm text-muted-foreground">
                      报告期: {formatDate8(item.end_date)}
                    </div>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {formatDate8(item.ann_date)}
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">EPS: </span>
                    <span className="font-medium">{formatNumber(item.eps, 4)}元</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">ROE: </span>
                    <span className={`font-medium ${item.roe && item.roe >= 15 ? 'text-red-600' : ''}`}>
                      {formatPercent(item.roe)}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">资产负债率: </span>
                    <span className={`font-medium ${item.debt_to_assets && item.debt_to_assets >= 70 ? 'text-orange-600' : ''}`}>
                      {formatPercent(item.debt_to_assets)}
                    </span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">毛利率: </span>
                    <span className="font-medium">{formatPercent(item.grossprofit_margin)}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">净利率: </span>
                    <span className="font-medium">{formatPercent(item.netprofit_margin)}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">ROA: </span>
                    <span className="font-medium">{formatPercent(item.roa)}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">流动比率: </span>
                    <span className="font-medium">{formatNumber(item.current_ratio)}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">EPS增长: </span>
                    <span className={`font-medium ${item.basic_eps_yoy && item.basic_eps_yoy >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                      {formatPercent(item.basic_eps_yoy)}
                    </span>
                  </div>
                </div>
              </div>
            )}
            pagination={{
              page: dp.page,
              pageSize: dp.pageSize,
              total: dp.total,
              onPageChange: dp.handlePageChange,
              onPageSizeChange: dp.handlePageSizeChange,
              pageSizeOptions: [10, 20, 30, 50, 100]
            }}
          />
        </CardContent>
      </Card>

      {/* 同步弹窗 */}
      <SyncDialog
        open={dp.syncDialogOpen}
        onOpenChange={dp.setSyncDialogOpen}
        onConfirm={dp.handleSyncConfirm}
        title="同步财务指标"
        description="将从 Tushare 增量同步最新财务指标数据，无需选择日期。"
        disabled={dp.syncing}
      />
    </div>
  )
}
