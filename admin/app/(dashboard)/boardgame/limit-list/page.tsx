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
import { limitListApi, type LimitListData, type LimitListStatistics } from '@/lib/api'
import { formatStockCode } from '@/lib/utils'
import { useTaskStore } from '@/stores/task-store'
import { useSystemConfig } from '@/contexts'
import { TrendingUp, TrendingDown, Zap, BarChart3, ListFilter, RefreshCw, Layers } from 'lucide-react'

const PAGE_SIZE = 50

export default function LimitListPage() {
  const [data, setData] = useState<LimitListData[]>([])
  const [statistics, setStatistics] = useState<LimitListStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [limitType, setLimitType] = useState<string>('ALL')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc' | null>(null)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const syncing = isTaskRunning('tasks.sync_limit_list')
  const { config } = useSystemConfig()

  const openStockAnalysis = (tsCode: string) => {
    const url = config?.stock_analysis_url
    if (!url) return
    window.open(url.replace('{code}', formatStockCode(tsCode)), '_blank')
  }

  useEffect(() => {
    loadData(1).catch(() => {})
  }, [])

  const buildDateStr = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

  const loadData = async (
    targetPage: number = page,
    overrideSortKey?: string | null,
    overrideSortDir?: 'asc' | 'desc' | null
  ) => {
    setIsLoading(true)
    try {
      const tradeDateStr = tradeDate ? buildDateStr(tradeDate) : undefined

      const params = {
        trade_date: tradeDateStr,
        ts_code: tsCode.trim() || undefined,
        limit_type: limitType !== 'ALL' ? limitType : undefined,
        page: targetPage,
        page_size: PAGE_SIZE,
        sort_by: (overrideSortKey !== undefined ? overrideSortKey : sortKey) ?? undefined,
        sort_order: (overrideSortDir !== undefined ? overrideSortDir : sortDirection) ?? undefined
      }

      const response = await limitListApi.getData(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items)
        setTotal(response.data.total)
        setStatistics(response.data.statistics)
        setPage(targetPage)
        // 回填后端解析的实际日期（初始加载时 tradeDate 为空）
        if (!tradeDate && response.data.trade_date) {
          setTradeDate(new Date(response.data.trade_date + 'T00:00:00'))
        }
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
      const response = await limitListApi.syncAsync({})

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

  // 涨跌停类型色彩
  const limitTypeColor = (type: string | null) => {
    if (type === 'U') return 'text-red-600'
    if (type === 'D') return 'text-green-600'
    if (type === 'Z') return 'text-orange-500'
    return ''
  }

  const columns: Column<LimitListData>[] = [
    {
      key: 'ts_code',
      header: '股票',
      accessor: (row) => (
        <span
          className={`cursor-pointer hover:underline whitespace-nowrap ${limitTypeColor(row.limit_type)}`}
          onClick={() => openStockAnalysis(row.ts_code)}
        >
          {row.name || '-'}[{formatStockCode(row.ts_code)}]
        </span>
      ),
      width: 160,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'limit_type',
      header: '类型',
      accessor: (row) => {
        if (row.limit_type === 'U') return <span className="text-red-600 font-semibold">涨停</span>
        if (row.limit_type === 'D') return <span className="text-green-600 font-semibold">跌停</span>
        if (row.limit_type === 'Z') return <span className="text-orange-500 font-semibold">炸板</span>
        return '-'
      },
      width: 60,
      cellClassName: 'text-center'
    },
    {
      key: 'pct_chg',
      header: '涨跌幅%',
      accessor: (row) => {
        if (row.pct_chg === null || row.pct_chg === undefined) return '-'
        return (
          <span className={row.pct_chg >= 0 ? 'text-red-600' : 'text-green-600'}>
            {row.pct_chg >= 0 ? '+' : ''}{row.pct_chg.toFixed(2)}%
          </span>
        )
      },
      width: 90,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'limit_times',
      header: '连板',
      accessor: (row) => row.limit_times ?? '-',
      width: 60,
      cellClassName: 'text-right font-semibold text-red-600'
    },
    {
      key: 'open_times',
      header: '炸板次数',
      accessor: (row) => row.open_times !== null ? row.open_times : '-',
      width: 80,
      cellClassName: 'text-right'
    },
    {
      key: 'first_time',
      header: '首封',
      accessor: (row) => row.first_time || '-',
      width: 80,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'last_time',
      header: '最后封板',
      accessor: (row) => row.last_time || '-',
      width: 80,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'close',
      header: '收盘价',
      accessor: (row) => row.close?.toFixed(2) ?? '-',
      width: 80,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'amount',
      header: '成交额(万)',
      accessor: (row) => row.amount ? (row.amount / 10000).toFixed(0) : '-',
      width: 100,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'turnover_ratio',
      header: '换手率%',
      accessor: (row) => row.turnover_ratio ? row.turnover_ratio.toFixed(2) + '%' : '-',
      width: 90,
      cellClassName: 'text-right whitespace-nowrap'
    },
    {
      key: 'industry',
      header: '行业',
      accessor: (row) => row.industry || '-',
      cellClassName: 'whitespace-nowrap'
    },
  ]

  const mobileCard = (item: LimitListData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b">
        <div>
          <span
            className={`font-medium cursor-pointer hover:underline ${limitTypeColor(item.limit_type)}`}
            onClick={() => openStockAnalysis(item.ts_code)}
          >
            {item.name || '-'}
          </span>
          <span className="text-xs text-gray-500 ml-2">{formatStockCode(item.ts_code)}</span>
        </div>
        <div className="flex items-center gap-1">
          {item.limit_type === 'U' && <TrendingUp className="h-4 w-4 text-red-600" />}
          {item.limit_type === 'D' && <TrendingDown className="h-4 w-4 text-green-600" />}
          {item.limit_type === 'Z' && <Zap className="h-4 w-4 text-orange-500" />}
          <span className={`text-xs font-semibold ${limitTypeColor(item.limit_type)}`}>
            {item.limit_type === 'U' ? '涨停' : item.limit_type === 'D' ? '跌停' : item.limit_type === 'Z' ? '炸板' : ''}
          </span>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">涨跌幅:</span>
          <span className={(item.pct_chg ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'}>
            {item.pct_chg !== null ? `${(item.pct_chg ?? 0) >= 0 ? '+' : ''}${item.pct_chg!.toFixed(2)}%` : '-'}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">连板:</span>
          <span className="text-red-600 font-semibold">{item.limit_times ?? '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">首封:</span>
          <span>{item.first_time || '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">炸板:</span>
          <span>{item.open_times !== null ? item.open_times : '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">日期:</span>
          <span>{item.trade_date || '-'}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">行业:</span>
          <span>{item.industry || '-'}</span>
        </div>
      </div>
    </div>
  )

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
              <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
            ) : (
              <><RefreshCw className="h-4 w-4 mr-1" />同步数据</>
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
                  <p className="text-xs sm:text-sm text-gray-600">总记录数</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.total_count.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground">交易天数: {statistics.trade_days}</p>
                </div>
                <BarChart3 className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">涉及股票</p>
                  <p className="text-xl sm:text-2xl font-bold">{statistics.stock_count.toLocaleString()}</p>
                  <p className="text-xs text-muted-foreground">均涨跌幅: {statistics.avg_pct_chg?.toFixed(2)}%</p>
                </div>
                <Layers className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">最大连板数</p>
                  <p className="text-xl sm:text-2xl font-bold text-red-600">{statistics.max_limit_times}</p>
                  <p className="text-xs text-muted-foreground">均连板: {statistics.avg_limit_times?.toFixed(1)}</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-red-600" />
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">最大涨跌幅</p>
                  <p className="text-xl sm:text-2xl font-bold text-red-600">+{statistics.max_pct_chg?.toFixed(2)}%</p>
                  <p className="text-xs text-muted-foreground">本页条数: {data.length}</p>
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
              <label className="text-sm font-medium mb-1 block">涨跌停类型</label>
              <Select value={limitType} onValueChange={setLimitType}>
                <SelectTrigger>
                  <SelectValue placeholder="全部" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部</SelectItem>
                  <SelectItem value="U">涨停</SelectItem>
                  <SelectItem value="D">跌停</SelectItem>
                  <SelectItem value="Z">炸板</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">股票代码</label>
              <Input
                placeholder="如 000001 或 000001.SZ"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
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
