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
import { balancesheetApi } from '@/lib/api/balancesheet-api'
import type { BalancesheetData, BalancesheetStatistics } from '@/lib/api/balancesheet-api'
import { useTaskStore } from '@/stores/task-store'
import { TrendingUp, TrendingDown, DollarSign, PieChart } from 'lucide-react'

export default function BalancesheetPage() {
  const [data, setData] = useState<BalancesheetData[]>([])
  const [statistics, setStatistics] = useState<BalancesheetStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState('')
  const [reportType, setReportType] = useState<string>('1')
  const [compType, setCompType] = useState<string>('1')

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

      const params = {
        start_date: startDate ? formatDate(startDate) : undefined,
        end_date: endDate ? formatDate(endDate) : undefined,
        ts_code: tsCode || undefined,
        report_type: reportType !== 'all' ? reportType : undefined,
        comp_type: compType !== 'all' ? compType : undefined,
        limit: pageSize,
        offset: (page - 1) * pageSize
      }

      const [dataResponse, statsResponse] = await Promise.all([
        balancesheetApi.getData(params),
        balancesheetApi.getStatistics(params)
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
      const response = await balancesheetApi.syncAsync({
        ts_code: tsCode || undefined,
        start_date: startDate ? formatDateToYYYYMMDD(startDate) : undefined,
        end_date: endDate ? formatDateToYYYYMMDD(endDate) : undefined,
        report_type: reportType !== 'all' ? reportType : undefined
      })

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

        // 注册任务完成回调：自动刷新数据
        const completionCallback = (task: any) => {
          if (task.status === 'success') {
            loadData().catch(() => {})
            toast.success('数据同步完成', {
              description: '资产负债表数据已更新'
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

  const formatDateToYYYYMMDD = (date: Date): string => {
    const year = date.getFullYear()
    const month = String(date.getMonth() + 1).padStart(2, '0')
    const day = String(date.getDate()).padStart(2, '0')
    return `${year}${month}${day}`
  }

  const formatAmount = (amount: number | null | undefined): string => {
    if (amount === null || amount === undefined) return '-'
    return amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  const columns: Column<BalancesheetData>[] = [
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code,
      className: 'font-mono'
    },
    {
      key: 'end_date',
      header: '报告期',
      accessor: (row) => row.end_date
    },
    {
      key: 'total_assets',
      header: '总资产（万元）',
      accessor: (row) => formatAmount(row.total_assets),
      className: 'text-right'
    },
    {
      key: 'total_cur_assets',
      header: '流动资产（万元）',
      accessor: (row) => formatAmount(row.total_cur_assets),
      className: 'text-right hidden md:table-cell'
    },
    {
      key: 'total_liab',
      header: '总负债（万元）',
      accessor: (row) => formatAmount(row.total_liab),
      className: 'text-right'
    },
    {
      key: 'total_cur_liab',
      header: '流动负债（万元）',
      accessor: (row) => formatAmount(row.total_cur_liab),
      className: 'text-right hidden lg:table-cell'
    },
    {
      key: 'total_hldr_eqy_inc_min_int',
      header: '股东权益（万元）',
      accessor: (row) => formatAmount(row.total_hldr_eqy_inc_min_int),
      className: 'text-right'
    },
    {
      key: 'report_type',
      header: '报告类型',
      accessor: (row) => {
        const types: Record<string, string> = {
          '1': '合并报表',
          '2': '单季合并',
          '3': '调整单季',
          '4': '调整合并',
          '5': '调整前合并',
          '6': '母公司',
          '7': '母公司单季',
          '8': '母公司调整单季',
          '9': '母公司调整',
          '10': '母公司调整前',
          '11': '调整前合并',
          '12': '母公司调整前'
        }
        return types[row.report_type] || row.report_type
      },
      className: 'hidden xl:table-cell'
    }
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="资产负债表数据"
        description="上市公司资产负债表数据查询与同步（Tushare balancesheet_vip接口，2000积分/次）"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                记录数
              </CardTitle>
              <PieChart className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{(statistics.total_records || 0).toLocaleString()}</div>
              <p className="text-xs text-muted-foreground mt-1">
                股票数: {statistics.total_stocks || 0}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                平均总资产
              </CardTitle>
              <DollarSign className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatAmount(statistics.avg_total_assets)}</div>
              <p className="text-xs text-muted-foreground mt-1">万元</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                平均总负债
              </CardTitle>
              <TrendingDown className="h-4 w-4 text-red-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {formatAmount(statistics.avg_total_liab)}
              </div>
              <p className="text-xs text-muted-foreground mt-1">万元</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                平均股东权益
              </CardTitle>
              <TrendingUp className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {formatAmount(statistics.avg_equity)}
              </div>
              <p className="text-xs text-muted-foreground mt-1">万元</p>
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">股票代码</label>
              <Input
                placeholder="如：600000.SH"
                value={tsCode}
                onChange={(e) => setTsCode(e.target.value)}
              />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">开始日期（报告期）</label>
              <DatePicker date={startDate} onSelect={setStartDate} />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">结束日期（报告期）</label>
              <DatePicker date={endDate} onSelect={setEndDate} />
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">报告类型</label>
              <Select value={reportType} onValueChange={setReportType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部</SelectItem>
                  <SelectItem value="1">合并报表</SelectItem>
                  <SelectItem value="2">单季合并</SelectItem>
                  <SelectItem value="3">调整单季合并</SelectItem>
                  <SelectItem value="4">调整合并报表</SelectItem>
                  <SelectItem value="6">母公司报表</SelectItem>
                  <SelectItem value="7">母公司单季</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <label className="text-sm font-medium">公司类型</label>
              <Select value={compType} onValueChange={setCompType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部</SelectItem>
                  <SelectItem value="1">一般工商业</SelectItem>
                  <SelectItem value="2">银行</SelectItem>
                  <SelectItem value="3">保险</SelectItem>
                  <SelectItem value="4">证券</SelectItem>
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
                setTsCode('')
                setStartDate(undefined)
                setEndDate(undefined)
                setReportType('1')
                setCompType('1')
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
                    <div className="font-mono font-semibold">{item.ts_code}</div>
                    <div className="text-sm text-muted-foreground">报告期: {item.end_date}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-medium">总资产</div>
                    <div className="text-xs">{formatAmount(item.total_assets)}</div>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-2 pt-2 border-t">
                  <div>
                    <div className="text-xs text-muted-foreground">总负债</div>
                    <div className="text-sm font-medium text-red-600">{formatAmount(item.total_liab)}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted-foreground">股东权益</div>
                    <div className="text-sm font-medium text-green-600">
                      {formatAmount(item.total_hldr_eqy_inc_min_int)}
                    </div>
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
