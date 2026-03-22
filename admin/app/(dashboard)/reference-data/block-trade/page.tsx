'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { blockTradeApi, BlockTradeData, BlockTradeStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, Briefcase, DollarSign, BarChart3, Users } from 'lucide-react'

export default function BlockTradePage() {
  const [data, setData] = useState<BlockTradeData[]>([])
  const [statistics, setStatistics] = useState<BlockTradeStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [syncing, setSyncing] = useState(false)

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params: any = { limit: pageSize }
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]
      if (tsCode) params.ts_code = tsCode.trim()

      const [dataResponse, statsResponse] = await Promise.all([
        blockTradeApi.getData(params),
        blockTradeApi.getStatistics({
          start_date: params.start_date,
          end_date: params.end_date
        })
      ])

      if (dataResponse.code === 200) {
        setData(dataResponse.data?.items || [])
        setTotal(dataResponse.data?.count || 0)
      }

      if (statsResponse.code === 200) {
        setStatistics(statsResponse.data || null)
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast.error('加载失败', { description: err.message })
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, tsCode, pageSize])

  useEffect(() => {
    loadData()
  }, [loadData])

  // 异步同步数据
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params: any = {}
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]
      if (tsCode) params.ts_code = tsCode.trim()

      const response = await blockTradeApi.syncAsync(params)

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
            toast.success('数据同步完成', { description: '大宗交易数据已更新' })
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
      }
    } catch (err: any) {
      toast.error('同步失败', { description: err.message || '无法同步数据' })
    } finally {
      setSyncing(false)
    }
  }

  // 组件卸载清理
  useEffect(() => {
    return () => {
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
    }
  }, [unregisterCompletionCallback])

  // 格式化金额
  const formatAmount = (amount: number | null | undefined) => {
    if (amount === null || amount === undefined) return '-'
    return `${amount.toLocaleString()} 万元`
  }

  // 格式化数量
  const formatVolume = (vol: number | null | undefined) => {
    if (vol === null || vol === undefined) return '-'
    return `${vol.toLocaleString()} 万股`
  }

  // 格式化价格
  const formatPrice = (price: number | null | undefined) => {
    if (price === null || price === undefined) return '-'
    return `${price.toFixed(2)} 元`
  }

  // 表格列定义
  const columns: Column<BlockTradeData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => row.trade_date
    },
    {
      key: 'price',
      header: '成交价',
      accessor: (row) => formatPrice(row.price),
      align: 'right'
    },
    {
      key: 'vol',
      header: '成交量',
      accessor: (row) => formatVolume(row.vol),
      align: 'right'
    },
    {
      key: 'amount',
      header: '成交金额',
      accessor: (row) => formatAmount(row.amount),
      align: 'right'
    },
    {
      key: 'buyer',
      header: '买方营业部',
      accessor: (row) => (
        <span className="text-xs" title={row.buyer}>
          {row.buyer.length > 20 ? row.buyer.substring(0, 20) + '...' : row.buyer}
        </span>
      )
    },
    {
      key: 'seller',
      header: '卖方营业部',
      accessor: (row) => (
        <span className="text-xs" title={row.seller}>
          {row.seller.length > 20 ? row.seller.substring(0, 20) + '...' : row.seller}
        </span>
      )
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: BlockTradeData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">股票代码</span>
        <span className="font-medium">{item.ts_code}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">交易日期</span>
        <span className="font-medium">{item.trade_date}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">成交金额</span>
        <span className="font-medium text-blue-600">{formatAmount(item.amount)}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">成交价</span>
        <span className="font-medium">{formatPrice(item.price)}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">成交量</span>
        <span className="font-medium">{formatVolume(item.vol)}</span>
      </div>
      <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
        <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">买方营业部</div>
        <div className="text-xs font-medium break-all">{item.buyer}</div>
      </div>
      <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
        <div className="text-xs text-gray-600 dark:text-gray-400 mb-1">卖方营业部</div>
        <div className="text-xs font-medium break-all">{item.seller}</div>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="大宗交易"
        description="股票大宗交易数据，包含成交价、成交量、买卖方营业部等信息（300积分/次）"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">不同股票数</CardTitle>
              <Briefcase className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.stock_count || 0}</div>
              <p className="text-xs text-muted-foreground mt-1">
                参与大宗交易的股票数量
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">总记录数</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.total_records?.toLocaleString() || 0}</div>
              <p className="text-xs text-muted-foreground mt-1">
                最新日期：{statistics.latest_date || '-'}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">总成交金额</CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {((statistics.total_amount || 0) / 10000).toFixed(2)} 亿
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                平均：{((statistics.avg_amount || 0)).toFixed(2)} 万元
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最大成交金额</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {(statistics.max_amount || 0).toLocaleString()} 万元
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                单笔最大交易金额
              </p>
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
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">股票代码</label>
              <Input
                placeholder="如：000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">开始日期</label>
              <DatePicker
                date={startDate}
                onSelect={setStartDate}
              />
            </div>
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">结束日期</label>
              <DatePicker
                date={endDate}
                onSelect={setEndDate}
              />
            </div>
            <div className="flex items-end gap-2">
              <Button onClick={loadData} disabled={loading}>
                查询
              </Button>
              <Button
                onClick={handleSync}
                disabled={syncing}
                variant="outline"
              >
                <RefreshCw className={`mr-2 h-4 w-4 ${syncing ? 'animate-spin' : ''}`} />
                同步数据
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="pt-6">
          <DataTable
            columns={columns}
            data={data}
            loading={loading}
            emptyMessage="暂无大宗交易数据"
            mobileCard={mobileCard}
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: setPage,
              onPageSizeChange: setPageSize
            }}
          />
        </CardContent>
      </Card>
    </div>
  )
}
