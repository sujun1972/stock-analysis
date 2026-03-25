'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { topInstApi, type TopInstItem, type TopInstStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, TrendingDown, Building2, Users } from 'lucide-react'

export default function TopInstPage() {
  // 数据状态
  const [data, setData] = useState<TopInstItem[]>([])
  const [statistics, setStatistics] = useState<TopInstStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // 筛选条件
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [side, setSide] = useState<string>('ALL')
  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // 任务管理
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const syncing = isTaskRunning('tasks.sync_top_inst')

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
      if (tsCode) {
        params.ts_code = tsCode.trim()
      }
      if (side !== 'ALL') {
        params.side = side
      }

      const [dataResponse, statsResponse] = await Promise.all([
        topInstApi.getTopInst(params),
        topInstApi.getStatistics({
          start_date: params.start_date,
          end_date: params.end_date,
          ts_code: params.ts_code
        })
      ])

      if (dataResponse.code === 200) {
        setData(dataResponse.data?.items || [])
        setTotal(dataResponse.data?.total || 0)
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
  }, [startDate, endDate, tsCode, side, pageSize])

  // 初始加载
  useEffect(() => {
    loadData()
  }, [loadData])

  // 异步同步
  const handleSync = async () => {
    try {
      const params: any = {}
      if (startDate) {
        params.trade_date = startDate.toISOString().split('T')[0]
      }
      if (tsCode) {
        params.ts_code = tsCode.trim()
      }

      const response = await topInstApi.syncAsync(params)

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
            toast.success('数据同步完成', { description: '龙虎榜机构明细数据已更新' })
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 表格列定义
  const columns: Column<TopInstItem>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => row.trade_date || '-'
    },
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code || '-'
    },
    {
      key: 'exalter',
      header: '营业部名称',
      accessor: (row) => (
        <span className="truncate max-w-[200px]" title={row.exalter || ''}>
          {row.exalter || '-'}
        </span>
      )
    },
    {
      key: 'side',
      header: '买卖类型',
      accessor: (row) => (
        <span className={row.side === '0' ? 'text-red-600' : 'text-green-600'}>
          {row.side === '0' ? '买入' : '卖出'}
        </span>
      )
    },
    {
      key: 'buy',
      header: '买入额(万元)',
      accessor: (row) => row.buy?.toFixed(2) || '0.00',
      align: 'right'
    },
    {
      key: 'sell',
      header: '卖出额(万元)',
      accessor: (row) => row.sell?.toFixed(2) || '0.00',
      align: 'right'
    },
    {
      key: 'net_buy',
      header: '净成交额(万元)',
      accessor: (row) => {
        const value = row.net_buy || 0
        return (
          <span className={value >= 0 ? 'text-red-600 font-medium' : 'text-green-600 font-medium'}>
            {value >= 0 ? '+' : ''}{value.toFixed(2)}
          </span>
        )
      },
      align: 'right'
    },
    {
      key: 'reason',
      header: '上榜理由',
      accessor: (row) => (
        <span className="text-sm text-muted-foreground truncate max-w-[300px]" title={row.reason || ''}>
          {row.reason || '-'}
        </span>
      )
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: TopInstItem) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b">
        <span className="text-sm font-medium">{item.trade_date}</span>
        <span className={item.side === '0' ? 'text-red-600 font-medium' : 'text-green-600 font-medium'}>
          {item.side === '0' ? '买入' : '卖出'}
        </span>
      </div>
      <div className="flex justify-between">
        <span className="text-sm text-muted-foreground">股票代码</span>
        <span className="font-medium">{item.ts_code}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-sm text-muted-foreground">营业部</span>
        <span className="font-medium text-sm truncate max-w-[200px]">{item.exalter}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-sm text-muted-foreground">净成交额</span>
        <span className={(item.net_buy || 0) >= 0 ? 'text-red-600 font-medium' : 'text-green-600 font-medium'}>
          {(item.net_buy || 0) >= 0 ? '+' : ''}{(item.net_buy || 0).toFixed(2)} 万元
        </span>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="龙虎榜机构明细"
        description="龙虎榜机构成交明细"
        details={<>
          <div>接口：top_inst</div>
          <a href="https://tushare.pro/document/2?doc_id=107" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <Button onClick={handleSync} disabled={syncing}>
            {syncing ? (
              <>
                <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
                同步中...
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4 mr-1" />
                同步数据
              </>
            )}
          </Button>
        }
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">营业部数量</CardTitle>
              <Building2 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.exalter_count}</div>
              <p className="text-xs text-muted-foreground">总记录: {statistics.total_records}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">股票数量</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.stock_count}</div>
              <p className="text-xs text-muted-foreground">交易天数: {statistics.trading_days}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">累计净买入</CardTitle>
              <TrendingUp className="h-4 w-4 text-red-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {(statistics.total_net_buy / 10000).toFixed(2)} 亿
              </div>
              <p className="text-xs text-muted-foreground">
                平均: {statistics.avg_net_buy.toFixed(2)} 万
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">累计净卖出</CardTitle>
              <TrendingDown className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {(Math.abs(statistics.total_net_sell) / 10000).toFixed(2)} 亿
              </div>
              <p className="text-xs text-muted-foreground">
                最大净买入: {statistics.max_net_buy.toFixed(2)} 万
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选和操作 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="flex-1">
              <DatePicker date={startDate} onDateChange={setStartDate} placeholder="开始日期" />
            </div>
            <div className="flex-1">
              <DatePicker date={endDate} onDateChange={setEndDate} placeholder="结束日期" />
            </div>
            <div className="flex-1">
              <Input
                placeholder="股票代码（如 000001.SZ）"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="flex-1">
              <Select value={side} onValueChange={setSide}>
                <SelectTrigger>
                  <SelectValue placeholder="买卖类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="0">买入</SelectItem>
                  <SelectItem value="1">卖出</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button onClick={loadData} disabled={loading}>
              {loading ? '查询中...' : '查询'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card className="p-0 sm:p-0 overflow-hidden">
        {/* 移动端视图 */}
        <div className="sm:hidden">
          <div className="px-4 py-3 border-b bg-muted/50">
            <h3 className="text-sm font-medium">机构明细数据</h3>
          </div>
          <div className="divide-y">
            {!loading && !error && data.map((item, index) => (
              <div
                key={index}
                className={`p-4 transition-colors ${
                  index % 2 === 0
                    ? 'bg-white dark:bg-gray-900 hover:bg-blue-50 dark:hover:bg-blue-950/20 active:bg-blue-100'
                    : 'bg-gray-50 dark:bg-gray-950 hover:bg-blue-50 dark:hover:bg-blue-950/20 active:bg-blue-100'
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

        {/* 桌面端表格 */}
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
              onPageChange: (newPage) => setPage(newPage),
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
