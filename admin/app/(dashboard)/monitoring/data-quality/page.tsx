"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Progress } from "@/components/ui/progress"
import { PageHeader } from "@/components/PageHeader"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  Legend
} from 'recharts'
import {
  AlertCircle,
  CheckCircle,
  XCircle,
  TrendingUp,
  TrendingDown,
  Download,
  RefreshCw,
  Activity,
  Database,
  AlertTriangle
} from "lucide-react"
import { format } from "date-fns"

interface QualityMetric {
  data_source: string
  total_records: number
  valid_records: number
  error_count: number
  warning_count: number
  completeness: number
  accuracy: number
  timeliness: number
  last_updated: string
}

interface HealthSummary {
  overall_status: "healthy" | "warning" | "critical"
  total_data_sources: number
  healthy_sources: number
  warning_sources: number
  critical_sources: number
  recommendations: string[]
}

interface QualityTrend {
  date: string
  completeness: number
  accuracy: number
  timeliness: number
}

interface Alert {
  id: number
  severity: "low" | "medium" | "high"
  data_source: string
  message: string
  created_at: string
  acknowledged: boolean
}

const COLORS = {
  healthy: "#10b981",
  warning: "#f59e0b",
  critical: "#ef4444",
  primary: "#3b82f6"
}

export default function DataQualityPage() {
  const [loading, setLoading] = useState(false)
  const [metrics, setMetrics] = useState<Record<string, QualityMetric>>({})
  const [healthSummary, setHealthSummary] = useState<HealthSummary | null>(null)
  const [trends, setTrends] = useState<Record<string, QualityTrend[]>>({})
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [selectedDataSource, setSelectedDataSource] = useState("all")
  const [selectedPeriod, setSelectedPeriod] = useState("7")

  // 获取实时指标
  const fetchMetrics = async () => {
    try {
      setLoading(true)
      const response = await fetch("/api/data-quality/real-time-metrics", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setMetrics(data)
      }
    } catch (error) {
      console.error("获取质量指标失败:", error)
    } finally {
      setLoading(false)
    }
  }

  // 获取健康摘要
  const fetchHealthSummary = async () => {
    try {
      const response = await fetch("/api/data-quality/health-summary", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setHealthSummary(data)
      }
    } catch (error) {
      console.error("获取健康摘要失败:", error)
    }
  }

  // 获取质量趋势
  const fetchTrends = async () => {
    try {
      const response = await fetch(`/api/data-quality/quality-trends?days=${selectedPeriod}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setTrends(data.trends)
      }
    } catch (error) {
      console.error("获取质量趋势失败:", error)
    }
  }

  // 获取活跃告警
  const fetchAlerts = async () => {
    try {
      const response = await fetch("/api/data-quality/alerts/active", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setAlerts(data)
      }
    } catch (error) {
      console.error("获取告警失败:", error)
    }
  }

  // 确认告警
  const acknowledgeAlert = async (alertId: number) => {
    try {
      const response = await fetch(`/api/data-quality/alerts/acknowledge/${alertId}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`
        }
      })
      if (response.ok) {
        fetchAlerts()
      }
    } catch (error) {
      console.error("确认告警失败:", error)
    }
  }

  // 导出报告
  const exportReport = async (format: "json" | "html") => {
    try {
      const response = await fetch(`/api/data-quality/daily-report?format=${format}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`
        }
      })
      if (response.ok) {
        const blob = await response.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = `quality-report-${new Date().toISOString().split("T")[0]}.${format}`
        a.click()
      }
    } catch (error) {
      console.error("导出报告失败:", error)
    }
  }

  useEffect(() => {
    fetchMetrics()
    fetchHealthSummary()
    fetchAlerts()
  }, [])

  useEffect(() => {
    fetchTrends()
  }, [selectedPeriod])

  // 准备饼图数据
  const getPieData = () => {
    if (!healthSummary) return []
    return [
      { name: "健康", value: healthSummary.healthy_sources, color: COLORS.healthy },
      { name: "警告", value: healthSummary.warning_sources, color: COLORS.warning },
      { name: "严重", value: healthSummary.critical_sources, color: COLORS.critical }
    ].filter(item => item.value > 0)
  }

  // 准备趋势图数据
  const getTrendData = () => {
    if (!selectedDataSource || selectedDataSource === "all" || !trends[selectedDataSource]) {
      // 聚合所有数据源的趋势
      const aggregated: Record<string, QualityTrend> = {}
      Object.values(trends).forEach(sourceTrends => {
        sourceTrends.forEach(trend => {
          if (!aggregated[trend.date]) {
            aggregated[trend.date] = {
              date: trend.date,
              completeness: 0,
              accuracy: 0,
              timeliness: 0
            }
          }
          aggregated[trend.date].completeness += trend.completeness
          aggregated[trend.date].accuracy += trend.accuracy
          aggregated[trend.date].timeliness += trend.timeliness
        })
      })

      const sourceCount = Object.keys(trends).length
      return Object.values(aggregated).map(trend => ({
        ...trend,
        completeness: trend.completeness / sourceCount,
        accuracy: trend.accuracy / sourceCount,
        timeliness: trend.timeliness / sourceCount
      }))
    }
    return trends[selectedDataSource]
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "healthy":
        return <Badge className="bg-green-500">健康</Badge>
      case "warning":
        return <Badge className="bg-yellow-500">警告</Badge>
      case "critical":
        return <Badge className="bg-red-500">严重</Badge>
      default:
        return <Badge>未知</Badge>
    }
  }

  const getAlertIcon = (severity: string) => {
    switch (severity) {
      case "high":
        return <XCircle className="h-4 w-4 text-red-500" />
      case "medium":
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />
      case "low":
        return <AlertCircle className="h-4 w-4 text-blue-500" />
      default:
        return <AlertCircle className="h-4 w-4" />
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="数据质量监控"
        description="实时监控数据质量指标，确保数据准确性和完整性"
        actions={
          <div className="flex gap-2">
            <Button variant="outline" size="sm" onClick={() => exportReport("json")}>
              <Download className="h-4 w-4 mr-1" />
              导出JSON
            </Button>
            <Button variant="outline" size="sm" onClick={() => exportReport("html")}>
              <Download className="h-4 w-4 mr-1" />
              导出HTML
            </Button>
            <Button size="sm" onClick={fetchMetrics} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
              刷新
            </Button>
          </div>
        }
      />

      {/* 健康状态摘要 */}
      {healthSummary && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>系统健康状态</span>
              {getStatusBadge(healthSummary.overall_status)}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-6 md:grid-cols-2">
              <div>
                <div className="grid grid-cols-3 gap-4 mb-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-500">
                      {healthSummary.healthy_sources}
                    </div>
                    <div className="text-xs text-muted-foreground">健康</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-yellow-500">
                      {healthSummary.warning_sources}
                    </div>
                    <div className="text-xs text-muted-foreground">警告</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-red-500">
                      {healthSummary.critical_sources}
                    </div>
                    <div className="text-xs text-muted-foreground">严重</div>
                  </div>
                </div>

                {healthSummary.recommendations.length > 0 && (
                  <div className="space-y-2">
                    <div className="text-sm font-medium">建议：</div>
                    <ul className="text-sm text-muted-foreground space-y-1">
                      {healthSummary.recommendations.map((rec, idx) => (
                        <li key={idx} className="flex items-start">
                          <span className="mr-2">•</span>
                          <span>{rec}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>

              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={getPieData()}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                      label
                    >
                      {getPieData().map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* 质量趋势 */}
      <Card>
        <CardHeader>
          <CardTitle>质量趋势</CardTitle>
          <div className="flex gap-4 mt-4">
            <Select value={selectedDataSource} onValueChange={setSelectedDataSource}>
              <SelectTrigger className="w-48">
                <SelectValue placeholder="选择数据源" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">所有数据源</SelectItem>
                {Object.keys(metrics).map(source => (
                  <SelectItem key={source} value={source}>
                    {source}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={selectedPeriod} onValueChange={setSelectedPeriod}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">7天</SelectItem>
                <SelectItem value="14">14天</SelectItem>
                <SelectItem value="30">30天</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          <div className="h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={getTrendData()}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis
                  dataKey="date"
                  tickFormatter={(value) => format(new Date(value), "MM-dd")}
                />
                <YAxis domain={[0, 100]} />
                <Tooltip />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="completeness"
                  stroke={COLORS.healthy}
                  name="完整性"
                  strokeWidth={2}
                />
                <Line
                  type="monotone"
                  dataKey="accuracy"
                  stroke={COLORS.primary}
                  name="准确性"
                  strokeWidth={2}
                />
                <Line
                  type="monotone"
                  dataKey="timeliness"
                  stroke={COLORS.warning}
                  name="及时性"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* 数据源指标 */}
      <Card>
        <CardHeader>
          <CardTitle>数据源质量指标</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {Object.entries(metrics).map(([source, metric]) => (
              <Card key={source}>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium">
                    {source}
                  </CardTitle>
                  <CardDescription className="text-xs">
                    更新时间: {format(new Date(metric.last_updated), "MM-dd HH:mm")}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">记录总数</span>
                    <span className="font-medium">{metric.total_records.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">有效记录</span>
                    <span className="font-medium text-green-600">
                      {metric.valid_records.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">错误数</span>
                    <span className="font-medium text-red-600">
                      {metric.error_count}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">警告数</span>
                    <span className="font-medium text-yellow-600">
                      {metric.warning_count}
                    </span>
                  </div>

                  <div className="space-y-2 pt-2 border-t">
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span>完整性</span>
                        <span>{metric.completeness}%</span>
                      </div>
                      <Progress value={metric.completeness} className="h-1" />
                    </div>
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span>准确性</span>
                        <span>{metric.accuracy}%</span>
                      </div>
                      <Progress value={metric.accuracy} className="h-1" />
                    </div>
                    <div className="space-y-1">
                      <div className="flex justify-between text-xs">
                        <span>及时性</span>
                        <span>{metric.timeliness}%</span>
                      </div>
                      <Progress value={metric.timeliness} className="h-1" />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 活跃告警 */}
      {alerts.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>活跃告警</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {alerts.map(alert => (
                <Alert key={alert.id}>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {getAlertIcon(alert.severity)}
                      <div>
                        <AlertTitle className="text-sm">
                          {alert.data_source}
                        </AlertTitle>
                        <AlertDescription className="text-xs">
                          {alert.message}
                          <div className="text-xs text-muted-foreground mt-1">
                            {format(new Date(alert.created_at), "yyyy-MM-dd HH:mm")}
                          </div>
                        </AlertDescription>
                      </div>
                    </div>
                    {!alert.acknowledged && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => acknowledgeAlert(alert.id)}
                      >
                        确认
                      </Button>
                    )}
                  </div>
                </Alert>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}