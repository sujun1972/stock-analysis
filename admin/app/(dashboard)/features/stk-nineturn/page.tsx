'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { stkNineturnApi, type StkNineturnData, type StkNineturnStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { useSystemConfig } from '@/contexts'
import { formatStockCode } from '@/lib/utils'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, TrendingDown, BarChart3, Activity, ListFilter } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

const PAGE_SIZE = 100

export default function StkNineturnPage() {
  const [data, setData] = useState<StkNineturnData[]>([])
  const [statistics, setStatistics] = useState<StkNineturnStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')

  // 分页状态
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  // 排序状态
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc' | null>(null)

  // 同步弹窗状态
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncTsCode, setSyncTsCode] = useState('')
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const { config } = useSystemConfig()

  // 从 task store 实时派生——不用本地 useState
  const syncing = isTaskRunning('tasks.sync_stk_nineturn')

  // 时区安全的日期字符串构建
  const toDateStr = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

  const openStockAnalysis = useCallback((tsCode: string) => {
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(tsCode)), '_blank')
  }, [config])

  // 加载数据
  const loadData = async (
    targetPage: number = page,
    overrideSortKey?: string | null,
    overrideSortDir?: 'asc' | 'desc' | null
  ) => {
    try {
      setIsLoading(true)

      const params: any = {
        page: targetPage,
        page_size: PAGE_SIZE,
        sort_by: (overrideSortKey !== undefined ? overrideSortKey : sortKey) ?? undefined,
        sort_order: (overrideSortDir !== undefined ? overrideSortDir : sortDirection) ?? undefined,
      }
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)

      const response = await stkNineturnApi.getData(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics || null)
        setTotal(response.data.total || 0)
        setPage(targetPage)
        // 回填后端解析的默认日期范围（仅在用户未选日期时）
        if (!startDate && response.data.start_date) {
          setStartDate(new Date(response.data.start_date + 'T00:00:00'))
        }
        if (!endDate && response.data.end_date) {
          setEndDate(new Date(response.data.end_date + 'T00:00:00'))
        }
      } else {
        toast.error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      toast.error('加载失败', { description: err.message || '加载数据失败' })
    } finally {
      setIsLoading(false)
    }
  }

  // 初始加载：只跑一次
  useEffect(() => {
    loadData(1).catch(() => {})
  }, [])

  // 同步确认
  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    try {
      const params: any = {}
      if (syncTsCode.trim()) params.ts_code = syncTsCode.trim()
      if (syncStartDate) params.start_date = toDateStr(syncStartDate)
      if (syncEndDate) params.end_date = toDateStr(syncEndDate)

      const response = await stkNineturnApi.syncAsync(params)

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
            toast.success('数据同步完成', { description: '神奇九转指标数据已更新' })
          }
          unregisterCompletionCallback(taskId, completionCallback)
          activeCallbacksRef.current.delete(taskId)
        }

        activeCallbacksRef.current.set(taskId, completionCallback)
        registerCompletionCallback(taskId, completionCallback)
        triggerPoll()
        toast.success(response.message || '同步任务已提交')
      } else {
        toast.error(response.message || '提交同步任务失败')
      }
    } catch (err: any) {
      toast.error('同步失败', { description: err.message || '无法同步数据' })
    }
  }

  // 组件卸载清理
  useEffect(() => {
    return () => {
      // eslint-disable-next-line react-hooks/exhaustive-deps
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
    }
  }, [unregisterCompletionCallback])

  // 移动端卡片
  const mobileCard = (item: StkNineturnData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div
            className="font-semibold text-base cursor-pointer hover:underline"
            onClick={() => openStockAnalysis(item.ts_code)}
          >
            {item.name ? `${item.name}[${formatStockCode(item.ts_code)}]` : item.ts_code}
          </div>
          <div className="text-sm text-gray-500">{item.trade_date ? item.trade_date.split(' ')[0] : '-'}</div>
        </div>
        <div className="flex gap-1">
          {item.nine_up_turn === '+9' && <span className="text-xs font-bold text-red-600">+9↑</span>}
          {item.nine_down_turn === '-9' && <span className="text-xs font-bold text-green-600">-9↓</span>}
        </div>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">收盘价</span>
          <span className="font-medium">{item.close !== null ? item.close.toFixed(2) : '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">上九转计数</span>
          <span className={item.up_count !== null && item.up_count >= 9 ? 'font-semibold text-red-600' : 'font-medium'}>
            {item.up_count !== null ? item.up_count.toFixed(1) : '-'}
            {item.up_count !== null && item.up_count < 9 && (
              <span className="text-gray-400 ml-1">({(9 - item.up_count).toFixed(1)}格)</span>
            )}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">下九转计数</span>
          <span className={item.down_count !== null && item.down_count >= 9 ? 'font-semibold text-green-600' : 'font-medium'}>
            {item.down_count !== null ? item.down_count.toFixed(1) : '-'}
            {item.down_count !== null && item.down_count < 9 && (
              <span className="text-gray-400 ml-1">({(9 - item.down_count).toFixed(1)}格)</span>
            )}
          </span>
        </div>
      </div>
    </div>
  )

  // 桌面端表格列定义
  const columns: Column<StkNineturnData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票',
      accessor: (row) => (
        <span
          className="cursor-pointer hover:underline whitespace-nowrap"
          onClick={() => openStockAnalysis(row.ts_code)}
        >
          {row.name ? `${row.name}[${formatStockCode(row.ts_code)}]` : row.ts_code}
        </span>
      ),
      width: 150,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => row.trade_date ? row.trade_date.split(' ')[0] : '-',
      width: 110,
      sortable: true,
    },
    {
      key: 'close',
      header: '收盘价',
      accessor: (row) => row.close !== null ? row.close.toFixed(2) : '-',
      width: 90,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'up_count',
      header: '上九转计数',
      accessor: (row) => {
        if (row.up_count === null) return '-'
        const count = row.up_count.toFixed(1)
        return (
          <span className={row.up_count >= 9 ? 'text-red-600 font-semibold' : ''}>
            {count}
          </span>
        )
      },
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'down_count',
      header: '下九转计数',
      accessor: (row) => {
        if (row.down_count === null) return '-'
        const count = row.down_count.toFixed(1)
        return (
          <span className={row.down_count >= 9 ? 'text-green-600 font-semibold' : ''}>
            {count}
          </span>
        )
      },
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'nine_up_turn',
      header: '上九转',
      accessor: (row) => {
        if (row.nine_up_turn === '+9') {
          return <span className="text-red-600 font-bold">+9 ⚠️</span>
        }
        return '-'
      },
      width: 80
    },
    {
      key: 'nine_down_turn',
      header: '下九转',
      accessor: (row) => {
        if (row.nine_down_turn === '-9') {
          return <span className="text-green-600 font-bold">-9 ⚠️</span>
        }
        return '-'
      },
      width: 80
    }
  ], [openStockAnalysis])

  return (
    <div className="space-y-6">
      <PageHeader
        title="神奇九转指标"
        description="基于技术分析的趋势反转指标，识别连续9天特定走势（6000积分/次）"
        details={<>
          <div>接口：stk_nineturn</div>
          <a href="https://tushare.pro/document/2?doc_id=295" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <Button onClick={() => setSyncDialogOpen(true)} disabled={syncing}>
            {syncing ? (
              <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
            ) : (
              <><RefreshCw className="h-4 w-4 mr-1" />同步数据</>
            )}
          </Button>
        }
      />

      {/* 统计卡片 — 左文字右图标 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">总记录数</p>
                  <p className="text-xl sm:text-2xl font-bold">{(statistics.total_records ?? 0).toLocaleString()}</p>
                  <p className="text-xs text-gray-400 mt-0.5">条</p>
                </div>
                <BarChart3 className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">覆盖股票</p>
                  <p className="text-xl sm:text-2xl font-bold">{(statistics.stock_count ?? 0).toLocaleString()}</p>
                  <p className="text-xs text-gray-400 mt-0.5">只</p>
                </div>
                <Activity className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">上九转信号</p>
                  <p className="text-xl sm:text-2xl font-bold text-red-600">{(statistics.up_turn_count ?? 0).toLocaleString()}</p>
                  <p className="text-xs text-gray-400 mt-0.5">次（潜在顶部）</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-red-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">下九转信号</p>
                  <p className="text-xl sm:text-2xl font-bold text-green-600">{(statistics.down_turn_count ?? 0).toLocaleString()}</p>
                  <p className="text-xs text-gray-400 mt-0.5">次（潜在底部）</p>
                </div>
                <TrendingDown className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选区域（仅查询控件，同步按钮在 PageHeader） */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ListFilter className="h-5 w-5" />
            数据查询
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="w-full sm:w-48">
              <label className="text-sm font-medium mb-1 block">股票代码</label>
              <Input
                placeholder="如 000001 或 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="w-full sm:w-44">
              <label className="text-sm font-medium mb-1 block">开始日期</label>
              <DatePicker date={startDate} onDateChange={setStartDate} />
            </div>
            <div className="w-full sm:w-44">
              <label className="text-sm font-medium mb-1 block">结束日期</label>
              <DatePicker date={endDate} onDateChange={setEndDate} />
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <Button onClick={() => loadData(1).catch(() => {})} disabled={isLoading} className="flex-1 sm:flex-none">
                {isLoading ? '查询中...' : '查询'}
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
            emptyMessage="暂无神奇九转指标数据"
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

      {/* 同步弹窗 */}
      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent className="sm:max-w-[440px]">
          <DialogHeader>
            <DialogTitle>同步神奇九转指标数据</DialogTitle>
            <DialogDescription>
              所有参数均为可选，不填写将同步最近30天数据（6000积分/次，数据从2023年起）。
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">股票代码（可选）</label>
              <Input
                placeholder="如 600000.SH，留空同步全市场"
                value={syncTsCode}
                onChange={(e) => setSyncTsCode(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">开始日期（可选）</label>
              <DatePicker date={syncStartDate} onDateChange={setSyncStartDate} placeholder="留空同步最近30天" />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">结束日期（可选）</label>
              <DatePicker date={syncEndDate} onDateChange={setSyncEndDate} placeholder="留空同步最近30天" />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncDialogOpen(false)}>取消</Button>
            <Button onClick={handleSyncConfirm} disabled={syncing}>
              {syncing ? <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</> : '确认同步'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
