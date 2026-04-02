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
import { ccassHoldApi, type CcassHoldData, type CcassHoldStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { RefreshCw, TrendingUp, Users, Percent, Database, ListFilter } from 'lucide-react'

const toDateStr = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

export default function CcassHoldPage() {
  const [data, setData] = useState<CcassHoldData[]>([])
  const [statistics, setStatistics] = useState<CcassHoldStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc' | null>(null)

  // 查询条件
  const [tsCode, setTsCode] = useState('')
  const [hkCode, setHkCode] = useState('')
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)

  // 同步对话框
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  const syncing = isTaskRunning('tasks.sync_ccass_hold')

  const PAGE_SIZE = 100

  const loadData = useCallback(async (targetPage = 1, overrideSortKey = sortKey, overrideSortDir = sortDirection) => {
    setIsLoading(true)
    try {
      const params: any = { page: targetPage, page_size: PAGE_SIZE }
      if (tsCode) params.ts_code = tsCode
      if (hkCode) params.hk_code = hkCode
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      if (overrideSortKey) {
        params.sort_by = overrideSortKey
        params.sort_order = overrideSortDir ?? 'desc'
      }

      const response = await ccassHoldApi.getData(params)
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
  }, [tsCode, hkCode, tradeDate, sortKey, sortDirection])

  useEffect(() => {
    loadData(1)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)

    const params: any = {}
    if (syncStartDate) params.start_date = toDateStr(syncStartDate)
    if (syncEndDate) params.end_date = toDateStr(syncEndDate)

    const response = await ccassHoldApi.syncAsync(params)
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
    }
  }, [unregisterCompletionCallback])

  const formatNumber = (value: number | null | undefined, decimals = 0): string => {
    if (value === null || value === undefined) return '-'
    return value.toLocaleString('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
  }

  const columns = useMemo((): Column<CcassHoldData>[] => [
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
      header: '港交所代码',
      accessor: (row) => row.hk_code || '-',
      key: 'hk_code',
      width: 100,
      cellClassName: 'whitespace-nowrap font-mono text-xs'
    },
    {
      header: '股票名称',
      accessor: (row) => row.name || '-',
      key: 'name',
    },
    {
      header: '持股量(股)',
      accessor: (row) => formatNumber(row.shareholding),
      key: 'shareholding',
      sortable: true,
      width: 130,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      header: '参与者数目',
      accessor: (row) => formatNumber(row.hold_nums),
      key: 'hold_nums',
      sortable: true,
      width: 110,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      header: '占比(%)',
      accessor: (row) => formatNumber(row.hold_ratio, 2),
      key: 'hold_ratio',
      sortable: true,
      width: 90,
      cellClassName: 'text-right whitespace-nowrap'
    }
  ], [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="中央结算系统持股汇总"
        description="描述：获取中央结算系统持股汇总数据，覆盖全部历史数据，根据交易所披露时间，当日数据在下一交易日早上9点前完成入库"
        details={<>
          <div>接口：ccass_hold</div>
          <a href="https://tushare.pro/document/2?doc_id=295" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <Button onClick={() => setSyncDialogOpen(true)} disabled={syncing}>
            {syncing
              ? <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
              : <><RefreshCw className="h-4 w-4 mr-1" />同步数据</>}
          </Button>
        }
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">平均持股量</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.avg_shareholding)}</p>
                  <p className="text-xs text-gray-400 mt-0.5">股</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">最大持股量</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.max_shareholding)}</p>
                  <p className="text-xs text-gray-400 mt-0.5">股</p>
                </div>
                <Database className="h-6 w-6 sm:h-8 sm:w-8 text-orange-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">平均参与者数</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.avg_hold_nums)}</p>
                  <p className="text-xs text-gray-400 mt-0.5">个</p>
                </div>
                <Users className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">平均占比</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.avg_hold_ratio, 2)}</p>
                  <p className="text-xs text-gray-400 mt-0.5">%</p>
                </div>
                <Percent className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
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
                placeholder="如 000001 或 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value.toUpperCase())}
                className="w-full sm:w-40"
              />
            </div>
            <div className="space-y-1 w-full sm:w-auto">
              <Label htmlFor="hk_code">港交所代码</Label>
              <Input
                id="hk_code"
                placeholder="如 95009"
                value={hkCode}
                onChange={(e) => setHkCode(e.target.value)}
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
                  <span className="font-semibold text-sm">{row.name || row.ts_code}</span>
                  <span className="text-xs text-muted-foreground">{row.trade_date}</span>
                </div>
                <div className="text-xs text-muted-foreground font-mono">{row.ts_code}{row.hk_code ? ` · ${row.hk_code}` : ''}</div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">持股量</span>
                  <span className="font-medium">{formatNumber(row.shareholding)} 股</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">参与者数目</span>
                  <span className="font-medium">{formatNumber(row.hold_nums)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">占比</span>
                  <span className="font-medium">{formatNumber(row.hold_ratio, 2)}%</span>
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
            <DialogTitle>同步中央结算系统持股汇总</DialogTitle>
            <DialogDescription>从Tushare接口同步数据（5000积分/次）。留空则同步最新数据。</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
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
            <Button onClick={handleSyncConfirm} disabled={syncing}>确认同步</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
