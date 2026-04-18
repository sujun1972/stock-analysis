'use client'

import { useState, useEffect, useMemo } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useDataPage } from '@/hooks/useDataPage'
import { marginApi } from '@/lib/api'
import { axiosInstance } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { formatStockCode } from '@/lib/utils'
import { useSystemConfig } from '@/contexts'
import { RefreshCw, TrendingUp, BarChart3, DollarSign, ListFilter } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

// 数据类型定义
interface MarginDetailData {
  trade_date: string
  ts_code: string
  name: string
  rzye: number | null
  rqye: number | null
  rzmre: number | null
  rqyl: number | null
  rzche: number | null
  rqchl: number | null
  rqmcl: number | null
  rzrqye: number | null
}

interface Statistics {
  avg_rzrqye: number
  total_rzrqye: number
  max_rzrqye: number
  stock_count: number
}

export default function MarginDetailPage() {
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [topStocks, setTopStocks] = useState<any[]>([])

  const { config } = useSystemConfig()

  const isStock = (tsCode: string) => {
    const code = tsCode.split('.')[0]
    return !code.startsWith('5') && !code.startsWith('1')
  }

  const openStockAnalysis = (code: string) => {
    if (!isStock(code)) return
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(code)), '_blank')
  }

  const dp = useDataPage<MarginDetailData, Statistics>({
    apiCall: (params) => marginApi.getMarginDetail(params),
    syncFn: (params) => marginApi.syncMarginDetailAsync(params),
    taskName: 'tasks.sync_margin_detail',
    bulkOps: {
      tableKey: 'margin_detail',
      syncFn: (params) => axiosInstance.post('/api/margin-detail/sync-async', null, { params }),
      taskName: 'tasks.sync_margin_detail',
    },
    paginationMode: 'page',
    pageSize: 100,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tsCode) params.ts_code = tsCode
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      return params
    },
    onBackfillDate: (dateStr) => setTradeDate(new Date(dateStr + 'T00:00:00')),
    syncSuccessMessage: '融资融券交易明细数据已更新',
  })

  // 加载 TOP 股票（图表，独立不阻断主流程）
  const loadTopStocks = async () => {
    try {
      const response = await marginApi.getMarginDetailTopStocks({ limit: 20 })
      if (response.code === 200 && response.data) {
        setTopStocks(response.data)
      }
    } catch {
      // 图表加载失败不阻断主流程
    }
  }

  useEffect(() => {
    loadTopStocks().catch(() => {})
  }, [])

  const toYi = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '-'
    return (value / 100000000).toFixed(2) + '亿'
  }

  const formatDate = (dateStr: string) => {
    if (!dateStr || dateStr.length !== 8) return dateStr
    return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
  }

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      { label: '统计股票数', value: `${s.stock_count ?? 0} 只`, icon: BarChart3, iconColor: 'text-blue-600' },
      { label: '平均融资融券余额', value: toYi(s.avg_rzrqye), subValue: '当日各股均值', icon: TrendingUp, iconColor: 'text-orange-600' },
      { label: '最大融资融券余额', value: <span className="text-red-600">{toYi(s.max_rzrqye)}</span>, subValue: '单股最大值', icon: TrendingUp, iconColor: 'text-green-600' },
      { label: '合计融资融券余额', value: toYi(s.total_rzrqye), subValue: '当日全市场合计', icon: DollarSign, iconColor: 'text-purple-600' },
    ]
  }, [dp.statistics])

  const columns: Column<MarginDetailData>[] = useMemo(() => [
    {
      key: 'name',
      header: '股票',
      accessor: (row) => (
        <span
          className={`whitespace-nowrap${isStock(row.ts_code) ? ' cursor-pointer hover:underline' : ''}`}
          onClick={() => isStock(row.ts_code) && openStockAnalysis(row.ts_code)}
        >
          {row.name || '-'}[{formatStockCode(row.ts_code)}]
        </span>
      ),
      width: 160,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'rzrqye',
      header: '融资融券余额',
      accessor: (row) => toYi(row.rzrqye),
      width: 130,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rzye',
      header: '融资余额',
      accessor: (row) => toYi(row.rzye),
      hideOnMobile: true,
      width: 120,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rqye',
      header: '融券余额',
      accessor: (row) => toYi(row.rqye),
      hideOnMobile: true,
      width: 120,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rzmre',
      header: '融资买入',
      accessor: (row) => toYi(row.rzmre),
      hideOnMobile: true,
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rzche',
      header: '融资偿还',
      accessor: (row) => toYi(row.rzche),
      hideOnMobile: true,
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rqmcl',
      header: '融券卖出量',
      accessor: (row) => row.rqmcl !== null && row.rqmcl !== undefined ? row.rqmcl.toFixed(0) + '股' : '-',
      hideOnMobile: true,
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
  ], [config])

  const mobileCard = (item: MarginDetailData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div
            className={`font-semibold text-base${isStock(item.ts_code) ? ' cursor-pointer hover:underline' : ''}`}
            onClick={() => isStock(item.ts_code) && openStockAnalysis(item.ts_code)}
          >
            {item.name || '-'}
          </div>
          <div className="text-sm text-gray-500">{item.ts_code}</div>
        </div>
        <span className="text-xs text-gray-500">{formatDate(item.trade_date)}</span>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">融资融券余额</span>
          <span className="font-medium">{toYi(item.rzrqye)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">融资余额</span>
          <span className="font-medium">{toYi(item.rzye)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">融券余额</span>
          <span className="font-medium">{toYi(item.rqye)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">融资买入</span>
          <span className="font-medium">{toYi(item.rzmre)}</span>
        </div>
      </div>
    </div>
  )

  // 图表数据
  const chartData = useMemo(() => topStocks.slice(0, 20).map((stock) => ({
    name: stock.name || stock.ts_code,
    融资融券余额: Number((stock.rzrqye / 100000000).toFixed(2)),
    融资余额: Number((stock.rzye / 100000000).toFixed(2)),
    融券余额: Number((stock.rqye / 100000000).toFixed(2)),
  })), [topStocks])

  return (
    <div className="space-y-6">
      <PageHeader
        title="融资融券交易明细"
        description="获取沪深两市每日融资融券明细"
        details={<>
          <div>接口：margin_detail</div>
          <a href="https://tushare.pro/document/2?doc_id=59" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="融资融券交易明细"
            />
          </div>
        }
      />

      <SyncDialog
        open={dp.syncDialogOpen}
        onOpenChange={dp.setSyncDialogOpen}
        onConfirm={dp.handleSyncConfirm}
        title="同步融资融券交易明细"
        description="选择同步日期范围（留空则同步最新交易日数据）。"
        disabled={dp.syncing}
        showDateRange
        startDate={dp.syncStartDate}
        onStartDateChange={dp.setSyncStartDate}
        endDate={dp.syncEndDate}
        onEndDateChange={dp.setSyncEndDate}
      />

      <StatisticsCards items={statsCards} />

      {/* TOP 20 图表 */}
      {chartData.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              融资融券余额 TOP 20
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <div style={{ minWidth: '600px' }}>
                <ResponsiveContainer width="100%" height={360}>
                  <BarChart data={chartData} margin={{ top: 10, right: 20, left: 10, bottom: 60 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis
                      dataKey="name"
                      angle={-45}
                      textAnchor="end"
                      height={80}
                      interval={0}
                      tick={{ fontSize: 11 }}
                    />
                    <YAxis tickFormatter={(v) => v.toFixed(1)} />
                    <Tooltip formatter={(v) => typeof v === 'number' ? v.toFixed(2) + '亿' : '-'} />
                    <Legend />
                    <Bar dataKey="融资融券余额" fill="#8884d8" />
                    <Bar dataKey="融资余额" fill="#82ca9d" />
                    <Bar dataKey="融券余额" fill="#ffc658" />
                  </BarChart>
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
            <div className="w-full sm:w-48">
              <label className="text-sm font-medium mb-1 block">股票代码</label>
              <Input
                placeholder="如 000001 或 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">交易日期</label>
              <DatePicker date={tradeDate} onDateChange={setTradeDate} />
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
            emptyMessage="暂无融资融券交易明细数据"
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
    </div>
  )
}
