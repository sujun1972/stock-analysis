'use client'

/**
 * 通知系统监控页面
 *
 * Phase 3: 提供通知系统实时监控、统计分析、失败诊断
 */

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Mail,
  MessageSquare,
  RefreshCw,
  TrendingUp,
  XCircle,
} from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { toast } from 'sonner'
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  PieChart,
  Pie,
  Cell,
} from 'recharts'

interface HealthStatus {
  status: 'healthy' | 'warning' | 'critical'
  success_rate_24h: number
  pending_count: number
  failure_rate: number
  alerts: string[]
  timestamp: string
}

interface RealtimeStats {
  last_24h: {
    total: number
    sent: number
    failed: number
    success_rate: number
    by_channel: Record<string, any>
  }
  last_hour: {
    total: number
    sent: number
    failed: number
  }
  pending_count: number
  recent_failures: any[]
}

interface ChannelPerformance {
  [key: string]: {
    total: number
    success_rate: number
    avg_delivery_time: number
    failure_reasons: Array<{ reason: string; count: number }>
    peak_hours: Array<{ hour: number; count: number }>
  }
}

export default function NotificationMonitoringPage() {
  const [loading, setLoading] = useState(true)
  const [healthStatus, setHealthStatus] = useState<HealthStatus | null>(null)
  const [realtimeStats, setRealtimeStats] = useState<RealtimeStats | null>(null)
  const [channelPerformance, setChannelPerformance] = useState<ChannelPerformance | null>(null)
  const [dailyTrend, setDailyTrend] = useState<any[]>([])
  const [failureReasons, setFailureReasons] = useState<any[]>([])

  useEffect(() => {
    loadData()
    // 自动刷新（每分钟）
    const interval = setInterval(loadData, 60000)
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)

      // 并行加载所有数据
      const [health, realtime, performance, trend, reasons] = await Promise.all([
        apiClient.get('/api/notification-monitoring/health-check'),
        apiClient.get('/api/notification-monitoring/realtime'),
        apiClient.get('/api/notification-monitoring/channel-performance'),
        apiClient.get('/api/notification-monitoring/daily-trend', {
          params: { days: 7 }
        }),
        apiClient.get('/api/notification-monitoring/failure-reasons'),
      ])

      setHealthStatus(health.data.data)
      setRealtimeStats(realtime.data.data)
      setChannelPerformance(performance.data.data)
      setDailyTrend(trend.data.data)
      setFailureReasons(reasons.data.data)
    } catch (error) {
      console.error('加载监控数据失败:', error)
      toast.error('加载监控数据失败')
    } finally {
      setLoading(false)
    }
  }

  const triggerHealthCheck = async () => {
    try {
      const response = await apiClient.post('/api/notification-monitoring/check-and-alert')
      const result = response.data.data

      if (result.alerts_triggered && result.alerts_triggered.length > 0) {
        toast.warning(`发现 ${result.alerts_triggered.length} 条异常告警`)
      } else {
        toast.success('系统运行正常')
      }

      await loadData()
    } catch (error) {
      toast.error('执行健康检查失败')
    }
  }

  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'healthy':
        return 'bg-green-500'
      case 'warning':
        return 'bg-yellow-500'
      case 'critical':
        return 'bg-red-500'
      default:
        return 'bg-gray-500'
    }
  }

  const getStatusIcon = (status?: string) => {
    switch (status) {
      case 'healthy':
        return <CheckCircle2 className="h-5 w-5 text-green-500" />
      case 'warning':
        return <AlertTriangle className="h-5 w-5 text-yellow-500" />
      case 'critical':
        return <XCircle className="h-5 w-5 text-red-500" />
      default:
        return <Activity className="h-5 w-5 text-gray-500" />
    }
  }

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8']

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">通知系统监控</h1>
          <p className="text-muted-foreground mt-1">
            实时监控通知发送状态、成功率和性能指标
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={loadData}
            disabled={loading}
          >
            <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            刷新
          </Button>
          <Button
            onClick={triggerHealthCheck}
          >
            <Activity className="mr-2 h-4 w-4" />
            执行健康检查
          </Button>
        </div>
      </div>

      {/* 健康状态概览 */}
      {healthStatus && (
        <Alert variant={healthStatus.status === 'healthy' ? 'default' : 'destructive'}>
          <div className="flex items-center gap-3">
            {getStatusIcon(healthStatus.status)}
            <div className="flex-1">
              <AlertTitle className="text-lg">
                系统状态: {healthStatus.status === 'healthy' ? '正常' : healthStatus.status === 'warning' ? '警告' : '严重'}
              </AlertTitle>
              <AlertDescription className="mt-2 space-y-1">
                <div className="flex gap-4 text-sm">
                  <span>24小时成功率: <strong>{healthStatus.success_rate_24h.toFixed(2)}%</strong></span>
                  <span>失败率: <strong>{healthStatus.failure_rate.toFixed(2)}%</strong></span>
                  <span>待发送: <strong>{healthStatus.pending_count}</strong></span>
                </div>
                {healthStatus.alerts && healthStatus.alerts.length > 0 && (
                  <div className="mt-2">
                    <strong>告警信息:</strong>
                    <ul className="list-disc list-inside mt-1">
                      {healthStatus.alerts.map((alert, idx) => (
                        <li key={idx}>{alert}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </AlertDescription>
            </div>
          </div>
        </Alert>
      )}

      {/* 实时统计卡片 */}
      {realtimeStats && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">24小时总计</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{realtimeStats.last_24h.total}</div>
              <p className="text-xs text-muted-foreground">
                成功 {realtimeStats.last_24h.sent} | 失败 {realtimeStats.last_24h.failed}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">成功率</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {realtimeStats.last_24h.success_rate.toFixed(1)}%
              </div>
              <p className="text-xs text-muted-foreground">
                最近 24 小时
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">最近1小时</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{realtimeStats.last_hour.total}</div>
              <p className="text-xs text-muted-foreground">
                成功 {realtimeStats.last_hour.sent} | 失败 {realtimeStats.last_hour.failed}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">待发送</CardTitle>
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{realtimeStats.pending_count}</div>
              <p className="text-xs text-muted-foreground">
                队列中等待发送
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 详细监控 Tabs */}
      <Tabs defaultValue="trend" className="space-y-4">
        <TabsList>
          <TabsTrigger value="trend">发送趋势</TabsTrigger>
          <TabsTrigger value="channels">渠道性能</TabsTrigger>
          <TabsTrigger value="failures">失败分析</TabsTrigger>
        </TabsList>

        {/* 发送趋势 */}
        <TabsContent value="trend" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>最近 7 天发送趋势</CardTitle>
              <CardDescription>每日发送总数和成功率</CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={dailyTrend}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip />
                  <Legend />
                  <Area
                    yAxisId="left"
                    type="monotone"
                    dataKey="total"
                    stackId="1"
                    stroke="#8884d8"
                    fill="#8884d8"
                    name="总数"
                  />
                  <Area
                    yAxisId="left"
                    type="monotone"
                    dataKey="failed"
                    stackId="1"
                    stroke="#ff8042"
                    fill="#ff8042"
                    name="失败"
                  />
                  <Line
                    yAxisId="right"
                    type="monotone"
                    dataKey="success_rate"
                    stroke="#00C49F"
                    name="成功率(%)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 渠道性能 */}
        <TabsContent value="channels" className="space-y-4">
          {channelPerformance && Object.entries(channelPerformance).map(([channel, stats]) => (
            <Card key={channel}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  {channel === 'email' && <Mail className="h-5 w-5" />}
                  {channel === 'telegram' && <MessageSquare className="h-5 w-5" />}
                  {channel === 'in_app' && <Activity className="h-5 w-5" />}
                  {channel.toUpperCase()} 渠道
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="grid gap-4 md:grid-cols-3">
                  <div>
                    <p className="text-sm text-muted-foreground">总发送</p>
                    <p className="text-2xl font-bold">{stats.total}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">成功率</p>
                    <p className="text-2xl font-bold">{stats.success_rate.toFixed(1)}%</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">平均送达时间</p>
                    <p className="text-2xl font-bold">{stats.avg_delivery_time.toFixed(1)}s</p>
                  </div>
                </div>

                {stats.failure_reasons && stats.failure_reasons.length > 0 && (
                  <div className="mt-4">
                    <p className="text-sm font-medium mb-2">失败原因 Top 5</p>
                    <div className="space-y-2">
                      {stats.failure_reasons.map((reason, idx) => (
                        <div key={idx} className="flex items-center justify-between text-sm">
                          <span className="text-muted-foreground">{reason.reason}</span>
                          <Badge variant="outline">{reason.count}</Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </TabsContent>

        {/* 失败分析 */}
        <TabsContent value="failures" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>失败原因统计</CardTitle>
              <CardDescription>最近 7 天失败原因分布</CardDescription>
            </CardHeader>
            <CardContent>
              {failureReasons && failureReasons.length > 0 ? (
                <div className="grid gap-4 md:grid-cols-2">
                  <ResponsiveContainer width="100%" height={300}>
                    <PieChart>
                      <Pie
                        data={failureReasons}
                        cx="50%"
                        cy="50%"
                        labelLine={false}
                        label={entry => `${entry.reason}: ${entry.percentage}%`}
                        outerRadius={80}
                        fill="#8884d8"
                        dataKey="count"
                      >
                        {failureReasons.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip />
                    </PieChart>
                  </ResponsiveContainer>

                  <div className="space-y-2">
                    {failureReasons.map((reason, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between p-3 border rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          <div
                            className="h-4 w-4 rounded"
                            style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                          />
                          <span className="text-sm">{reason.reason}</span>
                        </div>
                        <div className="text-right">
                          <p className="text-sm font-medium">{reason.count} 次</p>
                          <p className="text-xs text-muted-foreground">{reason.percentage}%</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="text-center text-muted-foreground py-8">
                  暂无失败记录
                </p>
              )}
            </CardContent>
          </Card>

          {/* 最近失败记录 */}
          {realtimeStats && realtimeStats.recent_failures && realtimeStats.recent_failures.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle>最近失败记录</CardTitle>
                <CardDescription>最新 10 条失败记录</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {realtimeStats.recent_failures.map((failure, idx) => (
                    <div key={idx} className="flex items-start gap-3 p-3 border rounded-lg">
                      <XCircle className="h-5 w-5 text-red-500 mt-0.5" />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{failure.channel}</Badge>
                          <span className="text-sm text-muted-foreground">
                            用户 {failure.user_id}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {new Date(failure.created_at).toLocaleString()}
                          </span>
                        </div>
                        <p className="text-sm font-medium mt-1">{failure.title}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {failure.failed_reason}
                        </p>
                        {failure.retry_count > 0 && (
                          <Badge variant="secondary" className="mt-2">
                            已重试 {failure.retry_count} 次
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
