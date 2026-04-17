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
import { balancesheetApi } from '@/lib/api/balancesheet-api'
import type { BalancesheetData, BalancesheetStatistics } from '@/lib/api/balancesheet-api'
import { toDateStr } from '@/lib/date-utils'
import { TrendingUp, TrendingDown, DollarSign, PieChart, RefreshCw } from 'lucide-react'

// ============== 工具函数 ==============

const formatAmount = (amount: number | null | undefined): string => {
  if (amount === null || amount === undefined) return '-'
  return amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ============== 页面组件 ==============

export default function BalancesheetPage() {
  // 查询筛选状态
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [reportType, setReportType] = useState<string>('all')
  const [compType, setCompType] = useState<string>('all')

  const dp = useDataPage<BalancesheetData, BalancesheetStatistics>({
    apiCall: (params) => balancesheetApi.getData(params),
    statisticsCall: (params) => balancesheetApi.getStatistics(params),
    syncFn: () => balancesheetApi.syncAsync(),
    taskName: ['tasks.sync_balancesheet', 'tasks.sync_balancesheet_full_history'],
    bulkOps: {
      tableKey: 'balancesheet',
      syncFn: (params) => balancesheetApi.syncFullHistoryAsync(params),
      taskName: 'tasks.sync_balancesheet_full_history',
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
    syncSuccessMessage: '资产负债表数据同步完成',
  })

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '记录数',
        value: (s.total_records || 0).toLocaleString(),
        subValue: `股票数: ${s.total_stocks || 0}`,
        icon: PieChart,
        iconColor: 'text-muted-foreground',
      },
      {
        label: '平均总资产',
        value: formatAmount(s.avg_total_assets),
        subValue: '万元',
        icon: DollarSign,
        iconColor: 'text-muted-foreground',
      },
      {
        label: '平均总负债',
        value: <span className="text-red-600">{formatAmount(s.avg_total_liab)}</span>,
        subValue: '万元',
        icon: TrendingDown,
        iconColor: 'text-red-600',
      },
      {
        label: '平均股东权益',
        value: <span className="text-green-600">{formatAmount(s.avg_equity)}</span>,
        subValue: '万元',
        icon: TrendingUp,
        iconColor: 'text-green-600',
      },
    ]
  }, [dp.statistics])

  // 表格列定义
  const columns: Column<BalancesheetData>[] = [
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
      key: 'total_assets',
      header: '总资产（万元）',
      accessor: (row) => formatAmount(row.total_assets),
      className: 'text-right'
    },
    {
      key: 'total_cur_assets',
      header: '流动资产（万元）',
      accessor: (row) => formatAmount(row.total_cur_assets),
      className: 'text-right hidden md:table-cell'
    },
    {
      key: 'total_liab',
      header: '总负债（万元）',
      accessor: (row) => formatAmount(row.total_liab),
      className: 'text-right'
    },
    {
      key: 'total_cur_liab',
      header: '流动负债（万元）',
      accessor: (row) => formatAmount(row.total_cur_liab),
      className: 'text-right hidden lg:table-cell'
    },
    {
      key: 'total_hldr_eqy_inc_min_int',
      header: '股东权益（万元）',
      accessor: (row) => formatAmount(row.total_hldr_eqy_inc_min_int),
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
        title="资产负债表"
        description="获取上市公司资产负债表"
        details={<>
          <div>接口：balancesheet</div>
          <a href="https://tushare.pro/document/2?doc_id=36" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="资产负债表"
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
                    <div className="text-sm font-medium">总资产</div>
                    <div className="text-xs">{formatAmount(item.total_assets)}</div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 pt-2 border-t">
                  <div>
                    <div className="text-xs text-muted-foreground">总负债</div>
                    <div className="text-sm font-medium text-red-600">{formatAmount(item.total_liab)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">股东权益</div>
                    <div className="text-sm font-medium text-green-600">
                      {formatAmount(item.total_hldr_eqy_inc_min_int)}
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
        title="同步资产负债表"
        description="将从 Tushare 增量同步最新资产负债表数据，无需选择日期。"
        disabled={dp.syncing}
      />
    </div>
  )
}
