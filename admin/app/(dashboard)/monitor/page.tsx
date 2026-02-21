/**
 * 系统监控页面
 *
 * 功能：
 * 1. 实时健康检查 - 每10秒自动刷新服务状态（数据库、Redis、核心服务、熔断器）
 * 2. 性能监控 - 显示数据库和Redis的响应时间，帮助快速识别性能问题
 * 3. 监控工具集成 - 提供Grafana和Prometheus的快速访问入口
 *
 * 架构说明：
 * - Admin监控页面：适合日常巡检和快速故障排查
 * - Grafana：适合详细的性能分析、历史趋势查看和容量规划
 * - Prometheus：适合原始指标查询和告警规则配置
 */
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
  Cpu,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  BarChart3,
  Zap,
  ExternalLink,
  LineChart
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

export default function MonitorPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)

  // Grafana 和 Prometheus 配置
  // 这些URL用于快速跳转到专业监控工具
  const GRAFANA_URL = 'http://localhost:3001'
  const GRAFANA_DASHBOARD_UID = 'stock-analysis-overview'

  useEffect(() => {
    loadMonitorData()

    // 自动刷新健康检查
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

  /**
   * 加载监控数据
   * 调用后端 /health 接口获取服务健康状态和性能指标
   */
  const loadMonitorData = async () => {
    try {
      setIsLoading(true)
      setError(null)

      const healthResponse = await apiClient.healthCheck()

      if (healthResponse) {
        setHealth(healthResponse as any)
      }

      setLastUpdate(new Date())
    } catch (err: any) {
      setError(err.message || '加载监控数据失败')
      console.error('Failed to load monitor data:', err)
    } finally {
      setIsLoading(false)
    }
  }

  // 打开 Grafana 完整仪表板
  const openGrafana = () => {
    window.open(`${GRAFANA_URL}/d/${GRAFANA_DASHBOARD_UID}`, '_blank')
  }

  // 打开 Prometheus
  const openPrometheus = () => {
    window.open('http://localhost:9090', '_blank')
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

  /**
   * 解析服务健康状态
   * 统一处理不同服务的健康检查响应格式
   * @param serviceCheck - 服务健康检查数据
   * @returns 统一的状态对象（包含状态、消息和响应时间）
   */
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
                系统监控
              </h1>
              <p className="text-gray-600 dark:text-gray-300 mt-2">
                实时查看系统健康状态和性能指标
              </p>
            </div>
            <div className="flex gap-3">
              <Button
                variant="outline"
                onClick={openPrometheus}
              >
                <BarChart3 className="h-4 w-4 mr-2" />
                Prometheus
                <ExternalLink className="h-3 w-3 ml-1" />
              </Button>
              <Button
                variant="default"
                onClick={openGrafana}
              >
                <LineChart className="h-4 w-4 mr-2" />
                Grafana 仪表板
                <ExternalLink className="h-3 w-3 ml-1" />
              </Button>
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

          {/* 监控工具链接 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                监控工具
              </CardTitle>
              <p className="text-sm text-muted-foreground mt-2">
                使用专业的监控工具查看详细的性能指标和系统状态
              </p>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Grafana 卡片 */}
                <Card className="border-2 border-blue-200 dark:border-blue-800 hover:border-blue-400 dark:hover:border-blue-600 transition-colors">
                  <CardContent className="pt-6">
                    <div className="flex items-start gap-4">
                      <div className="p-3 bg-blue-100 dark:bg-blue-900 rounded-lg">
                        <LineChart className="h-8 w-8 text-blue-600 dark:text-blue-400" />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold text-lg mb-2">Grafana 仪表板</h3>
                        <p className="text-sm text-muted-foreground mb-4">
                          可视化监控仪表板，提供丰富的图表和自定义查询功能
                        </p>
                        <ul className="text-sm space-y-1.5 mb-4 text-muted-foreground">
                          <li>• 请求速率和响应时间分析</li>
                          <li>• 缓存性能和数据库监控</li>
                          <li>• 自定义时间范围查询</li>
                          <li>• 告警规则配置</li>
                        </ul>
                        <Button onClick={openGrafana} className="w-full">
                          <LineChart className="h-4 w-4 mr-2" />
                          打开 Grafana
                          <ExternalLink className="h-3 w-3 ml-2" />
                        </Button>
                        <p className="text-xs text-muted-foreground mt-2 text-center">
                          默认账号: admin / admin123
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Prometheus 卡片 */}
                <Card className="border-2 border-orange-200 dark:border-orange-800 hover:border-orange-400 dark:hover:border-orange-600 transition-colors">
                  <CardContent className="pt-6">
                    <div className="flex items-start gap-4">
                      <div className="p-3 bg-orange-100 dark:bg-orange-900 rounded-lg">
                        <BarChart3 className="h-8 w-8 text-orange-600 dark:text-orange-400" />
                      </div>
                      <div className="flex-1">
                        <h3 className="font-semibold text-lg mb-2">Prometheus</h3>
                        <p className="text-sm text-muted-foreground mb-4">
                          强大的监控和告警系统，支持 PromQL 查询语言
                        </p>
                        <ul className="text-sm space-y-1.5 mb-4 text-muted-foreground">
                          <li>• 原始指标数据查看</li>
                          <li>• PromQL 查询语言</li>
                          <li>• 目标状态监控</li>
                          <li>• 规则评估和告警</li>
                        </ul>
                        <Button onClick={openPrometheus} variant="outline" className="w-full">
                          <BarChart3 className="h-4 w-4 mr-2" />
                          打开 Prometheus
                          <ExternalLink className="h-3 w-3 ml-2" />
                        </Button>
                        <p className="text-xs text-muted-foreground mt-2 text-center">
                          无需登录，直接访问
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* 快速链接 */}
              <div className="mt-6 p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
                <h4 className="font-medium mb-3 flex items-center gap-2">
                  <ExternalLink className="h-4 w-4" />
                  快速访问
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                  <a
                    href="http://localhost:3001/d/stock-analysis-overview"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
                  >
                    <LineChart className="h-4 w-4 text-blue-600" />
                    <span>Stock Analysis 仪表板</span>
                    <ExternalLink className="h-3 w-3 ml-auto" />
                  </a>
                  <a
                    href="http://localhost:9090/targets"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
                  >
                    <BarChart3 className="h-4 w-4 text-orange-600" />
                    <span>Prometheus 目标状态</span>
                    <ExternalLink className="h-3 w-3 ml-auto" />
                  </a>
                  <a
                    href="http://localhost:8000/metrics"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
                  >
                    <Server className="h-4 w-4 text-green-600" />
                    <span>Backend 原始指标</span>
                    <ExternalLink className="h-3 w-3 ml-auto" />
                  </a>
                  <a
                    href="http://localhost:9090/graph"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded"
                  >
                    <Activity className="h-4 w-4 text-purple-600" />
                    <span>Prometheus 查询</span>
                    <ExternalLink className="h-3 w-3 ml-auto" />
                  </a>
                </div>
              </div>
            </CardContent>
          </Card>

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

          {/* 监控说明 */}
          <Card className="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-950 dark:to-indigo-950 border-blue-200 dark:border-blue-800">
            <CardContent className="pt-6">
              <div className="flex items-start gap-3">
                <Activity className="h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <h3 className="font-semibold text-blue-900 dark:text-blue-200 mb-3 text-lg">
                    监控架构说明
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div>
                      <h4 className="font-medium text-blue-800 dark:text-blue-300 mb-2 text-sm">
                        健康检查（本页面）
                      </h4>
                      <ul className="text-sm text-blue-700 dark:text-blue-400 space-y-1.5">
                        <li>• 自动每 10 秒刷新服务状态</li>
                        <li>• 监控数据库、Redis、核心服务</li>
                        <li>• 显示响应时间和连接状态</li>
                        <li>• 适合快速巡检和故障排查</li>
                      </ul>
                    </div>
                    <div>
                      <h4 className="font-medium text-blue-800 dark:text-blue-300 mb-2 text-sm">
                        性能指标（Grafana）
                      </h4>
                      <ul className="text-sm text-blue-700 dark:text-blue-400 space-y-1.5">
                        <li>• 图表自动每 10 秒刷新数据</li>
                        <li>• 显示请求量、响应时间、错误率</li>
                        <li>• 支持自定义时间范围查询</li>
                        <li>• 适合性能分析和容量规划</li>
                      </ul>
                    </div>
                  </div>
                  <div className="mt-4 pt-4 border-t border-blue-200 dark:border-blue-800">
                    <p className="text-sm text-blue-700 dark:text-blue-400">
                      <strong>访问地址：</strong>
                      Grafana: <code className="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900 rounded">http://localhost:3001</code>
                      （默认账号：admin / admin123） |
                      Prometheus: <code className="px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900 rounded ml-2">http://localhost:9090</code>
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
  )
}
