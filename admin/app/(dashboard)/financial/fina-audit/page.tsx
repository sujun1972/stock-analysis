'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { financialDataApi, FinaAuditData, FinaAuditStatistics } from '@/lib/api/financial-data'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, Building2, Users, DollarSign } from 'lucide-react'
import { useDataBulkOps } from '@/hooks/useDataBulkOps'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'

const toDateStr = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

export default function FinaAuditPage() {
  const [data, setData] = useState<FinaAuditData[]>([])
  const [statistics, setStatistics] = useState<FinaAuditStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 筛选条件
  const [tsCode, setTsCode] = useState('')
  const [annDate, setAnnDate] = useState<Date | undefined>(undefined)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [period, setPeriod] = useState<Date | undefined>(undefined)

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // 同步弹窗状态
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)

  // 存储活跃的任务回调
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  // 任务存储Hook
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()

  const syncing = isTaskRunning('tasks.sync_fina_audit') || isTaskRunning('tasks.sync_fina_audit_full_history')

  /**
   * 加载数据
   */
  const loadData = useCallback(async (currentPage = page, currentPageSize = pageSize) => {
    try {
      setLoading(true)
      setError(null)

      const params: any = {
        limit: currentPageSize,
        offset: (currentPage - 1) * currentPageSize
      }

      if (tsCode) params.ts_code = tsCode
      if (annDate) params.ann_date = toDateStr(annDate)
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      if (period) params.period = toDateStr(period)

      const response = await financialDataApi.getFinaAudit(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics)
        setTotal(response.data.total || 0)
      } else {
        throw new Error(response.message || '加载数据失败')
      }
    } catch (err: any) {
      const errorMsg = err.message || '加载数据失败'
      setError(errorMsg)
      toast.error('加载失败', { description: errorMsg })
    } finally {
      setLoading(false)
    }
  }, [tsCode, annDate, startDate, endDate, period, page, pageSize])

  /**
   * 异步同步数据
   */
  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    try {
      const response = await financialDataApi.syncFinaAuditAsync()

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

        // 注册任务完成回调
        const completionCallback = (task: any) => {
          if (task.status === 'success') {
            loadData(1, pageSize).catch(() => {})
            toast.success('数据同步完成', { description: '财务审计意见数据已更新' })
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
    tableKey: 'fina_audit',
    syncFn: (params) => financialDataApi.syncFinaAuditFullHistoryAsync({ start_date: params?.start_date }),
    taskName: 'tasks.sync_fina_audit_full_history',
    onSuccess: loadData,
  })

  // 组件挂载时加载数据
  useEffect(() => {
    loadData()
  }, [loadData])

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
    const formatDate = (dateStr: string) => {
      if (!dateStr || dateStr.length !== 8) return dateStr
      return `${dateStr.substring(0, 4)}-${dateStr.substring(4, 6)}-${dateStr.substring(6, 8)}`
    }

    return (
      <div className="space-y-2">
        <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">股票代码</span>
          <span className="font-medium">{item.ts_code}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">公告日期</span>
          <span>{formatDate(item.ann_date)}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">报告期</span>
          <span>{formatDate(item.end_date)}</span>
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
              tableName="财务审计意见"
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
                  <p className="text-xs sm:text-sm text-muted-foreground">总记录数</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.total_count.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground mt-1">统计期内审计记录</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">公司数量</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.stock_count.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground mt-1">不同公司数量</p>
                </div>
                <Building2 className="h-6 w-6 sm:h-8 sm:w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">事务所数量</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.agency_count.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground mt-1">会计事务所数量</p>
                </div>
                <Users className="h-6 w-6 sm:h-8 sm:w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-muted-foreground">平均审计费用</p>
                  <p className="text-xl sm:text-2xl font-bold">{(statistics.avg_fees / 10000).toFixed(2)}万</p>
                  <p className="text-xs text-muted-foreground mt-1">最高: {(statistics.max_fees / 10000).toFixed(2)}万</p>
                </div>
                <DollarSign className="h-6 w-6 sm:h-8 sm:w-8 text-muted-foreground" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选和操作区域 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
          <CardDescription>输入股票代码（必填）和日期范围进行查询</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* 股票代码 */}
            <div className="space-y-2">
              <Label htmlFor="ts-code">股票代码 *</Label>
              <Input
                id="ts-code"
                placeholder="例如: 600000.SH"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>

            {/* 公告日期 */}
            <div className="space-y-2">
              <Label>公告日期</Label>
              <DatePicker
                date={annDate}
                onDateChange={setAnnDate}
                placeholder="选择公告日期"
              />
            </div>

            {/* 开始日期 */}
            <div className="space-y-2">
              <Label>开始日期</Label>
              <DatePicker
                date={startDate}
                onDateChange={setStartDate}
                placeholder="选择开始日期"
              />
            </div>

            {/* 结束日期 */}
            <div className="space-y-2">
              <Label>结束日期</Label>
              <DatePicker
                date={endDate}
                onDateChange={setEndDate}
                placeholder="选择结束日期"
              />
            </div>

            {/* 报告期 */}
            <div className="space-y-2">
              <Label>报告期</Label>
              <DatePicker
                date={period}
                onDateChange={setPeriod}
                placeholder="选择报告期"
              />
            </div>
          </div>

          {/* 操作按钮 */}
          <div className="flex flex-col sm:flex-row gap-2 mt-4">
            <Button
              variant="default"
              size="sm"
              onClick={() => loadData()}
              disabled={loading}
            >
              {loading ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                  查询中...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4 mr-1" />
                  查询数据
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card className="p-0 sm:p-0 overflow-hidden">
        {/* 移动端视图 */}
        <div className="sm:hidden">
          <div className="px-4 py-3 border-b bg-muted/50">
            <h3 className="text-sm font-medium">审计意见列表</h3>
          </div>
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {!loading && !error && data.map((item, index) => (
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

          {/* 移动端状态显示 */}
          {loading && (
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
          {!loading && !error && data.length === 0 && (
            <div className="p-8 text-center">
              <p className="text-sm text-muted-foreground">暂无数据</p>
            </div>
          )}

          {/* 移动端分页 */}
          {!loading && !error && data.length > 0 && (
            <div className="p-4 border-t bg-muted/30">
              <div className="flex items-center justify-between">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => { const newPage = Math.max(1, page - 1); setPage(newPage); loadData(newPage, pageSize).catch(() => {}) }}
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
                  onClick={() => { const newPage = Math.min(Math.ceil(total / pageSize), page + 1); setPage(newPage); loadData(newPage, pageSize).catch(() => {}) }}
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
            loading={loading}
            error={error}
            emptyMessage="暂无数据，请输入股票代码进行查询"
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: (newPage) => { setPage(newPage); loadData(newPage, pageSize).catch(() => {}) },
              onPageSizeChange: (newPageSize) => { setPageSize(newPageSize); setPage(1); loadData(1, newPageSize).catch(() => {}) },
              pageSizeOptions: [10, 20, 30, 50, 100]
            }}
          />
        </div>
      </Card>

      {/* 同步弹窗 */}
      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent className="sm:max-w-[420px]">
          <DialogHeader>
            <DialogTitle>同步财务审计意见</DialogTitle>
            <DialogDescription>
              将从 Tushare 增量同步最新财务审计意见数据，无需选择日期。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncDialogOpen(false)}>取消</Button>
            <Button onClick={handleSyncConfirm} disabled={syncing}>确认同步</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
