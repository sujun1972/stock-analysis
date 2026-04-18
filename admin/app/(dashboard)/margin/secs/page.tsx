'use client'

import { useState, useEffect, useMemo } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useDataPage } from '@/hooks/useDataPage'
import { marginSecsApi } from '@/lib/api'
import type { MarginSecsItem, MarginSecsStatistics } from '@/lib/api/margin-secs'
import { axiosInstance } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { formatStockCode } from '@/lib/utils'
import { useSystemConfig } from '@/contexts'
import { RefreshCw, BarChart3, TrendingUp, Building2, CalendarDays } from 'lucide-react'
import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from 'recharts'

// 交易所常量
const EXCHANGES = [
  { value: 'ALL', label: '全部' },
  { value: 'SSE', label: '上交所' },
  { value: 'SZSE', label: '深交所' },
  { value: 'BSE', label: '北交所' },
]

const EXCHANGE_LABEL: Record<string, string> = {
  SSE: '上交所',
  SZSE: '深交所',
  BSE: '北交所',
}

const EXCHANGE_COLORS: Record<string, string> = {
  SSE: '#8884d8',
  SZSE: '#82ca9d',
  BSE: '#ffc658',
}

export default function MarginSecsPage() {
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [exchange, setExchange] = useState('ALL')
  const [exchangeDistribution, setExchangeDistribution] = useState<any[]>([])

  const { config } = useSystemConfig()

  const isStock = (tsCode: string) => {
    const code = tsCode.split('.')[0]
    return !code.startsWith('5') && !code.startsWith('1') && !code.startsWith('821')
  }

  const openStockAnalysis = (tsCode: string) => {
    if (!isStock(tsCode)) return
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(tsCode)), '_blank')
  }

  const dp = useDataPage<MarginSecsItem, MarginSecsStatistics>({
    apiCall: (params) => marginSecsApi.getMarginSecs(params),
    syncFn: () => marginSecsApi.syncMarginSecsAsync(),
    taskName: ['extended.sync_margin_secs', 'tasks.sync_margin_secs_full_history'],
    bulkOps: {
      tableKey: 'margin_secs',
      syncFn: (params) => axiosInstance.post('/api/margin-secs/sync-full-history', null, { params }),
      taskName: 'tasks.sync_margin_secs_full_history',
    },
    paginationMode: 'page',
    pageSize: 100,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      if (tsCode) params.ts_code = tsCode
      if (exchange && exchange !== 'ALL') params.exchange = exchange
      return params
    },
    onBackfillDate: (dateStr) => setTradeDate(new Date(dateStr + 'T00:00:00')),
    syncSuccessMessage: '融资融券标的数据已更新',
  })

  // 加载交易所分布图表（独立，不阻断主流程）
  const loadExchangeDistribution = async () => {
    try {
      const response = await marginSecsApi.getLatestMarginSecs()
      if (response.code === 200 && response.data) {
        setExchangeDistribution(response.data.statistics.exchange_distribution || [])
      }
    } catch {
      // 图表加载失败不阻断主流程
    }
  }

  useEffect(() => {
    loadExchangeDistribution().catch(() => {})
  }, [])

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      { label: '标的数量', value: `${s.unique_stocks ?? 0} 只`, subValue: '当日不重复标的数', icon: BarChart3, iconColor: 'text-blue-600' },
      { label: '总记录数', value: (s.total_count ?? 0).toLocaleString(), subValue: '当前筛选范围内', icon: TrendingUp, iconColor: 'text-orange-600' },
      { label: '交易所数', value: `${s.exchange_count ?? 0} 个`, subValue: '涵盖交易所数量', icon: Building2, iconColor: 'text-green-600' },
      { label: '数据天数', value: `${s.trading_days ?? 0} 天`, subValue: '数据覆盖交易日数', icon: CalendarDays, iconColor: 'text-purple-600' },
    ]
  }, [dp.statistics])

  const columns: Column<MarginSecsItem>[] = [
    {
      key: 'name',
      header: '标的',
      accessor: (row) => (
        <span
          className={`whitespace-nowrap${isStock(row.ts_code) ? ' cursor-pointer hover:underline' : ''}`}
          onClick={() => isStock(row.ts_code) && openStockAnalysis(row.ts_code)}
        >
          {row.name || '-'}[{formatStockCode(row.ts_code)}]
        </span>
      ),
      width: 180,
      cellClassName: 'whitespace-nowrap',
    },
    {
      key: 'exchange',
      header: '交易所',
      accessor: (row) => EXCHANGE_LABEL[row.exchange] || row.exchange,
      width: 90,
      cellClassName: 'text-center',
    },
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => row.trade_date,
      width: 120,
      cellClassName: 'whitespace-nowrap text-center',
    },
  ]

  const mobileCard = (item: MarginSecsItem) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start">
        <div>
          <div
            className={`font-semibold text-base${isStock(item.ts_code) ? ' cursor-pointer hover:underline' : ''}`}
            onClick={() => isStock(item.ts_code) && openStockAnalysis(item.ts_code)}
          >
            {item.name || '-'}
          </div>
          <div className="text-sm text-gray-500">{item.ts_code}</div>
        </div>
        <div className="text-right">
          <div className="text-sm font-medium">{EXCHANGE_LABEL[item.exchange] || item.exchange}</div>
          <div className="text-xs text-gray-500 mt-0.5">{item.trade_date}</div>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="融资融券标的"
        description="获取沪深京三大交易所融资融券标的（包括ETF），每天盘前更新"
        details={<>
          <div>接口：margin_secs</div>
          <a href="https://tushare.pro/document/2?doc_id=326" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="融资融券标的"
            />
          </div>
        }
      />

      <SyncDialog
        open={dp.syncDialogOpen}
        onOpenChange={dp.setSyncDialogOpen}
        onConfirm={dp.handleSyncConfirm}
        title="同步融资融券标的"
        description="将从 Tushare 增量同步最新融资融券标的数据，无需选择日期。"
        disabled={dp.syncing}
      />

      <StatisticsCards items={statsCards} />

      {/* 交易所分布图表 */}
      {exchangeDistribution.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>最新交易日标的交易所分布</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[260px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={exchangeDistribution}
                    dataKey="count"
                    nameKey="exchange"
                    cx="50%"
                    cy="50%"
                    outerRadius={90}
                    label={(entry: any) =>
                      `${EXCHANGE_LABEL[entry.exchange] || entry.exchange}: ${entry.count}`
                    }
                  >
                    {exchangeDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={EXCHANGE_COLORS[entry.exchange] || '#999999'} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value: any) => `${value} 只`} />
                  <Legend
                    formatter={(value) => EXCHANGE_LABEL[value] || value}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 筛选区域 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            数据查询
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="w-full sm:w-48">
              <label className="text-sm font-medium mb-1 block">标的代码</label>
              <Input
                placeholder="如 510050 或 510050.SH"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="w-full sm:w-36">
              <label className="text-sm font-medium mb-1 block">交易所</label>
              <Select value={exchange} onValueChange={setExchange}>
                <SelectTrigger>
                  <SelectValue placeholder="全部" />
                </SelectTrigger>
                <SelectContent>
                  {EXCHANGES.map((ex) => (
                    <SelectItem key={ex.value} value={ex.value}>
                      {ex.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
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
            emptyMessage="暂无融资融券标的数据"
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
