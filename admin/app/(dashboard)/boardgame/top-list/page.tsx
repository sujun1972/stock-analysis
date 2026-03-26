'use client'

import { useState, useEffect, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'

import { toast } from 'sonner'
import { topListApi, type TopListItem, type TopListStatistics } from '@/lib/api'
import { formatStockCode, pctChangeColor } from '@/lib/utils'
import { useTaskStore } from '@/stores/task-store'
import { useSystemConfig } from '@/contexts'
import { TrendingUp, TrendingDown, BarChart3, ListFilter, RefreshCw } from 'lucide-react'

const PAGE_SIZE = 100

export default function TopListPage() {
  const [data, setData] = useState<TopListItem[]>([])
  const [statistics, setStatistics] = useState<TopListStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc' | null>(null)
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const syncing = isTaskRunning('tasks.sync_top_list')
  const { config } = useSystemConfig()

  const openStockAnalysis = (tsCode: string) => {
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(tsCode)), '_blank')
  }

  useEffect(() => {
    loadData(1).catch(() => {})
  }, [])

  const loadData = async (targetPage: number = page, overrideSortKey?: string | null, overrideSortDir?: 'asc' | 'desc' | null) => {
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

      const [dataResponse, statsResponse] = await Promise.all([
        topListApi.getTopList(params),
        topListApi.getStatistics({ trade_date: tradeDateStr })
      ])

      if (dataResponse.code === 200 && dataResponse.data) {
        setData(dataResponse.data.items)
        setTotal(dataResponse.data.total)
        setPage(targetPage)
        // 回填后端解析的实际日期（初始加载时 tradeDate 为空，后端自动选最近有数据的交易日）
        if (!tradeDate && dataResponse.data.trade_date) {
          setTradeDate(new Date(dataResponse.data.trade_date + 'T00:00:00'))
        }
      }

      if (statsResponse.code === 200 && statsResponse.data) {
        setStatistics(statsResponse.data)
      }
    } catch (error: any) {
      toast.error(error.message || '加载数据失败')
    } finally {
      setIsLoading(false)
    }
  }

  const handleQuery = () => {
    loadData(1).catch(() => {})
  }

  const handleSync = async () => {
    try {
      const response = await topListApi.syncAsync({})

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
            toast.success('数据同步完成')
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
    } catch (error: any) {
      toast.error(error.message || '提交同步任务失败')
    }
  }

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

  const toYi = (val: number | null | undefined) => {
    if (val === null || val === undefined) return '-'
    return (val / 10000).toFixed(2) + '亿'
  }

  const columns: Column<TopListItem>[] = [
    {
      key: 'name',
      header: '股票',
      accessor: (row) => (
        <span
          className={`cursor-pointer hover:underline ${pctChangeColor(row.pct_change)}`}
          onClick={() => openStockAnalysis(row.ts_code)}
        >
          {row.name || '-'}[{formatStockCode(row.ts_code)}]
        </span>
      ),
      width: 160,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'close',
      header: '收盘价',
      accessor: (row) => (
        <span className={pctChangeColor(row.pct_change)}>
          {row.close !== null ? row.close.toFixed(2) : '-'}
        </span>
      ),
      width: 80,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'pct_change',
      header: '涨跌幅%',
      accessor: (row) => {
        if (row.pct_change === null) return '-'
        const value = row.pct_change
        return (
          <span className={pctChangeColor(value)}>
            {value >= 0 ? '+' : ''}{value.toFixed(2)}%
          </span>
        )
      },
      width: 100,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'turnover_rate',
      header: '换手率%',
      accessor: (row) => (
        <span className={pctChangeColor(row.pct_change)}>
          {row.turnover_rate !== null ? row.turnover_rate.toFixed(2) + '%' : '-'}
        </span>
      ),
      width: 100,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'amount',
      header: '总成交额',
      accessor: (row) => (
        <span className={pctChangeColor(row.pct_change)}>
          {toYi(row.amount)}
        </span>
      ),
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'net_amount',
      header: '净买入',
      accessor: (row) => {
        if (row.net_amount === null) return '-'
        const value = row.net_amount / 10000
        return (
          <span className={value >= 0 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'}>
            {value >= 0 ? '+' : ''}{value.toFixed(2)}亿
          </span>
        )
      },
      width: 100,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'l_amount',
      header: '榜单成交额',
      accessor: (row) => (
        <span className={pctChangeColor(row.pct_change)}>
          {toYi(row.l_amount)}
        </span>
      ),
      width: 120,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'reason',
      header: '上榜理由',
      accessor: (row) => (
        <div className="truncate" title={row.reason || '-'}>
          {row.reason || '-'}
        </div>
      ),
      width: 200
    }
  ]

  // 移动端卡片视图
  const mobileCard = (item: TopListItem) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div className="font-semibold text-base">{item.name}</div>
          <div className="text-sm text-gray-500">{item.ts_code}</div>
        </div>
        <div className="text-right">
          <div className="font-semibold">{item.close !== null ? `¥${item.close.toFixed(2)}` : '-'}</div>
          {item.pct_change !== null && (
            <div className={item.pct_change >= 0 ? 'text-red-600' : 'text-green-600'}>
              {item.pct_change >= 0 ? '+' : ''}{item.pct_change.toFixed(2)}%
            </div>
          )}
        </div>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">龙虎榜净买入:</span>
          {item.net_amount !== null && (
            <span className={item.net_amount >= 0 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'}>
              {item.net_amount >= 0 ? '+' : ''}{(item.net_amount / 10000).toFixed(2)}亿
            </span>
          )}
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">龙虎榜成交额:</span>
          <span>{item.l_amount !== null ? `${(item.l_amount / 10000).toFixed(2)}亿` : '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">换手率:</span>
          <span>{item.turnover_rate !== null ? `${item.turnover_rate.toFixed(2)}%` : '-'}</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-gray-600">上榜理由:</span>
          <span className="text-xs break-all">{item.reason || '-'}</span>
        </div>
      </div>
    </div>
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="龙虎榜每日明细"
        description="龙虎榜每日交易明细"
        details={<>
          <div>接口：top_list</div>
          <a href="https://tushare.pro/document/2?doc_id=106" target="_blank" rel="noopener noreferrer">查看文档</a>
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
                  <p className="text-xs sm:text-sm text-gray-600">上榜股票数</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.stock_count}</p>
                </div>
                <BarChart3 className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">平均净买入(亿)</p>
                  <p className={`text-xl sm:text-2xl font-bold ${statistics.avg_net_amount >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {statistics.avg_net_amount >= 0 ? '+' : ''}{(statistics.avg_net_amount / 10000).toFixed(2)}
                  </p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-orange-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">最大净买入(亿)</p>
                  <p className="text-xl sm:text-2xl font-bold text-red-600">
                    +{(statistics.max_net_amount / 10000).toFixed(2)}
                  </p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">平均涨跌幅%</p>
                  <p className={`text-xl sm:text-2xl font-bold ${statistics.avg_pct_change >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {statistics.avg_pct_change >= 0 ? '+' : ''}{statistics.avg_pct_change.toFixed(2)}%
                  </p>
                </div>
                <TrendingDown className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选和操作区域 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ListFilter className="h-5 w-5" />
            数据查询
          </CardTitle>
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
      <Card>
        <CardContent className="p-0 sm:p-6">
          <DataTable
            columns={columns}
            data={data}
            loading={isLoading}
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
        </CardContent>
      </Card>
    </div>
  )
}
