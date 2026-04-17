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
import { stkAuctionCApi } from '@/lib/api/stk-auction-c'
import type { StkAuctionCData, StkAuctionCStatistics } from '@/lib/api/stk-auction-c'
import { apiClient } from '@/lib/api-client'
import { toDateStr } from '@/lib/date-utils'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { RefreshCw, TrendingUp, BarChart3, DollarSign, Activity } from 'lucide-react'

// ============== 工具函数 ==============

const formatDate = (dateStr: string) => {
  if (!dateStr || dateStr.length !== 8) return dateStr
  return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
}

const formatNumber = (value: number | null | undefined, decimals: number = 2): string => {
  if (value === null || value === undefined) return '-'
  return value.toLocaleString('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

// ============== 页面组件 ==============

export default function StkAuctionCPage() {
  // 查询筛选状态
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')

  // 同步弹窗额外字段
  const [syncTsCode, setSyncTsCode] = useState('')
  const [syncTradeDate, setSyncTradeDate] = useState<Date | undefined>(undefined)

  const dp = useDataPage<StkAuctionCData, StkAuctionCStatistics>({
    apiCall: (params) => stkAuctionCApi.getData(params),
    syncFn: (params) => stkAuctionCApi.syncAsync(params),
    taskName: 'tasks.sync_stk_auction_c',
    bulkOps: {
      tableKey: 'stk_auction_c',
      syncFn: (params) => apiClient.post('/api/stk-auction-c/sync-async', null, { params }),
      taskName: 'tasks.sync_stk_auction_c',
    },
    paginationMode: 'page',
    pageSize: 30,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      return params
    },
    onBackfillDate: (dateStr) => {
      if (!tradeDate) setTradeDate(new Date(dateStr + 'T00:00:00'))
    },
    syncSuccessMessage: '收盘集合竞价数据同步完成',
  })

  // 覆盖同步确认：需要额外传 syncTsCode / syncTradeDate
  const handleCustomSyncConfirm = async () => {
    dp.setSyncDialogOpen(false)
    const params: Record<string, unknown> = {}
    if (syncTsCode.trim()) params.ts_code = syncTsCode.trim()
    if (syncTradeDate) params.trade_date = toDateStr(syncTradeDate)
    if (dp.syncStartDate) params.start_date = toDateStr(dp.syncStartDate)
    if (dp.syncEndDate) params.end_date = toDateStr(dp.syncEndDate)
    await dp.handleSyncDirect(params)
  }

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '股票数量',
        value: (s.stock_count ?? 0).toLocaleString(),
        subValue: '只',
        icon: Activity,
        iconColor: 'text-blue-600',
      },
      {
        label: '平均成交量',
        value: formatNumber(s.avg_vol),
        subValue: '手',
        icon: TrendingUp,
        iconColor: 'text-green-600',
      },
      {
        label: '最大成交量',
        value: formatNumber(s.max_vol),
        subValue: '手',
        icon: BarChart3,
        iconColor: 'text-orange-600',
      },
      {
        label: '最大成交额',
        value: formatNumber(s.max_amount),
        subValue: '万元',
        icon: DollarSign,
        iconColor: 'text-purple-600',
      },
    ]
  }, [dp.statistics])

  // 移动端卡片
  const mobileCard = useCallback((item: StkAuctionCData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div className="font-semibold text-base">{item.ts_code}</div>
          <div className="text-sm text-gray-500">{formatDate(item.trade_date)}</div>
        </div>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">开盘价</span>
          <span className="font-medium">{formatNumber(item.open)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">收盘价</span>
          <span className="font-medium">{formatNumber(item.close)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">成交量</span>
          <span className="font-medium">{formatNumber(item.vol)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">成交额</span>
          <span className="font-medium">{formatNumber(item.amount)}</span>
        </div>
        {item.vwap !== null && item.vwap !== undefined && (
          <div className="flex justify-between">
            <span className="text-gray-600">均价</span>
            <span className="font-medium">{formatNumber(item.vwap)}</span>
          </div>
        )}
      </div>
    </div>
  ), [])

  // 桌面端表格列定义
  const columns: Column<StkAuctionCData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code,
      width: 110
    },
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => formatDate(row.trade_date),
      width: 110
    },
    {
      key: 'open',
      header: '开盘价',
      accessor: (row) => formatNumber(row.open),
      width: 90,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'high',
      header: '最高价',
      accessor: (row) => formatNumber(row.high),
      width: 90,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'low',
      header: '最低价',
      accessor: (row) => formatNumber(row.low),
      width: 90,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'close',
      header: '收盘价',
      accessor: (row) => formatNumber(row.close),
      width: 90,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'vwap',
      header: '均价',
      accessor: (row) => formatNumber(row.vwap),
      width: 90,
      cellClassName: 'text-right whitespace-nowrap',
      hideOnMobile: true
    },
    {
      key: 'vol',
      header: '成交量(手)',
      accessor: (row) => formatNumber(row.vol),
      width: 110,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'amount',
      header: '成交额(万元)',
      accessor: (row) => formatNumber(row.amount),
      width: 120,
      cellClassName: 'text-right whitespace-nowrap'
    }
  ], [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="股票收盘集合竞价"
        description="股票收盘15:00集合竞价数据，每天盘后更新"
        details={<>
          <div>接口：stk_auction_c</div>
          <a href="https://tushare.pro/document/2?doc_id=354" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="收盘集合竞价"
            />
          </div>
        }
      />

      <StatisticsCards items={statsCards} />

      {/* 筛选区域 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <Label className="mb-2 block">股票代码</Label>
              <Input
                placeholder="如 000001 或 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div>
              <Label className="mb-2 block">交易日期</Label>
              <DatePicker date={tradeDate} onDateChange={setTradeDate} placeholder="留空默认最近有数据日期" />
            </div>
          </div>
          <div className="mt-4">
            <Button onClick={dp.handleQuery} disabled={dp.isLoading}>
              {dp.isLoading ? '查询中...' : '查询'}
            </Button>
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
            emptyMessage="暂无收盘集合竞价数据"
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
        onConfirm={handleCustomSyncConfirm}
        title="同步收盘集合竞价数据"
        description="所有参数均为可选，不填写将同步最近交易日数据（需开通股票分钟权限）。"
        disabled={dp.syncing}
      >
        <div className="py-4 space-y-4">
          <div>
            <Label className="mb-2 block">股票代码（可选）</Label>
            <Input
              placeholder="如 600000.SH，留空同步全市场"
              value={syncTsCode}
              onChange={(e) => setSyncTsCode(e.target.value)}
            />
          </div>
          <div>
            <Label className="mb-2 block">交易日期（可选）</Label>
            <DatePicker date={syncTradeDate} onDateChange={setSyncTradeDate} placeholder="留空同步最新交易日" />
          </div>
          <div>
            <Label className="mb-2 block">开始日期（可选）</Label>
            <DatePicker date={dp.syncStartDate} onDateChange={dp.setSyncStartDate} placeholder="日期范围起始" />
          </div>
          <div>
            <Label className="mb-2 block">结束日期（可选）</Label>
            <DatePicker date={dp.syncEndDate} onDateChange={dp.setSyncEndDate} placeholder="日期范围结束" />
          </div>
        </div>
      </SyncDialog>
    </div>
  )
}
