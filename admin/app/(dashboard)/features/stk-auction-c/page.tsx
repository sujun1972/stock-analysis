'use client'

import { useState, useEffect, useMemo, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Input } from '@/components/ui/input'
import { stkAuctionCApi } from '@/lib/api/stk-auction-c'
import type { StkAuctionCData, StkAuctionCStatistics } from '@/lib/api/stk-auction-c'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, BarChart3, DollarSign, Activity } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

export default function StkAuctionCPage() {
  const [data, setData] = useState<StkAuctionCData[]>([])
  const [statistics, setStatistics] = useState<StkAuctionCStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // 同步弹窗状态
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncTsCode, setSyncTsCode] = useState('')
  const [syncTradeDate, setSyncTradeDate] = useState<Date | undefined>(undefined)
  const [syncStartDate, setSyncStartDate] = useState<Date | undefined>(undefined)
  const [syncEndDate, setSyncEndDate] = useState<Date | undefined>(undefined)

  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()

  // 从 task store 实时派生——不用本地 useState
  const syncing = isTaskRunning('tasks.sync_stk_auction_c')

  // 时区安全的日期字符串构建
  const toDateStr = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

  // 加载数据
  const loadData = async (targetPage: number = page) => {
    try {
      setIsLoading(true)

      const params: any = {
        page: targetPage,
        page_size: pageSize
      }
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (tradeDate) params.trade_date = toDateStr(tradeDate)

      const response = await stkAuctionCApi.getData(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics || null)
        setTotal(response.data.total || 0)
        setPage(targetPage)
        // 回填默认日期
        if (!tradeDate && response.data.trade_date) {
          setTradeDate(new Date(response.data.trade_date + 'T00:00:00'))
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
      if (syncTradeDate) params.trade_date = toDateStr(syncTradeDate)
      if (syncStartDate) params.start_date = toDateStr(syncStartDate)
      if (syncEndDate) params.end_date = toDateStr(syncEndDate)

      const response = await stkAuctionCApi.syncAsync(params)

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
            toast.success('数据同步完成', { description: '收盘集合竞价数据已更新' })
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

  // 格式化数字
  const formatNumber = (value: number | null | undefined, decimals: number = 2): string => {
    if (value === null || value === undefined) return '-'
    return value.toLocaleString('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
  }

  // 移动端卡片
  const mobileCard = (item: StkAuctionCData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div className="font-semibold text-base">{item.ts_code}</div>
          <div className="text-sm text-gray-500">{formatDate(item.trade_date)}</div>
        </div>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">开盘价</span>
          <span className="font-medium">{formatNumber(item.open)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">收盘价</span>
          <span className="font-medium">{formatNumber(item.close)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">成交量</span>
          <span className="font-medium">{formatNumber(item.vol)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">成交额</span>
          <span className="font-medium">{formatNumber(item.amount)}</span>
        </div>
        {item.vwap !== null && item.vwap !== undefined && (
          <div className="flex justify-between">
            <span className="text-gray-600">均价</span>
            <span className="font-medium">{formatNumber(item.vwap)}</span>
          </div>
        )}
      </div>
    </div>
  )

  // 桌面端表格列定义
  const columns: Column<StkAuctionCData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code,
      width: 110
    },
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => formatDate(row.trade_date),
      width: 110
    },
    {
      key: 'open',
      header: '开盘价',
      accessor: (row) => formatNumber(row.open),
      width: 90,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'high',
      header: '最高价',
      accessor: (row) => formatNumber(row.high),
      width: 90,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'low',
      header: '最低价',
      accessor: (row) => formatNumber(row.low),
      width: 90,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'close',
      header: '收盘价',
      accessor: (row) => formatNumber(row.close),
      width: 90,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'vwap',
      header: '均价',
      accessor: (row) => formatNumber(row.vwap),
      width: 90,
      cellClassName: 'text-right whitespace-nowrap',
      hideOnMobile: true
    },
    {
      key: 'vol',
      header: '成交量(手)',
      accessor: (row) => formatNumber(row.vol),
      width: 110,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'amount',
      header: '成交额(万元)',
      accessor: (row) => formatNumber(row.amount),
      width: 120,
      cellClassName: 'text-right whitespace-nowrap'
    }
  ], [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="股票收盘集合竞价"
        description="股票收盘15:00集合竞价数据，每天盘后更新"
        details={<>
          <div>接口：stk_auction_c</div>
          <a href="https://tushare.pro/document/2?doc_id=354" target="_blank" rel="noopener noreferrer">查看文档</a>
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
                  <p className="text-xs sm:text-sm text-gray-600">股票数量</p>
                  <p className="text-xl sm:text-2xl font-bold">{(statistics.stock_count ?? 0).toLocaleString()}</p>
                  <p className="text-xs text-gray-400 mt-0.5">只</p>
                </div>
                <Activity className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">平均成交量</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.avg_vol)}</p>
                  <p className="text-xs text-gray-400 mt-0.5">手</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">最大成交量</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.max_vol)}</p>
                  <p className="text-xs text-gray-400 mt-0.5">手</p>
                </div>
                <BarChart3 className="h-6 w-6 sm:h-8 sm:w-8 text-orange-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">最大成交额</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.max_amount)}</p>
                  <p className="text-xs text-gray-400 mt-0.5">万元</p>
                </div>
                <DollarSign className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
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
              <label className="text-sm font-medium mb-2 block">交易日期</label>
              <DatePicker date={tradeDate} onDateChange={setTradeDate} placeholder="留空默认最近有数据日期" />
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
            emptyMessage="暂无收盘集合竞价数据"
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
            <DialogTitle>同步收盘集合竞价数据</DialogTitle>
            <DialogDescription>
              所有参数均为可选，不填写将同步最近交易日数据（需开通股票分钟权限）。
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
              <label className="text-sm font-medium mb-2 block">交易日期（可选）</label>
              <DatePicker date={syncTradeDate} onDateChange={setSyncTradeDate} placeholder="留空同步最新交易日" />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">开始日期（可选）</label>
              <DatePicker date={syncStartDate} onDateChange={setSyncStartDate} placeholder="日期范围起始" />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">结束日期（可选）</label>
              <DatePicker date={syncEndDate} onDateChange={setSyncEndDate} placeholder="日期范围结束" />
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
