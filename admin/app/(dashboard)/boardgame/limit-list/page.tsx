'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DatePicker } from '@/components/ui/date-picker'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { limitListApi, type LimitListData, type LimitListStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, TrendingDown, Zap } from 'lucide-react'

export default function LimitListPage() {
  const [data, setData] = useState<LimitListData[]>([])
  const [statistics, setStatistics] = useState<LimitListStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [limitType, setLimitType] = useState<string>('ALL')
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const syncing = isTaskRunning('tasks.sync_limit_list')

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params: any = { limit: 100 }
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]
      if (tsCode) params.ts_code = tsCode
      if (limitType && limitType !== 'ALL') params.limit_type = limitType

      const response = await limitListApi.getData(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics || null)
      } else {
        throw new Error(response.message || '加载数据失败')
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast.error('加载数据失败', { description: err.message })
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, tsCode, limitType])

  useEffect(() => {
    loadData()
  }, [loadData])

  // 异步同步
  const handleSync = async () => {
    try {
      const params: any = {}
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]
      if (tsCode) params.ts_code = tsCode
      if (limitType && limitType !== 'ALL') params.limit_type = limitType

      const response = await limitListApi.syncAsync(params)

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
            toast.success('数据同步完成', { description: '涨跌停列表数据已更新' })
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

  // 清理回调
  useEffect(() => {
    return () => {
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
    }
  }, [unregisterCompletionCallback])

  // 表格列定义
  const columns: Column<LimitListData>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '日期',
      accessor: (row) => row.trade_date?.slice(0, 4) + '-' + row.trade_date?.slice(4, 6) + '-' + row.trade_date?.slice(6, 8)
    },
    {
      key: 'ts_code',
      header: '代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'name',
      header: '名称',
      accessor: (row) => row.name || '-'
    },
    {
      key: 'limit_type',
      header: '类型',
      accessor: (row) => {
        if (row.limit_type === 'U') return <span className="text-red-600 font-semibold">涨停</span>
        if (row.limit_type === 'D') return <span className="text-green-600 font-semibold">跌停</span>
        if (row.limit_type === 'Z') return <span className="text-orange-600 font-semibold">炸板</span>
        return '-'
      }
    },
    {
      key: 'close',
      header: '收盘价',
      accessor: (row) => row.close?.toFixed(2) || '-',
      className: 'text-right'
    },
    {
      key: 'pct_chg',
      header: '涨跌幅%',
      accessor: (row) => {
        if (row.pct_chg === null || row.pct_chg === undefined) return '-'
        const val = row.pct_chg
        return (
          <span className={val >= 0 ? 'text-red-600' : 'text-green-600'}>
            {val >= 0 ? '+' : ''}{val.toFixed(2)}%
          </span>
        )
      },
      className: 'text-right'
    },
    {
      key: 'limit_times',
      header: '连板数',
      accessor: (row) => row.limit_times || '-',
      className: 'text-right'
    },
    {
      key: 'first_time',
      header: '首封时间',
      accessor: (row) => row.first_time || '-'
    },
    {
      key: 'open_times',
      header: '炸板次数',
      accessor: (row) => row.open_times !== null ? row.open_times : '-',
      className: 'text-right'
    }
  ], [])

  // 移动端卡片
  const mobileCard = useCallback((item: LimitListData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b">
        <div>
          <span className="font-medium">{item.name || '-'}</span>
          <span className="text-xs text-gray-500 ml-2">{item.ts_code}</span>
        </div>
        {item.limit_type === 'U' && <TrendingUp className="h-4 w-4 text-red-600" />}
        {item.limit_type === 'D' && <TrendingDown className="h-4 w-4 text-green-600" />}
        {item.limit_type === 'Z' && <Zap className="h-4 w-4 text-orange-600" />}
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">涨跌幅:</span>
          <span className={(item.pct_chg ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}>
            {item.pct_chg !== null ? `${(item.pct_chg ?? 0) >= 0 ? '+' : ''}${item.pct_chg.toFixed(2)}%` : '-'}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">连板数:</span>
          <span>{item.limit_times || '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">首封:</span>
          <span>{item.first_time || '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">炸板:</span>
          <span>{item.open_times !== null ? item.open_times : '-'}</span>
        </div>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="涨跌停列表"
        description="获取A股每日涨跌停、炸板数据情况，数据从2020年开始（不提供ST股票的统计）"
        details={<>
          <div>接口：limit_list_d</div>
          <a href="https://tushare.pro/document/2?doc_id=298" target="_blank" rel="noopener noreferrer">查看文档</a>
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
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">总记录数</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.total_count}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">交易天数</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.trade_days}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">涉及股票</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.stock_count}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">最大连板数</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">{statistics.max_limit_times}</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选区 */}
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
              <Select value={limitType} onValueChange={setLimitType}>
                <SelectTrigger>
                  <SelectValue placeholder="涨跌停类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="U">涨停</SelectItem>
                  <SelectItem value="D">跌停</SelectItem>
                  <SelectItem value="Z">炸板</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex-1">
              <Input
                placeholder="股票代码"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="flex gap-2">
              <Button onClick={loadData} disabled={loading}>
                查询
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card className="p-0 sm:p-0 overflow-hidden">
        {/* 移动端 */}
        <div className="sm:hidden">
          <div className="px-4 py-3 border-b bg-muted/50">
            <h3 className="text-sm font-medium">涨跌停列表</h3>
          </div>
          <div className="divide-y">
            {!loading && !error && data.map((item, index) => (
              <div
                key={index}
                className={`p-4 transition-colors ${
                  index % 2 === 0
                    ? 'bg-white dark:bg-gray-900 hover:bg-blue-50 dark:hover:bg-blue-950/20'
                    : 'bg-gray-50 dark:bg-gray-950 hover:bg-blue-50 dark:hover:bg-blue-950/20'
                }`}
              >
                {mobileCard(item)}
              </div>
            ))}
          </div>
          {loading && <div className="p-8 text-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto" /></div>}
          {error && <div className="p-8 text-center text-destructive">{error}</div>}
          {!loading && !error && data.length === 0 && <div className="p-8 text-center text-muted-foreground">暂无数据</div>}
        </div>

        {/* 桌面端 */}
        <div className="hidden sm:block">
          <DataTable
            columns={columns}
            data={data}
            loading={loading}
            error={error}
            emptyMessage="暂无数据"
          />
        </div>
      </Card>
    </div>
  )
}
