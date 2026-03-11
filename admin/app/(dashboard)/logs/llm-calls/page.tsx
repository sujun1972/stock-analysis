/**
 * LLM调用日志页面
 * 展示所有AI模型调用的详细记录，支持筛选、分页和详情查看
 */

'use client'

import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  ChevronLeft,
  ChevronRight,
  Eye,
  Search,
  Download,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Minus
} from 'lucide-react'
import {
  getLLMCallLogs,
  getLLMSummary,
  type LLMCallLog,
  type LLMCallLogQuery,
  businessTypeMap,
  statusMap,
  providerMap
} from '@/lib/llm-logs-api'
import { format } from 'date-fns'
import { zhCN } from 'date-fns/locale'

export default function LLMCallLogsPage() {
  // 查询参数
  const [queryParams, setQueryParams] = useState<LLMCallLogQuery>({
    page: 1,
    page_size: 20
  })

  // 详情弹窗
  const [detailLog, setDetailLog] = useState<LLMCallLog | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)

  // 获取日志列表
  const { data: logsData, isLoading, refetch } = useQuery({
    queryKey: ['llm-logs', queryParams],
    queryFn: () => getLLMCallLogs(queryParams),
  })

  // 获取概览数据
  const { data: summaryData } = useQuery({
    queryKey: ['llm-summary', 7],
    queryFn: () => getLLMSummary(7),
  })

  const logs = logsData?.data?.logs || []
  const pagination = logsData?.data?.pagination
  const summary = summaryData

  // 查看详情
  const handleViewDetail = (log: LLMCallLog) => {
    setDetailLog(log)
    setDetailOpen(true)
  }

  // 格式化时间
  const formatDateTime = (dateStr: string) => {
    try {
      return format(new Date(dateStr), 'yyyy-MM-dd HH:mm:ss', { locale: zhCN })
    } catch {
      return dateStr
    }
  }

  // 格式化耗时
  const formatDuration = (ms: number | null) => {
    if (!ms) return '-'
    if (ms < 1000) return `${ms}ms`
    return `${(ms / 1000).toFixed(2)}s`
  }

  // 格式化成本
  const formatCost = (cost: number | null) => {
    if (!cost) return '-'
    return `$${cost.toFixed(4)}`
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">LLM调用日志</h1>
          <p className="text-gray-500 mt-1">查看和管理所有AI模型调用记录</p>
        </div>
        <Button onClick={() => refetch()} variant="outline" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" />
          刷新
        </Button>
      </div>

      {/* 概览卡片 */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardDescription>总调用次数（7天）</CardDescription>
              <CardTitle className="text-3xl">{summary.overview.total_calls}</CardTitle>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardDescription>成功率</CardDescription>
              <CardTitle className="text-3xl flex items-center gap-2">
                {summary.overview.success_rate.toFixed(1)}%
                {summary.overview.success_rate >= 95 ? (
                  <TrendingUp className="w-5 h-5 text-green-500" />
                ) : summary.overview.success_rate >= 80 ? (
                  <Minus className="w-5 h-5 text-yellow-500" />
                ) : (
                  <TrendingDown className="w-5 h-5 text-red-500" />
                )}
              </CardTitle>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardDescription>总消耗Tokens</CardDescription>
              <CardTitle className="text-3xl">{summary.overview.total_tokens.toLocaleString()}</CardTitle>
            </CardHeader>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardDescription>总成本</CardDescription>
              <CardTitle className="text-3xl">${summary.overview.total_cost.toFixed(4)}</CardTitle>
            </CardHeader>
          </Card>
        </div>
      )}

      {/* 筛选器 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">筛选条件</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Select
              value={queryParams.business_type || 'all'}
              onValueChange={(value) =>
                setQueryParams({ ...queryParams, business_type: value === 'all' ? undefined : value as any, page: 1 })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="业务类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部业务</SelectItem>
                <SelectItem value="sentiment_analysis">市场情绪分析</SelectItem>
                <SelectItem value="premarket_analysis">盘前碰撞分析</SelectItem>
                <SelectItem value="strategy_generation">策略代码生成</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={queryParams.provider || 'all'}
              onValueChange={(value) =>
                setQueryParams({ ...queryParams, provider: value === 'all' ? undefined : value, page: 1 })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="AI提供商" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部提供商</SelectItem>
                <SelectItem value="deepseek">DeepSeek</SelectItem>
                <SelectItem value="gemini">Gemini</SelectItem>
                <SelectItem value="openai">OpenAI</SelectItem>
              </SelectContent>
            </Select>

            <Select
              value={queryParams.status || 'all'}
              onValueChange={(value) =>
                setQueryParams({ ...queryParams, status: value === 'all' ? undefined : value as any, page: 1 })
              }
            >
              <SelectTrigger>
                <SelectValue placeholder="状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="success">成功</SelectItem>
                <SelectItem value="failed">失败</SelectItem>
                <SelectItem value="timeout">超时</SelectItem>
                <SelectItem value="rate_limited">限流</SelectItem>
              </SelectContent>
            </Select>

            <Input
              type="date"
              value={queryParams.start_date || ''}
              onChange={(e) => setQueryParams({ ...queryParams, start_date: e.target.value || undefined, page: 1 })}
              placeholder="开始日期"
            />
          </div>
        </CardContent>
      </Card>

      {/* 日志列表 */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">调用记录</CardTitle>
          <CardDescription>
            共 {pagination?.total || 0} 条记录
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>调用时间</TableHead>
                  <TableHead>业务类型</TableHead>
                  <TableHead>提供商</TableHead>
                  <TableHead>模型</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead className="text-right">Tokens</TableHead>
                  <TableHead className="text-right">成本</TableHead>
                  <TableHead className="text-right">耗时</TableHead>
                  <TableHead className="text-center">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {isLoading ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8 text-gray-500">
                      加载中...
                    </TableCell>
                  </TableRow>
                ) : logs.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8 text-gray-500">
                      暂无数据
                    </TableCell>
                  </TableRow>
                ) : (
                  logs.map((log) => (
                    <TableRow key={log.call_id}>
                      <TableCell className="text-sm">
                        {formatDateTime(log.created_at)}
                      </TableCell>
                      <TableCell>
                        <span className="text-sm">
                          {businessTypeMap[log.business_type] || log.business_type}
                        </span>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">
                          {providerMap[log.provider] || log.provider}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm font-mono">
                        {log.model_name}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={log.status === 'success' ? 'default' : 'destructive'}
                        >
                          {statusMap[log.status]?.text || log.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right text-sm">
                        {log.tokens_total?.toLocaleString() || '-'}
                      </TableCell>
                      <TableCell className="text-right text-sm">
                        {formatCost(log.cost_estimate)}
                      </TableCell>
                      <TableCell className="text-right text-sm">
                        {formatDuration(log.duration_ms)}
                      </TableCell>
                      <TableCell className="text-center">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleViewDetail(log)}
                        >
                          <Eye className="w-4 h-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>
          </div>

          {/* 分页 */}
          {pagination && pagination.total_pages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <div className="text-sm text-gray-500">
                第 {pagination.page} / {pagination.total_pages} 页
              </div>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setQueryParams({ ...queryParams, page: (queryParams.page || 1) - 1 })}
                  disabled={!pagination || pagination.page <= 1}
                >
                  <ChevronLeft className="w-4 h-4" />
                  上一页
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setQueryParams({ ...queryParams, page: (queryParams.page || 1) + 1 })}
                  disabled={!pagination || pagination.page >= pagination.total_pages}
                >
                  下一页
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 详情弹窗 */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle>LLM调用详情</DialogTitle>
            <DialogDescription>
              调用ID: {detailLog?.call_id}
            </DialogDescription>
          </DialogHeader>

          {detailLog && (
            <ScrollArea className="h-[60vh]">
              <div className="space-y-6 pr-4">
                {/* 基本信息 */}
                <div>
                  <h3 className="font-semibold mb-3 text-lg">基本信息</h3>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-500">业务类型：</span>
                      <span className="ml-2">{businessTypeMap[detailLog.business_type]}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">业务日期：</span>
                      <span className="ml-2">{detailLog.business_date || '-'}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">AI提供商：</span>
                      <Badge variant="outline" className="ml-2">
                        {providerMap[detailLog.provider]}
                      </Badge>
                    </div>
                    <div>
                      <span className="text-gray-500">模型：</span>
                      <span className="ml-2 font-mono text-xs">{detailLog.model_name}</span>
                    </div>
                    <div>
                      <span className="text-gray-500">状态：</span>
                      <Badge variant={detailLog.status === 'success' ? 'default' : 'destructive'} className="ml-2">
                        {statusMap[detailLog.status]?.text}
                      </Badge>
                    </div>
                    <div>
                      <span className="text-gray-500">触发方式：</span>
                      <span className="ml-2">{detailLog.is_scheduled ? '定时任务' : '手动触发'}</span>
                    </div>
                  </div>
                </div>

                {/* 性能指标 */}
                <div>
                  <h3 className="font-semibold mb-3 text-lg">性能指标</h3>
                  <div className="grid grid-cols-3 gap-4">
                    <Card>
                      <CardHeader className="pb-2">
                        <CardDescription>Tokens消耗</CardDescription>
                        <CardTitle className="text-2xl">{detailLog.tokens_total?.toLocaleString() || '-'}</CardTitle>
                      </CardHeader>
                    </Card>
                    <Card>
                      <CardHeader className="pb-2">
                        <CardDescription>成本</CardDescription>
                        <CardTitle className="text-2xl">{formatCost(detailLog.cost_estimate)}</CardTitle>
                      </CardHeader>
                    </Card>
                    <Card>
                      <CardHeader className="pb-2">
                        <CardDescription>耗时</CardDescription>
                        <CardTitle className="text-2xl">{formatDuration(detailLog.duration_ms)}</CardTitle>
                      </CardHeader>
                    </Card>
                  </div>
                </div>

                {/* 调用参数 */}
                <div>
                  <h3 className="font-semibold mb-3 text-lg">调用参数</h3>
                  <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg text-xs overflow-auto">
                    {JSON.stringify(detailLog.call_parameters, null, 2)}
                  </pre>
                </div>

                {/* 输入Prompt */}
                <div>
                  <h3 className="font-semibold mb-3 text-lg">输入Prompt</h3>
                  <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
                    <p className="text-xs text-gray-500 mb-2">
                      长度: {detailLog.prompt_length} 字符
                    </p>
                    <pre className="text-sm whitespace-pre-wrap max-h-60 overflow-auto">
                      {detailLog.prompt_text}
                    </pre>
                  </div>
                </div>

                {/* 输出Response */}
                {detailLog.response_text && (
                  <div>
                    <h3 className="font-semibold mb-3 text-lg">输出Response</h3>
                    <div className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg">
                      <p className="text-xs text-gray-500 mb-2">
                        长度: {detailLog.response_length} 字符
                      </p>
                      <pre className="text-sm whitespace-pre-wrap max-h-60 overflow-auto">
                        {detailLog.response_text}
                      </pre>
                    </div>
                  </div>
                )}

                {/* 错误信息 */}
                {detailLog.error_message && (
                  <div>
                    <h3 className="font-semibold mb-3 text-lg text-red-600">错误信息</h3>
                    <div className="bg-red-50 dark:bg-red-900/20 p-4 rounded-lg">
                      <p className="text-sm text-red-600 dark:text-red-400">
                        {detailLog.error_message}
                      </p>
                      {detailLog.error_code && (
                        <p className="text-xs text-gray-500 mt-2">
                          错误代码: {detailLog.error_code}
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
