'use client'

import { useState, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { useDataPage } from '@/hooks/useDataPage'
import { financialDataApi } from '@/lib/api/financial-data'
import type { FinaAuditData, FinaAuditStatistics } from '@/lib/api/financial-data'
import { toDateStr } from '@/lib/date-utils'
import { RefreshCw, TrendingUp, Building2, Users, DollarSign } from 'lucide-react'

// ============== 页面组件 ==============

export default function FinaAuditPage() {
  // 查询筛选状态
  const [tsCode, setTsCode] = useState('')
  const [annDate, setAnnDate] = useState<Date | undefined>(undefined)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [period, setPeriod] = useState<Date | undefined>(undefined)

  const dp = useDataPage<FinaAuditData, FinaAuditStatistics>({
    apiCall: (params) => financialDataApi.getFinaAudit(params),
    syncFn: () => financialDataApi.syncFinaAuditAsync(),
    taskName: ['tasks.sync_fina_audit', 'tasks.sync_fina_audit_full_history'],
    bulkOps: {
      tableKey: 'fina_audit',
      syncFn: (params) => financialDataApi.syncFinaAuditFullHistoryAsync({ start_date: params?.start_date }),
      taskName: 'tasks.sync_fina_audit_full_history',
    },
    paginationMode: 'offset',
    pageSize: 30,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (tsCode) params.ts_code = tsCode
      if (annDate) params.ann_date = toDateStr(annDate)
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      if (period) params.period = toDateStr(period)
      return params
    },
    syncSuccessMessage: '财务审计意见数据同步完成',
  })

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '总记录数',
        value: s.total_count.toLocaleString(),
        subValue: '统计期内审计记录',
        icon: TrendingUp,
        iconColor: 'text-muted-foreground',
      },
      {
        label: '公司数量',
        value: s.stock_count.toLocaleString(),
        subValue: '不同公司数量',
        icon: Building2,
        iconColor: 'text-muted-foreground',
      },
      {
        label: '事务所数量',
        value: s.agency_count.toLocaleString(),
        subValue: '会计事务所数量',
        icon: Users,
        iconColor: 'text-muted-foreground',
      },
      {
        label: '平均审计费用',
        value: `${(s.avg_fees / 10000).toFixed(2)}万`,
        subValue: `最高: ${(s.max_fees / 10000).toFixed(2)}万`,
        icon: DollarSign,
        iconColor: 'text-muted-foreground',
      },
    ]
  }, [dp.statistics])

  // 表格列定义
  const columns: Column<FinaAuditData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'ann_date',
      header: '公告日期',
      accessor: (row) => {
        const dateStr = row.ann_date
        if (!dateStr || dateStr.length !== 8) return dateStr
        return `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`
      }
    },
    {
      key: 'end_date',
      header: '报告期',
      accessor: (row) => {
        const dateStr = row.end_date
        if (!dateStr || dateStr.length !== 8) return dateStr
        return `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`
      }
    },
    {
      key: 'audit_result',
      header: '审计结果',
      accessor: (row) => row.audit_result || '-'
    },
    {
      key: 'audit_fees',
      header: '审计费用(元)',
      accessor: (row) => {
        if (row.audit_fees === null || row.audit_fees === undefined) return '-'
        return row.audit_fees.toLocaleString('zh-CN', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2
        })
      }
    },
    {
      key: 'audit_agency',
      header: '会计事务所',
      accessor: (row) => row.audit_agency || '-'
    },
    {
      key: 'audit_sign',
      header: '签字会计师',
      accessor: (row) => row.audit_sign || '-'
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: FinaAuditData) => {
    const fmtDate = (dateStr: string) => {
      if (!dateStr || dateStr.length !== 8) return dateStr
      return `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`
    }

    return (
      <div className="p-4 space-y-2">
        <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">股票代码</span>
          <span className="font-medium">{item.ts_code}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">公告日期</span>
          <span>{fmtDate(item.ann_date)}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">报告期</span>
          <span>{fmtDate(item.end_date)}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">审计结果</span>
          <span>{item.audit_result || '-'}</span>
        </div>
        {item.audit_fees !== null && item.audit_fees !== undefined && (
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-400">审计费用</span>
            <span>{item.audit_fees.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} 元</span>
          </div>
        )}
        {item.audit_agency && (
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-400">会计事务所</span>
            <span className="text-right">{item.audit_agency}</span>
          </div>
        )}
        {item.audit_sign && (
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-600 dark:text-gray-400">签字会计师</span>
            <span className="text-right">{item.audit_sign}</span>
          </div>
        )}
      </div>
    )
  }, [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="财务审计意见"
        description="获取上市公司定期财务审计意见数据"
        details={<>
          <div>接口：fina_audit</div>
          <a href="https://tushare.pro/document/2?doc_id=80" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="财务审计意见"
            />
          </div>
        }
      />

      <StatisticsCards items={statsCards} />

      {/* 筛选和操作区域 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
          <CardDescription>输入股票代码（必填）和日期范围进行查询</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="ts-code">股票代码 *</Label>
              <Input id="ts-code" placeholder="例如: 600000.SH" value={tsCode} onChange={(e) => setTsCode(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>公告日期</Label>
              <DatePicker date={annDate} onDateChange={setAnnDate} placeholder="选择公告日期" />
            </div>
            <div className="space-y-2">
              <Label>开始日期</Label>
              <DatePicker date={startDate} onDateChange={setStartDate} placeholder="选择开始日期" />
            </div>
            <div className="space-y-2">
              <Label>结束日期</Label>
              <DatePicker date={endDate} onDateChange={setEndDate} placeholder="选择结束日期" />
            </div>
            <div className="space-y-2">
              <Label>报告期</Label>
              <DatePicker date={period} onDateChange={setPeriod} placeholder="选择报告期" />
            </div>
          </div>
          <div className="flex flex-col sm:flex-row gap-2">
            <Button onClick={dp.handleQuery} disabled={dp.isLoading}>
              {dp.isLoading ? (
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />查询中...</>
              ) : (
                <><RefreshCw className="h-4 w-4 mr-1" />查询数据</>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="pt-6">
          <DataTable
            columns={columns}
            data={dp.data}
            loading={dp.isLoading}
            emptyMessage="暂无数据，请输入股票代码进行查询"
            pagination={{
              page: dp.page,
              pageSize: dp.pageSize,
              total: dp.total,
              onPageChange: dp.handlePageChange,
              onPageSizeChange: dp.handlePageSizeChange,
              pageSizeOptions: [10, 20, 30, 50, 100]
            }}
            mobileCard={mobileCard}
          />
        </CardContent>
      </Card>

      {/* 同步弹窗 */}
      <SyncDialog
        open={dp.syncDialogOpen}
        onOpenChange={dp.setSyncDialogOpen}
        onConfirm={dp.handleSyncConfirm}
        title="同步财务审计意见"
        description="将从 Tushare 增量同步最新财务审计意见数据，无需选择日期。"
        disabled={dp.syncing}
      />
    </div>
  )
}
