'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { stkSurvApi, type StkSurvData, type StkSurvStatistics } from '@/lib/api'
import { apiClient } from '@/lib/api-client'
import { useTaskStore } from '@/stores/task-store'
import { useDataBulkOps } from '@/hooks/useDataBulkOps'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { toast } from 'sonner'
import { RefreshCw, FileText, Building2, Calendar, Users } from 'lucide-react'

const toDateStr = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

export default function StkSurvPage() {
  const [data, setData] = useState<StkSurvData[]>([])
  const [statistics, setStatistics] = useState<StkSurvStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [receMode, setReceMode] = useState('')
  const [orgType, setOrgType] = useState('')

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // 同步对话框状态
  const [showSyncDialog, setShowSyncDialog] = useState(false)
  const [syncTsCode, setSyncTsCode] = useState('')
  const [syncTradeDate, setSyncTradeDate] = useState<Date | undefined>(undefined)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()

  // 从 task store 实时派生 syncing 状态
  const syncing = isTaskRunning('tasks.sync_stk_surv')

  const loadData = useCallback(async (targetPage: number = 1) => {
    try {
      setIsLoading(true)

      const params: any = {
        page: targetPage,
        page_size: pageSize
      }
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (receMode) params.rece_mode = receMode
      if (orgType) params.org_type = orgType

      const response = await stkSurvApi.getData(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics || null)
        setTotal(response.data.total || 0)
        setPage(targetPage)
      } else {
        throw new Error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      toast.error('加载失败', { description: err.message || '加载数据失败' })
    } finally {
      setIsLoading(false)
    }
  }, [startDate, endDate, tsCode, receMode, orgType, pageSize])

  const {
    handleFullSync,
    handleClear,
    fullSyncing,
    isClearing,
    isClearDialogOpen,
    setIsClearDialogOpen,
    cleanup,
    earliestHistoryDate,
  } = useDataBulkOps({
    tableKey: 'stk_surv',
    syncFn: (params) => apiClient.post('/api/stk-surv/sync-async', null, { params }),
    taskName: 'tasks.sync_stk_surv',
    onSuccess: loadData,
  })

  useEffect(() => {
    loadData(1).catch(() => {})
  }, [])

  // 组件卸载时清理回调
  useEffect(() => {
    return () => {
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
      cleanup()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSyncConfirm = async () => {
    setShowSyncDialog(false)

    try {
      const params: any = {}
      if (syncTsCode.trim()) params.ts_code = syncTsCode.trim()
      if (syncTradeDate) params.trade_date = toDateStr(syncTradeDate)
      if (syncStartDate) params.start_date = toDateStr(syncStartDate)
      if (syncEndDate) params.end_date = toDateStr(syncEndDate)

      const response = await stkSurvApi.syncAsync(params)

      if (response.code === 200 && response.data) {
        const taskId = response.data.celery_task_id

        addTask({
          taskId,
          taskName: response.data.task_name,
          displayName: response.data.display_name,
          taskType: 'data_sync',
          status: 'running',
          progress: 0,
          startTime: Date.now()
        })

        const completionCallback = (task: any) => {
          if (task.status === 'success') {
            loadData(1).catch(() => {})
            toast.success('数据同步完成', { description: '机构调研数据已更新' })
          } else if (task.status === 'failure') {
            toast.error('数据同步失败', { description: task.error || '同步过程中发生错误' })
          }
          unregisterCompletionCallback(taskId, completionCallback)
          activeCallbacksRef.current.delete(taskId)
        }

        activeCallbacksRef.current.set(taskId, completionCallback)
        registerCompletionCallback(taskId, completionCallback)
        triggerPoll()

        toast.success('任务已提交', {
          description: `"${response.data.display_name}" 已开始执行，可在任务面板查看进度`
        })
      } else {
        throw new Error(response.message || '同步失败')
      }
    } catch (err: any) {
      toast.error('同步失败', { description: err.message || '无法同步数据' })
    }
  }

  const truncateText = (text: string | null | undefined, maxLength: number = 30): string => {
    if (!text) return '-'
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text
  }

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
            <Button onClick={() => setShowSyncDialog(true)} disabled={syncing}>
              {syncing ? (
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
              ) : (
                <><RefreshCw className="h-4 w-4 mr-1" />同步数据</>
              )}
            </Button>
            <BulkOpsButtons
              onFullSync={handleFullSync}
              onClearConfirm={handleClear}
              isClearDialogOpen={isClearDialogOpen}
              setIsClearDialogOpen={setIsClearDialogOpen}
              fullSyncing={fullSyncing}
              isClearing={isClearing}
              earliestHistoryDate={earliestHistoryDate}
              tableName="机构调研"
            />
          </div>
        }
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">总记录数</p>
                  <p className="text-2xl font-bold mt-1">{statistics.total_records.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground mt-1">条调研记录</p>
                </div>
                <FileText className="h-8 w-8 text-muted-foreground shrink-0" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">股票数</p>
                  <p className="text-2xl font-bold mt-1">{statistics.unique_stocks.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground mt-1">个上市公司</p>
                </div>
                <Building2 className="h-8 w-8 text-muted-foreground shrink-0" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">调研日期数</p>
                  <p className="text-2xl font-bold mt-1">{statistics.unique_dates.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground mt-1">天</p>
                </div>
                <Calendar className="h-8 w-8 text-muted-foreground shrink-0" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">机构类型数</p>
                  <p className="text-2xl font-bold mt-1">{statistics.unique_org_types.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground mt-1">种机构类型</p>
                </div>
                <Users className="h-8 w-8 text-muted-foreground shrink-0" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

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
              <Button onClick={() => loadData(1)} disabled={isLoading} className="w-full sm:w-auto">
                {isLoading ? '查询中...' : '查询'}
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
            data={data}
            loading={isLoading}
            emptyMessage="暂无数据"
            mobileCard={mobileCard}
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: (newPage) => loadData(newPage),
              onPageSizeChange: () => {},
              pageSizeOptions: [30]
            }}
          />
        </CardContent>
      </Card>

      {/* 同步对话框 */}
      <Dialog open={showSyncDialog} onOpenChange={setShowSyncDialog}>
        <DialogContent className="sm:max-w-[450px]">
          <DialogHeader>
            <DialogTitle>同步机构调研数据</DialogTitle>
            <DialogDescription>
              所有参数均为可选，不填写参数将同步最新数据
            </DialogDescription>
          </DialogHeader>

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
                <DatePicker date={syncStartDate} onDateChange={setSyncStartDate} placeholder="开始日期" />
                <span className="text-muted-foreground">至</span>
                <DatePicker date={syncEndDate} onDateChange={setSyncEndDate} placeholder="结束日期" />
              </div>
            </div>

            <div className="rounded-lg bg-amber-50 dark:bg-amber-950 p-3 border border-amber-200 dark:border-amber-800">
              <p className="text-sm text-amber-800 dark:text-amber-200">
                <strong>注意：</strong>此接口消耗 5000 积分，单次最大返回 100 条数据。
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setShowSyncDialog(false)}>取消</Button>
            <Button onClick={handleSyncConfirm} disabled={syncing}>
              {syncing ? (
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
              ) : (
                <><RefreshCw className="h-4 w-4 mr-1" />开始同步</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
