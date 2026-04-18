'use client'

import { useState, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { useDataPage } from '@/hooks/useDataPage'
import { stkHoldertradeApi, type StkHoldertradeData, type StkHoldertradeStatistics } from '@/lib/api'
import { axiosInstance } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { RefreshCw, TrendingUp, TrendingDown, Users, FileText } from 'lucide-react'

// ============== 工具函数 ==============

const formatHolderType = (type: string) => {
  const types: Record<string, string> = { 'G': '高管', 'P': '个人', 'C': '公司' }
  return types[type] || type
}

const formatTradeType = (type: string) => type === 'IN' ? '增持' : type === 'DE' ? '减持' : type

const formatNumber = (num: number | null | undefined, decimals: number = 2) => {
  if (num === null || num === undefined) return '-'
  return num.toLocaleString('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
}

// ============== 页面组件 ==============

export default function StkHoldertradePage() {
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState<string>('')
  const [holderType, setHolderType] = useState<string>('ALL')
  const [tradeType, setTradeType] = useState<string>('ALL')

  const dp = useDataPage<StkHoldertradeData, StkHoldertradeStatistics>({
    apiCall: (params) => stkHoldertradeApi.getStkHoldertrade(params),
    syncFn: (params) => stkHoldertradeApi.syncAsync(params),
    taskName: 'tasks.sync_stk_holdertrade',
    bulkOps: {
      tableKey: 'stk_holdertrade',
      syncFn: (params) => axiosInstance.post('/api/stk-holdertrade/sync-full-history', null, { params }),
      taskName: 'tasks.sync_stk_holdertrade_full_history',
    },
    paginationMode: 'offset',
    pageSize: 100,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      if (tsCode) params.ts_code = tsCode
      if (holderType && holderType !== 'ALL') params.holder_type = holderType
      if (tradeType && tradeType !== 'ALL') params.trade_type = tradeType
      return params
    },
    syncSuccessMessage: '股东增减持数据同步完成',
  })

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '总记录数',
        value: s.total_count?.toLocaleString(),
        subValue: `涉及 ${s.stock_count} 只股票`,
        icon: FileText,
        iconColor: 'text-blue-500',
      },
      {
        label: '增持记录',
        value: <span className="text-red-600">{s.increase_count?.toLocaleString()}</span>,
        subValue: `平均比例 ${formatNumber(s.avg_increase_ratio, 2)}%`,
        icon: TrendingUp,
        iconColor: 'text-red-500',
      },
      {
        label: '减持记录',
        value: <span className="text-green-600">{s.decrease_count?.toLocaleString()}</span>,
        subValue: `平均比例 ${formatNumber(s.avg_decrease_ratio, 2)}%`,
        icon: TrendingDown,
        iconColor: 'text-green-500',
      },
      {
        label: '累计变动',
        value: (
          <div className="text-sm mt-1">
            <div className="flex justify-between mb-1">
              <span className="text-red-600">增持:</span>
              <span className="font-semibold">{formatNumber(s.total_increase_vol, 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-green-600">减持:</span>
              <span className="font-semibold">{formatNumber(s.total_decrease_vol, 0)}</span>
            </div>
          </div>
        ),
        icon: Users,
        iconColor: 'text-purple-500',
      },
    ]
  }, [dp.statistics])

  // 表格列定义
  const columns: Column<StkHoldertradeData>[] = useMemo(() => [
    { key: 'ts_code', header: '股票代码', accessor: (row) => row.ts_code },
    { key: 'ann_date', header: '公告日期', accessor: (row) => row.ann_date },
    { key: 'holder_name', header: '股东名称', accessor: (row) => row.holder_name },
    { key: 'holder_type', header: '股东类型', accessor: (row) => formatHolderType(row.holder_type) },
    {
      key: 'in_de',
      header: '交易类型',
      accessor: (row) => (
        <span className={row.in_de === 'IN' ? 'text-red-600' : 'text-green-600'}>
          {formatTradeType(row.in_de)}
        </span>
      )
    },
    { key: 'change_vol', header: '变动数量', accessor: (row) => formatNumber(row.change_vol, 0) },
    { key: 'change_ratio', header: '占流通比例(%)', accessor: (row) => formatNumber(row.change_ratio, 2) },
    { key: 'avg_price', header: '平均价格', accessor: (row) => formatNumber(row.avg_price, 2) },
    { key: 'after_share', header: '变动后持股', accessor: (row) => formatNumber(row.after_share, 0) },
    { key: 'after_ratio', header: '变动后比例(%)', accessor: (row) => formatNumber(row.after_ratio, 2) }
  ], [])

  const mobileCard = useCallback((item: StkHoldertradeData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium">{item.ts_code}</span>
        <span className={`font-semibold ${item.in_de === 'IN' ? 'text-red-600' : 'text-green-600'}`}>
          {formatTradeType(item.in_de)}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">公告日期</span>
        <span>{item.ann_date}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">股东名称</span>
        <span className="text-right">{item.holder_name}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">股东类型</span>
        <span>{formatHolderType(item.holder_type)}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">变动数量</span>
        <span>{formatNumber(item.change_vol, 0)}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">占流通比例</span>
        <span>{formatNumber(item.change_ratio, 2)}%</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">平均价格</span>
        <span>{formatNumber(item.avg_price, 2)}</span>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="股东增减持"
        description="获取上市公司增减持数据，了解重要股东近期及历史上的股份增减变化"
        details={<>
          <div>接口：stk_holdertrade</div>
          <a href="https://tushare.pro/document/2?doc_id=175" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="股东增减持"
            />
          </div>
        }
      />

      <SyncDialog
        open={dp.syncDialogOpen}
        onOpenChange={dp.setSyncDialogOpen}
        onConfirm={dp.handleSyncConfirm}
        title="同步数据"
        description="选择同步日期范围（留空则同步最新数据）。"
        disabled={dp.syncing}
        showDateRange
        startDate={dp.syncStartDate}
        onStartDateChange={dp.setSyncStartDate}
        endDate={dp.syncEndDate}
        onEndDateChange={dp.setSyncEndDate}
      />

      <StatisticsCards items={statsCards} />

      {/* 筛选区域 */}
      <Card>
        <CardHeader><CardTitle>数据查询</CardTitle></CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="text-sm font-medium mb-2 block">开始日期</label>
              <DatePicker date={startDate} onDateChange={setStartDate} />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">结束日期</label>
              <DatePicker date={endDate} onDateChange={setEndDate} />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">股票代码（可选）</label>
              <Input placeholder="输入股票代码" value={tsCode} onChange={(e) => setTsCode(e.target.value)} />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">股东类型</label>
              <Select value={holderType} onValueChange={setHolderType}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="G">高管</SelectItem>
                  <SelectItem value="P">个人</SelectItem>
                  <SelectItem value="C">公司</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">交易类型</label>
              <Select value={tradeType} onValueChange={setTradeType}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="IN">增持</SelectItem>
                  <SelectItem value="DE">减持</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <Button onClick={dp.handleQuery} disabled={dp.isLoading}>查询</Button>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="pt-6">
          <DataTable
            columns={columns}
            data={dp.data}
            loading={dp.isLoading}
            emptyMessage="暂无股东增减持数据"
            mobileCard={mobileCard}
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
