'use client'

import { useState, useEffect, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { dcIndexApi, type DcIndexData, type DcIndexStatistics } from '@/lib/api'
import { apiClient } from '@/lib/api-client'
import { useTaskStore } from '@/stores/task-store'
import { pctChangeColor, formatStockCode } from '@/lib/utils'
import { useSystemConfig } from '@/contexts'
import { useDataBulkOps } from '@/hooks/useDataBulkOps'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { toast } from 'sonner'
import { RefreshCw, Database, Calendar, Layers, TrendingUp, AlertTriangle, ListFilter } from 'lucide-react'

const PAGE_SIZE = 100

const IDX_TYPE_OPTIONS = [
  { value: '概念板块', label: '概念板块' },
  { value: '行业板块', label: '行业板块' },
  { value: '地域板块', label: '地域板块' },
]

export default function DcIndexPage() {
  const [data, setData] = useState<DcIndexData[]>([])
  const [statistics, setStatistics] = useState<DcIndexStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [idxType, setIdxType] = useState<string>('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc' | null>(null)

  // 同步对话框
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncIdxType, setSyncIdxType] = useState<string>('概念板块')
  const [syncTsCode, setSyncTsCode] = useState<string>('')
  const [syncName, setSyncName] = useState<string>('')
  const [syncTradeDate, setSyncTradeDate] = useState<Date | undefined>(undefined)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const syncing = isTaskRunning('tasks.sync_dc_index')
  const { config } = useSystemConfig()

  const openStockAnalysis = (tsCode: string) => {
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(tsCode)), '_blank')
  }

  useEffect(() => {
    loadData(1).catch(() => {})
  }, [])

  const tradeDateStr = (d: Date | undefined) => d
    ? `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    : undefined

  const loadData = async (
    targetPage: number = page,
    overrideSortKey?: string | null,
    overrideSortDir?: 'asc' | 'desc' | null
  ) => {
    setIsLoading(true)
    try {
      const dateStr = tradeDateStr(tradeDate)
      const params = {
        trade_date: dateStr,
        idx_type: idxType || undefined,
        page: targetPage,
        page_size: PAGE_SIZE,
        sort_by: (overrideSortKey !== undefined ? overrideSortKey : sortKey) ?? undefined,
        sort_order: (overrideSortDir !== undefined ? overrideSortDir : sortDirection) ?? undefined,
      }

      const [dataResponse, statsResponse] = await Promise.all([
        dcIndexApi.getData(params),
        dcIndexApi.getStatistics({ trade_date: dateStr, idx_type: idxType || undefined })
      ])

      if (dataResponse.code === 200 && dataResponse.data) {
        setData(dataResponse.data.items)
        setTotal(dataResponse.data.total)
        setPage(targetPage)
        // 回填后端解析的实际日期
        if (!tradeDate && dataResponse.data.trade_date) {
          setTradeDate(new Date(dataResponse.data.trade_date + 'T00:00:00'))
        }
      }

      if (statsResponse.code === 200 && statsResponse.data) {
        setStatistics(statsResponse.data)
      }
    } catch (error: any) {
      toast.error(error.message || '加载数据失败')
    } finally {
      setIsLoading(false)
    }
  }

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
    tableKey: 'dc_index',
    syncFn: (params) => apiClient.post('/api/dc-index/sync-async', null, { params }),
    taskName: 'tasks.sync_dc_index',
    onSuccess: loadData,
  })

  const handleQuery = () => {
    loadData(1).catch(() => {})
  }

  const submitSingleSync = async (idxTypeVal: string, baseParams: any) => {
    const params = { ...baseParams, idx_type: idxTypeVal }
    const response = await dcIndexApi.syncAsync(params)
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
          toast.success(`${idxTypeVal}同步完成`)
        }
        unregisterCompletionCallback(taskId, completionCallback)
        activeCallbacksRef.current.delete(taskId)
      }
      activeCallbacksRef.current.set(taskId, completionCallback)
      registerCompletionCallback(taskId, completionCallback)
      triggerPoll()
    } else {
      throw new Error(response.message || `${idxTypeVal}提交失败`)
    }
  }

  const handleSync = async () => {
    setSyncDialogOpen(false)
    try {
      const baseParams: any = {}
      if (syncTsCode.trim()) baseParams.ts_code = syncTsCode.trim()
      if (syncName.trim()) baseParams.name = syncName.trim()
      if (syncTradeDate) baseParams.trade_date = tradeDateStr(syncTradeDate)
      if (syncStartDate) baseParams.start_date = tradeDateStr(syncStartDate)
      if (syncEndDate) baseParams.end_date = tradeDateStr(syncEndDate)

      if (syncIdxType === 'ALL') {
        const types = IDX_TYPE_OPTIONS.map((o) => o.value)
        for (const t of types) {
          await submitSingleSync(t, baseParams)
        }
        toast.success('已依次提交概念板块、行业板块、地域板块三个同步任务')
      } else {
        await submitSingleSync(syncIdxType, baseParams)
        toast.success('同步任务已提交')
      }
    } catch (error: any) {
      toast.error(error.message || '提交同步任务失败')
    }
  }

  useEffect(() => {
    return () => {
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
      cleanup()
    }
  }, [unregisterCompletionCallback])

  const formatPct = (value: number | null | undefined) => {
    if (value === null || value === undefined) return '-'
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  const columns: Column<DcIndexData>[] = [
    {
      key: 'name',
      header: '板块',
      accessor: (row) => (
        <span className={`font-medium ${pctChangeColor(row.pct_change)}`}>
          {row.name || row.ts_code}[{row.ts_code}]
        </span>
      ),
      width: 200,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'idx_type',
      header: '类型',
      accessor: (row) => row.idx_type || '-',
      width: 90,
      cellClassName: 'whitespace-nowrap text-center'
    },
    {
      key: 'pct_change',
      header: '涨跌幅%',
      accessor: (row) => (
        <span className={pctChangeColor(row.pct_change)}>
          {formatPct(row.pct_change)}
        </span>
      ),
      width: 100,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'leading_stock',
      header: '领涨股',
      accessor: (row) => row.leading_stock && row.leading_code ? (
        <span
          className={`cursor-pointer hover:underline ${pctChangeColor(row.leading_pct)}`}
          onClick={() => openStockAnalysis(row.leading_code!)}
        >
          {row.leading_stock}[{formatStockCode(row.leading_code)}]
        </span>
      ) : (row.leading_stock || '-'),
      width: 160,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'leading_pct',
      header: '领涨幅%',
      accessor: (row) => (
        <span className={pctChangeColor(row.leading_pct)}>
          {formatPct(row.leading_pct)}
        </span>
      ),
      width: 100,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'turnover_rate',
      header: '换手率%',
      accessor: (row) => (
        <span className={pctChangeColor(row.pct_change)}>
          {row.turnover_rate !== null ? row.turnover_rate.toFixed(2) + '%' : '-'}
        </span>
      ),
      width: 100,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'up_num',
      header: '涨/跌',
      accessor: (row) => (
        <span>
          <span className="text-red-600">{row.up_num ?? '-'}</span>
          <span className="text-gray-400 mx-1">/</span>
          <span className="text-green-600">{row.down_num ?? '-'}</span>
        </span>
      ),
      width: 80,
      sortable: true,
      cellClassName: 'text-center whitespace-nowrap'
    },
    {
      key: 'total_mv',
      header: '总市值(亿)',
      accessor: (row) => row.total_mv !== null
        ? (row.total_mv / 10000).toFixed(0) + '亿'
        : '-',
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
  ]

  // 移动端卡片
  const mobileCard = (item: DcIndexData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div className={`font-semibold text-base ${pctChangeColor(item.pct_change)}`}>{item.name || item.ts_code}</div>
          <div className="text-sm text-gray-500">{item.ts_code} · {item.idx_type}</div>
        </div>
        <div className={`font-bold text-base ${pctChangeColor(item.pct_change)}`}>
          {formatPct(item.pct_change)}
        </div>
      </div>
      <div className="space-y-1 text-sm">
        {item.leading_stock && (
          <div className="flex justify-between">
            <span className="text-gray-600">领涨股:</span>
            <span
              className={`cursor-pointer hover:underline ${pctChangeColor(item.leading_pct)}`}
              onClick={() => item.leading_code && openStockAnalysis(item.leading_code)}
            >
              {item.leading_stock}{item.leading_code ? `[${formatStockCode(item.leading_code)}]` : ''}
            </span>
          </div>
        )}
        <div className="flex justify-between">
          <span className="text-gray-600">换手率:</span>
          <span>{item.turnover_rate !== null ? `${item.turnover_rate.toFixed(2)}%` : '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">上涨/下跌:</span>
          <span>
            <span className="text-red-600">{item.up_num ?? '-'}</span>
            <span className="text-gray-400 mx-1">/</span>
            <span className="text-green-600">{item.down_num ?? '-'}</span>
          </span>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="东方财富板块数据"
        description="获取东方财富每个交易日的概念/行业/地域板块行情数据"
        details={<>
          <div>接口：dc_index</div>
          <a href="https://tushare.pro/document/2?doc_id=362" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <div className="flex gap-2">
            <Button onClick={() => setSyncDialogOpen(true)} disabled={syncing}>
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
              tableName="东财板块数据"
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
                  <p className="text-xl sm:text-2xl font-bold">{(statistics.total_records ?? 0).toLocaleString()}</p>
                </div>
                <Database className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">板块数量</p>
                  <p className="text-xl sm:text-2xl font-bold">{(statistics.board_count ?? 0).toLocaleString()}</p>
                </div>
                <Layers className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">日期数量</p>
                  <p className="text-xl sm:text-2xl font-bold">{(statistics.date_count ?? 0).toLocaleString()}</p>
                </div>
                <Calendar className="h-6 w-6 sm:h-8 sm:w-8 text-orange-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">均涨跌幅</p>
                  <p className={`text-xl sm:text-2xl font-bold ${pctChangeColor(statistics.avg_pct_change)}`}>
                    {statistics.avg_pct_change !== null ? formatPct(statistics.avg_pct_change) : '-'}
                  </p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选区域 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ListFilter className="h-5 w-5" />
            数据查询
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">交易日期</label>
              <DatePicker date={tradeDate} onDateChange={setTradeDate} />
            </div>
            <div className="flex-1 min-w-[140px]">
              <label className="text-sm font-medium mb-1 block">板块类型</label>
              <Select value={idxType || 'ALL'} onValueChange={(v) => setIdxType(v === 'ALL' ? '' : v)}>
                <SelectTrigger>
                  <SelectValue placeholder="全部类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部类型</SelectItem>
                  {IDX_TYPE_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <Button onClick={handleQuery} disabled={isLoading} className="flex-1 sm:flex-none">
                查询
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="p-0 sm:p-6">
          <DataTable
            columns={columns}
            data={data}
            loading={isLoading}
            mobileCard={mobileCard}
            tableClassName="table-fixed w-full [&_th]:border-r [&_td]:border-r [&_th:last-child]:border-r-0 [&_td:last-child]:border-r-0 [&_th]:!text-center"
            sort={{
              key: sortKey,
              direction: sortDirection,
              onSort: (key, direction) => {
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
              onPageChange: (newPage) => loadData(newPage)
            }}
          />
        </CardContent>
      </Card>

      {/* 同步参数对话框 */}
      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>同步东方财富板块数据</DialogTitle>
            <DialogDescription>
              配置同步参数后提交后台任务。idx_type 为必填参数。
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="flex items-start gap-2 p-3 bg-yellow-50 dark:bg-yellow-950/20 rounded-md border border-yellow-200 dark:border-yellow-800">
              <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-yellow-700 dark:text-yellow-400">
                每类板块消耗 <strong>6000</strong> 积分，单次最大返回 5000 条。
                选择<strong>全部</strong>将依次提交三个任务，共消耗 <strong>18000</strong> 积分。
              </p>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">板块类型 <span className="text-red-500">*</span></label>
              <Select value={syncIdxType} onValueChange={setSyncIdxType}>
                <SelectTrigger>
                  <SelectValue placeholder="选择板块类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部（概念+行业+地域）</SelectItem>
                  {IDX_TYPE_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">板块代码（可选）</label>
              <Input
                placeholder="如：BK0001"
                value={syncTsCode}
                onChange={(e) => setSyncTsCode(e.target.value)}
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">板块名称（可选）</label>
              <Input
                placeholder="如：人形机器人"
                value={syncName}
                onChange={(e) => setSyncName(e.target.value)}
              />
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">指定交易日期（可选）</label>
              <DatePicker date={syncTradeDate} onDateChange={setSyncTradeDate} />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm font-medium mb-2 block">开始日期（可选）</label>
                <DatePicker date={syncStartDate} onDateChange={setSyncStartDate} />
              </div>
              <div>
                <label className="text-sm font-medium mb-2 block">结束日期（可选）</label>
                <DatePicker date={syncEndDate} onDateChange={setSyncEndDate} />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSync} disabled={syncing || !syncIdxType} className={syncIdxType === 'ALL' ? 'bg-orange-600 hover:bg-orange-700' : ''}>
              {syncing ? (
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />提交中...</>
              ) : (
                '提交同步任务'
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
