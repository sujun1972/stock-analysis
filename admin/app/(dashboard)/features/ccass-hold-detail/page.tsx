'use client'

import { useState, useEffect, useMemo, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { ccassHoldDetailApi, type CcassHoldDetailData, type CcassHoldDetailStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, Users, Calendar, Database } from 'lucide-react'

export default function CcassHoldDetailPage() {
  const [data, setData] = useState<CcassHoldDetailData[]>([])
  const [statistics, setStatistics] = useState<CcassHoldDetailStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState<string>('')
  const [participantId, setParticipantId] = useState<string>('')

  // 同步弹窗状态
  const [showSyncDialog, setShowSyncDialog] = useState(false)
  const [syncTsCode, setSyncTsCode] = useState<string>('')
  const [syncHkCode, setSyncHkCode] = useState<string>('')
  const [syncTradeDate, setSyncTradeDate] = useState<Date | undefined>(undefined)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()

  // 从 task store 实时派生——不用本地 useState
  const syncing = isTaskRunning('tasks.sync_ccass_hold_detail')

  // 时区安全的日期字符串构建
  const toDateStr = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

  // 加载数据
  const loadData = async (targetPage: number = page) => {
    try {
      setIsLoading(true)

      const params: any = { limit: pageSize }
      if (startDate) params.start_date = toDateStr(startDate)
      if (endDate) params.end_date = toDateStr(endDate)
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (participantId.trim()) params.col_participant_id = participantId.trim()

      const response = await ccassHoldDetailApi.getData(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics || null)
        setTotal(response.data.total || 0)
        setPage(targetPage)
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

  // 关闭同步弹窗并重置
  const closeSyncDialog = () => {
    setShowSyncDialog(false)
    setSyncTsCode('')
    setSyncHkCode('')
    setSyncTradeDate(undefined)
    setSyncStartDate(undefined)
    setSyncEndDate(undefined)
  }

  // 同步确认
  const handleSyncConfirm = async () => {
    const hasTsCode = syncTsCode.trim() !== ''
    const hasHkCode = syncHkCode.trim() !== ''
    const hasTradeDate = syncTradeDate !== undefined
    const hasDateRange = syncStartDate !== undefined || syncEndDate !== undefined

    if (!hasTsCode && !hasHkCode && !hasTradeDate && !hasDateRange) {
      toast.error('参数错误', { description: '请至少填写股票代码、港交所代码、交易日期或日期范围中的一个' })
      return
    }

    closeSyncDialog()

    try {
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
            toast.success('数据同步完成', { description: '中央结算系统持股明细数据已更新' })
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

  // 格式化数字
  const formatNumber = (value: number | null | undefined, decimals: number = 0): string => {
    if (value === null || value === undefined) return '-'
    return value.toLocaleString('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
  }

  // 移动端卡片
  const mobileCard = (item: CcassHoldDetailData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div className="font-semibold text-base">{item.name || item.ts_code}</div>
          <div className="text-sm text-gray-500">{item.col_participant_id} {item.col_participant_name ? `· ${item.col_participant_name}` : ''}</div>
        </div>
        <span className="text-xs text-gray-500">{item.trade_date}</span>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">股票代码</span>
          <span className="font-medium">{item.ts_code}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">持股量(股)</span>
          <span className="font-medium">{formatNumber(item.col_shareholding)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">持股比例</span>
          <span className="font-medium">{formatNumber(item.col_shareholding_percent, 2)}%</span>
        </div>
      </div>
    </div>
  )

  // 桌面端表格列定义
  const columns: Column<CcassHoldDetailData>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => row.trade_date,
      width: 110
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
      accessor: (row) => row.name || '-',
      width: 100
    },
    {
      key: 'col_participant_id',
      header: '参与者编号',
      accessor: (row) => row.col_participant_id,
      width: 110
    },
    {
      key: 'col_participant_name',
      header: '机构名称',
      accessor: (row) => row.col_participant_name || '-',
      width: 160
    },
    {
      key: 'col_shareholding',
      header: '持股量(股)',
      accessor: (row) => formatNumber(row.col_shareholding),
      width: 130,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'col_shareholding_percent',
      header: '持股比例(%)',
      accessor: (row) => formatNumber(row.col_shareholding_percent, 2),
      width: 110,
      cellClassName: 'text-right whitespace-nowrap'
    }
  ], [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="中央结算系统持股明细"
        description="查询中央结算系统（CCASS）参与者持股明细数据（8000积分/次）"
        details={<>
          <div>接口：ccass_hold_detail</div>
          <a href="https://tushare.pro/document/2?doc_id=207" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <Button onClick={() => setShowSyncDialog(true)} disabled={syncing}>
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

      {/* 筛选区域 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">股票代码</label>
              <Input
                placeholder="如 000001 或 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">参与者编号</label>
              <Input
                placeholder="如：C00001"
                value={participantId}
                onChange={(e) => setParticipantId(e.target.value)}
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
            <Button onClick={() => loadData(1).catch(() => {})} disabled={isLoading}>
              {isLoading ? '查询中...' : '查询'}
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
            emptyMessage="暂无持股明细数据"
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: (newPage) => loadData(newPage),
              onPageSizeChange: (newPageSize) => {
                setPageSize(newPageSize)
                loadData(1)
              },
              pageSizeOptions: [10, 20, 30, 50, 100]
            }}
          />
        </CardContent>
      </Card>

      {/* 同步参数弹窗 */}
      <Dialog open={showSyncDialog} onOpenChange={setShowSyncDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>同步中央结算系统持股明细</DialogTitle>
            <DialogDescription>
              请至少填写一个参数（股票代码、港交所代码、交易日期或日期范围）
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="sync-ts-code">股票代码</Label>
              <Input
                id="sync-ts-code"
                placeholder="如：00960.HK"
                value={syncTsCode}
                onChange={(e) => setSyncTsCode(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">港股代码格式，如：00960.HK</p>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="sync-hk-code">港交所代码</Label>
              <Input
                id="sync-hk-code"
                placeholder="如：95009"
                value={syncHkCode}
                onChange={(e) => setSyncHkCode(e.target.value)}
              />
            </div>

            <div className="grid gap-2">
              <Label>交易日期</Label>
              <DatePicker date={syncTradeDate} onDateChange={setSyncTradeDate} placeholder="选择交易日期" />
            </div>

            <div className="grid gap-2">
              <Label>日期范围（可选）</Label>
              <div className="flex gap-2 items-center">
                <DatePicker date={syncStartDate} onDateChange={setSyncStartDate} placeholder="开始日期" />
                <span className="text-muted-foreground">至</span>
                <DatePicker date={syncEndDate} onDateChange={setSyncEndDate} placeholder="结束日期" />
              </div>
              <p className="text-xs text-muted-foreground">单次最大6000条</p>
            </div>

            <div className="rounded-lg bg-amber-50 dark:bg-amber-950 p-3 border border-amber-200 dark:border-amber-800">
              <p className="text-sm text-amber-800 dark:text-amber-200">
                <strong>注意：</strong>此接口消耗 8000 积分/次，单次最大返回 6000 条数据
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={closeSyncDialog} disabled={syncing}>取消</Button>
            <Button onClick={handleSyncConfirm} disabled={syncing}>
              {syncing ? (
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
              ) : (
                <><RefreshCw className="h-4 w-4 mr-1" />开始同步</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
