'use client'

import { useState, useMemo } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useDataPage } from '@/hooks/useDataPage'
import { topInstApi, type TopInstItem, type TopInstStatistics } from '@/lib/api'
import { apiClient } from '@/lib/api-client'
import { toDateStr } from '@/lib/date-utils'
import { formatStockCode } from '@/lib/utils'
import { useSystemConfig } from '@/contexts'
import { TrendingUp, TrendingDown, BarChart3, ListFilter, RefreshCw, Building2 } from 'lucide-react'

// ============== 页面组件 ==============

export default function TopInstPage() {
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [side, setSide] = useState<string>('ALL')
  const { config } = useSystemConfig()

  const openStockAnalysis = (code: string) => {
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(code)), '_blank')
  }

  const dp = useDataPage<TopInstItem, TopInstStatistics>({
    apiCall: (params) => topInstApi.getTopInst(params),
    statisticsCall: (params) => topInstApi.getStatistics(params),
    syncFn: (params) => topInstApi.syncAsync(params),
    taskName: 'tasks.sync_top_inst',
    bulkOps: {
      tableKey: 'top_inst',
      syncFn: (params) => apiClient.post('/api/top-inst/sync-async', null, { params }),
      taskName: 'tasks.sync_top_inst',
    },
    paginationMode: 'page',
    pageSize: 100,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (side !== 'ALL') params.side = side
      return params
    },
    onBackfillDate: (dateStr) => setTradeDate(new Date(dateStr + 'T00:00:00')),
    syncSuccessMessage: '龙虎榜机构明细数据同步完成',
  })

  // Service 已将金额从元转为万元，÷10000 转为亿元显示
  const formatYi = (val: number | null | undefined) => {
    if (val === null || val === undefined) return '-'
    return (val / 10000).toFixed(2) + '亿'
  }

  const sideColor = (s: string) => s === '0' ? 'text-red-600' : 'text-green-600'

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '上榜营业部',
        value: s.exalter_count,
        subValue: `总记录: ${s.total_records}`,
        icon: Building2,
        iconColor: 'text-blue-600',
      },
      {
        label: '上榜股票数',
        value: s.stock_count,
        subValue: `交易天数: ${s.trading_days}`,
        icon: BarChart3,
        iconColor: 'text-purple-600',
      },
      {
        label: '累计净买入',
        value: <span className="text-red-600">{formatYi(s.total_net_buy)}</span>,
        subValue: `均值: ${formatYi(s.avg_net_buy)}`,
        icon: TrendingUp,
        iconColor: 'text-red-600',
      },
      {
        label: '最大净买入',
        value: <span className="text-red-600">+{formatYi(s.max_net_buy)}</span>,
        subValue: `累计净卖出: ${formatYi(Math.abs(s.total_net_sell))}`,
        icon: TrendingDown,
        iconColor: 'text-orange-600',
      },
    ]
  }, [dp.statistics])

  const columns: Column<TopInstItem>[] = [
    {
      key: 'ts_code',
      header: '股票',
      accessor: (row) => (
        <span
          className={`cursor-pointer hover:underline ${sideColor(row.side)}`}
          onClick={() => openStockAnalysis(row.ts_code)}
        >
          {row.name || '-'}[{formatStockCode(row.ts_code)}]
        </span>
      ),
      width: 160,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'exalter',
      header: '营业部名称',
      accessor: (row) => (
        <div className="truncate" title={row.exalter || ''}>
          {row.exalter || '-'}
        </div>
      ),
      width: 220
    },
    {
      key: 'side',
      header: '买卖',
      accessor: (row) => (
        <span className={row.side === '0' ? 'text-red-600 font-medium' : 'text-green-600 font-medium'}>
          {row.side === '0' ? '买入' : '卖出'}
        </span>
      ),
      width: 60,
      cellClassName: 'text-center whitespace-nowrap'
    },
    {
      key: 'buy',
      header: '买入额',
      accessor: (row) => <span className="text-red-600">{formatYi(row.buy)}</span>,
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'sell',
      header: '卖出额',
      accessor: (row) => <span className="text-green-600">{formatYi(row.sell)}</span>,
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'net_buy',
      header: '净成交额',
      accessor: (row) => {
        if (row.net_buy === null) return '-'
        return (
          <span className={row.net_buy >= 0 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'}>
            {row.net_buy >= 0 ? '+' : ''}{formatYi(row.net_buy)}
          </span>
        )
      },
      width: 120,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'buy_rate',
      header: '买入占比%',
      accessor: (row) => row.buy_rate !== null ? `${row.buy_rate.toFixed(2)}%` : '-',
      width: 100,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'sell_rate',
      header: '卖出占比%',
      accessor: (row) => row.sell_rate !== null ? `${row.sell_rate.toFixed(2)}%` : '-',
      width: 100,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'reason',
      header: '上榜理由',
      accessor: (row) => (
        <div className="truncate" title={row.reason || '-'}>
          {row.reason || '-'}
        </div>
      ),
      width: 200
    }
  ]

  const mobileCard = (item: TopInstItem) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div
            className={`font-semibold text-base cursor-pointer hover:underline ${sideColor(item.side)}`}
            onClick={() => openStockAnalysis(item.ts_code)}
          >
            {item.name || item.ts_code}[{formatStockCode(item.ts_code)}]
          </div>
          <div className="text-sm text-gray-500 truncate max-w-[200px] mt-0.5">{item.exalter}</div>
        </div>
        <div className="text-right">
          <div className={`font-semibold ${sideColor(item.side)}`}>
            {item.side === '0' ? '买入' : '卖出'}
          </div>
          {item.net_buy !== null && (
            <div className={`font-semibold text-sm ${sideColor(item.side)}`}>
              净: {item.net_buy >= 0 ? '+' : ''}{formatYi(item.net_buy)}
            </div>
          )}
        </div>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">买入额:</span>
          <span className="text-red-600">{formatYi(item.buy)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">卖出额:</span>
          <span className="text-green-600">{formatYi(item.sell)}</span>
        </div>
        {item.reason && (
          <div className="flex flex-col gap-1">
            <span className="text-gray-600">上榜理由:</span>
            <span className="text-xs break-all">{item.reason}</span>
          </div>
        )}
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="龙虎榜机构明细"
        description="龙虎榜机构成交明细"
        details={<>
          <div>接口：top_inst</div>
          <a href="https://tushare.pro/document/2?doc_id=107" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <div className="flex gap-2">
            <Button onClick={() => dp.handleSyncDirect({})} disabled={dp.syncing}>
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
              tableName="龙虎榜机构明细"
            />
          </div>
        }
      />

      <StatisticsCards items={statsCards} />

      {/* 筛选和操作区域 */}
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
              <label className="text-sm font-medium mb-1 block">交易日期</label>
              <DatePicker date={tradeDate} onDateChange={setTradeDate} />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">股票代码</label>
              <Input placeholder="如 000001 或 000001.SZ" value={tsCode} onChange={(e) => setTsCode(e.target.value)} />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">买卖类型</label>
              <Select value={side} onValueChange={setSide}>
                <SelectTrigger><SelectValue placeholder="全部" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="0">买入</SelectItem>
                  <SelectItem value="1">卖出</SelectItem>
                </SelectContent>
              </Select>
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
