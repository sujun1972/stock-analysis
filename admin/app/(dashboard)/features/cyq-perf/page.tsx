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
import { cyqPerfApi, type CyqPerfData, type CyqPerfStatistics } from '@/lib/api'
import { apiClient } from '@/lib/api-client'
import { useTaskStore } from '@/stores/task-store'
import { useDataBulkOps } from '@/hooks/useDataBulkOps'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { RefreshCw, TrendingUp, TrendingDown, BarChart3, DollarSign, ListFilter } from 'lucide-react'

const toDateStr = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

export default function CyqPerfPage() {
  const [data, setData] = useState<CyqPerfData[]>([])
  const [statistics, setStatistics] = useState<CyqPerfStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc' | null>(null)

  // 查询条件
  const [tsCode, setTsCode] = useState('')
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)

  // 同步对话框
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncTsCode, setSyncTsCode] = useState('')
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  const syncing = isTaskRunning('tasks.sync_cyq_perf')

  const PAGE_SIZE = 100

  const loadData = useCallback(async (targetPage = 1, overrideSortKey = sortKey, overrideSortDir = sortDirection) => {
    setIsLoading(true)
    try {
      const params: any = { page: targetPage, page_size: PAGE_SIZE }
      if (tsCode) params.ts_code = tsCode
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      if (overrideSortKey) {
        params.sort_by = overrideSortKey
        params.sort_order = overrideSortDir ?? 'desc'
      }

      const response = await cyqPerfApi.getData(params)
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
  }, [tsCode, tradeDate, sortKey, sortDirection])

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
    tableKey: 'cyq_perf',
    syncFn: (params) => apiClient.post('/api/cyq-perf/sync-async', null, { params }),
    taskName: 'tasks.sync_cyq_perf',
    onSuccess: loadData,
  })

  useEffect(() => {
    loadData(1)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSyncConfirm = async () => {
    if (!syncTsCode) {
      toast.error('请输入股票代码')
      return
    }
    setSyncDialogOpen(false)

    const params: any = { ts_code: syncTsCode }
    if (syncStartDate) params.start_date = toDateStr(syncStartDate)
    if (syncEndDate) params.end_date = toDateStr(syncEndDate)

    const response = await cyqPerfApi.syncAsync(params)
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

  const columns = useMemo((): Column<CyqPerfData>[] => [
    {
      header: '股票代码',
      accessor: (row) => row.ts_code,
      key: 'ts_code',
      width: 110,
      cellClassName: 'whitespace-nowrap font-mono text-xs'
    },
    {
      header: '交易日期',
      accessor: (row) => {
        const d = row.trade_date
        if (!d || d.length !== 8) return d
        return `${d.slice(0, 4)}-${d.slice(4, 6)}-${d.slice(6, 8)}`
      },
      key: 'trade_date',
      sortable: true,
      width: 100,
      cellClassName: 'whitespace-nowrap'
    },
    {
      header: '历史最低',
      accessor: (row) => row.his_low?.toFixed(2) ?? '-',
      key: 'his_low',
      width: 85,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      header: '历史最高',
      accessor: (row) => row.his_high?.toFixed(2) ?? '-',
      key: 'his_high',
      width: 85,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      header: '5%成本',
      accessor: (row) => row.cost_5pct?.toFixed(2) ?? '-',
      key: 'cost_5pct',
      width: 75,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      header: '15%成本',
      accessor: (row) => row.cost_15pct?.toFixed(2) ?? '-',
      key: 'cost_15pct',
      width: 80,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      header: '50%成本',
      accessor: (row) => row.cost_50pct?.toFixed(2) ?? '-',
      key: 'cost_50pct',
      sortable: true,
      width: 80,
      cellClassName: 'text-right whitespace-nowrap font-semibold'
    },
    {
      header: '85%成本',
      accessor: (row) => row.cost_85pct?.toFixed(2) ?? '-',
      key: 'cost_85pct',
      width: 80,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      header: '95%成本',
      accessor: (row) => row.cost_95pct?.toFixed(2) ?? '-',
      key: 'cost_95pct',
      width: 80,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      header: '加权均成本',
      accessor: (row) => row.weight_avg?.toFixed(2) ?? '-',
      key: 'weight_avg',
      sortable: true,
      width: 95,
      cellClassName: 'text-right whitespace-nowrap font-semibold'
    },
    {
      header: '胜率(%)',
      accessor: (row) => {
        const rate = row.winner_rate
        if (rate === null || rate === undefined) return <span>-</span>
        const cls = rate >= 60 ? 'text-red-600 font-semibold' : rate <= 40 ? 'text-green-600 font-semibold' : 'font-semibold'
        return <span className={cls}>{rate.toFixed(2)}%</span>
      },
      key: 'winner_rate',
      sortable: true,
      width: 85,
      cellClassName: 'text-right whitespace-nowrap'
    }
  ], [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="每日筹码及胜率"
        description="获取A股每日筹码平均成本和胜率情况，每天18~19点左右更新，数据从2018年开始"
        details={<>
          <div>接口：cyq_perf</div>
          <a href="https://tushare.pro/document/2?doc_id=293" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="每日筹码及胜率"
            />
          </div>
        }
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">平均胜率</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.avg_winner_rate?.toFixed(2) ?? 0}%</div>
              <p className="text-xs text-muted-foreground mt-1">筛选范围内平均</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最高胜率</CardTitle>
              <TrendingUp className="h-4 w-4 text-red-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{statistics.max_winner_rate?.toFixed(2) ?? 0}%</div>
              <p className="text-xs text-muted-foreground mt-1">胜率最高值</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最低胜率</CardTitle>
              <TrendingDown className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{statistics.min_winner_rate?.toFixed(2) ?? 0}%</div>
              <p className="text-xs text-muted-foreground mt-1">胜率最低值</p>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">加权均成本</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">¥{statistics.avg_cost?.toFixed(2) ?? 0}</div>
              <p className="text-xs text-muted-foreground mt-1">平均加权成本</p>
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
                placeholder="如 000001 或 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value.toUpperCase())}
                className="w-full sm:w-40"
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
                  <span className="font-semibold text-sm">{row.ts_code}</span>
                  <span className="text-xs text-muted-foreground">
                    {row.trade_date?.length === 8
                      ? `${row.trade_date.slice(0,4)}-${row.trade_date.slice(4,6)}-${row.trade_date.slice(6,8)}`
                      : row.trade_date}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                  <div className="flex justify-between"><span className="text-muted-foreground">50%成本</span><span className="font-medium">{row.cost_50pct?.toFixed(2) ?? '-'}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">加权均</span><span className="font-medium">{row.weight_avg?.toFixed(2) ?? '-'}</span></div>
                  <div className="flex justify-between"><span className="text-muted-foreground">胜率</span>
                    <span className={`font-semibold ${(row.winner_rate ?? 0) >= 60 ? 'text-red-600' : (row.winner_rate ?? 0) <= 40 ? 'text-green-600' : ''}`}>
                      {row.winner_rate?.toFixed(2) ?? '-'}%
                    </span>
                  </div>
                  <div className="flex justify-between"><span className="text-muted-foreground">历史区间</span><span>{row.his_low?.toFixed(2) ?? '-'} - {row.his_high?.toFixed(2) ?? '-'}</span></div>
                </div>
              </div>
            )}
          />
        </CardContent>
      </Card>

      {/* 同步对话框 */}
      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>同步筹码及胜率数据</DialogTitle>
            <DialogDescription>从Tushare接口同步数据（5000积分/次）。股票代码必填。</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-1">
              <Label>股票代码 *</Label>
              <Input
                placeholder="如 000001.SZ"
                value={syncTsCode}
                onChange={(e) => setSyncTsCode(e.target.value.toUpperCase())}
              />
            </div>
            <div className="space-y-1">
              <Label>开始日期（可选）</Label>
              <DatePicker date={syncStartDate} onDateChange={setSyncStartDate} placeholder="留空从最早日期开始" />
            </div>
            <div className="space-y-1">
              <Label>结束日期（可选）</Label>
              <DatePicker date={syncEndDate} onDateChange={setSyncEndDate} placeholder="留空同步到最新日期" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncDialogOpen(false)}>取消</Button>
            <Button onClick={handleSyncConfirm} disabled={syncing || !syncTsCode}>确认同步</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
