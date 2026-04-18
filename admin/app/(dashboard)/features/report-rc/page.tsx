'use client'

import { useState, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { useDataPage } from '@/hooks/useDataPage'
import { reportRcApi, type ReportRcData, type ReportRcStatistics } from '@/lib/api'
import { axiosInstance } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useSystemConfig } from '@/contexts'
import { formatStockCode } from '@/lib/utils'
import { RefreshCw, TrendingUp, Building2, FileText, BarChart3, ListFilter } from 'lucide-react'

// ============== 工具函数 ==============

const formatDate = (dateStr: string) => {
  if (!dateStr || dateStr.length !== 8) return dateStr
  return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
}

// ============== 页面组件 ==============

export default function ReportRcPage() {
  // 查询筛选状态
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [orgName, setOrgName] = useState('')

  const { config } = useSystemConfig()

  const dp = useDataPage<ReportRcData, ReportRcStatistics>({
    apiCall: (params) => reportRcApi.getData(params),
    syncFn: (params) => reportRcApi.syncAsync(params),
    taskName: 'tasks.sync_report_rc',
    bulkOps: {
      tableKey: 'report_rc',
      syncFn: (params) => axiosInstance.post('/api/report-rc/sync-async', null, { params }),
      taskName: 'tasks.sync_report_rc',
    },
    paginationMode: 'page',
    pageSize: 100,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (orgName.trim()) params.org_name = orgName.trim()
      return params
    },
    backfillDateField: 'report_date',
    onBackfillDate: (dateStr) => {
      if (!tradeDate) setTradeDate(new Date(dateStr + 'T00:00:00'))
    },
    syncSuccessMessage: '卖方盈利预测数据同步完成',
  })

  const openStockAnalysis = useCallback((code: string) => {
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(code)), '_blank')
  }, [config])

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '研报数量',
        value: (s.total_count ?? 0).toLocaleString(),
        subValue: '条研报记录',
        icon: FileText,
        iconColor: 'text-blue-600',
      },
      {
        label: '覆盖股票',
        value: (s.stock_count ?? 0).toLocaleString(),
        subValue: '只股票',
        icon: TrendingUp,
        iconColor: 'text-orange-600',
      },
      {
        label: '参与机构',
        value: (s.org_count ?? 0).toLocaleString(),
        subValue: '家券商',
        icon: Building2,
        iconColor: 'text-green-600',
      },
      {
        label: '平均EPS',
        value: (s.avg_eps ?? 0).toFixed(2),
        subValue: '元/股',
        icon: BarChart3,
        iconColor: 'text-purple-600',
      },
    ]
  }, [dp.statistics])

  // 表格列定义
  const columns: Column<ReportRcData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票',
      accessor: (row) => (
        <span
          className="cursor-pointer hover:underline text-blue-600"
          onClick={() => openStockAnalysis(row.ts_code)}
        >
          {row.name || '-'}[{formatStockCode(row.ts_code)}]
        </span>
      ),
      width: 160,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'org_name',
      header: '机构',
      accessor: (row) => (
        <div className="truncate" title={row.org_name || ''}>
          {row.org_name || '-'}
        </div>
      ),
      width: 130
    },
    {
      key: 'quarter',
      header: '预测期',
      accessor: (row) => row.quarter,
      width: 80,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'eps',
      header: 'EPS(元)',
      accessor: (row) => row.eps !== null ? row.eps.toFixed(2) : '-',
      width: 85,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'pe',
      header: 'PE',
      accessor: (row) => row.pe !== null ? row.pe.toFixed(2) : '-',
      width: 75,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'roe',
      header: 'ROE(%)',
      accessor: (row) => row.roe !== null ? (row.roe * 100).toFixed(2) : '-',
      width: 85,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rating',
      header: '评级',
      accessor: (row) => (
        <span className={
          row.rating === '买入' || row.rating === '强烈推荐' ? 'text-red-600 font-medium' :
          row.rating === '增持' ? 'text-orange-500 font-medium' :
          row.rating === '卖出' || row.rating === '减持' ? 'text-green-600 font-medium' :
          ''
        }>
          {row.rating || '-'}
        </span>
      ),
      width: 80,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'max_price',
      header: '目标价(元)',
      accessor: (row) => row.max_price !== null ? row.max_price.toFixed(2) : '-',
      width: 100,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    }
  ], [openStockAnalysis])

  // 移动端卡片
  const mobileCard = useCallback((item: ReportRcData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div
            className="font-semibold text-base cursor-pointer hover:underline text-blue-600"
            onClick={() => openStockAnalysis(item.ts_code)}
          >
            {item.name || '-'}[{formatStockCode(item.ts_code)}]
          </div>
          <div className="text-sm text-gray-500">{item.org_name}</div>
        </div>
        <span className="text-xs text-gray-500">{formatDate(item.report_date)}</span>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">预测期</span>
          <span className="font-medium">{item.quarter}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">EPS</span>
          <span className="font-medium">{item.eps !== null ? `${item.eps.toFixed(2)}元` : '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">评级</span>
          <span className={`font-medium ${
            item.rating === '买入' || item.rating === '强烈推荐' ? 'text-red-600' :
            item.rating === '增持' ? 'text-orange-500' :
            item.rating === '卖出' || item.rating === '减持' ? 'text-green-600' : 'text-blue-600'
          }`}>{item.rating || '-'}</span>
        </div>
        {item.max_price !== null && (
          <div className="flex justify-between">
            <span className="text-gray-600">目标价</span>
            <span className="font-medium text-green-600">{item.max_price.toFixed(2)} 元</span>
          </div>
        )}
      </div>
    </div>
  ), [openStockAnalysis])

  return (
    <div className="space-y-6">
      <PageHeader
        title="卖方盈利预测数据"
        description="获取券商（卖方）每天研报的盈利预测数据，数据从2010年开始，每晚19~22点更新当日数据"
        details={<>
          <div>接口：report_rc</div>
          <a href="https://tushare.pro/document/2?doc_id=292" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="卖方盈利预测"
            />
          </div>
        }
      />

      <StatisticsCards items={statsCards} />

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
              <Label className="mb-1 block">研报日期</Label>
              <DatePicker date={tradeDate} onDateChange={setTradeDate} />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <Label className="mb-1 block">股票代码</Label>
              <Input
                placeholder="如 000001 或 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <Label className="mb-1 block">机构名称</Label>
              <Input
                placeholder="如: 安信证券"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
              />
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
            emptyMessage="暂无卖方盈利预测数据"
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
        title="同步卖方盈利预测数据"
        description="选择同步日期范围（留空则同步最新数据）。"
        disabled={dp.syncing}
        showDateRange
        startDate={dp.syncStartDate}
        onStartDateChange={dp.setSyncStartDate}
        endDate={dp.syncEndDate}
        onEndDateChange={dp.setSyncEndDate}
        startDateLabel="开始日期（可选）"
        endDateLabel="结束日期（可选）"
      />
    </div>
  )
}
