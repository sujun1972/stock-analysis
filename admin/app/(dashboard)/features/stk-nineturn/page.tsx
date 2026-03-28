'use client'

import { useState, useEffect, useMemo, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { stkNineturnApi, type StkNineturnData, type StkNineturnStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, TrendingDown, BarChart3, Activity } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

export default function StkNineturnPage() {
  const [data, setData] = useState<StkNineturnData[]>([])
  const [statistics, setStatistics] = useState<StkNineturnStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [freq, setFreq] = useState('daily')

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // 同步弹窗状态
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncTsCode, setSyncTsCode] = useState('')
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()

  // 从 task store 实时派生——不用本地 useState
  const syncing = isTaskRunning('tasks.sync_stk_nineturn')

  // 时区安全的日期字符串构建
  const toDateStr = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

  // 加载数据
  const loadData = async (targetPage: number = page) => {
    try {
      setIsLoading(true)

      const params: any = {
        freq,
        page: targetPage,
        page_size: pageSize
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
      const params: any = { freq }
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
          <div className="font-semibold text-base">{item.ts_code}</div>
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
          <span className={item.up_count && item.up_count >= 9 ? 'font-semibold text-red-600' : 'font-medium'}>
            {item.up_count !== null ? item.up_count.toFixed(1) : '-'}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">下九转计数</span>
          <span className={item.down_count && item.down_count >= 9 ? 'font-semibold text-green-600' : 'font-medium'}>
            {item.down_count !== null ? item.down_count.toFixed(1) : '-'}
          </span>
        </div>
      </div>
    </div>
  )

  // 桌面端表格列定义
  const columns: Column<StkNineturnData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code,
      width: 110
    },
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => row.trade_date ? row.trade_date.split(' ')[0] : '-',
      width: 110
    },
    {
      key: 'close',
      header: '收盘价',
      accessor: (row) => row.close !== null ? row.close.toFixed(2) : '-',
      width: 90,
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
  ], [])

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
              <label className="text-sm font-medium mb-2 block">频率</label>
              <Select value={freq} onValueChange={setFreq}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="daily">日线</SelectItem>
                </SelectContent>
              </Select>
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
            emptyMessage="暂无神奇九转指标数据"
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
