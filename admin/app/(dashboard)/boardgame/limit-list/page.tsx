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
import { limitListApi, type LimitListData, type LimitListStatistics } from '@/lib/api'
import { axiosInstance } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { formatStockCode } from '@/lib/utils'
import { useSystemConfig } from '@/contexts'
import { TrendingUp, TrendingDown, Zap, BarChart3, ListFilter, RefreshCw, Layers } from 'lucide-react'

// ============== 页面组件 ==============

export default function LimitListPage() {
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [limitType, setLimitType] = useState<string>('ALL')
  const { config } = useSystemConfig()

  const openStockAnalysis = (code: string) => {
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(code)), '_blank')
  }

  const dp = useDataPage<LimitListData, LimitListStatistics>({
    apiCall: (params) => limitListApi.getData(params),
    syncFn: (params) => limitListApi.syncAsync(params),
    taskName: 'tasks.sync_limit_list',
    bulkOps: {
      tableKey: 'limit_list',
      syncFn: (params) => axiosInstance.post('/api/limit-list/sync-async', null, { params }),
      taskName: 'tasks.sync_limit_list',
    },
    paginationMode: 'page',
    pageSize: 50,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (limitType !== 'ALL') params.limit_type = limitType
      return params
    },
    onBackfillDate: (dateStr) => setTradeDate(new Date(dateStr + 'T00:00:00')),
    syncSuccessMessage: '涨跌停列表数据同步完成',
  })

  // 涨跌停类型色彩
  const limitTypeColor = (type: string | null) => {
    if (type === 'U') return 'text-red-600'
    if (type === 'D') return 'text-green-600'
    if (type === 'Z') return 'text-orange-500'
    return ''
  }

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '总记录数',
        value: s.total_count.toLocaleString(),
        subValue: `交易天数: ${s.trade_days}`,
        icon: BarChart3,
        iconColor: 'text-blue-600',
      },
      {
        label: '涉及股票',
        value: s.stock_count.toLocaleString(),
        subValue: `均涨跌幅: ${s.avg_pct_chg?.toFixed(2)}%`,
        icon: Layers,
        iconColor: 'text-purple-600',
      },
      {
        label: '最大连板数',
        value: <span className="text-red-600">{s.max_limit_times}</span>,
        subValue: `均连板: ${s.avg_limit_times?.toFixed(1)}`,
        icon: TrendingUp,
        iconColor: 'text-red-600',
      },
      {
        label: '最大涨跌幅',
        value: <span className="text-red-600">+{s.max_pct_chg?.toFixed(2)}%</span>,
        subValue: `本页条数: ${dp.data.length}`,
        icon: TrendingDown,
        iconColor: 'text-orange-600',
      },
    ]
  }, [dp.statistics, dp.data.length])

  const columns: Column<LimitListData>[] = [
    {
      key: 'ts_code',
      header: '股票',
      accessor: (row) => (
        <span
          className={`cursor-pointer hover:underline whitespace-nowrap ${limitTypeColor(row.limit_type)}`}
          onClick={() => openStockAnalysis(row.ts_code)}
        >
          {row.name || '-'}[{formatStockCode(row.ts_code)}]
        </span>
      ),
      width: 160,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'limit_type',
      header: '类型',
      accessor: (row) => {
        if (row.limit_type === 'U') return <span className="text-red-600 font-semibold">涨停</span>
        if (row.limit_type === 'D') return <span className="text-green-600 font-semibold">跌停</span>
        if (row.limit_type === 'Z') return <span className="text-orange-500 font-semibold">炸板</span>
        return '-'
      },
      width: 60,
      cellClassName: 'text-center'
    },
    {
      key: 'pct_chg',
      header: '涨跌幅%',
      accessor: (row) => {
        if (row.pct_chg === null || row.pct_chg === undefined) return '-'
        return (
          <span className={row.pct_chg >= 0 ? 'text-red-600' : 'text-green-600'}>
            {row.pct_chg >= 0 ? '+' : ''}{row.pct_chg.toFixed(2)}%
          </span>
        )
      },
      width: 90,
      cellClassName: 'text-right whitespace-nowrap'
    },
    { key: 'limit_times', header: '连板', accessor: (row) => row.limit_times ?? '-', width: 60, cellClassName: 'text-right font-semibold text-red-600' },
    { key: 'open_times', header: '炸板次数', accessor: (row) => row.open_times !== null ? row.open_times : '-', width: 80, cellClassName: 'text-right' },
    { key: 'first_time', header: '首封', accessor: (row) => row.first_time || '-', width: 80, cellClassName: 'whitespace-nowrap' },
    { key: 'last_time', header: '最后封板', accessor: (row) => row.last_time || '-', width: 80, cellClassName: 'whitespace-nowrap' },
    { key: 'close', header: '收盘价', accessor: (row) => row.close?.toFixed(2) ?? '-', width: 80, cellClassName: 'text-right whitespace-nowrap' },
    { key: 'amount', header: '成交额(万)', accessor: (row) => row.amount ? (row.amount / 10000).toFixed(0) : '-', width: 100, cellClassName: 'text-right whitespace-nowrap' },
    { key: 'turnover_ratio', header: '换手率%', accessor: (row) => row.turnover_ratio ? row.turnover_ratio.toFixed(2) + '%' : '-', width: 90, cellClassName: 'text-right whitespace-nowrap' },
    { key: 'industry', header: '行业', accessor: (row) => row.industry || '-', cellClassName: 'whitespace-nowrap' },
  ]

  const mobileCard = (item: LimitListData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b">
        <div>
          <span
            className={`font-medium cursor-pointer hover:underline ${limitTypeColor(item.limit_type)}`}
            onClick={() => openStockAnalysis(item.ts_code)}
          >
            {item.name || '-'}
          </span>
          <span className="text-xs text-gray-500 ml-2">{formatStockCode(item.ts_code)}</span>
        </div>
        <div className="flex items-center gap-1">
          {item.limit_type === 'U' && <TrendingUp className="h-4 w-4 text-red-600" />}
          {item.limit_type === 'D' && <TrendingDown className="h-4 w-4 text-green-600" />}
          {item.limit_type === 'Z' && <Zap className="h-4 w-4 text-orange-500" />}
          <span className={`text-xs font-semibold ${limitTypeColor(item.limit_type)}`}>
            {item.limit_type === 'U' ? '涨停' : item.limit_type === 'D' ? '跌停' : item.limit_type === 'Z' ? '炸板' : ''}
          </span>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">涨跌幅:</span>
          <span className={(item.pct_chg ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}>
            {item.pct_chg !== null ? `${(item.pct_chg ?? 0) >= 0 ? '+' : ''}${item.pct_chg!.toFixed(2)}%` : '-'}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">连板:</span>
          <span className="text-red-600 font-semibold">{item.limit_times ?? '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">首封:</span>
          <span>{item.first_time || '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">炸板:</span>
          <span>{item.open_times !== null ? item.open_times : '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">日期:</span>
          <span>{item.trade_date || '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">行业:</span>
          <span>{item.industry || '-'}</span>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="涨跌停列表"
        description="获取A股每日涨跌停、炸板数据情况，数据从2020年开始（不提供ST股票的统计）"
        details={<>
          <div>接口：limit_list_d</div>
          <a href="https://tushare.pro/document/2?doc_id=298" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="涨跌停列表"
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
              <label className="text-sm font-medium mb-1 block">涨跌停类型</label>
              <Select value={limitType} onValueChange={setLimitType}>
                <SelectTrigger><SelectValue placeholder="全部" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="U">涨停</SelectItem>
                  <SelectItem value="D">跌停</SelectItem>
                  <SelectItem value="Z">炸板</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">股票代码</label>
              <Input placeholder="如 000001 或 000001.SZ" value={tsCode} onChange={(e) => setTsCode(e.target.value)} />
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
