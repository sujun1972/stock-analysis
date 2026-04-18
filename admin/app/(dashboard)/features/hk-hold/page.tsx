'use client'

import { useState, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { useDataPage } from '@/hooks/useDataPage'
import { hkHoldApi, type HkHoldData, type HkHoldStatistics } from '@/lib/api'
import { axiosInstance } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { RefreshCw, BarChart3, Users, TrendingUp, Percent } from 'lucide-react'

// ============== 工具函数 ==============

const formatNumber = (value: number | null | undefined, decimals: number = 0): string => {
  if (value === null || value === undefined) return '-'
  return value.toLocaleString('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

// ============== 页面组件 ==============

export default function HkHoldPage() {
  // 查询筛选状态
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState<string>('')
  const [code, setCode] = useState<string>('')
  const [exchange, setExchange] = useState<string>('')

  // 同步弹窗额外字段
  const [syncDate, setSyncDate] = useState<Date | undefined>(undefined)

  const dp = useDataPage<HkHoldData, HkHoldStatistics>({
    apiCall: (params) => hkHoldApi.getData(params),
    syncFn: (params) => hkHoldApi.syncAsync(params),
    taskName: 'tasks.sync_hk_hold',
    bulkOps: {
      tableKey: 'hk_hold',
      syncFn: (params) => axiosInstance.post('/api/hk-hold/sync-async', null, { params }),
      taskName: 'tasks.sync_hk_hold',
    },
    paginationMode: 'page',
    pageSize: 100,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (code.trim()) params.code = code.trim()
      if (exchange.trim()) params.exchange = exchange.trim()
      return params
    },
    onBackfillDate: (dateStr) => {
      if (!tradeDate) setTradeDate(new Date(dateStr + 'T00:00:00'))
    },
    syncSuccessMessage: '北向资金持股数据同步完成',
  })

  // 覆盖同步确认：只传 syncDate
  const handleCustomSyncConfirm = async () => {
    dp.setSyncDialogOpen(false)
    const params: Record<string, unknown> = {}
    if (syncDate) params.trade_date = toDateStr(syncDate)
    await dp.handleSyncDirect(params)
  }

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '总记录数',
        value: `${formatNumber(s.total_count)}条`,
        subValue: '当前筛选结果',
        icon: BarChart3,
        iconColor: 'text-blue-600',
      },
      {
        label: '股票数',
        value: `${formatNumber(s.stock_count)}只`,
        subValue: '持仓标的数量',
        icon: Users,
        iconColor: 'text-orange-600',
      },
      {
        label: '平均持股数',
        value: `${formatNumber(s.avg_vol)}万股`,
        subValue: '平均持仓规模',
        icon: TrendingUp,
        iconColor: 'text-green-600',
      },
      {
        label: '最高持股比例',
        value: <span className="text-blue-600">{formatNumber(s.max_ratio, 2)}%</span>,
        subValue: '单只股票最高占比',
        icon: Percent,
        iconColor: 'text-purple-600',
      },
    ]
  }, [dp.statistics])

  // 移动端卡片
  const mobileCard = useCallback((item: HkHoldData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div className="font-semibold text-base">{item.name || item.ts_code || item.code}</div>
          <div className="text-sm text-gray-500">{[item.ts_code, item.code].filter(Boolean).join(' / ')}</div>
        </div>
        <span className="text-xs text-gray-500">{item.trade_date}</span>
      </div>
      <div className="space-y-1 text-sm">
        {item.exchange && (
          <div className="flex justify-between">
            <span className="text-gray-600">交易所</span>
            <span className="font-medium">{item.exchange}</span>
          </div>
        )}
        {item.vol !== null && item.vol !== undefined && (
          <div className="flex justify-between">
            <span className="text-gray-600">持股数</span>
            <span className="font-medium">{formatNumber(item.vol)}万股</span>
          </div>
        )}
        {item.ratio !== null && item.ratio !== undefined && (
          <div className="flex justify-between">
            <span className="text-gray-600">持股比例</span>
            <span className="font-medium text-blue-600">{formatNumber(item.ratio, 2)}%</span>
          </div>
        )}
      </div>
    </div>
  ), [])

  // 桌面端表格列定义
  const columns: Column<HkHoldData>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => row.trade_date,
      width: 110,
      sortable: true
    },
    {
      key: 'ts_code',
      header: 'A股代码',
      accessor: (row) => row.ts_code || '-',
      width: 100
    },
    {
      key: 'code',
      header: '港股代码',
      accessor: (row) => row.code || '-',
      width: 100
    },
    {
      key: 'name',
      header: '股票名称',
      accessor: (row) => row.name || '-',
      width: 100
    },
    {
      key: 'exchange',
      header: '交易所',
      accessor: (row) => row.exchange || '-',
      width: 80,
      hideOnMobile: true
    },
    {
      key: 'vol',
      header: '持股数(万股)',
      accessor: (row) => formatNumber(row.vol),
      width: 120,
      cellClassName: 'text-right whitespace-nowrap',
      hideOnMobile: true,
      sortable: true
    },
    {
      key: 'amount',
      header: '持股额(百万元)',
      accessor: (row) => formatNumber(row.amount, 2),
      width: 130,
      cellClassName: 'text-right whitespace-nowrap',
      hideOnMobile: true,
      sortable: true
    },
    {
      key: 'ratio',
      header: '持股比例(%)',
      accessor: (row) => formatNumber(row.ratio, 2),
      width: 110,
      cellClassName: 'text-right whitespace-nowrap',
      sortable: true
    }
  ], [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="沪深港股通持股明细"
        description="获取沪深港股通持股明细，数据来源港交所。"
        details={<>
          <div>接口：hk_hold</div>
          <a href="https://tushare.pro/document/2?doc_id=188" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="沪深港股通持股明细"
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
          <div className="flex flex-col sm:flex-row gap-4 items-end flex-wrap">
            <div className="w-full sm:w-40">
              <Label className="mb-2 block">交易日期</Label>
              <DatePicker date={tradeDate} onDateChange={setTradeDate} placeholder="选择日期" />
            </div>
            <div className="w-full sm:w-40">
              <Label className="mb-2 block">A股代码</Label>
              <Input
                placeholder="如 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="w-full sm:w-40">
              <Label className="mb-2 block">港股代码</Label>
              <Input
                placeholder="如 00700.HK"
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
            </div>
            <div className="w-full sm:w-28">
              <Label className="mb-2 block">交易所</Label>
              <Input
                placeholder="SH / SZ"
                value={exchange}
                onChange={(e) => setExchange(e.target.value)}
              />
            </div>
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
            emptyMessage="暂无持股数据"
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
        onConfirm={handleCustomSyncConfirm}
        title="同步沪深港股通持股明细"
        description="选择同步日期（留空则同步最近30天数据）。消耗 2000 积分/次，2024年8月20日起改为季度披露。"
        disabled={dp.syncing}
      >
        <div className="py-4">
          <Label className="mb-2 block">交易日期（可选）</Label>
          <DatePicker date={syncDate} onDateChange={setSyncDate} placeholder="留空同步最近30天" />
        </div>
      </SyncDialog>
    </div>
  )
}
