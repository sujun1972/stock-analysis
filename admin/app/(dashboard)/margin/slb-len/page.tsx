'use client'

import { useState, useEffect, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, TrendingDown, DollarSign, BarChart3, ListFilter } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { slbLenApi } from '@/lib/api'
import { apiClient } from '@/lib/api-client'
import { useTaskStore } from '@/stores/task-store'
import { useDataBulkOps } from '@/hooks/useDataBulkOps'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import type { SlbLenData, SlbLenStatistics } from '@/lib/api/slb-len'

export default function SlbLenPage() {
  const [data, setData] = useState<SlbLenData[]>([])
  const [statistics, setStatistics] = useState<SlbLenStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  // 筛选条件
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)

  // 同步弹窗状态
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()

  // 从 task store 实时派生——不用本地 useState
  const syncing = isTaskRunning('tasks.sync_slb_len')

  // 时区安全的日期字符串构建
  const toDateStr = (date: Date) =>
    `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`

  // 加载数据
  const loadData = async () => {
    try {
      setIsLoading(true)

      const params = {
        start_date: startDate ? toDateStr(startDate) : undefined,
        end_date: endDate ? toDateStr(endDate) : undefined,
        limit: 100
      }

      const [dataRes, statsRes] = await Promise.all([
        slbLenApi.getSlbLen(params),
        slbLenApi.getSlbLenStatistics({ start_date: params.start_date, end_date: params.end_date })
      ])

      if (dataRes.code === 200 && dataRes.data) {
        setData(dataRes.data.items || [])
      } else {
        toast.error(dataRes.message || '获取数据失败')
      }

      if (statsRes.code === 200 && statsRes.data) {
        setStatistics(statsRes.data)
      }
    } catch (error: any) {
      toast.error('加载数据失败', { description: error.message })
    } finally {
      setIsLoading(false)
    }
  }

  // 同步确认
  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    try {
      const params: any = {}
      if (syncStartDate) params.start_date = toDateStr(syncStartDate)
      if (syncEndDate) params.end_date = toDateStr(syncEndDate)

      const response = await slbLenApi.syncSlbLenAsync(params)

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
            loadData().catch(() => {})
            toast.success('数据同步完成', { description: '转融资交易汇总数据已更新' })
          }
          unregisterCompletionCallback(taskId, completionCallback)
          activeCallbacksRef.current.delete(taskId)
        }

        activeCallbacksRef.current.set(taskId, completionCallback)
        registerCompletionCallback(taskId, completionCallback)
        triggerPoll()
        toast.success(response.message || '同步任务已提交，请在任务面板查看进度')
      } else {
        toast.error(response.message || '提交同步任务失败')
      }
    } catch (error: any) {
      toast.error('同步失败', { description: error.message || '无法提交同步任务' })
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
    tableKey: 'slb_len',
    syncFn: (params) => apiClient.post('/api/slb-len/sync-async', null, { params }),
    taskName: 'tasks.sync_slb_len',
    onSuccess: loadData,
  })

  // 初始加载
  useEffect(() => {
    loadData()
  }, [])

  // 组件卸载时清理未完成的回调
  useEffect(() => {
    return () => {
      // eslint-disable-next-line react-hooks/exhaustive-deps
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
      cleanup()
    }
  }, [unregisterCompletionCallback])

  // 格式化金额（数值已为亿元）
  const formatAmount = (amount: number | undefined | null) => {
    if (amount === null || amount === undefined) return '-'
    return amount.toFixed(2) + '亿'
  }

  // 格式化日期显示
  const formatDate = (dateStr: string) => {
    if (!dateStr) return '-'
    // 支持 YYYYMMDD 和 YYYY-MM-DD 两种格式
    if (dateStr.length === 8) {
      return `${dateStr.slice(0, 4)}-${dateStr.slice(4, 6)}-${dateStr.slice(6, 8)}`
    }
    return dateStr
  }

  // 表格列定义
  const columns: Column<SlbLenData>[] = [
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => formatDate(row.trade_date),
      width: 110,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'ob',
      header: '期初余额',
      accessor: (row) => formatAmount(row.ob),
      width: 120,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'auc_amount',
      header: '竞价成交',
      accessor: (row) => formatAmount(row.auc_amount),
      hideOnMobile: true,
      width: 120,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'repo_amount',
      header: '再借成交',
      accessor: (row) => formatAmount(row.repo_amount),
      hideOnMobile: true,
      width: 120,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'repay_amount',
      header: '偿还金额',
      accessor: (row) => formatAmount(row.repay_amount),
      hideOnMobile: true,
      width: 120,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'cb',
      header: '期末余额',
      accessor: (row) => formatAmount(row.cb),
      width: 120,
      cellClassName: 'text-right whitespace-nowrap'
    }
  ]

  // 移动端卡片视图
  const mobileCard = (item: SlbLenData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-center mb-3">
        <span className="font-semibold text-base">{formatDate(item.trade_date)}</span>
        <span className="text-sm font-medium text-blue-600">期末 {formatAmount(item.cb)}</span>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">期初余额</span>
          <span className="font-medium">{formatAmount(item.ob)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">竞价成交</span>
          <span className="font-medium">{formatAmount(item.auc_amount)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">再借成交</span>
          <span className="font-medium">{formatAmount(item.repo_amount)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">偿还金额</span>
          <span className="font-medium">{formatAmount(item.repay_amount)}</span>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="转融资交易汇总"
        description="转融通融资汇总"
        details={<>
          <div>接口：slb_len</div>
          <a href="https://tushare.pro/document/2?doc_id=331" target="_blank" rel="noopener noreferrer">查看文档</a>
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
              tableName="转融资交易汇总"
            />
          </div>
        }
      />

      {/* 统计卡片 — 左文字右图标布局 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">平均期末余额</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatAmount(statistics.avg_cb)}</p>
                  <p className="text-xs text-gray-400 mt-0.5">统计周期内均值</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">最大期末余额</p>
                  <p className="text-xl sm:text-2xl font-bold text-red-600">{formatAmount(statistics.max_cb)}</p>
                  <p className="text-xs text-gray-400 mt-0.5">历史最高值</p>
                </div>
                <BarChart3 className="h-6 w-6 sm:h-8 sm:w-8 text-red-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">累计竞价成交</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatAmount(statistics.total_auc_amount)}</p>
                  <p className="text-xs text-gray-400 mt-0.5">统计周期累计值</p>
                </div>
                <DollarSign className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">累计偿还金额</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatAmount(statistics.total_repay_amount)}</p>
                  <p className="text-xs text-gray-400 mt-0.5">统计周期累计值</p>
                </div>
                <TrendingDown className="h-6 w-6 sm:h-8 sm:w-8 text-orange-500" />
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
            <div className="flex flex-col sm:flex-row gap-4 flex-1">
              <div className="flex-1 min-w-[180px]">
                <label className="text-sm font-medium mb-2 block">开始日期</label>
                <DatePicker
                  date={startDate}
                  onDateChange={setStartDate}
                  placeholder="选择开始日期"
                />
              </div>
              <div className="flex-1 min-w-[180px]">
                <label className="text-sm font-medium mb-2 block">结束日期</label>
                <DatePicker
                  date={endDate}
                  onDateChange={setEndDate}
                  placeholder="选择结束日期"
                />
              </div>
            </div>
            <Button
              onClick={loadData}
              disabled={isLoading}
              variant="outline"
              className="w-full sm:w-auto"
            >
              {isLoading ? '加载中...' : '查询'}
            </Button>
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
            emptyMessage="暂无转融资数据"
            tableClassName="table-fixed w-full [&_th]:border-r [&_td]:border-r [&_th:last-child]:border-r-0 [&_td:last-child]:border-r-0 [&_th]:!text-center"
          />
        </CardContent>
      </Card>

      {/* 同步日期选择弹窗 */}
      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>同步转融资交易汇总</DialogTitle>
            <DialogDescription>
              选择同步日期范围（留空则同步最近30天数据）。
            </DialogDescription>
          </DialogHeader>
          <div className="py-4 space-y-4">
            <div>
              <label className="text-sm font-medium mb-2 block">开始日期（可选）</label>
              <DatePicker
                date={syncStartDate}
                onDateChange={setSyncStartDate}
                placeholder="留空同步最近30天"
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">结束日期（可选）</label>
              <DatePicker
                date={syncEndDate}
                onDateChange={setSyncEndDate}
                placeholder="留空同步至今天"
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSyncConfirm} disabled={syncing}>
              {syncing ? (
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
              ) : '确认同步'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
