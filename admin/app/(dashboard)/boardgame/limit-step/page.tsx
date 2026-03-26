'use client'

import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DatePicker } from '@/components/ui/date-picker'
import { Input } from '@/components/ui/input'
import { limitStepApi, type LimitStepData, type LimitStepStatistics } from '@/lib/api'
import { formatStockCode } from '@/lib/utils'
import { useTaskStore } from '@/stores/task-store'
import { useSystemConfig } from '@/contexts'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp } from 'lucide-react'

const PAGE_SIZE = 100

export default function LimitStepPage() {
  const [data, setData] = useState<LimitStepData[]>([])
  const [statistics, setStatistics] = useState<LimitStepStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [nums, setNums] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc' | null>(null)
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const syncing = isTaskRunning('tasks.sync_limit_step')
  const { config } = useSystemConfig()

  const openStockAnalysis = useCallback((tsCode: string) => {
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(tsCode)), '_blank')
  }, [config])

  useEffect(() => {
    loadData(1).catch(() => {})
  }, [])

  const loadData = async (
    targetPage: number = page,
    overrideSortKey?: string | null,
    overrideSortDir?: 'asc' | 'desc' | null
  ) => {
    setIsLoading(true)
    try {
      const tradeDateStr = tradeDate
        ? `${tradeDate.getFullYear()}-${String(tradeDate.getMonth() + 1).padStart(2, '0')}-${String(tradeDate.getDate()).padStart(2, '0')}`
        : undefined

      const params = {
        trade_date: tradeDateStr,
        nums: nums || undefined,
        page: targetPage,
        page_size: PAGE_SIZE,
        sort_by: (overrideSortKey !== undefined ? overrideSortKey : sortKey) ?? undefined,
        sort_order: (overrideSortDir !== undefined ? overrideSortDir : sortDirection) ?? undefined
      }

      const response = await limitStepApi.getData(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items)
        setTotal(response.data.total)
        setPage(targetPage)
        if (response.data.statistics) {
          setStatistics(response.data.statistics)
        }
        // 回填后端解析的实际日期（初始加载时 tradeDate 为空）
        if (!tradeDate && response.data.trade_date) {
          setTradeDate(new Date(response.data.trade_date + 'T00:00:00'))
        }
      }
    } catch (err: any) {
      toast.error('加载数据失败', { description: err.message })
    } finally {
      setIsLoading(false)
    }
  }

  const handleQuery = () => {
    loadData(1).catch(() => {})
  }

  // 异步同步
  const handleSync = async () => {
    try {
      const response = await limitStepApi.syncAsync({})

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
            toast.success('数据同步完成', { description: '连板天梯数据已更新' })
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
  const columns: Column<LimitStepData>[] = useMemo(() => [
    {
      key: 'name',
      header: '股票',
      accessor: (row) => (
        <span
          className="cursor-pointer hover:underline text-red-600 font-medium"
          onClick={() => openStockAnalysis(row.ts_code)}
        >
          {row.name || '-'}[{formatStockCode(row.ts_code)}]
        </span>
      ),
      width: 160,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'nums',
      header: '连板次数',
      accessor: (row) => {
        const numsValue = parseInt(row.nums) || 0
        return (
          <span className="text-red-600 font-semibold">
            {numsValue}板
          </span>
        )
      },
      width: 100,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    }
  ], [openStockAnalysis])

  // 移动端卡片
  const mobileCard = useCallback((item: LimitStepData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b">
        <div>
          <span
            className="font-medium text-red-600 cursor-pointer hover:underline"
            onClick={() => openStockAnalysis(item.ts_code)}
          >
            {item.name || '-'}
          </span>
          <span className="text-xs text-gray-500 ml-2">[{formatStockCode(item.ts_code)}]</span>
        </div>
        <TrendingUp className="h-4 w-4 text-red-600" />
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="flex flex-col">
          <span className="text-gray-600">交易日期</span>
          <span>
            {item.trade_date?.slice(0, 4)}-{item.trade_date?.slice(4, 6)}-{item.trade_date?.slice(6, 8)}
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-gray-600">连板次数</span>
          <span className="text-red-600 font-semibold">{parseInt(item.nums) || 0}板</span>
        </div>
      </div>
    </div>
  ), [config])

  return (
    <div className="space-y-6">
      <PageHeader
        title="连板天梯"
        description="获取每天连板个数晋级的股票，可以分析出每天连续涨停进阶个数，判断强势热度"
        details={<>
          <div>接口：limit_step</div>
          <a href="https://tushare.pro/document/2?doc_id=356" target="_blank" rel="noopener noreferrer">查看文档</a>
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
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">股票数</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.stock_count}</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">最大连板数</p>
                  <p className="text-xl sm:text-2xl font-bold text-red-600">{statistics.max_nums}板</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-red-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">平均连板数</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.avg_nums?.toFixed(2) || 0}板</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-orange-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">交易日数量</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.trade_date_count}</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
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
          <div className="flex flex-col sm:flex-row gap-4 items-end">
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">交易日期</label>
              <DatePicker date={tradeDate} onDateChange={setTradeDate} />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">连板次数</label>
              <Input
                placeholder="如：3 或 3,4,5"
                value={nums}
                onChange={(e) => setNums(e.target.value)}
              />
            </div>
            <div className="flex gap-2 w-full sm:w-auto">
              <Button onClick={handleQuery} disabled={isLoading} className="flex-1 sm:flex-none">
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
            <h3 className="text-sm font-medium">连板天梯</h3>
          </div>
          <div className="divide-y">
            {!isLoading && data.map((item, index) => (
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
          {isLoading && <div className="p-8 text-center"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto" /></div>}
          {!isLoading && data.length === 0 && <div className="p-8 text-center text-muted-foreground">暂无数据</div>}
        </div>

        {/* 桌面端 */}
        <div className="hidden sm:block">
          <DataTable
            columns={columns}
            data={data}
            loading={isLoading}
            emptyMessage="暂无数据"
            mobileCard={mobileCard}
            tableClassName="table-fixed w-full [&_th]:border-r [&_td]:border-r [&_th:last-child]:border-r-0 [&_td:last-child]:border-r-0 [&_th]:!text-center"
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
        </div>
      </Card>
    </div>
  )
}
