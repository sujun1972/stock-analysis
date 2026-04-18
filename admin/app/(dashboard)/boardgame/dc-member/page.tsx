'use client'

import { useState, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useDataPage } from '@/hooks/useDataPage'
import { dcMemberApi, type DcMemberData, type DcMemberStatistics } from '@/lib/api'
import { axiosInstance } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { formatStockCode } from '@/lib/utils'
import { useSystemConfig } from '@/contexts'
import { RefreshCw, Database, Layers, TrendingUp, Calendar } from 'lucide-react'

// ============== 页面组件 ==============

export default function DcMemberPage() {
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [conCode, setConCode] = useState('')
  const { config } = useSystemConfig()

  const openStockAnalysis = useCallback((code: string) => {
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(code)), '_blank')
  }, [config])

  const dp = useDataPage<DcMemberData, DcMemberStatistics>({
    apiCall: (params) => dcMemberApi.getData(params),
    statisticsCall: (params) => dcMemberApi.getStatistics(params),
    syncFn: (params) => dcMemberApi.syncAsync(params),
    taskName: 'tasks.sync_dc_member',
    bulkOps: {
      tableKey: 'dc_member',
      syncFn: (params) => axiosInstance.post('/api/dc-member/sync-async', null, { params }),
      taskName: 'tasks.sync_dc_member',
    },
    paginationMode: 'page',
    pageSize: 100,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (conCode.trim()) params.con_code = conCode.trim()
      return params
    },
    onBackfillDate: (dateStr) => setTradeDate(new Date(dateStr + 'T00:00:00')),
    syncSuccessMessage: '东方财富板块成分数据同步完成',
  })

  const formatNumber = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return '-'
    return value.toLocaleString('zh-CN')
  }

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      { label: '总记录数', value: formatNumber(s.total_records), icon: Database, iconColor: 'text-blue-600' },
      { label: '板块数量', value: formatNumber(s.board_count), icon: Layers, iconColor: 'text-purple-600' },
      { label: '成分股数量', value: formatNumber(s.stock_count), icon: TrendingUp, iconColor: 'text-green-600' },
      { label: '日期数量', value: formatNumber(s.date_count), icon: Calendar, iconColor: 'text-orange-600' },
    ]
  }, [dp.statistics])

  // 表格列定义
  const columns: Column<DcMemberData>[] = useMemo(() => [
    {
      key: 'name',
      header: '成分股',
      accessor: (row) => (
        row.con_code ? (
          <span
            className="cursor-pointer hover:underline text-blue-600 font-medium"
            onClick={() => openStockAnalysis(row.con_code)}
          >
            {row.name || '-'}[{formatStockCode(row.con_code)}]
          </span>
        ) : (
          <span>{row.name || '-'}</span>
        )
      ),
      width: 180,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'ts_code',
      header: '板块',
      accessor: (row) => (
        <span>
          {row.board_name ? `${row.board_name}[${row.ts_code}]` : row.ts_code}
        </span>
      ),
      width: 200,
      cellClassName: 'whitespace-nowrap'
    },
  ], [openStockAnalysis])

  // 移动端卡片
  const mobileCard = useCallback((item: DcMemberData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <div>
          {item.con_code ? (
            <span
              className="font-medium text-blue-600 cursor-pointer hover:underline"
              onClick={() => openStockAnalysis(item.con_code)}
            >
              {item.name || '-'}
            </span>
          ) : (
            <span className="font-medium">{item.name || '-'}</span>
          )}
          {item.con_code && (
            <span className="text-xs text-gray-500 ml-2">[{formatStockCode(item.con_code)}]</span>
          )}
        </div>
        <TrendingUp className="h-4 w-4 text-blue-600" />
      </div>
      <div className="text-sm">
        <span className="text-gray-600">板块：</span>
        <span className="font-medium">
          {item.board_name ? `${item.board_name}[${item.ts_code}]` : item.ts_code}
        </span>
      </div>
    </div>
  ), [openStockAnalysis])

  return (
    <div className="space-y-6">
      <PageHeader
        title="东方财富板块成分"
        description="获取东方财富板块每日成分数据，可以根据概念板块代码和交易日期，获取历史成分"
        details={<>
          <div>接口：dc_member</div>
          <a href="https://tushare.pro/document/2?doc_id=363" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="东财板块成分"
            />
          </div>
        }
      />

      <StatisticsCards items={statsCards} />

      {/* 筛选区 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">交易日期</label>
              <DatePicker date={tradeDate} onDateChange={setTradeDate} />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">板块代码</label>
              <Input placeholder="如：BK0001" value={tsCode} onChange={(e) => setTsCode(e.target.value)} />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">成分股代码</label>
              <Input placeholder="如：000001.SZ" value={conCode} onChange={(e) => setConCode(e.target.value)} />
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
            emptyMessage="暂无数据"
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
