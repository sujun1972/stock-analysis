'use client'

import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { toast } from 'sonner'
import { ccassHoldDetailApi, type CcassHoldDetailData, type CcassHoldDetailStatistics } from '@/lib/api'
import { apiClient } from '@/lib/api-client'
import { useTaskStore } from '@/stores/task-store'
import { useDataBulkOps } from '@/hooks/useDataBulkOps'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { RefreshCw, TrendingUp, Users, Calendar, Database, ListFilter } from 'lucide-react'

const toDateStr = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

export default function CcassHoldDetailPage() {
  const [data, setData] = useState<CcassHoldDetailData[]>([])
  const [statistics, setStatistics] = useState<CcassHoldDetailStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc' | null>(null)

  // 查询条件
  const [tsCode, setTsCode] = useState('')
  const [participantId, setParticipantId] = useState('')
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)

  // 同步对话框
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncTsCode, setSyncTsCode] = useState('')
  const [syncHkCode, setSyncHkCode] = useState('')
  const [syncTradeDate, setSyncTradeDate] = useState<Date | undefined>(undefined)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  const syncing = isTaskRunning('tasks.sync_ccass_hold_detail')

  const PAGE_SIZE = 100

  const loadData = useCallback(async (targetPage = 1, overrideSortKey = sortKey, overrideSortDir = sortDirection) => {
    setIsLoading(true)
    try {
      const params: any = { page: targetPage, page_size: PAGE_SIZE }
      if (tsCode) params.ts_code = tsCode
      if (participantId) params.col_participant_id = participantId
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      if (overrideSortKey) {
        params.sort_by = overrideSortKey
        params.sort_order = overrideSortDir ?? 'desc'
      }

      const response = await ccassHoldDetailApi.getData(params)
      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setTotal(response.data.total || 0)
        setStatistics(response.data.statistics || null)
        setPage(targetPage)

        // 初次加载且未选日期时，回填后端解析的默认日期
        if (!tradeDate && response.data.trade_date) {
          setTradeDate(new Date(response.data.trade_date + 'T00:00:00'))
        }
      }
    } catch (error: any) {
      toast.error(error.message || '加载数据失败')
    } finally {
      setIsLoading(false)
    }
  }, [tsCode, participantId, tradeDate, sortKey, sortDirection])

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
    tableKey: 'ccass_hold_detail',
    syncFn: (params) => apiClient.post('/api/ccass-hold-detail/sync-async', null, { params }),
    taskName: 'tasks.sync_ccass_hold_detail',
    onSuccess: loadData,
  })

  useEffect(() => {
    loadData(1)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const closeSyncDialog = () => {
    setSyncDialogOpen(false)
    setSyncTsCode('')
    setSyncHkCode('')
    setSyncTradeDate(undefined)
    setSyncStartDate(undefined)
    setSyncEndDate(undefined)
  }

  const handleSyncConfirm = async () => {
    const hasTsCode = syncTsCode.trim() !== ''
    const hasHkCode = syncHkCode.trim() !== ''
    const hasTradeDate = syncTradeDate !== undefined
    const hasDateRange = syncStartDate !== undefined || syncEndDate !== undefined

    if (!hasTsCode && !hasHkCode && !hasTradeDate && !hasDateRange) {
      toast.error('请至少填写股票代码、港交所代码、交易日期或日期范围中的一个')
      return
    }

    closeSyncDialog()

    const params: any = {}
    if (syncTsCode.trim()) params.ts_code = syncTsCode.trim()
    if (syncHkCode.trim()) params.hk_code = syncHkCode.trim()
    if (syncTradeDate) params.trade_date = toDateStr(syncTradeDate)
    if (syncStartDate) params.start_date = toDateStr(syncStartDate)
    if (syncEndDate) params.end_date = toDateStr(syncEndDate)

    const response = await ccassHoldDetailApi.syncAsync(params)
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
          toast.success('数据同步完成')
        }
        unregisterCompletionCallback(taskId, completionCallback)
        activeCallbacksRef.current.delete(taskId)
      }
      activeCallbacksRef.current.set(taskId, completionCallback)
      registerCompletionCallback(taskId, completionCallback)
      triggerPoll()
    }
  }

  useEffect(() => {
    return () => {
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((cb, taskId) => unregisterCompletionCallback(taskId, cb))
      callbacks.clear()
      cleanup()
    }
  }, [unregisterCompletionCallback])

  const formatNumber = (value: number | null | undefined, decimals = 0): string => {
    if (value === null || value === undefined) return '-'
    return value.toLocaleString('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
  }

  const columns = useMemo((): Column<CcassHoldDetailData>[] => [
    {
      header: '交易日期',
      accessor: (row) => row.trade_date,
      key: 'trade_date',
      sortable: true,
      width: 110,
      cellClassName: 'whitespace-nowrap'
    },
    {
      header: '股票代码',
      accessor: (row) => row.ts_code,
      key: 'ts_code',
      sortable: true,
      width: 110,
      cellClassName: 'whitespace-nowrap font-mono text-xs'
    },
    {
      header: '股票名称',
      accessor: (row) => row.name || '-',
      key: 'name',
      width: 100
    },
    {
      header: '参与者编号',
      accessor: (row) => row.col_participant_id,
      key: 'col_participant_id',
      width: 110,
      cellClassName: 'whitespace-nowrap font-mono text-xs'
    },
    {
      header: '机构名称',
      accessor: (row) => row.col_participant_name || '-',
      key: 'col_participant_name',
      width: 160
    },
    {
      header: '持股量(股)',
      accessor: (row) => formatNumber(row.col_shareholding),
      key: 'col_shareholding',
      sortable: true,
      width: 130,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      header: '持股比例(%)',
      accessor: (row) => formatNumber(row.col_shareholding_percent, 2),
      key: 'col_shareholding_percent',
      sortable: true,
      width: 110,
      cellClassName: 'text-right whitespace-nowrap'
    }
  ], [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="中央结算系统持股明细"
        description="获取中央结算系统机构席位持股明细，数据覆盖全历史，根据交易所披露时间，当日数据在下一交易日早上9点前完成"
        details={<>
          <div>接口：ccass_hold_detail</div>
          <a href="https://tushare.pro/document/2?doc_id=274" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <div className="flex gap-2">
            <Button onClick={() => setSyncDialogOpen(true)} disabled={syncing}>
              {syncing
                ? <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
                : <><RefreshCw className="h-4 w-4 mr-1" />同步数据</>}
            </Button>
            <BulkOpsButtons
              onFullSync={handleFullSync}
              onClearConfirm={handleClear}
              isClearDialogOpen={isClearDialogOpen}
              setIsClearDialogOpen={setIsClearDialogOpen}
              fullSyncing={fullSyncing}
              isClearing={isClearing}
              earliestHistoryDate={earliestHistoryDate}
              tableName="CCASS持股明细"
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
                  <p className="text-xs sm:text-sm text-gray-600">总记录数</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.total_records)}</p>
                  <p className="text-xs text-gray-400 mt-0.5">条</p>
                </div>
                <Database className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">交易日数</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.trading_days)}</p>
                  <p className="text-xs text-gray-400 mt-0.5">天</p>
                </div>
                <Calendar className="h-6 w-6 sm:h-8 sm:w-8 text-orange-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">股票数</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.stock_count)}</p>
                  <p className="text-xs text-gray-400 mt-0.5">只</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">机构数</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.participant_count)}</p>
                  <p className="text-xs text-gray-400 mt-0.5">个</p>
                </div>
                <Users className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 查询筛选 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ListFilter className="h-4 w-4" />
            数据查询
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="space-y-1 w-full sm:w-auto">
              <Label htmlFor="ts_code">股票代码</Label>
              <Input
                id="ts_code"
                placeholder="如 00960.HK"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value.toUpperCase())}
                className="w-full sm:w-40"
              />
            </div>
            <div className="space-y-1 w-full sm:w-auto">
              <Label htmlFor="participant_id">参与者编号</Label>
              <Input
                id="participant_id"
                placeholder="如 C00001"
                value={participantId}
                onChange={(e) => setParticipantId(e.target.value)}
                className="w-full sm:w-32"
              />
            </div>
            <div className="space-y-1">
              <Label>交易日期</Label>
              <DatePicker date={tradeDate} onDateChange={setTradeDate} placeholder="留空加载最新" />
            </div>
            <Button onClick={() => loadData(1)} disabled={isLoading}>
              {isLoading ? '查询中...' : '查询'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="pt-4">
          <DataTable
            columns={columns}
            data={data}
            loading={isLoading}
            emptyMessage="暂无数据"
            tableClassName="table-fixed w-full [&_th]:border-r [&_th]:border-gray-200 [&_td]:border-r [&_td]:border-gray-100 [&_th:last-child]:border-r-0 [&_td:last-child]:border-r-0"
            sort={{
              key: sortKey,
              direction: sortDirection,
              onSort: (key: string, direction: 'asc' | 'desc' | null) => {
                const newKey = direction ? key : null
                setSortKey(newKey)
                setSortDirection(direction)
                loadData(1, newKey, direction)
              }
            }}
            pagination={{
              page,
              pageSize: PAGE_SIZE,
              total,
              onPageChange: (p) => loadData(p)
            }}
            mobileCard={(row) => (
              <div className="p-4 space-y-2">
                <div className="flex justify-between items-center">
                  <div>
                    <div className="font-semibold text-sm">{row.name || row.ts_code}</div>
                    <div className="text-xs text-muted-foreground font-mono">{row.col_participant_id}{row.col_participant_name ? ` · ${row.col_participant_name}` : ''}</div>
                  </div>
                  <span className="text-xs text-muted-foreground">{row.trade_date}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">股票代码</span>
                  <span className="font-medium font-mono text-xs">{row.ts_code}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">持股量</span>
                  <span className="font-medium">{formatNumber(row.col_shareholding)} 股</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">持股比例</span>
                  <span className="font-medium">{formatNumber(row.col_shareholding_percent, 2)}%</span>
                </div>
              </div>
            )}
          />
        </CardContent>
      </Card>

      {/* 同步对话框 */}
      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>同步中央结算系统持股明细</DialogTitle>
            <DialogDescription>
              请至少填写一个参数（股票代码、港交所代码、交易日期或日期范围）。消耗 8000 积分/次，单次最大 6000 条。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-1">
              <Label>股票代码</Label>
              <Input
                placeholder="如：00960.HK"
                value={syncTsCode}
                onChange={(e) => setSyncTsCode(e.target.value.toUpperCase())}
              />
              <p className="text-xs text-muted-foreground">港股代码格式，如：00960.HK</p>
            </div>
            <div className="space-y-1">
              <Label>港交所代码</Label>
              <Input
                placeholder="如：95009"
                value={syncHkCode}
                onChange={(e) => setSyncHkCode(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label>交易日期（可选）</Label>
              <DatePicker date={syncTradeDate} onDateChange={setSyncTradeDate} placeholder="选择交易日期" />
            </div>
            <div className="space-y-1">
              <Label>日期范围（可选）</Label>
              <div className="flex gap-2 items-center">
                <DatePicker date={syncStartDate} onDateChange={setSyncStartDate} placeholder="开始日期" />
                <span className="text-muted-foreground">至</span>
                <DatePicker date={syncEndDate} onDateChange={setSyncEndDate} placeholder="结束日期" />
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={closeSyncDialog}>取消</Button>
            <Button
              onClick={handleSyncConfirm}
              disabled={syncing || (!syncTsCode.trim() && !syncHkCode.trim() && !syncTradeDate && !syncStartDate && !syncEndDate)}
            >
              确认同步
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
