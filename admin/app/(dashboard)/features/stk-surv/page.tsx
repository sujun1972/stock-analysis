'use client'

import { useState, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { SyncDialog } from '@/components/common/SyncDialog'
import { StatisticsCards, type StatisticsCardItem } from '@/components/common/StatisticsCards'
import { useDataPage } from '@/hooks/useDataPage'
import { stkSurvApi, type StkSurvData, type StkSurvStatistics } from '@/lib/api'
import { apiClient } from '@/lib/api-client'
import { toDateStr } from '@/lib/date-utils'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { RefreshCw, FileText, Building2, Calendar, Users } from 'lucide-react'

export default function StkSurvPage() {
  // 查询筛选状态
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [receMode, setReceMode] = useState('')
  const [orgType, setOrgType] = useState('')

  // 同步弹窗额外字段
  const [syncTsCode, setSyncTsCode] = useState('')
  const [syncTradeDate, setSyncTradeDate] = useState<Date | undefined>(undefined)

  const dp = useDataPage<StkSurvData, StkSurvStatistics>({
    apiCall: (params) => stkSurvApi.getData(params),
    syncFn: (params) => stkSurvApi.syncAsync(params),
    taskName: 'tasks.sync_stk_surv',
    bulkOps: {
      tableKey: 'stk_surv',
      syncFn: (params) => apiClient.post('/api/stk-surv/sync-async', null, { params }),
      taskName: 'tasks.sync_stk_surv',
    },
    paginationMode: 'page',
    pageSize: 30,
    buildParams: () => {
      const params: Record<string, unknown> = {}
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (receMode) params.rece_mode = receMode
      if (orgType) params.org_type = orgType
      return params
    },
    syncSuccessMessage: '机构调研数据同步完成',
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

  const truncateText = (text: string | null | undefined, maxLength: number = 30): string => {
    if (!text) return '-'
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text
  }

  // 统计卡片
  const statsCards: StatisticsCardItem[] = useMemo(() => {
    if (!dp.statistics) return []
    const s = dp.statistics
    return [
      {
        label: '总记录数',
        value: s.total_records.toLocaleString(),
        subValue: '条调研记录',
        icon: FileText,
        iconColor: 'text-muted-foreground',
      },
      {
        label: '股票数',
        value: s.unique_stocks.toLocaleString(),
        subValue: '个上市公司',
        icon: Building2,
        iconColor: 'text-muted-foreground',
      },
      {
        label: '调研日期数',
        value: s.unique_dates.toLocaleString(),
        subValue: '天',
        icon: Calendar,
        iconColor: 'text-muted-foreground',
      },
      {
        label: '机构类型数',
        value: s.unique_org_types.toLocaleString(),
        subValue: '种机构类型',
        icon: Users,
        iconColor: 'text-muted-foreground',
      },
    ]
  }, [dp.statistics])

  const columns: Column<StkSurvData>[] = useMemo(() => [
    {
      key: 'surv_date',
      header: '调研日期',
      accessor: (row) => row.surv_date
    },
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'name',
      header: '股票名称',
      accessor: (row) => row.name || '-'
    },
    {
      key: 'fund_visitors',
      header: '机构参与人员',
      accessor: (row) => (
        <span className="max-w-xs truncate block" title={row.fund_visitors || ''}>
          {truncateText(row.fund_visitors, 40)}
        </span>
      )
    },
    {
      key: 'rece_mode',
      header: '接待方式',
      accessor: (row) => row.rece_mode || '-'
    },
    {
      key: 'org_type',
      header: '接待公司类型',
      accessor: (row) => row.org_type || '-'
    },
    {
      key: 'rece_place',
      header: '接待地点',
      accessor: (row) => (
        <span className="max-w-xs truncate block" title={row.rece_place || ''}>
          {truncateText(row.rece_place, 30)}
        </span>
      )
    },
    {
      key: 'rece_org',
      header: '接待的公司',
      accessor: (row) => (
        <span className="max-w-xs truncate block" title={row.rece_org || ''}>
          {truncateText(row.rece_org, 30)}
        </span>
      )
    }
  ], [])

  const mobileCard = useCallback((item: StkSurvData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <div>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {item.name || item.ts_code}
          </span>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">{item.ts_code}</div>
        </div>
        <span className="text-xs text-gray-600 dark:text-gray-400">{item.surv_date}</span>
      </div>
      {item.rece_mode && (
        <div className="flex justify-between items-center text-sm">
          <span className="text-gray-600 dark:text-gray-400">接待方式:</span>
          <span className="font-medium">{item.rece_mode}</span>
        </div>
      )}
      {item.org_type && (
        <div className="flex justify-between items-center text-sm">
          <span className="text-gray-600 dark:text-gray-400">接待公司类型:</span>
          <span className="font-medium">{item.org_type}</span>
        </div>
      )}
      {item.fund_visitors && (
        <div className="flex flex-col gap-1">
          <span className="text-sm text-gray-600 dark:text-gray-400">机构参与人员:</span>
          <span className="text-sm text-gray-800 dark:text-gray-200 break-all">
            {truncateText(item.fund_visitors, 50)}
          </span>
        </div>
      )}
      {item.rece_org && (
        <div className="flex flex-col gap-1">
          <span className="text-sm text-gray-600 dark:text-gray-400">接待的公司:</span>
          <span className="text-sm text-gray-800 dark:text-gray-200 break-all">
            {truncateText(item.rece_org, 50)}
          </span>
        </div>
      )}
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="机构调研表"
        description="获取上市公司机构调研记录数据"
        details={
          <>
            <div>接口：stk_surv</div>
            <a href="https://tushare.pro/document/2?doc_id=275" target="_blank" rel="noopener noreferrer">查看文档</a>
          </>
        }
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
              tableName="机构调研"
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
          <div className="flex flex-col gap-4">
            <div className="flex flex-col sm:flex-row gap-4 items-end">
              <div className="flex-1">
                <Label className="mb-2 block">股票代码</Label>
                <Input
                  placeholder="如：000001.SZ"
                  value={tsCode}
                  onChange={(e) => setTsCode(e.target.value)}
                />
              </div>
              <div className="flex-1">
                <Label className="mb-2 block">接待方式</Label>
                <Select value={receMode || 'ALL'} onValueChange={(v) => setReceMode(v === 'ALL' ? '' : v)}>
                  <SelectTrigger><SelectValue placeholder="选择接待方式" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">全部</SelectItem>
                    <SelectItem value="实地调研">实地调研</SelectItem>
                    <SelectItem value="电话会议">电话会议</SelectItem>
                    <SelectItem value="特定对象调研">特定对象调研</SelectItem>
                    <SelectItem value="其他">其他</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="flex-1">
                <Label className="mb-2 block">接待公司类型</Label>
                <Select value={orgType || 'ALL'} onValueChange={(v) => setOrgType(v === 'ALL' ? '' : v)}>
                  <SelectTrigger><SelectValue placeholder="选择公司类型" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">全部</SelectItem>
                    <SelectItem value="证券公司">证券公司</SelectItem>
                    <SelectItem value="基金公司">基金公司</SelectItem>
                    <SelectItem value="保险公司">保险公司</SelectItem>
                    <SelectItem value="阳光私募">阳光私募</SelectItem>
                    <SelectItem value="其他">其他</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="flex flex-col sm:flex-row gap-4 items-end">
              <div className="flex-1">
                <Label className="mb-2 block">开始日期</Label>
                <DatePicker date={startDate} onDateChange={setStartDate} />
              </div>
              <div className="flex-1">
                <Label className="mb-2 block">结束日期</Label>
                <DatePicker date={endDate} onDateChange={setEndDate} />
              </div>
              <Button onClick={dp.handleQuery} disabled={dp.isLoading} className="w-full sm:w-auto">
                {dp.isLoading ? '查询中...' : '查询'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="p-0">
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
        </CardContent>
      </Card>

      {/* 同步对话框 */}
      <SyncDialog
        open={dp.syncDialogOpen}
        onOpenChange={dp.setSyncDialogOpen}
        onConfirm={handleCustomSyncConfirm}
        title="同步机构调研数据"
        description="所有参数均为可选，不填写参数将同步最新数据"
        disabled={dp.syncing}
      >
        <div className="grid gap-4 py-4">
          <div className="grid gap-2">
            <Label htmlFor="sync-ts-code">股票代码</Label>
            <Input
              id="sync-ts-code"
              placeholder="如：000001.SZ"
              value={syncTsCode}
              onChange={(e) => setSyncTsCode(e.target.value)}
            />
          </div>

          <div className="grid gap-2">
            <Label>调研日期</Label>
            <DatePicker date={syncTradeDate} onDateChange={setSyncTradeDate} placeholder="选择调研日期" />
          </div>

          <div className="grid gap-2">
            <Label>日期范围（可选）</Label>
            <div className="flex gap-2 items-center">
              <DatePicker date={dp.syncStartDate} onDateChange={dp.setSyncStartDate} placeholder="开始日期" />
              <span className="text-muted-foreground">至</span>
              <DatePicker date={dp.syncEndDate} onDateChange={dp.setSyncEndDate} placeholder="结束日期" />
            </div>
          </div>

          <div className="rounded-lg bg-amber-50 dark:bg-amber-950 p-3 border border-amber-200 dark:border-amber-800">
            <p className="text-sm text-amber-800 dark:text-amber-200">
              <strong>注意：</strong>此接口消耗 5000 积分，单次最大返回 100 条数据。
            </p>
          </div>
        </div>
      </SyncDialog>
    </div>
  )
}
