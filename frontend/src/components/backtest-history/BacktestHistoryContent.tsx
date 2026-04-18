'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, TrendingUp, TrendingDown, Calendar, Clock, Trash2, Eye, AlertCircle } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { apiClient } from '@/lib/api-client'
import { extractApiError } from '@/lib/error-formatter'

interface BacktestRecord {
  id: number
  execution_type: string
  status: string
  metrics: {
    total_return: number
    annual_return: number
    sharpe_ratio: number
    max_drawdown: number
    win_rate: number
    total_trades: number
  }
  execution_params: {
    stock_pool: string[]
    start_date: string
    end_date: string
    initial_capital: number
  }
  error_message?: string
  execution_duration_ms?: number
  started_at?: string
  completed_at?: string
  created_at: string
  strategy?: {
    id: number
    name: string
    display_name: string
    source_type: string
  }
}

export default function BacktestHistoryContent() {
  const router = useRouter()
  const { toast } = useToast()

  const [records, setRecords] = useState<BacktestRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [pageSize] = useState(20)
  const [statusFilter, setStatusFilter] = useState<string>('all')

  // 加载回测历史
  const loadBacktestHistory = async () => {
    setLoading(true)
    setError(null)

    try {
      const params: any = {
        page,
        page_size: pageSize,
      }

      if (statusFilter !== 'all') {
        params.status_filter = statusFilter
      }

      const response = await apiClient.get<{ items: BacktestRecord[]; total: number }>('/api/backtest-history', { params })

      // apiClient.get 已返回 response.data，直接访问 code 和 data
      if (response.code === 200) {
        setRecords(response.data.items)
        setTotal(response.data.total)
      } else {
        setError(response.message || '加载失败')
      }
    } catch (err: any) {
      const errorMsg = extractApiError(err)

      // 未登录错误由ProtectedRoute处理，此处忽略
      if (!errorMsg.includes('Not authenticated') && !errorMsg.includes('未认证')) {
        setError(errorMsg)
        toast({
          variant: 'destructive',
          title: '加载失败',
          description: errorMsg,
        })
      }
    } finally {
      setLoading(false)
    }
  }

  // 查看详情
  const handleViewDetail = (record: BacktestRecord) => {
    router.push(`/backtest-results/${record.id}`)
  }

  // 删除记录
  const handleDelete = async (id: number) => {
    if (!confirm('确定要删除这条回测记录吗？')) {
      return
    }

    try {
      const response = await apiClient.delete(`/api/backtest-history/${id}`)

      if (response.success) {
        toast({
          title: '删除成功',
          description: '回测记录已删除',
        })
        loadBacktestHistory()
      } else {
        toast({
          variant: 'destructive',
          title: '删除失败',
          description: response.message,
        })
      }
    } catch (err: any) {
      toast({
        variant: 'destructive',
        title: '删除失败',
        description: extractApiError(err),
      })
    }
  }

  // 格式化日期
  const formatDate = (dateStr?: string) => {
    if (!dateStr) return '-'
    return new Date(dateStr).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  // 格式化百分比
  const formatPercent = (value: number) => {
    return `${(value * 100).toFixed(2)}%`
  }

  // 获取状态徽章
  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { variant: any; label: string }> = {
      completed: { variant: 'default', label: '已完成' },
      running: { variant: 'secondary', label: '运行中' },
      failed: { variant: 'destructive', label: '失败' },
      pending: { variant: 'outline', label: '等待中' },
      cancelled: { variant: 'outline', label: '已取消' },
    }

    const statusInfo = statusMap[status] || { variant: 'outline', label: status }
    return <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>
  }

  useEffect(() => {
    loadBacktestHistory()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, statusFilter])

  if (loading && records.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
      </div>
    )
  }

  if (error && records.length === 0) {
    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-6">
      {/* 筛选栏 */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>回测记录</CardTitle>
              <CardDescription>共 {total} 条记录</CardDescription>
            </div>
            <div className="flex items-center gap-4">
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-[150px]">
                  <SelectValue placeholder="状态筛选" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部状态</SelectItem>
                  <SelectItem value="completed">已完成</SelectItem>
                  <SelectItem value="running">运行中</SelectItem>
                  <SelectItem value="failed">失败</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {records.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <p>暂无回测记录</p>
              <Button
                className="mt-4"
                onClick={() => router.push('/strategies')}
              >
                去创建回测
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {records.map((record) => (
                <Card key={record.id} className="hover:shadow-md transition-shadow">
                  <CardContent className="pt-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 space-y-3">
                        {/* 头部信息 */}
                        <div className="flex items-center gap-3">
                          {getStatusBadge(record.status)}
                          {record.strategy && (
                            <span className="font-medium text-gray-900 dark:text-white">
                              {record.strategy.display_name || record.strategy.name}
                            </span>
                          )}
                          <Badge variant="outline">{record.execution_type}</Badge>
                        </div>

                        {/* 时间和参数 */}
                        <div className="flex items-center gap-6 text-sm text-gray-600 dark:text-gray-400">
                          <div className="flex items-center gap-1">
                            <Calendar className="h-4 w-4" />
                            <span>
                              {record.execution_params.start_date} ~ {record.execution_params.end_date}
                            </span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Clock className="h-4 w-4" />
                            <span>{formatDate(record.created_at)}</span>
                          </div>
                          <span>股票池: {record.execution_params.stock_pool.length} 只</span>
                        </div>

                        {/* 绩效指标 */}
                        {record.status === 'completed' && (
                          <div className="grid grid-cols-6 gap-4 pt-2">
                            <div>
                              <p className="text-xs text-gray-500 dark:text-gray-400">总收益</p>
                              <p
                                className={`text-sm font-semibold ${
                                  record.metrics.total_return >= 0 ? 'text-green-600' : 'text-red-600'
                                }`}
                              >
                                {record.metrics.total_return >= 0 ? (
                                  <TrendingUp className="inline h-3 w-3 mr-1" />
                                ) : (
                                  <TrendingDown className="inline h-3 w-3 mr-1" />
                                )}
                                {formatPercent(record.metrics.total_return)}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-gray-500 dark:text-gray-400">年化收益</p>
                              <p className="text-sm font-semibold">
                                {formatPercent(record.metrics.annual_return)}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-gray-500 dark:text-gray-400">夏普比率</p>
                              <p className="text-sm font-semibold">
                                {record.metrics.sharpe_ratio.toFixed(2)}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-gray-500 dark:text-gray-400">最大回撤</p>
                              <p className="text-sm font-semibold text-red-600">
                                {formatPercent(record.metrics.max_drawdown)}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-gray-500 dark:text-gray-400">胜率</p>
                              <p className="text-sm font-semibold">
                                {formatPercent(record.metrics.win_rate)}
                              </p>
                            </div>
                            <div>
                              <p className="text-xs text-gray-500 dark:text-gray-400">交易次数</p>
                              <p className="text-sm font-semibold">{record.metrics.total_trades}</p>
                            </div>
                          </div>
                        )}

                        {/* 错误信息 */}
                        {record.status === 'failed' && record.error_message && (
                          <Alert variant="destructive">
                            <AlertCircle className="h-4 w-4" />
                            <AlertDescription className="text-sm">
                              {record.error_message}
                            </AlertDescription>
                          </Alert>
                        )}
                      </div>

                      {/* 操作按钮 */}
                      <div className="flex items-center gap-2 ml-4">
                        {record.status === 'completed' && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleViewDetail(record)}
                          >
                            <Eye className="h-4 w-4 mr-1" />
                            查看详情
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(record.id)}
                        >
                          <Trash2 className="h-4 w-4 text-red-600" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* 分页 */}
          {total > pageSize && (
            <div className="flex items-center justify-between mt-6">
              <div className="text-sm text-gray-600 dark:text-gray-400">
                显示 {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, total)} 条，共 {total} 条
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                >
                  上一页
                </Button>
                <span className="text-sm px-3">第 {page} 页</span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setPage((p) => p + 1)}
                  disabled={page * pageSize >= total}
                >
                  下一页
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
