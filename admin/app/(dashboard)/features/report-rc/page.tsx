'use client'

import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { reportRcApi, type ReportRcData, type ReportRcStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { useSystemConfig } from '@/contexts'
import { formatStockCode } from '@/lib/utils'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, Building2, FileText, BarChart3, ListFilter } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

const PAGE_SIZE = 100

export default function ReportRcPage() {
  const [data, setData] = useState<ReportRcData[]>([])
  const [statistics, setStatistics] = useState<ReportRcStatistics | null>(null)
  const [loading, setLoading] = useState(false)
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [orgName, setOrgName] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc' | null>(null)

  // 同步弹窗状态
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const { config } = useSystemConfig()

  // 从 task store 实时派生——不用本地 useState
  const syncing = isTaskRunning('tasks.sync_report_rc')

  const openStockAnalysis = useCallback((tsCode: string) => {
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(tsCode)), '_blank')
  }, [config])

  // 时区安全的日期字符串构建
  const toDateStr = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

  // 加载数据
  const loadData = async (
    targetPage: number = page,
    overrideSortKey?: string | null,
    overrideSortDir?: 'asc' | 'desc' | null
  ) => {
    try {
      setLoading(true)

      const params: any = {
        page: targetPage,
        page_size: PAGE_SIZE
      }
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (orgName.trim()) params.org_name = orgName.trim()

      const sk = overrideSortKey !== undefined ? overrideSortKey : sortKey
      const sd = overrideSortDir !== undefined ? overrideSortDir : sortDirection
      if (sk) {
        params.sort_by = sk
        params.sort_order = sd ?? 'desc'
      }

      const response = await reportRcApi.getData(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics || null)
        setTotal(response.data.total || 0)
        setPage(targetPage)
        // 回填后端解析的默认研报日期（初始加载时 tradeDate 为空）
        if (!tradeDate && response.data.report_date) {
          setTradeDate(new Date(response.data.report_date + 'T00:00:00'))
        }
      } else {
        toast.error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      toast.error('加载数据失败', { description: err.message || '无法获取卖方盈利预测数据' })
    } finally {
      setLoading(false)
    }
  }

  // 初始加载
  useEffect(() => {
    loadData(1).catch(() => {})
  }, [])

  const handleQuery = () => {
    loadData(1).catch(() => {})
  }

  // 同步确认
  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    try {
      const params: any = {}
      if (syncStartDate) params.start_date = toDateStr(syncStartDate)
      if (syncEndDate) params.end_date = toDateStr(syncEndDate)

      const response = await reportRcApi.syncAsync(params)

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
            toast.success('数据同步完成', { description: '卖方盈利预测数据已更新' })
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

  // 格式化日期
  const formatDate = (dateStr: string) => {
    if (!dateStr || dateStr.length !== 8) return dateStr
    return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
  }

  // 表格列定义
  const columns: Column<ReportRcData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票',
      accessor: (row) => (
        <span
          className="cursor-pointer hover:underline text-blue-600"
          onClick={() => openStockAnalysis(row.ts_code)}
        >
          {row.name || '-'}[{formatStockCode(row.ts_code)}]
        </span>
      ),
      width: 160,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'org_name',
      header: '机构',
      accessor: (row) => (
        <div className="truncate" title={row.org_name || ''}>
          {row.org_name || '-'}
        </div>
      ),
      width: 130
    },
    {
      key: 'quarter',
      header: '预测期',
      accessor: (row) => row.quarter,
      width: 80,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'eps',
      header: 'EPS(元)',
      accessor: (row) => row.eps !== null ? row.eps.toFixed(2) : '-',
      width: 85,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'pe',
      header: 'PE',
      accessor: (row) => row.pe !== null ? row.pe.toFixed(2) : '-',
      width: 75,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'roe',
      header: 'ROE(%)',
      accessor: (row) => row.roe !== null ? (row.roe * 100).toFixed(2) : '-',
      width: 85,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'rating',
      header: '评级',
      accessor: (row) => (
        <span className={
          row.rating === '买入' || row.rating === '强烈推荐' ? 'text-red-600 font-medium' :
          row.rating === '增持' ? 'text-orange-500 font-medium' :
          row.rating === '卖出' || row.rating === '减持' ? 'text-green-600 font-medium' :
          ''
        }>
          {row.rating || '-'}
        </span>
      ),
      width: 80,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'max_price',
      header: '目标价(元)',
      accessor: (row) => row.max_price !== null ? row.max_price.toFixed(2) : '-',
      width: 100,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    }
  ], [openStockAnalysis])

  // 移动端卡片
  const mobileCard = (item: ReportRcData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div
            className="font-semibold text-base cursor-pointer hover:underline text-blue-600"
            onClick={() => openStockAnalysis(item.ts_code)}
          >
            {item.name || '-'}[{formatStockCode(item.ts_code)}]
          </div>
          <div className="text-sm text-gray-500">{item.org_name}</div>
        </div>
        <span className="text-xs text-gray-500">{formatDate(item.report_date)}</span>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">预测期</span>
          <span className="font-medium">{item.quarter}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">EPS</span>
          <span className="font-medium">{item.eps !== null ? `${item.eps.toFixed(2)}元` : '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">评级</span>
          <span className={`font-medium ${
            item.rating === '买入' || item.rating === '强烈推荐' ? 'text-red-600' :
            item.rating === '增持' ? 'text-orange-500' :
            item.rating === '卖出' || item.rating === '减持' ? 'text-green-600' : 'text-blue-600'
          }`}>{item.rating || '-'}</span>
        </div>
        {item.max_price !== null && (
          <div className="flex justify-between">
            <span className="text-gray-600">目标价</span>
            <span className="font-medium text-green-600">{item.max_price.toFixed(2)} 元</span>
          </div>
        )}
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="卖方盈利预测数据"
        description="获取券商（卖方）每天研报的盈利预测数据，数据从2010年开始，每晚19~22点更新当日数据"
        details={<>
          <div>接口：report_rc</div>
          <a href="https://tushare.pro/document/2?doc_id=292" target="_blank" rel="noopener noreferrer">查看文档</a>
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
                  <p className="text-xs sm:text-sm text-gray-600">研报数量</p>
                  <p className="text-xl sm:text-2xl font-bold">{(statistics.total_count ?? 0).toLocaleString()}</p>
                  <p className="text-xs text-gray-400 mt-0.5">条研报记录</p>
                </div>
                <FileText className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">覆盖股票</p>
                  <p className="text-xl sm:text-2xl font-bold">{(statistics.stock_count ?? 0).toLocaleString()}</p>
                  <p className="text-xs text-gray-400 mt-0.5">只股票</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-orange-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">参与机构</p>
                  <p className="text-xl sm:text-2xl font-bold">{(statistics.org_count ?? 0).toLocaleString()}</p>
                  <p className="text-xs text-gray-400 mt-0.5">家券商</p>
                </div>
                <Building2 className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">平均EPS</p>
                  <p className="text-xl sm:text-2xl font-bold">{(statistics.avg_eps ?? 0).toFixed(2)}</p>
                  <p className="text-xs text-gray-400 mt-0.5">元/股</p>
                </div>
                <BarChart3 className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
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
              <label className="text-sm font-medium mb-1 block">研报日期</label>
              <DatePicker date={tradeDate} onDateChange={setTradeDate} />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">股票代码</label>
              <Input
                placeholder="如 000001 或 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">机构名称</label>
              <Input
                placeholder="如: 安信证券"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
              />
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <Button onClick={handleQuery} disabled={loading} className="flex-1 sm:flex-none">
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
            loading={loading}
            mobileCard={mobileCard}
            emptyMessage="暂无卖方盈利预测数据"
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
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>同步卖方盈利预测数据</DialogTitle>
            <DialogDescription>
              选择同步日期范围（留空则同步最新数据）。
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">开始日期（可选）</label>
              <DatePicker date={syncStartDate} onDateChange={setSyncStartDate} placeholder="留空同步最新数据" />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">结束日期（可选）</label>
              <DatePicker date={syncEndDate} onDateChange={setSyncEndDate} placeholder="留空同步最新数据" />
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
