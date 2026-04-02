'use client'

import { useState, useEffect, useMemo, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { hkHoldApi, type HkHoldData, type HkHoldStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, BarChart3, Users, TrendingUp, Percent } from 'lucide-react'

const PAGE_SIZE = 100

export default function HkHoldPage() {
  const [data, setData] = useState<HkHoldData[]>([])
  const [statistics, setStatistics] = useState<HkHoldStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState<string>('')
  const [code, setCode] = useState<string>('')
  const [exchange, setExchange] = useState<string>('')

  // 分页状态
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)

  // 排序状态
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc' | null>(null)

  // 同步弹窗
  const [syncDialogOpen, setSyncDialogOpen] = useState(false)
  const [syncDate, setSyncDate] = useState<Date | undefined>(undefined)

  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()

  // 从 task store 实时派生——不用本地 useState
  const syncing = isTaskRunning('tasks.sync_hk_hold')

  // 时区安全的日期字符串构建
  const toDateStr = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

  const loadData = async (
    targetPage: number = page,
    overrideSortKey?: string | null,
    overrideSortDir?: 'asc' | 'desc' | null
  ) => {
    try {
      setIsLoading(true)

      const activeSortKey = overrideSortKey !== undefined ? overrideSortKey : sortKey
      const activeSortDir = overrideSortDir !== undefined ? overrideSortDir : sortDirection

      const params: any = {
        page: targetPage,
        page_size: PAGE_SIZE,
      }
      if (tradeDate) params.trade_date = toDateStr(tradeDate)
      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (code.trim()) params.code = code.trim()
      if (exchange.trim()) params.exchange = exchange.trim()
      if (activeSortKey) {
        params.sort_by = activeSortKey
        params.sort_order = activeSortDir || 'desc'
      }

      const response = await hkHoldApi.getData(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics || null)
        setTotal(response.data.total || 0)
        setPage(targetPage)

        // 自动回填最近有数据的交易日
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

  // 初始加载
  useEffect(() => {
    loadData(1).catch(() => {})
  }, [])

  // 同步确认
  const handleSyncConfirm = async () => {
    setSyncDialogOpen(false)
    try {
      const params: any = {}
      if (syncDate) params.trade_date = toDateStr(syncDate)

      const response = await hkHoldApi.syncAsync(params)

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
            toast.success('数据同步完成', { description: '北向资金持股数据已更新' })
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

  const formatNumber = (value: number | null | undefined, decimals: number = 0): string => {
    if (value === null || value === undefined) return '-'
    return value.toLocaleString('zh-CN', { minimumFractionDigits: decimals, maximumFractionDigits: decimals })
  }

  // 移动端卡片
  const mobileCard = (item: HkHoldData) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div className="font-semibold text-base">{item.name || item.ts_code || item.code}</div>
          <div className="text-sm text-gray-500">{[item.ts_code, item.code].filter(Boolean).join(' / ')}</div>
        </div>
        <span className="text-xs text-gray-500">{item.trade_date}</span>
      </div>
      <div className="space-y-1 text-sm">
        {item.exchange && (
          <div className="flex justify-between">
            <span className="text-gray-600">交易所</span>
            <span className="font-medium">{item.exchange}</span>
          </div>
        )}
        {item.vol !== null && item.vol !== undefined && (
          <div className="flex justify-between">
            <span className="text-gray-600">持股数</span>
            <span className="font-medium">{formatNumber(item.vol)}万股</span>
          </div>
        )}
        {item.ratio !== null && item.ratio !== undefined && (
          <div className="flex justify-between">
            <span className="text-gray-600">持股比例</span>
            <span className="font-medium text-blue-600">{formatNumber(item.ratio, 2)}%</span>
          </div>
        )}
      </div>
    </div>
  )

  // 桌面端表格列定义
  const columns: Column<HkHoldData>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => row.trade_date,
      width: 110,
      sortable: true
    },
    {
      key: 'ts_code',
      header: 'A股代码',
      accessor: (row) => row.ts_code || '-',
      width: 100
    },
    {
      key: 'code',
      header: '港股代码',
      accessor: (row) => row.code || '-',
      width: 100
    },
    {
      key: 'name',
      header: '股票名称',
      accessor: (row) => row.name || '-',
      width: 100
    },
    {
      key: 'exchange',
      header: '交易所',
      accessor: (row) => row.exchange || '-',
      width: 80,
      hideOnMobile: true
    },
    {
      key: 'vol',
      header: '持股数(万股)',
      accessor: (row) => formatNumber(row.vol),
      width: 120,
      cellClassName: 'text-right whitespace-nowrap',
      hideOnMobile: true,
      sortable: true
    },
    {
      key: 'amount',
      header: '持股额(百万元)',
      accessor: (row) => formatNumber(row.amount, 2),
      width: 130,
      cellClassName: 'text-right whitespace-nowrap',
      hideOnMobile: true,
      sortable: true
    },
    {
      key: 'ratio',
      header: '持股比例(%)',
      accessor: (row) => formatNumber(row.ratio, 2),
      width: 110,
      cellClassName: 'text-right whitespace-nowrap',
      sortable: true
    }
  ], [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="沪深港股通持股明细"
        description="获取沪深港股通持股明细，数据来源港交所。"
        details={<>
          <div>接口：hk_hold</div>
          <a href="https://tushare.pro/document/2?doc_id=188" target="_blank" rel="noopener noreferrer">查看文档</a>
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

      {/* 统计卡片 — 左文字右图标，单位内联 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">总记录数</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.total_count)}条</p>
                  <p className="text-xs text-gray-400 mt-0.5">当前筛选结果</p>
                </div>
                <BarChart3 className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">股票数</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.stock_count)}只</p>
                  <p className="text-xs text-gray-400 mt-0.5">持仓标的数量</p>
                </div>
                <Users className="h-6 w-6 sm:h-8 sm:w-8 text-orange-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">平均持股数</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.avg_vol)}万股</p>
                  <p className="text-xs text-gray-400 mt-0.5">平均持仓规模</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">最高持股比例</p>
                  <p className="text-xl sm:text-2xl font-bold text-blue-600">{formatNumber(statistics.max_ratio, 2)}%</p>
                  <p className="text-xs text-gray-400 mt-0.5">单只股票最高占比</p>
                </div>
                <Percent className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
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
          <div className="flex flex-col sm:flex-row gap-4 items-end flex-wrap">
            <div className="w-full sm:w-40">
              <label className="text-sm font-medium mb-2 block">交易日期</label>
              <DatePicker date={tradeDate} onDateChange={setTradeDate} placeholder="选择日期" />
            </div>
            <div className="w-full sm:w-40">
              <label className="text-sm font-medium mb-2 block">A股代码</label>
              <Input
                placeholder="如 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="w-full sm:w-40">
              <label className="text-sm font-medium mb-2 block">港股代码</label>
              <Input
                placeholder="如 00700.HK"
                value={code}
                onChange={(e) => setCode(e.target.value)}
              />
            </div>
            <div className="w-full sm:w-28">
              <label className="text-sm font-medium mb-2 block">交易所</label>
              <Input
                placeholder="SH / SZ"
                value={exchange}
                onChange={(e) => setExchange(e.target.value)}
              />
            </div>
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
            emptyMessage="暂无持股数据"
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

      {/* 同步弹窗 — 仅选日期，与查询筛选解耦 */}
      <Dialog open={syncDialogOpen} onOpenChange={setSyncDialogOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>同步沪深港股通持股明细</DialogTitle>
            <DialogDescription>
              选择同步日期（留空则同步最近30天数据）。消耗 2000 积分/次，2024年8月20日起改为季度披露。
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <label className="text-sm font-medium mb-2 block">交易日期（可选）</label>
            <DatePicker date={syncDate} onDateChange={setSyncDate} placeholder="留空同步最近30天" />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncDialogOpen(false)}>取消</Button>
            <Button onClick={handleSyncConfirm} disabled={syncing}>
              {syncing ? (
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
              ) : (
                <><RefreshCw className="h-4 w-4 mr-1" />确认同步</>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
