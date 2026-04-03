'use client'

import { useState, useEffect, useCallback, useMemo, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DatePicker } from '@/components/ui/date-picker'
import { limitCptApi, type LimitCptData, type LimitCptStatistics } from '@/lib/api'
import { apiClient } from '@/lib/api-client'
import { useTaskStore } from '@/stores/task-store'
import { useDataBulkOps } from '@/hooks/useDataBulkOps'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { toast } from 'sonner'
import { RefreshCw, TrendingUp } from 'lucide-react'

const PAGE_SIZE = 100

export default function LimitCptPage() {
  const [data, setData] = useState<LimitCptData[]>([])
  const [statistics, setStatistics] = useState<LimitCptStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc' | null>(null)
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const syncing = isTaskRunning('tasks.sync_limit_cpt')

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
        page: targetPage,
        page_size: PAGE_SIZE,
        sort_by: (overrideSortKey !== undefined ? overrideSortKey : sortKey) ?? undefined,
        sort_order: (overrideSortDir !== undefined ? overrideSortDir : sortDirection) ?? undefined
      }

      const response = await limitCptApi.getData(params)

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

  const {
    handleFullSync,
    handleClear,
    fullSyncing,
    isClearing,
    isClearDialogOpen,
    setIsClearDialogOpen,
    cleanup,
    earliestHistoryDate,
  } = useDataBulkOps({
    tableKey: 'limit_cpt',
    syncFn: (params) => apiClient.post('/api/limit-cpt/sync-async', null, { params }),
    taskName: 'tasks.sync_limit_cpt',
    onSuccess: loadData,
  })

  const handleQuery = () => {
    loadData(1).catch(() => {})
  }

  // 异步同步
  const handleSync = async () => {
    try {
      const response = await limitCptApi.syncAsync({})

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
      cleanup()
    }
  }, [unregisterCompletionCallback])

  // 表格列定义
  const columns: Column<LimitCptData>[] = useMemo(() => [
    {
      key: 'rank',
      header: '排名',
      accessor: (row) => (
        <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900 text-blue-600 dark:text-blue-300 font-semibold text-sm">
          {row.rank}
        </span>
      ),
      width: 70,
      sortable: true,
      cellClassName: 'text-center whitespace-nowrap'
    },
    {
      key: 'name',
      header: '板块',
      accessor: (row) => (
        <span className="font-medium">
          {row.name || '-'}
          <span className="text-xs text-gray-500 ml-1">[{row.ts_code}]</span>
        </span>
      ),
      width: 220,
      cellClassName: 'whitespace-nowrap'
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
      width: 90,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'up_stat',
      header: '连板高度',
      accessor: (row) => (
        <span className="text-red-600 font-semibold">
          {row.up_stat || '-'}
        </span>
      ),
      width: 90,
      cellClassName: 'text-right whitespace-nowrap'
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
      width: 90,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
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
      width: 90,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
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
      width: 90,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
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
            <span className="text-xs text-gray-500 ml-2">[{item.ts_code}]</span>
          </div>
        </div>
        <TrendingUp className="h-4 w-4 text-red-600" />
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
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
        description="获取每天涨停股票最多最强的概念板块，可以分析强势板块的轮动，判断资金动向"
        details={<>
          <div>接口：limit_cpt_list</div>
          <a href="https://tushare.pro/document/2?doc_id=357" target="_blank" rel="noopener noreferrer">查看文档</a>
        </>}
        actions={
          <div className="flex gap-2">
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
            <BulkOpsButtons
              onFullSync={handleFullSync}
              onClearConfirm={handleClear}
              isClearDialogOpen={isClearDialogOpen}
              setIsClearDialogOpen={setIsClearDialogOpen}
              fullSyncing={fullSyncing}
              isClearing={isClearing}
              earliestHistoryDate={earliestHistoryDate}
              tableName="最强板块统计"
            />
          </div>
        }
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">交易天数</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.trading_days}</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">板块数量</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.concept_count}</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">平均涨停家数</p>
                  <p className="text-xl sm:text-2xl font-bold text-red-600">
                    {statistics.avg_up_nums?.toFixed(2) || 0}家
                  </p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-red-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">最大涨停家数</p>
                  <p className="text-xl sm:text-2xl font-bold text-red-600">
                    {statistics.max_up_nums || 0}家
                  </p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-orange-600" />
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
            <h3 className="text-sm font-medium">最强板块统计</h3>
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
