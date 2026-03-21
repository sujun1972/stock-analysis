'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DatePicker } from '@/components/ui/date-picker'
import { Input } from '@/components/ui/input'
import { limitCptApi, type LimitCptData, type LimitCptStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp } from 'lucide-react'

export default function LimitCptPage() {
  const [data, setData] = useState<LimitCptData[]>([])
  const [statistics, setStatistics] = useState<LimitCptStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [syncing, setSyncing] = useState(false)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params: any = { limit: 100 }
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]
      if (tsCode) params.ts_code = tsCode

      // 获取数据
      const [dataResponse, statsResponse] = await Promise.all([
        limitCptApi.getData(params),
        limitCptApi.getStatistics({
          start_date: params.start_date,
          end_date: params.end_date
        })
      ])

      if (dataResponse.code === 200 && dataResponse.data) {
        setData(dataResponse.data.items || [])
      } else {
        throw new Error(dataResponse.message || '加载数据失败')
      }

      if (statsResponse.code === 200 && statsResponse.data) {
        setStatistics(statsResponse.data)
      }
    } catch (err: any) {
      setError(err.message || '加载数据失败')
      toast.error('加载数据失败', { description: err.message })
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, tsCode])

  useEffect(() => {
    loadData()
  }, [loadData])

  // 异步同步
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params: any = {}
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]
      if (tsCode) params.ts_code = tsCode

      const response = await limitCptApi.syncAsync(params)

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
            toast.success('数据同步完成', { description: '最强板块统计数据已更新' })
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
    } finally {
      setSyncing(false)
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
  const columns: Column<LimitCptData>[] = useMemo(() => [
    {
      key: 'trade_date',
      header: '日期',
      accessor: (row) => row.trade_date
    },
    {
      key: 'rank',
      header: '排名',
      accessor: (row) => (
        <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300 font-semibold text-sm">
          {row.rank}
        </span>
      ),
      className: 'text-center'
    },
    {
      key: 'ts_code',
      header: '代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'name',
      header: '板块名称',
      accessor: (row) => row.name || '-',
      className: 'font-medium'
    },
    {
      key: 'days',
      header: '上榜天数',
      accessor: (row) => {
        const daysValue = row.days || 0
        return (
          <span className={daysValue >= 5 ? 'text-red-600 font-semibold' : ''}>
            {daysValue}天
          </span>
        )
      },
      className: 'text-right'
    },
    {
      key: 'up_stat',
      header: '连板高度',
      accessor: (row) => (
        <span className="text-red-600 font-semibold">
          {row.up_stat || '-'}
        </span>
      ),
      className: 'text-right'
    },
    {
      key: 'cons_nums',
      header: '连板家数',
      accessor: (row) => {
        const consValue = row.cons_nums || 0
        return (
          <span className={consValue >= 3 ? 'text-red-600 font-semibold' : ''}>
            {consValue}家
          </span>
        )
      },
      className: 'text-right'
    },
    {
      key: 'up_nums',
      header: '涨停家数',
      accessor: (row) => {
        const upValue = row.up_nums || 0
        return (
          <span className={upValue >= 5 ? 'text-red-600 font-semibold' : ''}>
            {upValue}家
          </span>
        )
      },
      className: 'text-right'
    },
    {
      key: 'pct_chg',
      header: '涨跌幅',
      accessor: (row) => {
        const pct = row.pct_chg || 0
        const isPositive = pct >= 0
        return (
          <span className={isPositive ? 'text-red-600' : 'text-green-600'}>
            {isPositive ? '+' : ''}{pct.toFixed(2)}%
          </span>
        )
      },
      className: 'text-right'
    }
  ], [])

  // 移动端卡片
  const mobileCard = useCallback((item: LimitCptData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300 font-semibold text-xs">
            {item.rank}
          </span>
          <div>
            <span className="font-medium">{item.name || '-'}</span>
            <span className="text-xs text-gray-500 ml-2">{item.ts_code}</span>
          </div>
        </div>
        <TrendingUp className="h-4 w-4 text-red-600" />
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="flex flex-col">
          <span className="text-gray-600">日期</span>
          <span>{item.trade_date}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-gray-600">上榜天数</span>
          <span className={item.days >= 5 ? 'text-red-600 font-semibold' : ''}>
            {item.days || 0}天
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-gray-600">连板高度</span>
          <span className="text-red-600 font-semibold">{item.up_stat || '-'}</span>
        </div>
        <div className="flex flex-col">
          <span className="text-gray-600">涨停家数</span>
          <span className={item.up_nums >= 5 ? 'text-red-600 font-semibold' : ''}>
            {item.up_nums || 0}家
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-gray-600">连板家数</span>
          <span className={item.cons_nums >= 3 ? 'text-red-600 font-semibold' : ''}>
            {item.cons_nums || 0}家
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-gray-600">涨跌幅</span>
          <span className={(item.pct_chg || 0) >= 0 ? 'text-red-600' : 'text-green-600'}>
            {(item.pct_chg || 0) >= 0 ? '+' : ''}{(item.pct_chg || 0).toFixed(2)}%
          </span>
        </div>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="最强板块统计"
        description="各板块涨停数据统计与排名（连板梯队）"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">交易天数</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.trading_days}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">板块数量</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.concept_count}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">平均涨停家数</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {statistics.avg_up_nums?.toFixed(2) || 0}家
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">最大涨停家数</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {statistics.max_up_nums || 0}家
              </div>
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
              <DatePicker date={startDate} onSelect={setStartDate} placeholder="开始日期" />
            </div>
            <div className="flex-1">
              <DatePicker date={endDate} onSelect={setEndDate} placeholder="结束日期" />
            </div>
            <div className="flex-1">
              <Input
                placeholder="板块代码（如：TS001）"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="flex gap-2">
              <Button onClick={loadData} disabled={loading}>
                查询
              </Button>
              <Button onClick={handleSync} disabled={syncing} variant="default">
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
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card className="p-0 sm:p-0 overflow-hidden">
        {/* 移动端 */}
        <div className="sm:hidden">
          <div className="px-4 py-3 border-b bg-muted/50">
            <h3 className="text-sm font-medium">最强板块统计</h3>
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
