'use client'

import { useState, useEffect, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'

import { toast } from 'sonner'
import { topInstApi, type TopInstItem, type TopInstStatistics } from '@/lib/api'
import { formatStockCode } from '@/lib/utils'
import { useTaskStore } from '@/stores/task-store'
import { useSystemConfig } from '@/contexts'
import { TrendingUp, TrendingDown, BarChart3, ListFilter, RefreshCw, Building2 } from 'lucide-react'

const PAGE_SIZE = 100

export default function TopInstPage() {
  const [data, setData] = useState<TopInstItem[]>([])
  const [statistics, setStatistics] = useState<TopInstStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [side, setSide] = useState<string>('ALL')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc' | null>(null)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const syncing = isTaskRunning('tasks.sync_top_inst')
  const { config } = useSystemConfig()

  const openStockAnalysis = (tsCode: string) => {
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(tsCode)), '_blank')
  }

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
        ts_code: tsCode.trim() || undefined,
        side: side !== 'ALL' ? side : undefined,
        page: targetPage,
        page_size: PAGE_SIZE,
        sort_by: (overrideSortKey !== undefined ? overrideSortKey : sortKey) ?? undefined,
        sort_order: (overrideSortDir !== undefined ? overrideSortDir : sortDirection) ?? undefined
      }

      const [dataResponse, statsResponse] = await Promise.all([
        topInstApi.getTopInst(params),
        topInstApi.getStatistics({ trade_date: tradeDateStr, ts_code: params.ts_code })
      ])

      if (dataResponse.code === 200 && dataResponse.data) {
        setData(dataResponse.data.items)
        setTotal(dataResponse.data.total)
        setPage(targetPage)
        // 回填后端解析的实际日期（初始加载时 tradeDate 为空）
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
      const response = await topInstApi.syncAsync({})

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

  // Service 已将金额从元转为万元，÷10000 转为亿元显示
  const formatYi = (val: number | null | undefined) => {
    if (val === null || val === undefined) return '-'
    return (val / 10000).toFixed(2) + '亿'
  }

  // 买入红色，卖出绿色
  const sideColor = (side: string) => side === '0' ? 'text-red-600' : 'text-green-600'

  const columns: Column<TopInstItem>[] = [
    {
      key: 'ts_code',
      header: '股票',
      accessor: (row) => (
        <span
          className={`cursor-pointer hover:underline ${sideColor(row.side)}`}
          onClick={() => openStockAnalysis(row.ts_code)}
        >
          {row.name || '-'}[{formatStockCode(row.ts_code)}]
        </span>
      ),
      width: 160,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'exalter',
      header: '营业部名称',
      accessor: (row) => (
        <div className="truncate" title={row.exalter || ''}>
          {row.exalter || '-'}
        </div>
      ),
      width: 220
    },
    {
      key: 'side',
      header: '买卖',
      accessor: (row) => (
        <span className={row.side === '0' ? 'text-red-600 font-medium' : 'text-green-600 font-medium'}>
          {row.side === '0' ? '买入' : '卖出'}
        </span>
      ),
      width: 60,
      cellClassName: 'text-center whitespace-nowrap'
    },
    {
      key: 'buy',
      header: '买入额',
      accessor: (row) => (
        <span className="text-red-600">
          {formatYi(row.buy)}
        </span>
      ),
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'sell',
      header: '卖出额',
      accessor: (row) => (
        <span className="text-green-600">
          {formatYi(row.sell)}
        </span>
      ),
      width: 110,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'net_buy',
      header: '净成交额',
      accessor: (row) => {
        if (row.net_buy === null) return '-'
        const value = row.net_buy
        return (
          <span className={value >= 0 ? 'text-red-600 font-semibold' : 'text-green-600 font-semibold'}>
            {value >= 0 ? '+' : ''}{formatYi(value)}
          </span>
        )
      },
      width: 120,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'buy_rate',
      header: '买入占比%',
      accessor: (row) => row.buy_rate !== null ? `${row.buy_rate.toFixed(2)}%` : '-',
      width: 100,
      sortable: true,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'sell_rate',
      header: '卖出占比%',
      accessor: (row) => row.sell_rate !== null ? `${row.sell_rate.toFixed(2)}%` : '-',
      width: 100,
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
  const mobileCard = (item: TopInstItem) => (
    <div className="p-4 hover:bg-blue-50 active:bg-blue-100 dark:hover:bg-gray-800 dark:active:bg-gray-700 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div>
          <div
            className={`font-semibold text-base cursor-pointer hover:underline ${sideColor(item.side)}`}
            onClick={() => openStockAnalysis(item.ts_code)}
          >
            {item.name || item.ts_code}[{formatStockCode(item.ts_code)}]
          </div>
          <div className="text-sm text-gray-500 truncate max-w-[200px] mt-0.5">{item.exalter}</div>
        </div>
        <div className="text-right">
          <div className={`font-semibold ${sideColor(item.side)}`}>
            {item.side === '0' ? '买入' : '卖出'}
          </div>
          {item.net_buy !== null && (
            <div className={`font-semibold text-sm ${sideColor(item.side)}`}>
              净: {item.net_buy >= 0 ? '+' : ''}{formatYi(item.net_buy)}
            </div>
          )}
        </div>
      </div>
      <div className="space-y-1 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">买入额:</span>
          <span className="text-red-600">{formatYi(item.buy)}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">卖出额:</span>
          <span className="text-green-600">{formatYi(item.sell)}</span>
        </div>
        {item.reason && (
          <div className="flex flex-col gap-1">
            <span className="text-gray-600">上榜理由:</span>
            <span className="text-xs break-all">{item.reason}</span>
          </div>
        )}
      </div>
    </div>
  )

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
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">上榜营业部</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.exalter_count}</p>
                  <p className="text-xs text-muted-foreground">总记录: {statistics.total_records}</p>
                </div>
                <Building2 className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">上榜股票数</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.stock_count}</p>
                  <p className="text-xs text-muted-foreground">交易天数: {statistics.trading_days}</p>
                </div>
                <BarChart3 className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">累计净买入</p>
                  <p className="text-xl sm:text-2xl font-bold text-red-600">
                    {formatYi(statistics.total_net_buy)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    均值: {formatYi(statistics.avg_net_buy)}
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
                  <p className="text-xs sm:text-sm text-gray-600">最大净买入</p>
                  <p className="text-xl sm:text-2xl font-bold text-red-600">
                    +{formatYi(statistics.max_net_buy)}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    累计净卖出: {formatYi(Math.abs(statistics.total_net_sell))}
                  </p>
                </div>
                <TrendingDown className="h-6 w-6 sm:h-8 sm:w-8 text-orange-600" />
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
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">股票代码</label>
              <Input
                placeholder="如 000001 或 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">买卖类型</label>
              <Select value={side} onValueChange={setSide}>
                <SelectTrigger>
                  <SelectValue placeholder="全部" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="0">买入</SelectItem>
                  <SelectItem value="1">卖出</SelectItem>
                </SelectContent>
              </Select>
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
