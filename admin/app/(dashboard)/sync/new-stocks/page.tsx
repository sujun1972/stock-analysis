'use client'

import { useState, useEffect, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { toast } from 'sonner'
import { newStockApi } from '@/lib/api'
import type { NewStockData, NewStockStatistics } from '@/lib/api/new-stock-api'
import { useTaskStore } from '@/stores/task-store'
import { TrendingUp, Calendar, BarChart3, PieChart } from 'lucide-react'

export default function NewStocksPage() {
  const [data, setData] = useState<NewStockData[]>([])
  const [statistics, setStatistics] = useState<NewStockStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [days, setDays] = useState<number>(30)
  const [market, setMarket] = useState<string>('all')

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  useEffect(() => {
    loadData().catch(() => {})
  }, [])

  // 分页变化时重新加载数据
  useEffect(() => {
    loadData().catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, pageSize])

  // 组件卸载时清理所有活跃的任务回调
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

  const loadData = async () => {
    try {
      setIsLoading(true)

      const params: any = {
        limit: pageSize,
        offset: (page - 1) * pageSize
      }

      // 日期参数优先级：days > start_date/end_date
      if (days && !startDate && !endDate) {
        params.days = days
      } else {
        if (startDate) params.start_date = formatDate(startDate)
        if (endDate) params.end_date = formatDate(endDate)
      }

      if (market !== 'all') {
        params.market = market
      }

      const [dataResponse, statsResponse] = await Promise.all([
        newStockApi.getData(params),
        newStockApi.getStatistics({ days: days || 90 })
      ])

      if (dataResponse.code === 200 && dataResponse.data) {
        setData(dataResponse.data.items)
        setTotal(dataResponse.data.total || dataResponse.data.items.length)
      }

      if (statsResponse.code === 200 && statsResponse.data) {
        setStatistics(statsResponse.data)
      }
    } catch (error) {
      toast.error('加载数据失败')
      console.error(error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleSync = async () => {
    try {
      const response = await newStockApi.syncAsync({
        days: days || 30
      })

      if (response.code === 200 && response.data) {
        const taskId = response.data.celery_task_id

        if (!taskId) {
          toast.error('任务ID缺失')
          return
        }

        addTask({
          taskId,
          taskName: response.data.task_name,
          displayName: response.data.display_name,
          taskType: 'data_sync',
          status: 'running',
          progress: 0,
          startTime: Date.now()
        })

        // 注册任务完成回调：自动刷新数据
        const completionCallback = (task: any) => {
          if (task.status === 'success') {
            loadData().catch(() => {})
            toast.success('数据同步完成', {
              description: '新股列表数据已更新'
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
        toast.success('同步任务已提交', {
          description: '可在任务面板查看进度'
        })
      } else {
        toast.error(response.message || '同步任务提交失败')
      }
    } catch (error) {
      toast.error('同步任务提交失败')
      console.error(error)
    }
  }

  const formatDate = (date: Date): string => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}-${month}-${day}`
  }

  const columns: Column<NewStockData>[] = [
    {
      key: 'code',
      header: '股票代码',
      accessor: (row) => row.code,
      className: 'font-mono'
    },
    {
      key: 'name',
      header: '股票名称',
      accessor: (row) => row.name
    },
    {
      key: 'market',
      header: '市场类型',
      accessor: (row) => row.market,
      className: 'hidden md:table-cell'
    },
    {
      key: 'industry',
      header: '所属行业',
      accessor: (row) => row.industry || '-',
      className: 'hidden lg:table-cell'
    },
    {
      key: 'area',
      header: '地区',
      accessor: (row) => row.area || '-',
      className: 'hidden xl:table-cell'
    },
    {
      key: 'list_date',
      header: '上市日期',
      accessor: (row) => row.list_date
    },
    {
      key: 'status',
      header: '状态',
      accessor: (row) => row.status,
      className: 'hidden md:table-cell'
    }
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="新股列表"
        description="查询和管理最近上市的新股信息（Tushare new_share接口）"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                总数量
              </CardTitle>
              <PieChart className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{statistics.total_count}</div>
              <p className="text-xs text-muted-foreground mt-1">
                统计范围内新上市股票
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                最近7天
              </CardTitle>
              <TrendingUp className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">{statistics.recent_7_days}</div>
              <p className="text-xs text-muted-foreground mt-1">新上市</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                最近30天
              </CardTitle>
              <Calendar className="h-4 w-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">{statistics.recent_30_days}</div>
              <p className="text-xs text-muted-foreground mt-1">新上市</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                最近90天
              </CardTitle>
              <BarChart3 className="h-4 w-4 text-purple-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-purple-600">{statistics.recent_90_days}</div>
              <p className="text-xs text-muted-foreground mt-1">新上市</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 筛选和操作区域 */}
      <Card>
        <CardHeader>
          <CardTitle>数据查询</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">最近天数</label>
              <Input
                type="number"
                min="1"
                max="365"
                value={days}
                onChange={(e) => setDays(parseInt(e.target.value) || 30)}
                placeholder="如：30"
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">开始日期</label>
              <DatePicker date={startDate} onSelect={setStartDate} />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">结束日期</label>
              <DatePicker date={endDate} onSelect={setEndDate} />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">市场类型</label>
              <Select value={market} onValueChange={setMarket}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部市场</SelectItem>
                  <SelectItem value="主板">主板</SelectItem>
                  <SelectItem value="科创板">科创板</SelectItem>
                  <SelectItem value="创业板">创业板</SelectItem>
                  <SelectItem value="北交所">北交所</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button onClick={loadData} disabled={isLoading}>
              {isLoading ? '查询中...' : '查询'}
            </Button>
            <Button onClick={handleSync} variant="outline">
              同步数据
            </Button>
            <Button
              onClick={() => {
                setDays(30)
                setStartDate(undefined)
                setEndDate(undefined)
                setMarket('all')
              }}
              variant="ghost"
            >
              重置
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card>
        <CardContent className="pt-6">
          <DataTable
            columns={columns}
            data={data}
            loading={isLoading}
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: (newPage) => {
                setPage(newPage)
              },
              onPageSizeChange: (newPageSize) => {
                setPageSize(newPageSize)
                setPage(1)
              },
              pageSizeOptions: [10, 20, 30, 50, 100]
            }}
            mobileCard={(item) => (
              <div className="p-4 space-y-2">
                <div className="flex justify-between items-start">
                  <div>
                    <div className="font-mono font-semibold">{item.code}</div>
                    <div className="text-sm text-muted-foreground">{item.name}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-medium">上市日期</div>
                    <div className="text-xs">{item.list_date}</div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 pt-2 border-t">
                  <div>
                    <div className="text-xs text-muted-foreground">市场类型</div>
                    <div className="text-sm font-medium">{item.market}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">行业</div>
                    <div className="text-sm font-medium">{item.industry || '-'}</div>
                  </div>
                </div>
              </div>
            )}
          />
        </CardContent>
      </Card>
    </div>
  )
}
