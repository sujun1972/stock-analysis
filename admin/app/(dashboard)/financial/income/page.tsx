'use client'

import { useState, useMemo } from 'react'
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
import { incomeApi } from '@/lib/api'
import type { IncomeData, IncomeStatistics } from '@/lib/api/income-api'
import { toDateStr } from '@/lib/date-utils'
import { TrendingUp, TrendingDown, DollarSign, PieChart, RefreshCw } from 'lucide-react'

// ============== 工具函数 ==============

const formatAmount = (amount: number | null | undefined): string => {
  if (amount === null || amount === undefined) return '-'
  return amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ============== 页面组件 ==============

export default function IncomePage() {
  // 查询筛选状态
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [reportType, setReportType] = useState<string>('all')
  const [compType, setCompType] = useState<string>('all')

  const dp = useDataPage<IncomeData, IncomeStatistics>({
    apiCall: (params) => incomeApi.getData(params),
    statisticsCall: (params) => incomeApi.getStatistics(params),
    syncFn: () => incomeApi.syncAsync(),
    taskName: ['tasks.sync_income', 'tasks.sync_income_full_history'],
    bulkOps: {
      tableKey: 'income',
      syncFn: (params) => incomeApi.syncFullHistoryAsync(params),
      taskName: 'tasks.sync_income_full_history',
    },
    paginationMode: 'offset',
    pageSize: 30,

    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      if (tsCode) params.ts_code = tsCode
      if (reportType !== 'all') params.report_type = reportType
      if (compType !== 'all') params.comp_type = compType
      return params
    },
    syncSuccessMessage: '利润表数据同步完成',
  })

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '记录数',
        value: s.total_count.toLocaleString(),
        subValue: `股票数: ${s.stock_count}`,
        icon: PieChart,
        iconColor: 'text-muted-foreground',
      },
      {
        label: '平均营业收入',
        value: formatAmount(s.avg_revenue),
        subValue: '万元',
        icon: DollarSign,
        iconColor: 'text-muted-foreground',
      },
      {
        label: '平均净利润',
        value: <span className={(s.avg_net_income ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}>{formatAmount(s.avg_net_income)}</span>,
        subValue: '万元',
        icon: TrendingUp,
        iconColor: 'text-green-600',
      },
      {
        label: '平均每股收益',
        value: s.avg_eps.toFixed(4),
        subValue: '元/股',
        icon: TrendingDown,
        iconColor: 'text-muted-foreground',
      },
    ]
  }, [dp.statistics])

  // 表格列定义
  const columns: Column<IncomeData>[] = [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code,
      className: 'font-mono'
    },
    {
      key: 'ann_date',
      header: '公告日期',
      accessor: (row) => row.ann_date || '-'
    },
    {
      key: 'end_date',
      header: '报告期',
      accessor: (row) => row.end_date
    },
    {
      key: 'total_revenue',
      header: '营业收入（万元）',
      accessor: (row) => formatAmount(row.total_revenue),
      className: 'text-right'
    },
    {
      key: 'oper_cost',
      header: '营业成本（万元）',
      accessor: (row) => formatAmount(row.oper_cost),
      className: 'text-right hidden md:table-cell'
    },
    {
      key: 'n_income',
      header: '净利润（万元）',
      accessor: (row) => formatAmount(row.n_income),
      className: 'text-right'
    },
    {
      key: 'n_income_attr_p',
      header: '归母净利润（万元）',
      accessor: (row) => formatAmount(row.n_income_attr_p),
      className: 'text-right hidden lg:table-cell'
    },
    {
      key: 'basic_eps',
      header: '基本每股收益',
      accessor: (row) => row.basic_eps?.toFixed(4) || '-',
      className: 'text-right'
    },
    {
      key: 'report_type',
      header: '报告类型',
      accessor: (row) => {
        const types: Record<string, string> = {
          '1': '合并报表', '2': '单季合并', '3': '调整单季',
          '4': '调整合并', '5': '调整前合并', '6': '母公司',
          '7': '母公司单季', '8': '母公司调整单季', '9': '母公司调整',
          '10': '母公司调整前', '11': '调整前合并', '12': '母公司调整前'
        }
        return types[row.report_type] || row.report_type
      },
      className: 'hidden xl:table-cell'
    }
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="利润表"
        description="获取上市公司财务利润表数据"
        details={<>
          <div>接口：income</div>
          <a href="https://tushare.pro/document/2?doc_id=33" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="利润表"
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
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">股票代码</label>
              <Input placeholder="如：600000.SH" value={tsCode} onChange={(e) => setTsCode(e.target.value)} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">开始日期（报告期）</label>
              <DatePicker date={startDate} onDateChange={setStartDate} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">结束日期（报告期）</label>
              <DatePicker date={endDate} onDateChange={setEndDate} />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">报告类型</label>
              <Select value={reportType} onValueChange={setReportType}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部</SelectItem>
                  <SelectItem value="1">合并报表</SelectItem>
                  <SelectItem value="2">单季合并</SelectItem>
                  <SelectItem value="3">调整单季合并</SelectItem>
                  <SelectItem value="4">调整合并报表</SelectItem>
                  <SelectItem value="6">母公司报表</SelectItem>
                  <SelectItem value="7">母公司单季</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">公司类型</label>
              <Select value={compType} onValueChange={setCompType}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部</SelectItem>
                  <SelectItem value="1">一般工商业</SelectItem>
                  <SelectItem value="2">银行</SelectItem>
                  <SelectItem value="3">保险</SelectItem>
                  <SelectItem value="4">证券</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button onClick={dp.handleQuery} disabled={dp.isLoading}>
              {dp.isLoading ? '查询中...' : '查询'}
            </Button>
            <Button onClick={() => { setTsCode(''); setStartDate(undefined); setEndDate(undefined); setReportType('all'); setCompType('all') }} variant="ghost">
              重置
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
            pagination={{
              page: dp.page,
              pageSize: dp.pageSize,
              total: dp.total,
              onPageChange: dp.handlePageChange,
              onPageSizeChange: dp.handlePageSizeChange,
              pageSizeOptions: [10, 20, 30, 50, 100]
            }}
            mobileCard={(item) => (
              <div className="p-4 space-y-2">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-mono font-semibold">{item.ts_code}</div>
                    <div className="text-sm text-muted-foreground">报告期: {item.end_date}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-medium">EPS</div>
                    <div className="text-xs">{item.basic_eps?.toFixed(4) || '-'}</div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 pt-2 border-t">
                  <div>
                    <div className="text-xs text-muted-foreground">营业收入</div>
                    <div className="text-sm font-medium">{formatAmount(item.total_revenue)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">净利润</div>
                    <div className={`text-sm font-medium ${(item.n_income ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                      {formatAmount(item.n_income)}
                    </div>
                  </div>
                </div>
              </div>
            )}
          />
        </CardContent>
      </Card>

      {/* 同步弹窗 */}
      <SyncDialog
        open={dp.syncDialogOpen}
        onOpenChange={dp.setSyncDialogOpen}
        onConfirm={dp.handleSyncConfirm}
        title="同步利润表"
        description="将从 Tushare 增量同步最新利润表数据，无需选择日期。"
        disabled={dp.syncing}
      />
    </div>
  )
}
