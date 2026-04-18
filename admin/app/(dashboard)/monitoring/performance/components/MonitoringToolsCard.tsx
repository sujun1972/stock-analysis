'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Activity,
  Server,
  BarChart3,
  ExternalLink,
  LineChart,
} from 'lucide-react'

interface MonitoringToolsCardProps {
  openGrafana: () => void
  openPrometheus: () => void
}

export const MonitoringToolsCard = ({ openGrafana, openPrometheus }: MonitoringToolsCardProps) => {
  return (
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
              <div className="flex flex-col sm:flex-row items-start gap-4">
                <div className="p-3 bg-blue-100 dark:bg-blue-900 rounded-lg shrink-0">
                  <LineChart className="h-8 w-8 text-blue-600 dark:text-blue-400" />
                </div>
                <div className="flex-1 w-full min-w-0">
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
              <div className="flex flex-col sm:flex-row items-start gap-4">
                <div className="p-3 bg-orange-100 dark:bg-orange-900 rounded-lg shrink-0">
                  <BarChart3 className="h-8 w-8 text-orange-600 dark:text-orange-400" />
                </div>
                <div className="flex-1 w-full min-w-0">
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
        <div className="mt-6 p-3 sm:p-4 bg-gray-50 dark:bg-gray-900 rounded-lg">
          <h4 className="font-medium mb-3 flex items-center gap-2 text-sm sm:text-base">
            <ExternalLink className="h-4 w-4" />
            快速访问
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs sm:text-sm">
            <a
              href="http://localhost:3001/d/stock-analysis-overview"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded min-w-0"
            >
              <LineChart className="h-4 w-4 text-blue-600 shrink-0" />
              <span className="truncate">Stock Analysis 仪表板</span>
              <ExternalLink className="h-3 w-3 ml-auto shrink-0" />
            </a>
            <a
              href="http://localhost:9090/targets"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded min-w-0"
            >
              <BarChart3 className="h-4 w-4 text-orange-600 shrink-0" />
              <span className="truncate">Prometheus 目标状态</span>
              <ExternalLink className="h-3 w-3 ml-auto shrink-0" />
            </a>
            <a
              href="http://localhost:8000/metrics"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded min-w-0"
            >
              <Server className="h-4 w-4 text-green-600 shrink-0" />
              <span className="truncate">Backend 原始指标</span>
              <ExternalLink className="h-3 w-3 ml-auto shrink-0" />
            </a>
            <a
              href="http://localhost:9090/graph"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded min-w-0"
            >
              <Activity className="h-4 w-4 text-purple-600 shrink-0" />
              <span className="truncate">Prometheus 查询</span>
              <ExternalLink className="h-3 w-3 ml-auto shrink-0" />
            </a>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
