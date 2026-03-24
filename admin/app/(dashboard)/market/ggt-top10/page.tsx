'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ggtTop10Api, type GgtTop10Data, type GgtTop10Statistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, TrendingDown, Activity, DollarSign } from 'lucide-react'

export default function GgtTop10Page() {
  // 数据状态
  const [data, setData] = useState<GgtTop10Data[]>([])
  const [statistics, setStatistics] = useState<GgtTop10Statistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 筛选条件
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [marketType, setMarketType] = useState<string>('ALL')
  const [syncing, setSyncing] = useState(false)

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // 任务存储
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params: any = {
        limit: pageSize
      }

      if (startDate) {
        params.start_date = startDate.toISOString().split('T')[0]
      }
      if (endDate) {
        params.end_date = endDate.toISOString().split('T')[0]
      }
      if (tsCode.trim()) {
        params.ts_code = tsCode.trim()
      }
      if (marketType && marketType !== 'ALL') {
        params.market_type = marketType
      }

      const [dataResponse, statsResponse] = await Promise.all([
        ggtTop10Api.getGgtTop10(params),
        ggtTop10Api.getStatistics({
          start_date: params.start_date,
          end_date: params.end_date,
          market_type: params.market_type
        })
      ])

      if (dataResponse.code === 200) {
        setData(dataResponse.data.items)
        setTotal(dataResponse.data.total)
      } else {
        throw new Error(dataResponse.message || '加载数据失败')
      }

      if (statsResponse.code === 200) {
        setStatistics(statsResponse.data)
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast.error('加载失败', {
        description: err.message || '无法加载数据'
      })
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, tsCode, marketType, pageSize])

  // 初始加载
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
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 异步同步数据
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params: any = {}
      if (startDate) {
        params.start_date = startDate.toISOString().split('T')[0]
      }
      if (endDate) {
        params.end_date = endDate.toISOString().split('T')[0]
      }
      if (tsCode.trim()) {
        params.ts_code = tsCode.trim()
      }
      if (marketType && marketType !== 'ALL') {
        params.market_type = marketType
      }

      const response = await ggtTop10Api.syncAsync(params)

      if (response.code === 200 && response.data) {
        const taskId = response.data.celery_task_id

        // 添加到任务存储
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
            loadData().catch(() => {})
            toast.success('数据同步完成', {
              description: '港股通十大成交股数据已更新'
            })
          } else if (task.status === 'failure') {
            toast.error('数据同步失败', {
              description: task.error || '同步过程中发生错误'
            })
          }
          unregisterCompletionCallback(taskId, completionCallback)
          activeCallbacksRef.current.delete(taskId)
        }

        activeCallbacksRef.current.set(taskId, completionCallback)
        registerCompletionCallback(taskId, completionCallback)

        // 立即触发轮询
        triggerPoll()

        toast.success('任务已提交', {
          description: `"${response.data.display_name}" 已开始执行，可在任务面板查看进度`
        })
      } else {
        throw new Error(response.message || '同步失败')
      }
    } catch (err: any) {
      toast.error('同步失败', {
        description: err.message || '无法同步数据'
      })
    } finally {
      setSyncing(false)
    }
  }

  // 表格列定义
  const columns: Column<HsgtTop10Data>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => row.trade_date
    },
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'name',
      header: '股票名称',
      accessor: (row) => row.name
    },
    {
      key: 'market_type',
      header: (
        <>
          <span className="sm:hidden">市</span>
          <span className="hidden sm:inline">市场类型</span>
        </>
      ),
      accessor: (row) => row.market_type === '1' ? '沪市' : row.market_type === '3' ? '深市' : row.market_type
    },
    {
      key: 'rank',
      header: '排名',
      accessor: (row) => row.rank
    },
    {
      key: 'close',
      header: '收盘价',
      accessor: (row) => row.close?.toFixed(2) || '-'
    },
    {
      key: 'change',
      header: '涨跌额',
      accessor: (row) => {
        const change = row.change
        if (change === null || change === undefined) return '-'
        const color = change >= 0 ? 'text-red-600' : 'text-green-600'
        return <span className={color}>{change >= 0 ? '+' : ''}{change.toFixed(2)}</span>
      }
    },
    {
      key: 'amount',
      header: (
        <>
          <span className="sm:hidden">成交额</span>
          <span className="hidden sm:inline">成交金额(万元)</span>
        </>
      ),
      accessor: (row) => (row.amount / 10000).toFixed(2)
    },
    {
      key: 'net_amount',
      header: (
        <>
          <span className="sm:hidden">净额</span>
          <span className="hidden sm:inline">净成交金额(万元)</span>
        </>
      ),
      accessor: (row) => {
        const netAmount = row.net_amount / 10000
        const color = netAmount >= 0 ? 'text-red-600' : 'text-green-600'
        return <span className={color}>{netAmount >= 0 ? '+' : ''}{netAmount.toFixed(2)}</span>
      }
    },
    {
      key: 'buy',
      header: (
        <>
          <span className="sm:hidden">买</span>
          <span className="hidden sm:inline">买入金额(万元)</span>
        </>
      ),
      accessor: (row) => (row.buy / 10000).toFixed(2)
    },
    {
      key: 'sell',
      header: (
        <>
          <span className="sm:hidden">卖</span>
          <span className="hidden sm:inline">卖出金额(万元)</span>
        </>
      ),
      accessor: (row) => (row.sell / 10000).toFixed(2)
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: HsgtTop10Data) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <div>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">{item.ts_code}</span>
          <span className="ml-2 text-xs text-gray-500">{item.name}</span>
        </div>
        <span className="text-xs px-2 py-1 rounded bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200">
          排名 {item.rank}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">交易日期</span>
          <span className="font-medium text-sm">{item.trade_date}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">市场类型</span>
          <span className="font-medium text-sm">
            {item.market_type === '1' ? '沪市' : item.market_type === '3' ? '深市' : item.market_type}
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">收盘价</span>
          <span className="font-medium text-sm">{item.close?.toFixed(2) || '-'}</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">涨跌额</span>
          <span className={`font-medium text-sm ${(item.change ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
            {(item.change ?? 0) >= 0 ? '+' : ''}{item.change?.toFixed(2) || '-'}
          </span>
        </div>
        <div className="flex justify-between items-center col-span-2">
          <span className="text-sm text-gray-600 dark:text-gray-400">成交金额</span>
          <span className="font-medium text-sm">{(item.amount / 10000).toFixed(2)} 万元</span>
        </div>
        <div className="flex justify-between items-center col-span-2">
          <span className="text-sm text-gray-600 dark:text-gray-400">净成交金额</span>
          <span className={`font-medium text-sm ${(item.net_amount ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}`}>
            {(item.net_amount ?? 0) >= 0 ? '+' : ''}{(item.net_amount / 10000).toFixed(2)} 万元
          </span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">买入</span>
          <span className="font-medium text-sm">{(item.buy / 10000).toFixed(2)} 万元</span>
        </div>
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">卖出</span>
          <span className="font-medium text-sm">{(item.sell / 10000).toFixed(2)} 万元</span>
        </div>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="港股通十大成交股"
        description="查看港股通(沪)、港股通(深)每日前十大成交详细数据，每天18~20点之间完成当日更新"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">平均成交金额</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.avg_amount_yi.toFixed(2)}</div>
              <p className="text-xs text-muted-foreground">亿元</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">平均净成交金额</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className={`text-2xl font-bold ${statistics.avg_net_amount_yi >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                {statistics.avg_net_amount_yi >= 0 ? '+' : ''}{statistics.avg_net_amount_yi.toFixed(2)}
              </div>
              <p className="text-xs text-muted-foreground">亿元</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最大成交金额</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.max_amount_yi.toFixed(2)}</div>
              <p className="text-xs text-muted-foreground">亿元</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">统计股票数</CardTitle>
              <TrendingDown className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.stock_count}</div>
              <p className="text-xs text-muted-foreground">{statistics.trading_days} 个交易日</p>
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
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 items-end">
            <div className="space-y-2">
              <Label htmlFor="start-date">开始日期</Label>
              <DatePicker
                date={startDate}
                onSelect={setStartDate}
                placeholder="选择开始日期"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="end-date">结束日期</Label>
              <DatePicker
                date={endDate}
                onSelect={setEndDate}
                placeholder="选择结束日期"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ts-code">股票代码</Label>
              <Input
                id="ts-code"
                placeholder="如：600519.SH"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="market-type">市场类型</Label>
              <Select value={marketType} onValueChange={setMarketType}>
                <SelectTrigger>
                  <SelectValue placeholder="选择市场" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="1">沪市</SelectItem>
                  <SelectItem value="3">深市</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex gap-2">
              <Button onClick={loadData} disabled={loading} className="flex-1">
                查询
              </Button>
              <Button
                variant="default"
                onClick={handleSync}
                disabled={syncing}
              >
                {syncing ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                    <span className="hidden sm:inline">同步中...</span>
                  </>
                ) : (
                  <>
                    <RefreshCw className="h-4 w-4 mr-1" />
                    <span className="hidden sm:inline">同步数据</span>
                  </>
                )}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card className="p-0 sm:p-0 overflow-hidden">
        {/* 移动端视图 */}
        <div className="sm:hidden">
          <div className="px-4 py-3 border-b bg-muted/50">
            <h3 className="text-sm font-medium">十大成交股数据</h3>
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
            loading={loading}
            error={error}
            emptyMessage="暂无数据"
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: (newPage) => {
                setPage(newPage)
              },
              onPageSizeChange: (newPageSize) => {
                setPageSize(newPageSize)
                setPage(1)
              },
              pageSizeOptions: [10, 20, 30, 50, 100]
            }}
          />
        </div>
      </Card>
    </div>
  )
}
