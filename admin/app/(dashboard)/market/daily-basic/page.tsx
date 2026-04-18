'use client'

import { useState, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { useDataPage } from '@/hooks/useDataPage'
import { axiosInstance } from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { RefreshCw, Database, TrendingUp, BarChart3, Package } from 'lucide-react'

// ============== 类型定义 ==============

interface DailyBasicData {
  ts_code: string
  trade_date: string
  close: number | null
  turnover_rate: number | null
  turnover_rate_f: number | null
  volume_ratio: number | null
  pe: number | null
  pe_ttm: number | null
  pb: number | null
  ps: number | null
  ps_ttm: number | null
  dv_ratio: number | null
  dv_ttm: number | null
  total_share: number | null
  float_share: number | null
  free_share: number | null
  total_mv: number | null
  circ_mv: number | null
}

interface DailyBasicStatistics {
  total_records: number
  date_range: {
    earliest_date: string
    latest_date: string
  }
  avg_turnover_rate: number
  avg_pe_ttm: number
  stock_count: number
}

// ============== 页面组件 ==============

export default function DailyBasicPage() {
  const [tsCode, setTsCode] = useState('')
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)

  const dp = useDataPage<DailyBasicData, DailyBasicStatistics>({
    apiCall: (params) => axiosInstance.get('/api/daily-basic', { params }),
    statisticsCall: (params) => axiosInstance.get('/api/daily-basic/statistics', { params }),
    syncFn: () => axiosInstance.post('/api/daily-basic/sync-async'),
    taskName: ['tasks.sync_daily_basic_incremental', 'tasks.sync_daily_basic_full_history'],
    bulkOps: {
      tableKey: 'daily_basic',
      syncFn: (params) => axiosInstance.post('/api/daily-basic/sync-full-history', null, { params }),
      taskName: 'tasks.sync_daily_basic_full_history',
    },
    paginationMode: 'page',
    pageSize: 30,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      return params
    },
    syncSuccessMessage: '每日指标数据同步完成',
  })

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      { label: '总记录数', value: s.total_records?.toLocaleString() || '0', icon: Database, iconColor: 'text-blue-600' },
      { label: '统计股票数', value: s.stock_count?.toLocaleString() || '0', icon: Package, iconColor: 'text-orange-600' },
      {
        label: '平均换手率',
        value: s.avg_turnover_rate !== null && s.avg_turnover_rate !== undefined ? `${s.avg_turnover_rate.toFixed(2)}%` : '-',
        icon: BarChart3,
        iconColor: 'text-green-600',
      },
      {
        label: '平均市盈率(TTM)',
        value: s.avg_pe_ttm !== null && s.avg_pe_ttm !== undefined ? s.avg_pe_ttm.toFixed(2) : '-',
        icon: TrendingUp,
        iconColor: 'text-purple-600',
      },
    ]
  }, [dp.statistics])

  // 表格列定义
  const columns: Column<DailyBasicData>[] = useMemo(() => [
    { key: 'trade_date', header: '交易日期', accessor: (row) => row.trade_date },
    { key: 'ts_code', header: '股票代码', accessor: (row) => row.ts_code },
    { key: 'close', header: '收盘价', accessor: (row) => row.close !== null ? `¥${row.close.toFixed(2)}` : '-' },
    { key: 'turnover_rate', header: '换手率', accessor: (row) => row.turnover_rate !== null ? `${row.turnover_rate.toFixed(2)}%` : '-' },
    { key: 'volume_ratio', header: '量比', accessor: (row) => row.volume_ratio !== null ? row.volume_ratio.toFixed(2) : '-' },
    { key: 'pe_ttm', header: '市盈率(TTM)', accessor: (row) => row.pe_ttm !== null ? row.pe_ttm.toFixed(2) : '-' },
    { key: 'pb', header: '市净率', accessor: (row) => row.pb !== null ? row.pb.toFixed(2) : '-' },
    { key: 'ps_ttm', header: '市销率(TTM)', accessor: (row) => row.ps_ttm !== null ? row.ps_ttm.toFixed(2) : '-' },
    { key: 'total_mv', header: '总市值(万元)', accessor: (row) => row.total_mv !== null ? row.total_mv.toFixed(0) : '-' },
    { key: 'circ_mv', header: '流通市值(万元)', accessor: (row) => row.circ_mv !== null ? row.circ_mv.toFixed(0) : '-' },
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: DailyBasicData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">日期</span>
        <span className="font-medium">{item.trade_date}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">股票代码</span>
        <span className="font-medium">{item.ts_code}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">收盘价</span>
        <span className="font-medium">{item.close !== null ? `¥${item.close.toFixed(2)}` : '-'}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">换手率</span>
        <span className="font-medium">{item.turnover_rate !== null ? `${item.turnover_rate.toFixed(2)}%` : '-'}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">市盈率(TTM)</span>
        <span className="font-medium">{item.pe_ttm !== null ? item.pe_ttm.toFixed(2) : '-'}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">市净率</span>
        <span className="font-medium">{item.pb !== null ? item.pb.toFixed(2) : '-'}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">总市值</span>
        <span className="font-medium">{item.total_mv !== null ? `${item.total_mv.toFixed(0)}万元` : '-'}</span>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="每日指标"
        description="获取全部股票每日重要的基本面指标，可用于选股分析、报表展示等。单次请求最大返回6000条数据，可按日线循环提取全部历史。"
        details={<>
          <div>接口：daily_basic</div>
          <a href="https://tushare.pro/document/2?doc_id=32" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="每日指标"
            />
          </div>
        }
      />

      <SyncDialog
        open={dp.syncDialogOpen}
        onOpenChange={dp.setSyncDialogOpen}
        onConfirm={dp.handleSyncConfirm}
        title="同步每日指标"
        description="将从 Tushare 增量同步最新每日指标数据，无需选择日期。"
        disabled={dp.syncing}
      />

      <StatisticsCards items={statsCards} />

      {/* 查询条件 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            <div className="space-y-2">
              <Label htmlFor="ts-code">股票代码</Label>
              <Input id="ts-code" placeholder="如：000001.SZ" value={tsCode} onChange={(e) => setTsCode(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>交易日期</Label>
              <DatePicker date={tradeDate} onDateChange={setTradeDate} placeholder="选择日期" />
            </div>
            <div className="space-y-2">
              <Label>开始日期</Label>
              <DatePicker date={startDate} onDateChange={setStartDate} placeholder="开始日期" />
            </div>
            <div className="space-y-2">
              <Label>结束日期</Label>
              <DatePicker date={endDate} onDateChange={setEndDate} placeholder="结束日期" />
            </div>
            <div className="flex items-end">
              <Button onClick={dp.handleQuery} className="w-full">查询</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <DataTable
          columns={columns}
          data={dp.data}
          loading={dp.isLoading}
          emptyMessage="暂无数据"
          mobileCard={mobileCard}
          pagination={{
            page: dp.page,
            pageSize: dp.pageSize,
            total: dp.total,
            onPageChange: dp.handlePageChange,
          }}
        />
      </Card>
    </div>
  )
}
