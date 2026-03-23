'use client'

import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { stkSurvApi, type StkSurvData, type StkSurvStatistics } from '@/lib/api'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { RefreshCw, FileText, Building2, Calendar, Users } from 'lucide-react'

export default function StkSurvPage() {
  const [data, setData] = useState<StkSurvData[]>([])
  const [statistics, setStatistics] = useState<StkSurvStatistics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)
  const [tsCode, setTsCode] = useState<string>('')
  const [receMode, setReceMode] = useState<string>('')
  const [orgType, setOrgType] = useState<string>('')
  const [syncing, setSyncing] = useState(false)

  // 分页状态
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(30)
  const [total, setTotal] = useState(0)

  // 存储活跃的任务回调
  const activeCallbacksRef = useRef<Map<string, any>>(new Map())

  const { addTask, triggerPoll, registerCompletionCallback, unregisterCompletionCallback } = useTaskStore()

  // 加载数据
  const loadData = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)

      const params: any = {
        limit: pageSize
      }

      if (startDate) {
        params.start_date = startDate.toISOString().split('T')[0]
      }
      if (endDate) {
        params.end_date = endDate.toISOString().split('T')[0]
      }
      if (tsCode.trim()) {
        params.ts_code = tsCode.trim()
      }
      if (receMode) {
        params.rece_mode = receMode
      }
      if (orgType) {
        params.org_type = orgType
      }

      const response = await stkSurvApi.getData(params)

      if (response.code === 200 && response.data) {
        setData(response.data.items || [])
        setTotal(response.data.total || 0)
      } else {
        throw new Error(response.message || '获取数据失败')
      }

      // 加载统计信息
      const statsParams: any = {}
      if (startDate) statsParams.start_date = startDate.toISOString().split('T')[0]
      if (endDate) statsParams.end_date = endDate.toISOString().split('T')[0]

      const statsResponse = await stkSurvApi.getStatistics(statsParams)
      if (statsResponse.code === 200 && statsResponse.data) {
        setStatistics(statsResponse.data)
      }
    } catch (err: any) {
      const errorMsg = err.message || '加载数据失败'
      setError(errorMsg)
      toast.error('加载失败', { description: errorMsg })
    } finally {
      setIsLoading(false)
    }
  }, [startDate, endDate, tsCode, receMode, orgType, pageSize])

  // 初始加载
  useEffect(() => {
    loadData()
  }, [loadData])

  // 异步同步数据
  const handleSync = async () => {
    try {
      setSyncing(true)

      const params: any = {}
      if (startDate) params.start_date = startDate.toISOString().split('T')[0]
      if (endDate) params.end_date = endDate.toISOString().split('T')[0]
      if (tsCode.trim()) params.ts_code = tsCode.trim()

      const response = await stkSurvApi.syncAsync(params)

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
              description: '机构调研数据已更新'
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

  // 组件卸载时清理回调
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

  // 格式化数字
  const formatNumber = (value: number | null | undefined): string => {
    if (value === null || value === undefined) return '-'
    return value.toLocaleString('zh-CN')
  }

  // 截断文本
  const truncateText = (text: string | null | undefined, maxLength: number = 30): string => {
    if (!text) return '-'
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text
  }

  // 移动端卡片视图
  const mobileCard = useCallback((item: StkSurvData) => (
    <div className="space-y-2">
      <div className="flex justify-between items-center pb-2 border-b border-gray-200 dark:border-gray-700">
        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">调研日期</span>
        <span className="font-medium">{item.surv_date}</span>
      </div>

      <div className="flex justify-between items-center">
        <span className="text-sm text-gray-600 dark:text-gray-400">股票代码</span>
        <span className="font-medium">{item.ts_code}</span>
      </div>

      {item.name && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">股票名称</span>
          <span className="font-medium">{item.name}</span>
        </div>
      )}

      {item.rece_mode && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">接待方式</span>
          <span className="font-medium">{item.rece_mode}</span>
        </div>
      )}

      {item.org_type && (
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-600 dark:text-gray-400">接待公司类型</span>
          <span className="font-medium">{item.org_type}</span>
        </div>
      )}

      {item.fund_visitors && (
        <div className="flex flex-col gap-1">
          <span className="text-sm text-gray-600 dark:text-gray-400">机构参与人员</span>
          <span className="text-sm text-gray-800 dark:text-gray-200 break-all">
            {truncateText(item.fund_visitors, 50)}
          </span>
        </div>
      )}

      {item.rece_place && (
        <div className="flex flex-col gap-1">
          <span className="text-sm text-gray-600 dark:text-gray-400">接待地点</span>
          <span className="text-sm text-gray-800 dark:text-gray-200 break-all">
            {truncateText(item.rece_place, 50)}
          </span>
        </div>
      )}

      {item.rece_org && (
        <div className="flex flex-col gap-1">
          <span className="text-sm text-gray-600 dark:text-gray-400">接待的公司</span>
          <span className="text-sm text-gray-800 dark:text-gray-200 break-all">
            {truncateText(item.rece_org, 50)}
          </span>
        </div>
      )}
    </div>
  ), [])

  // 桌面端表格列定义
  const columns: Column<StkSurvData>[] = useMemo(() => [
    {
      key: 'surv_date',
      header: '调研日期',
      accessor: (row) => row.surv_date
    },
    {
      key: 'ts_code',
      header: '股票代码',
      accessor: (row) => row.ts_code
    },
    {
      key: 'name',
      header: '股票名称',
      accessor: (row) => row.name || '-'
    },
    {
      key: 'fund_visitors',
      header: '机构参与人员',
      accessor: (row) => (
        <span className="max-w-xs truncate block" title={row.fund_visitors || ''}>
          {truncateText(row.fund_visitors, 40)}
        </span>
      )
    },
    {
      key: 'rece_mode',
      header: '接待方式',
      accessor: (row) => row.rece_mode || '-'
    },
    {
      key: 'org_type',
      header: '接待公司类型',
      accessor: (row) => row.org_type || '-'
    },
    {
      key: 'rece_place',
      header: '接待地点',
      accessor: (row) => (
        <span className="max-w-xs truncate block" title={row.rece_place || ''}>
          {truncateText(row.rece_place, 30)}
        </span>
      )
    },
    {
      key: 'rece_org',
      header: '接待的公司',
      accessor: (row) => (
        <span className="max-w-xs truncate block" title={row.rece_org || ''}>
          {truncateText(row.rece_org, 30)}
        </span>
      )
    }
  ], [])

  return (
    <div className="space-y-6">
      <PageHeader
        title="机构调研表"
        description="上市公司机构调研记录数据"
      />

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">总记录数</CardTitle>
              <FileText className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(statistics.total_records)}</div>
              <p className="text-xs text-muted-foreground">条</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">股票数</CardTitle>
              <Building2 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(statistics.unique_stocks)}</div>
              <p className="text-xs text-muted-foreground">个</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">日期数</CardTitle>
              <Calendar className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(statistics.unique_dates)}</div>
              <p className="text-xs text-muted-foreground">天</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">机构类型数</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(statistics.unique_org_types)}</div>
              <p className="text-xs text-muted-foreground">种</p>
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
          <div className="flex flex-col gap-4">
            {/* 第一行 */}
            <div className="flex flex-col sm:flex-row gap-4 items-end">
              <div className="flex-1">
                <label className="text-sm font-medium mb-2 block">股票代码</label>
                <Input
                  placeholder="如：000001.SZ"
                  value={tsCode}
                  onChange={(e) => setTsCode(e.target.value)}
                />
              </div>

              <div className="flex-1">
                <label className="text-sm font-medium mb-2 block">接待方式</label>
                <Select
                  value={receMode || 'ALL'}
                  onValueChange={(value) => setReceMode(value === 'ALL' ? '' : value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择接待方式" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">全部</SelectItem>
                    <SelectItem value="实地调研">实地调研</SelectItem>
                    <SelectItem value="电话会议">电话会议</SelectItem>
                    <SelectItem value="特定对象调研">特定对象调研</SelectItem>
                    <SelectItem value="其他">其他</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex-1">
                <label className="text-sm font-medium mb-2 block">接待公司类型</label>
                <Select
                  value={orgType || 'ALL'}
                  onValueChange={(value) => setOrgType(value === 'ALL' ? '' : value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择公司类型" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="ALL">全部</SelectItem>
                    <SelectItem value="证券公司">证券公司</SelectItem>
                    <SelectItem value="基金公司">基金公司</SelectItem>
                    <SelectItem value="保险公司">保险公司</SelectItem>
                    <SelectItem value="阳光私募">阳光私募</SelectItem>
                    <SelectItem value="其他">其他</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* 第二行 */}
            <div className="flex flex-col sm:flex-row gap-4 items-end">
              <div className="flex-1">
                <label className="text-sm font-medium mb-2 block">开始日期</label>
                <DatePicker date={startDate} onSelect={setStartDate} />
              </div>

              <div className="flex-1">
                <label className="text-sm font-medium mb-2 block">结束日期</label>
                <DatePicker date={endDate} onSelect={setEndDate} />
              </div>

              <Button onClick={loadData} disabled={isLoading}>
                {isLoading ? '查询中...' : '查询'}
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
          </div>
        </CardContent>
      </Card>

      {/* 数据表格 */}
      <Card className="p-0 sm:p-0 overflow-hidden">
        {/* 移动端视图 */}
        <div className="sm:hidden">
          <div className="px-4 py-3 border-b bg-muted/50">
            <h3 className="text-sm font-medium">机构调研数据</h3>
          </div>
          <div className="divide-y divide-gray-200 dark:divide-gray-700">
            {!isLoading && !error && data.map((item, index) => (
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

          {/* 移动端状态显示 */}
          {isLoading && (
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
          {!isLoading && !error && data.length === 0 && (
            <div className="p-8 text-center">
              <p className="text-sm text-muted-foreground">暂无数据</p>
            </div>
          )}

          {/* 移动端分页 */}
          {!isLoading && !error && data.length > 0 && (
            <div className="p-4 border-t bg-muted/30">
              <div className="flex items-center justify-between">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                >
                  上一页
                </Button>
                <span className="text-sm text-muted-foreground">
                  第 {page} / {Math.ceil(total / pageSize)} 页
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage(Math.min(Math.ceil(total / pageSize), page + 1))}
                  disabled={page >= Math.ceil(total / pageSize)}
                >
                  下一页
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* 桌面端表格视图 */}
        <div className="hidden sm:block">
          <DataTable
            columns={columns}
            data={data}
            loading={isLoading}
            error={error}
            emptyMessage="暂无数据"
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: (newPage) => setPage(newPage),
              onPageSizeChange: (newPageSize) => {
                setPageSize(newPageSize)
                setPage(1)
              },
              pageSizeOptions: [10, 20, 30, 50, 100]
            }}
          />
        </div>
      </Card>
    </div>
  )
}
