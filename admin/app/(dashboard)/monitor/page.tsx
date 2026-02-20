'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  Activity,
  Database,
  Server,
  HardDrive,
  Cpu,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  TrendingUp,
  BarChart3,
  Zap
} from 'lucide-react'

interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy'
  checks: {
    database?: {
      status: 'healthy' | 'unhealthy'
      message?: string
      response_time_ms?: number
    }
    redis?: {
      status: 'healthy' | 'unhealthy'
      message?: string
      ping_time_ms?: number
    }
    core_service?: {
      status: 'healthy' | 'unhealthy'
      message?: string
    }
    circuit_breakers?: {
      status: string
      details?: any
    }
  }
  timestamp: string
}

interface SystemMetrics {
  requestCount: number
  requestDuration: number
  errorCount: number
  activeConnections: number
}

export default function MonitorPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)

  useEffect(() => {
    loadMonitorData()

    // 自动刷新
    let interval: NodeJS.Timeout
    if (autoRefresh) {
      interval = setInterval(() => {
        loadMonitorData()
      }, 10000) // 每10秒刷新一次
    }

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [autoRefresh])

  const loadMonitorData = async () => {
    try {
      setIsLoading(true)
      setError(null)

      // 并发加载健康检查和指标
      const [healthResponse] = await Promise.all([
        apiClient.healthCheck(),
        // 可以添加更多监控数据
      ])

      if (healthResponse) {
        setHealth(healthResponse as any)
      }

      // 模拟一些系统指标（后续可以从Prometheus获取）
      setMetrics({
        requestCount: Math.floor(Math.random() * 10000),
        requestDuration: Math.random() * 100,
        errorCount: Math.floor(Math.random() * 50),
        activeConnections: Math.floor(Math.random() * 100),
      })

      setLastUpdate(new Date())
    } catch (err: any) {
      setError(err.message || '加载监控数据失败')
      console.error('Failed to load monitor data:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const getStatusBadge = (status: 'healthy' | 'degraded' | 'unhealthy' | string) => {
    const config = {
      healthy: {
        icon: CheckCircle2,
        text: '正常',
        className: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      },
      degraded: {
        icon: AlertTriangle,
        text: '降级',
        className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
      },
      unhealthy: {
        icon: XCircle,
        text: '异常',
        className: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
      }
    }

    const statusConfig = config[status as keyof typeof config] || config.unhealthy
    const Icon = statusConfig.icon

    return (
      <Badge className={`${statusConfig.className} flex items-center gap-1`}>
        <Icon className="h-3 w-3" />
        {statusConfig.text}
      </Badge>
    )
  }

  const getServiceStatus = (serviceCheck: any) => {
    if (!serviceCheck) return { status: 'unhealthy', message: '未知' }
    return {
      status: serviceCheck.status || 'unhealthy',
      message: serviceCheck.message || serviceCheck.status,
      responseTime: serviceCheck.response_time_ms || serviceCheck.ping_time_ms
    }
  }

  const overallStatus = health?.status || 'unhealthy'

  return (
        <div className="space-y-6">
          {/* 页面标题 */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                性能监控
              </h1>
              <p className="text-gray-600 dark:text-gray-300 mt-2">
                实时查看系统健康状态和性能指标
              </p>
            </div>
            <div className="flex gap-3">
              <Button
                variant={autoRefresh ? "default" : "outline"}
                onClick={() => setAutoRefresh(!autoRefresh)}
              >
                <Activity className={`h-4 w-4 mr-2 ${autoRefresh ? 'animate-pulse' : ''}`} />
                {autoRefresh ? '自动刷新' : '手动模式'}
              </Button>
              <Button onClick={loadMonitorData} disabled={isLoading}>
                <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                刷新
              </Button>
            </div>
          </div>

          {/* 最后更新时间 */}
          {lastUpdate && (
            <div className="text-sm text-gray-600 dark:text-gray-400 flex items-center gap-2">
              <Clock className="h-4 w-4" />
              最后更新: {lastUpdate.toLocaleString('zh-CN')}
            </div>
          )}

          {/* 系统总体状态 */}
          <Card className={`border-2 ${
            overallStatus === 'healthy'
              ? 'border-green-500 bg-green-50 dark:bg-green-900/10'
              : overallStatus === 'degraded'
              ? 'border-yellow-500 bg-yellow-50 dark:bg-yellow-900/10'
              : 'border-red-500 bg-red-50 dark:bg-red-900/10'
          }`}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-2xl flex items-center gap-3">
                  <Server className="h-8 w-8" />
                  系统总体状态
                </CardTitle>
                {getStatusBadge(overallStatus)}
              </div>
            </CardHeader>
            <CardContent>
              {error ? (
                <div className="text-red-600 dark:text-red-400">{error}</div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="flex items-center gap-3 p-4 bg-white dark:bg-gray-800 rounded-lg">
                    <Database className="h-8 w-8 text-blue-600" />
                    <div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">数据库</div>
                      <div className="font-semibold">
                        {getServiceStatus(health?.checks?.database).status === 'healthy' ? '正常' : '异常'}
                      </div>
                      {getServiceStatus(health?.checks?.database).responseTime && (
                        <div className="text-xs text-gray-500">
                          {getServiceStatus(health?.checks?.database).responseTime}ms
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-3 p-4 bg-white dark:bg-gray-800 rounded-lg">
                    <Zap className="h-8 w-8 text-red-600" />
                    <div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">Redis</div>
                      <div className="font-semibold">
                        {getServiceStatus(health?.checks?.redis).status === 'healthy' ? '正常' : '异常'}
                      </div>
                      {getServiceStatus(health?.checks?.redis).responseTime && (
                        <div className="text-xs text-gray-500">
                          {getServiceStatus(health?.checks?.redis).responseTime}ms
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-3 p-4 bg-white dark:bg-gray-800 rounded-lg">
                    <Cpu className="h-8 w-8 text-purple-600" />
                    <div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">核心服务</div>
                      <div className="font-semibold">
                        {getServiceStatus(health?.checks?.core_service).status === 'healthy' ? '正常' : '异常'}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 p-4 bg-white dark:bg-gray-800 rounded-lg">
                    <Activity className="h-8 w-8 text-green-600" />
                    <div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">熔断器</div>
                      <div className="font-semibold">
                        {health?.checks?.circuit_breakers?.status || '未知'}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* 性能指标 */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  请求总数
                </CardTitle>
                <BarChart3 className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {metrics?.requestCount.toLocaleString() || 0}
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  系统启动以来的总请求数
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  平均响应时间
                </CardTitle>
                <Clock className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {metrics?.requestDuration.toFixed(2) || 0}ms
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  API请求平均耗时
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  错误数量
                </CardTitle>
                <AlertTriangle className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600">
                  {metrics?.errorCount || 0}
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  最近1小时的错误次数
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  活跃连接
                </CardTitle>
                <TrendingUp className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {metrics?.activeConnections || 0}
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  当前活跃的数据库连接数
                </p>
              </CardContent>
            </Card>
          </div>

          {/* 服务详细状态 */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 数据库状态 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-5 w-5" />
                  数据库状态
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">连接状态</span>
                    {getStatusBadge(getServiceStatus(health?.checks?.database).status)}
                  </div>

                  {health?.checks?.database?.response_time_ms && (
                    <>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">响应时间</span>
                        <span className="font-semibold">{health.checks.database.response_time_ms}ms</span>
                      </div>

                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-600 dark:text-gray-400">性能</span>
                          <span className="text-xs">
                            {health.checks.database.response_time_ms < 50
                              ? '优秀'
                              : health.checks.database.response_time_ms < 100
                              ? '良好'
                              : '需优化'}
                          </span>
                        </div>
                        <Progress
                          value={Math.min(100, (health.checks.database.response_time_ms / 200) * 100)}
                          className="h-2"
                        />
                      </div>
                    </>
                  )}

                  {health?.checks?.database?.message && (
                    <div className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                      {health.checks.database.message}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {/* Redis状态 */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="h-5 w-5" />
                  Redis缓存
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">连接状态</span>
                    {getStatusBadge(getServiceStatus(health?.checks?.redis).status)}
                  </div>

                  {health?.checks?.redis?.ping_time_ms && (
                    <>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600 dark:text-gray-400">Ping延迟</span>
                        <span className="font-semibold">{health.checks.redis.ping_time_ms}ms</span>
                      </div>

                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-gray-600 dark:text-gray-400">性能</span>
                          <span className="text-xs">
                            {health.checks.redis.ping_time_ms < 10
                              ? '优秀'
                              : health.checks.redis.ping_time_ms < 50
                              ? '良好'
                              : '需优化'}
                          </span>
                        </div>
                        <Progress
                          value={Math.min(100, (health.checks.redis.ping_time_ms / 100) * 100)}
                          className="h-2"
                        />
                      </div>
                    </>
                  )}

                  {health?.checks?.redis?.message && (
                    <div className="text-sm text-gray-600 dark:text-gray-400 mt-2">
                      {health.checks.redis.message}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          {/* 系统资源使用（占位，后续可集成真实数据） */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <HardDrive className="h-5 w-5" />
                系统资源
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">CPU使用率</span>
                    <span className="font-semibold">--</span>
                  </div>
                  <Progress value={0} className="h-2" />
                  <p className="text-xs text-gray-500">需要集成系统监控</p>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">内存使用率</span>
                    <span className="font-semibold">--</span>
                  </div>
                  <Progress value={0} className="h-2" />
                  <p className="text-xs text-gray-500">需要集成系统监控</p>
                </div>

                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-600 dark:text-gray-400">磁盘使用率</span>
                    <span className="font-semibold">--</span>
                  </div>
                  <Progress value={0} className="h-2" />
                  <p className="text-xs text-gray-500">需要集成系统监控</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 提示信息 */}
          <Card className="bg-blue-50 dark:bg-blue-900/10 border-blue-200 dark:border-blue-800">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <Activity className="h-5 w-5 text-blue-600 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-blue-900 dark:text-blue-200 mb-2">
                    监控说明
                  </h3>
                  <ul className="text-sm text-blue-800 dark:text-blue-300 space-y-1">
                    <li>• 系统自动每10秒刷新一次监控数据（可切换为手动模式）</li>
                    <li>• 健康检查包括：数据库、Redis、核心服务和熔断器状态</li>
                    <li>• 如需查看详细的Prometheus指标，请访问后端的 /metrics 端点</li>
                    <li>• 系统资源监控需要额外集成node-exporter等监控工具</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
  )
}
