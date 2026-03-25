'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
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
import { dcIndexApi, type DcIndexData, type DcIndexStatistics } from '@/lib/api'
import { useTaskStore, type Task } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, Database, Calendar, Layers, TrendingUp, AlertTriangle } from 'lucide-react'

const IDX_TYPE_OPTIONS = [
  { value: '概念板块', label: '概念板块' },
  { value: '行业板块', label: '行业板块' },
  { value: '地域板块', label: '地域板块' },
]

export default function DcIndexPage() {
  const [data, setData] = useState<DcIndexData[]>([])
  const [statistics, setStatistics] = useState<DcIndexStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState<string>('')
  const [nameFilter, setNameFilter] = useState<string>('')
  const [idxType, setIdxType] = useState<string>('')
  // 同步对话框状态
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncTsCode, setSyncTsCode] = useState<string>('')
  const [syncName, setSyncName] = useState<string>('')
  const [syncIdxType, setSyncIdxType] = useState<string>('概念板块')
  const [syncTradeDate, setSyncTradeDate] = useState<Date | undefined>(undefined)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const syncing = isTaskRunning('tasks.sync_dc_index')

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)

      const params: any = { limit: pageSize }

      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (nameFilter.trim()) params.name = nameFilter.trim()
      if (idxType) params.idx_type = idxType

      const response = await dcIndexApi.getData(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setTotal(response.data.total || 0)
      } else {
        throw new Error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      const errorMsg = err.message || '加载数据失败'
      setError(errorMsg)
      toast.error('加载失败', { description: errorMsg })
    } finally {
      setIsLoading(false)
    }
  }, [startDate, endDate, tsCode, nameFilter, idxType, pageSize])

  const loadStatistics = useCallback(async () => {
    try {
      const params: any = {}
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (idxType) params.idx_type = idxType

      const response = await dcIndexApi.getStatistics(params)
      if (response.code === 200 && response.data) {
        setStatistics(response.data)
      }
    } catch (err: any) {
      // 统计信息加载失败不阻断主流程
    }
  }, [startDate, endDate, tsCode, idxType])

  useEffect(() => {
    loadData()
    loadStatistics()
  }, [])

  const handleSync = async () => {
    try {
      setSyncDialogOpen(false)

      const params: any = { idx_type: syncIdxType }
      if (syncTsCode.trim()) params.ts_code = syncTsCode.trim()
      if (syncName.trim()) params.name = syncName.trim()
      if (syncTradeDate) params.trade_date = syncTradeDate.toISOString().split('T')[0]
      if (syncStartDate) params.start_date = syncStartDate.toISOString().split('T')[0]
      if (syncEndDate) params.end_date = syncEndDate.toISOString().split('T')[0]

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

        const callback = (task: Task) => {
          if (task.taskId === taskId && task.status === 'success') {
            setTimeout(() => {
              loadData().catch(() => {})
              loadStatistics().catch(() => {})
            }, 1000)
            activeCallbacksRef.current.delete(taskId)
            unregisterCompletionCallback(taskId, callback)
          }
        }

        activeCallbacksRef.current.set(taskId, callback)
        registerCompletionCallback(taskId, callback)
        triggerPoll()

        toast.success('同步任务已提交', {
          description: `"${response.data.display_name}" 已开始执行，可在任务面板查看进度`
        })

        setTimeout(() => loadData().catch(() => {}), 3000)
      } else {
        throw new Error(response.message || '同步失败')
      }
    } catch (err: any) {
      toast.error('同步失败', {
        description: err.message || '无法同步数据'
      })
    }
  }

  useEffect(() => {
    return () => {
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const formatNumber = (value: number | null | undefined, decimals: number = 2): string => {
    if (value === null || value === undefined) return '-'
    return value.toLocaleString('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
  }

  const formatDate = (dateStr: string | null | undefined): string => {
    if (!dateStr || dateStr.length !== 8) return '-'
    return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
  }

  const formatPct = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return '-'
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  const getPctColor = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return ''
    return value >= 0 ? 'text-red-600' : 'text-green-600'
  }

  const mobileCard = useCallback((item: DcIndexData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <div>
          <span className="text-sm font-medium">{item.name || item.ts_code}</span>
          {item.idx_type && (
            <span className="ml-2 text-xs text-muted-foreground">{item.idx_type}</span>
          )}
        </div>
        <span className={`font-bold text-sm ${getPctColor(item.pct_change)}`}>
          {formatPct(item.pct_change)}
        </span>
      </div>

      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">板块代码</span>
        <span className="font-medium text-sm">{item.ts_code}</span>
      </div>

      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">交易日期</span>
        <span className="font-medium text-sm">{formatDate(item.trade_date)}</span>
      </div>

      {item.leading_stock && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">领涨股</span>
          <span className="font-medium text-sm">
            {item.leading_stock}
            {item.leading_pct !== null && item.leading_pct !== undefined && (
              <span className={`ml-1 text-xs ${getPctColor(item.leading_pct)}`}>
                {formatPct(item.leading_pct)}
              </span>
            )}
          </span>
        </div>
      )}

      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">换手率</span>
        <span className="font-medium text-sm">{item.turnover_rate != null ? `${formatNumber(item.turnover_rate)}%` : '-'}</span>
      </div>

      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">上涨/下跌</span>
        <span className="font-medium text-sm">
          <span className="text-red-600">{item.up_num ?? '-'}</span>
          <span className="text-gray-400 mx-1">/</span>
          <span className="text-green-600">{item.down_num ?? '-'}</span>
        </span>
      </div>
    </div>
  ), [])

  const columns: Column<DcIndexData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '板块代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'name',
      header: '板块名称',
      accessor: (row) => row.name || '-'
    },
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => formatDate(row.trade_date)
    },
    {
      key: 'idx_type',
      header: '板块类型',
      accessor: (row) => row.idx_type || '-'
    },
    {
      key: 'pct_change',
      header: '涨跌幅(%)',
      accessor: (row) => (
        <span className={getPctColor(row.pct_change)}>
          {formatPct(row.pct_change)}
        </span>
      ) as any
    },
    {
      key: 'leading_stock',
      header: '领涨股',
      accessor: (row) => row.leading_stock || '-'
    },
    {
      key: 'leading_pct',
      header: '领涨涨幅(%)',
      accessor: (row) => (
        <span className={getPctColor(row.leading_pct)}>
          {formatPct(row.leading_pct)}
        </span>
      ) as any
    },
    {
      key: 'turnover_rate',
      header: '换手率(%)',
      accessor: (row) => row.turnover_rate != null ? `${formatNumber(row.turnover_rate)}%` : '-'
    },
    {
      key: 'total_mv',
      header: '总市值(万元)',
      accessor: (row) => row.total_mv != null ? formatNumber(row.total_mv, 0) : '-'
    },
    {
      key: 'up_num',
      header: '上涨家数',
      accessor: (row) => (
        <span className="text-red-600">{row.up_num ?? '-'}</span>
      ) as any
    },
    {
      key: 'down_num',
      header: '下跌家数',
      accessor: (row) => (
        <span className="text-green-600">{row.down_num ?? '-'}</span>
      ) as any
    },
  ], [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="东方财富概念板块"
        description="获取东方财富每个交易日的概念板块数据，支持按日期查询"
        details={<>
          <div>接口：dc_index</div>
          <a href="https://tushare.pro/document/2?doc_id=362" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <Button onClick={() => setSyncDialogOpen(true)} disabled={syncing}>
            {syncing ? (
              <>
                <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                同步中...
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4 mr-1" />
                同步数据
              </>
            )}
          </Button>
        }
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">总记录数</CardTitle>
              <Database className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{(statistics.total_records ?? 0).toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">条</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">板块数量</CardTitle>
              <Layers className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{(statistics.board_count ?? 0).toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">个</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">日期数量</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{(statistics.date_count ?? 0).toLocaleString()}</div>
              <p className="text-xs text-muted-foreground">天</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最新日期</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-xl font-bold">{statistics.latest_date ? formatDate(statistics.latest_date) : '-'}</div>
              <p className="text-xs text-muted-foreground">
                均涨跌幅: {statistics.avg_pct_change != null ? formatPct(statistics.avg_pct_change) : '-'}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选和操作区域 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-end flex-wrap">
            <div className="flex-1 min-w-[120px]">
              <label className="text-sm font-medium mb-2 block">板块代码</label>
              <Input
                placeholder="如：BK0001"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>

            <div className="flex-1 min-w-[120px]">
              <label className="text-sm font-medium mb-2 block">板块名称</label>
              <Input
                placeholder="模糊搜索"
                value={nameFilter}
                onChange={(e) => setNameFilter(e.target.value)}
              />
            </div>

            <div className="flex-1 min-w-[140px]">
              <label className="text-sm font-medium mb-2 block">板块类型</label>
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

            <div className="flex-1 min-w-[140px]">
              <label className="text-sm font-medium mb-2 block">开始日期</label>
              <DatePicker date={startDate} onDateChange={setStartDate} />
            </div>

            <div className="flex-1 min-w-[140px]">
              <label className="text-sm font-medium mb-2 block">结束日期</label>
              <DatePicker date={endDate} onDateChange={setEndDate} />
            </div>

            <Button onClick={loadData} disabled={isLoading}>
              {isLoading ? '查询中...' : '查询'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card className="p-0 sm:p-0 overflow-hidden">
        {/* 移动端视图 */}
        <div className="sm:hidden">
          <div className="px-4 py-3 border-b bg-muted/50">
            <h3 className="text-sm font-medium">板块数据</h3>
          </div>
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {!isLoading && !error && data.map((item, index) => (
              <div
                key={index}
                className={`p-4 transition-colors ${
                  index % 2 === 0
                    ? 'bg-white dark:bg-gray-900 hover:bg-blue-50 dark:hover:bg-blue-950/20 active:bg-blue-100 dark:active:bg-blue-900/30'
                    : 'bg-gray-50 dark:bg-gray-950 hover:bg-blue-50 dark:hover:bg-blue-950/20 active:bg-blue-100 dark:active:bg-blue-900/30'
                }`}
              >
                {mobileCard(item)}
              </div>
            ))}
          </div>

          {isLoading && (
            <div className="p-8 text-center">
              <div className="flex flex-col items-center justify-center gap-2">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                <span className="text-sm text-muted-foreground">加载中...</span>
              </div>
            </div>
          )}
          {error && (
            <div className="p-8 text-center">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}
          {!isLoading && !error && data.length === 0 && (
            <div className="p-8 text-center">
              <p className="text-sm text-muted-foreground">暂无数据</p>
            </div>
          )}

          {!isLoading && !error && data.length > 0 && (
            <div className="p-4 border-t bg-muted/30">
              <div className="flex items-center justify-between">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                >
                  上一页
                </Button>
                <span className="text-sm text-muted-foreground">
                  第 {page} / {Math.ceil(total / pageSize)} 页
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(Math.min(Math.ceil(total / pageSize), page + 1))}
                  disabled={page >= Math.ceil(total / pageSize)}
                >
                  下一页
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* 桌面端表格视图 */}
        <div className="hidden sm:block">
          <DataTable
            columns={columns}
            data={data}
            loading={isLoading}
            error={error}
            emptyMessage="暂无数据"
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: (newPage) => setPage(newPage),
              onPageSizeChange: (newPageSize) => {
                setPageSize(newPageSize)
                setPage(1)
              },
              pageSizeOptions: [10, 20, 30, 50, 100]
            }}
          />
        </div>
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
            {/* 积分提示 */}
            <div className="flex items-start gap-2 p-3 bg-yellow-50 dark:bg-yellow-950/20 rounded-md border border-yellow-200 dark:border-yellow-800">
              <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-yellow-700 dark:text-yellow-400">
                每次调用消耗 <strong>6000</strong> 积分，单次最大返回 5000 条数据，请谨慎操作。
              </p>
            </div>

            <div>
              <label className="text-sm font-medium mb-2 block">板块类型 <span className="text-red-500">*</span></label>
              <Select value={syncIdxType} onValueChange={setSyncIdxType}>
                <SelectTrigger>
                  <SelectValue placeholder="选择板块类型" />
                </SelectTrigger>
                <SelectContent>
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
            <Button onClick={handleSync} disabled={syncing || !syncIdxType}>
              {syncing ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                  提交中...
                </>
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
