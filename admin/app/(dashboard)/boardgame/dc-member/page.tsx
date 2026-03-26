'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { dcMemberApi, type DcMemberData, type DcMemberStatistics } from '@/lib/api'
import { formatStockCode } from '@/lib/utils'
import { useTaskStore } from '@/stores/task-store'
import { useSystemConfig } from '@/contexts'
import { toast } from 'sonner'
import { RefreshCw, Database, Layers, TrendingUp, Calendar } from 'lucide-react'

const PAGE_SIZE = 100

export default function DcMemberPage() {
  const [data, setData] = useState<DcMemberData[]>([])
  const [statistics, setStatistics] = useState<DcMemberStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [tradeDate, setTradeDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [conCode, setConCode] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [sortKey, setSortKey] = useState<string | null>(null)
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc' | null>(null)

  const activeCallbacksRef = useRef<Map<string, any>>(new Map())
  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback, isTaskRunning } = useTaskStore()
  const syncing = isTaskRunning('tasks.sync_dc_member')
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
        ts_code: tsCode.trim() || undefined,
        con_code: conCode.trim() || undefined,
        page: targetPage,
        page_size: PAGE_SIZE,
        sort_by: (overrideSortKey !== undefined ? overrideSortKey : sortKey) ?? undefined,
        sort_order: (overrideSortDir !== undefined ? overrideSortDir : sortDirection) ?? undefined
      }

      const [dataResponse, statsResponse] = await Promise.all([
        dcMemberApi.getData(params),
        dcMemberApi.getStatistics({
          trade_date: tradeDateStr,
          ts_code: tsCode.trim() || undefined
        })
      ])

      if (dataResponse.code === 200 && dataResponse.data) {
        setData(dataResponse.data.items)
        setTotal(dataResponse.data.total)
        setPage(targetPage)
        // 回填后端解析的实际交易日期
        if (!tradeDate && dataResponse.data.trade_date) {
          setTradeDate(new Date(dataResponse.data.trade_date + 'T00:00:00'))
        }
      }

      if (statsResponse.code === 200 && statsResponse.data) {
        setStatistics(statsResponse.data)
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

  const handleSync = async () => {
    try {
      const response = await dcMemberApi.syncAsync({})

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
            toast.success('数据同步完成', { description: '东方财富板块成分数据已更新' })
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

  // 组件卸载时清理回调
  useEffect(() => {
    return () => {
      const callbacks = activeCallbacksRef.current
      callbacks.forEach((callback, taskId) => {
        unregisterCompletionCallback(taskId, callback)
      })
      callbacks.clear()
    }
  }, [unregisterCompletionCallback])

  const formatNumber = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return '-'
    return value.toLocaleString('zh-CN')
  }

  // 表格列定义
  const columns: Column<DcMemberData>[] = useMemo(() => [
    {
      key: 'name',
      header: '成分股',
      accessor: (row) => (
        row.con_code ? (
          <span
            className="cursor-pointer hover:underline text-blue-600 font-medium"
            onClick={() => openStockAnalysis(row.con_code)}
          >
            {row.name || '-'}[{formatStockCode(row.con_code)}]
          </span>
        ) : (
          <span>{row.name || '-'}</span>
        )
      ),
      width: 180,
      cellClassName: 'whitespace-nowrap'
    },
    {
      key: 'ts_code',
      header: '板块',
      accessor: (row) => (
        <span>
          {row.board_name ? `${row.board_name}[${row.ts_code}]` : row.ts_code}
        </span>
      ),
      width: 200,
      cellClassName: 'whitespace-nowrap'
    },
  ], [openStockAnalysis])

  // 移动端卡片
  const mobileCard = useCallback((item: DcMemberData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <div>
          {item.con_code ? (
            <span
              className="font-medium text-blue-600 cursor-pointer hover:underline"
              onClick={() => openStockAnalysis(item.con_code)}
            >
              {item.name || '-'}
            </span>
          ) : (
            <span className="font-medium">{item.name || '-'}</span>
          )}
          {item.con_code && (
            <span className="text-xs text-gray-500 ml-2">[{formatStockCode(item.con_code)}]</span>
          )}
        </div>
        <TrendingUp className="h-4 w-4 text-blue-600" />
      </div>
      <div className="text-sm">
        <span className="text-gray-600">板块：</span>
        <span className="font-medium">
          {item.board_name ? `${item.board_name}[${item.ts_code}]` : item.ts_code}
        </span>
      </div>
    </div>
  ), [openStockAnalysis])

  return (
    <div className="space-y-6">
      <PageHeader
        title="东方财富板块成分"
        description="获取东方财富板块每日成分数据，可以根据概念板块代码和交易日期，获取历史成分"
        details={<>
          <div>接口：dc_member</div>
          <a href="https://tushare.pro/document/2?doc_id=363" target="_blank" rel="noopener noreferrer">查看文档</a>
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
                  <p className="text-xs sm:text-sm text-gray-600">总记录数</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.total_records)}</p>
                </div>
                <Database className="h-6 w-6 sm:h-8 sm:w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">板块数量</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.board_count)}</p>
                </div>
                <Layers className="h-6 w-6 sm:h-8 sm:w-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">成分股数量</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.stock_count)}</p>
                </div>
                <TrendingUp className="h-6 w-6 sm:h-8 sm:w-8 text-green-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600">日期数量</p>
                  <p className="text-xl sm:text-2xl font-bold">{formatNumber(statistics.date_count)}</p>
                </div>
                <Calendar className="h-6 w-6 sm:h-8 sm:w-8 text-orange-600" />
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
              <label className="text-sm font-medium mb-1 block">板块代码</label>
              <Input
                placeholder="如：BK0001"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>
            <div className="flex-1 w-full sm:w-auto">
              <label className="text-sm font-medium mb-1 block">成分股代码</label>
              <Input
                placeholder="如：000001.SZ"
                value={conCode}
                onChange={(e) => setConCode(e.target.value)}
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
            <h3 className="text-sm font-medium">板块成分数据</h3>
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
          {isLoading && (
            <div className="p-8 text-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto" />
            </div>
          )}
          {!isLoading && data.length === 0 && (
            <div className="p-8 text-center text-muted-foreground">暂无数据</div>
          )}
          {/* 移动端分页 */}
          {!isLoading && data.length > 0 && (
            <div className="p-4 border-t bg-muted/30">
              <div className="flex items-center justify-between">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => loadData(Math.max(1, page - 1))}
                  disabled={page === 1}
                >
                  上一页
                </Button>
                <span className="text-sm text-muted-foreground">
                  第 {page} / {Math.ceil(total / PAGE_SIZE)} 页
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => loadData(Math.min(Math.ceil(total / PAGE_SIZE), page + 1))}
                  disabled={page >= Math.ceil(total / PAGE_SIZE)}
                >
                  下一页
                </Button>
              </div>
            </div>
          )}
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
