'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { stkNineturnApi, type StkNineturnData, type StkNineturnStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp, TrendingDown, BarChart3, Activity } from 'lucide-react'

export default function StkNineturnPage() {
  const [data, setData] = useState<StkNineturnData[]>([])
  const [statistics, setStatistics] = useState<StkNineturnStatistics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState<string>('')
  const [freq, setFreq] = useState<string>('daily')
  const [syncing, setSyncing] = useState(false)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params: any = {
        freq,
        limit: 30
      }

      if (tsCode.trim()) {
        params.ts_code = tsCode.trim()
      }
      if (startDate) {
        params.start_date = startDate.toISOString().split('T')[0]
      }
      if (endDate) {
        params.end_date = endDate.toISOString().split('T')[0]
      }

      const response = await stkNineturnApi.getData(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setStatistics(response.data.statistics || null)
      } else {
        throw new Error(response.message || '获取数据失败')
      }
    } catch (err: any) {
      setError(err.message || '获取数据失败')
      toast.error('加载失败', {
        description: err.message || '无法加载神奇九转数据'
      })
    } finally {
      setLoading(false)
    }
  }, [startDate, endDate, tsCode, freq])

  // 初始加载
  useEffect(() => {
    loadData()
  }, [loadData])

  // 异步同步数据
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params: any = { freq }

      if (tsCode.trim()) params.ts_code = tsCode.trim()
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]

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

        // 注册任务完成回调
        const completionCallback = (task: any) => {
          if (task.status === 'success') {
            loadData().catch(() => {})
            toast.success('数据同步完成', {
              description: '神奇九转指标数据已更新'
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
  const columns: Column<StkNineturnData>[] = useMemo(() => [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'trade_date',
      header: '交易日期',
      accessor: (row) => row.trade_date ? row.trade_date.split(' ')[0] : '-'
    },
    {
      key: 'close',
      header: '收盘价',
      accessor: (row) => row.close !== null ? row.close.toFixed(2) : '-'
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
      }
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
      }
    },
    {
      key: 'nine_up_turn',
      header: '上九转',
      accessor: (row) => {
        if (row.nine_up_turn === '+9') {
          return <span className="text-red-600 font-bold">+9 ⚠️</span>
        }
        return '-'
      }
    },
    {
      key: 'nine_down_turn',
      header: '下九转',
      accessor: (row) => {
        if (row.nine_down_turn === '-9') {
          return <span className="text-green-600 font-bold">-9 ⚠️</span>
        }
        return '-'
      }
    }
  ], [])

  // 移动端卡片视图
  const mobileCard = useCallback((item: StkNineturnData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">股票代码</span>
        <span className="font-medium">{item.ts_code}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">交易日期</span>
        <span className="font-medium">{item.trade_date ? item.trade_date.split(' ')[0] : '-'}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">收盘价</span>
        <span className="font-medium">{item.close !== null ? item.close.toFixed(2) : '-'}</span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">上九转计数</span>
        <span className={item.up_count && item.up_count >= 9 ? 'font-semibold text-red-600' : 'font-medium'}>
          {item.up_count !== null ? item.up_count.toFixed(1) : '-'}
        </span>
      </div>
      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">下九转计数</span>
        <span className={item.down_count && item.down_count >= 9 ? 'font-semibold text-green-600' : 'font-medium'}>
          {item.down_count !== null ? item.down_count.toFixed(1) : '-'}
        </span>
      </div>
      {item.nine_up_turn === '+9' && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">上九转</span>
          <span className="font-bold text-red-600">+9 ⚠️</span>
        </div>
      )}
      {item.nine_down_turn === '-9' && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">下九转</span>
          <span className="font-bold text-green-600">-9 ⚠️</span>
        </div>
      )}
    </div>
  ), [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="神奇九转指标"
        description="神奇九转(又称'九转序列')是一种基于技术分析的股票趋势反转指标，通过识别连续9天的特定走势来判断潜在反转点"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">总记录数</p>
                  <p className="text-2xl font-bold">{statistics.total_records || 0}</p>
                </div>
                <BarChart3 className="h-8 w-8 text-blue-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">股票数</p>
                  <p className="text-2xl font-bold">{statistics.stock_count || 0}</p>
                </div>
                <Activity className="h-8 w-8 text-purple-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">上九转信号</p>
                  <p className="text-2xl font-bold text-red-600">{statistics.up_turn_count || 0}</p>
                </div>
                <TrendingUp className="h-8 w-8 text-red-500" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">下九转信号</p>
                  <p className="text-2xl font-bold text-green-600">{statistics.down_turn_count || 0}</p>
                </div>
                <TrendingDown className="h-8 w-8 text-green-500" />
              </div>
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
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
            <div className="space-y-2">
              <Label>股票代码</Label>
              <Input
                placeholder="如：000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <Label>频率</Label>
              <Select value={freq} onValueChange={setFreq}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="daily">日线</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>开始日期</Label>
              <DatePicker
                date={startDate}
                onDateChange={setStartDate}
                placeholder="选择开始日期"
              />
            </div>

            <div className="space-y-2">
              <Label>结束日期</Label>
              <DatePicker
                date={endDate}
                onDateChange={setEndDate}
                placeholder="选择结束日期"
              />
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button onClick={loadData} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-1 ${loading ? 'animate-spin' : ''}`} />
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

          {/* 提示信息 */}
          <div className="mt-4 rounded-lg bg-amber-50 dark:bg-amber-950 p-3 border border-amber-200 dark:border-amber-800">
            <p className="text-sm text-amber-800 dark:text-amber-200">
              <strong>注意：</strong>此接口消耗 6000 积分/次，单次最大返回 10000 行数据。数据从 2023 年开始，每天 21 点更新。
            </p>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card className="p-0 sm:p-0 overflow-hidden">
        {/* 移动端视图 */}
        <div className="sm:hidden">
          <div className="px-4 py-3 border-b bg-muted/50">
            <h3 className="text-sm font-medium">神奇九转数据</h3>
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
        </div>

        {/* 桌面端表格 */}
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
