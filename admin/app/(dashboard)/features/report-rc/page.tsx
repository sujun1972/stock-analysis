'use client'

import { useState, useEffect, useRef, useMemo } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Input } from '@/components/ui/input'
import { reportRcApi, type ReportRcData, type ReportRcStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, Building2, FileText, BarChart3 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

export default function ReportRcPage() {
  const [data, setData] = useState<ReportRcData[]>([])
  const [statistics, setStatistics] = useState<ReportRcStatistics | null>(null)
  const [loading, setLoading] = useState(false)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [orgName, setOrgName] = useState('')

  // 同步弹窗状态
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()

  // 从 task store 实时派生——不用本地 useState
  const syncing = isTaskRunning('tasks.sync_report_rc')

  // 时区安全的日期字符串构建
  const toDateStr = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

  // 加载数据
  const loadData = async () => {
    try {
      setLoading(true)

      const params: any = { limit: 100 }
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (orgName.trim()) params.org_name = orgName.trim()

      const response = await reportRcApi.getData(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics || null)
      } else {
        toast.error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      toast.error('加载数据失败', { description: err.message || '无法获取卖方盈利预测数据' })
    } finally {
      setLoading(false)
    }
  }

  // 初始加载：只跑一次
  useEffect(() => {
    loadData().catch(() => {})
  }, [])

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
            loadData().catch(() => {})
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
      key: 'report_date',
      header: '研报日期',
      accessor: (row) => formatDate(row.report_date),
      width: 100
    },
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code,
      width: 100
    },
    {
      key: 'name',
      header: '股票名称',
      accessor: (row) => row.name,
      width: 100
    },
    {
      key: 'org_name',
      header: '机构',
      accessor: (row) => row.org_name,
      width: 120,
      hideOnMobile: true
    },
    {
      key: 'quarter',
      header: '预测期',
      accessor: (row) => row.quarter,
      width: 80,
      hideOnMobile: true
    },
    {
      key: 'eps',
      header: 'EPS(元)',
      accessor: (row) => row.eps !== null ? row.eps.toFixed(2) : '-',
      width: 80,
      cellClassName: 'text-right whitespace-nowrap',
      hideOnMobile: true
    },
    {
      key: 'pe',
      header: 'PE',
      accessor: (row) => row.pe !== null ? row.pe.toFixed(2) : '-',
      width: 70,
      cellClassName: 'text-right whitespace-nowrap',
      hideOnMobile: true
    },
    {
      key: 'roe',
      header: 'ROE(%)',
      accessor: (row) => row.roe !== null ? (row.roe * 100).toFixed(2) : '-',
      width: 80,
      cellClassName: 'text-right whitespace-nowrap',
      hideOnMobile: true
    },
    {
      key: 'rating',
      header: '评级',
      accessor: (row) => row.rating || '-',
      width: 100
    },
    {
      key: 'max_price',
      header: '目标价(元)',
      accessor: (row) => row.max_price !== null ? row.max_price.toFixed(2) : '-',
      width: 100,
      cellClassName: 'text-right whitespace-nowrap',
      hideOnMobile: true
    }
  ], [])

  // 移动端卡片
  const mobileCard = (item: ReportRcData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div className="font-semibold text-base">{item.name}</div>
          <div className="text-sm text-gray-500">{item.ts_code}</div>
        </div>
        <span className="text-xs text-gray-500">{formatDate(item.report_date)}</span>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">机构</span>
          <span className="font-medium">{item.org_name}</span>
        </div>
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
          <span className="font-medium text-blue-600">{item.rating || '-'}</span>
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
        description="券商研报盈利预测数据，包含EPS、PE、ROE等关键指标和评级信息（5000积分/次）"
        details={<>
          <div>接口：report_rc</div>
          <a href="https://tushare.pro/document/2?doc_id=285" target="_blank" rel="noopener noreferrer">查看文档</a>
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
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">股票代码</label>
              <Input
                placeholder="如 000001 或 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">机构名称</label>
              <Input
                placeholder="如: 安信证券"
                value={orgName}
                onChange={(e) => setOrgName(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">开始日期</label>
              <DatePicker date={startDate} onDateChange={setStartDate} />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">结束日期</label>
              <DatePicker date={endDate} onDateChange={setEndDate} />
            </div>
          </div>
          <div className="mt-4">
            <Button onClick={() => loadData().catch(() => {})} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
              查询
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
            loading={loading}
            mobileCard={mobileCard}
            emptyMessage="暂无卖方盈利预测数据"
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
