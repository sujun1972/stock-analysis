'use client'

import { PageHeader } from '@/components/common/PageHeader'
import { Button } from '@/components/ui/button'
import {
  Activity,
  RefreshCw,
  BarChart3,
  Clock,
  LineChart,
} from 'lucide-react'
import { useMonitorData } from './hooks'
import {
  OverallStatusCard,
  MonitoringToolsCard,
  ServiceDetailCards,
  MonitoringInfoCard,
} from './components'

export default function MonitorPage() {
  const {
    health,
    isLoading,
    error,
    lastUpdate,
    autoRefresh,
    setAutoRefresh,
    overallStatus,
    loadMonitorData,
    openGrafana,
    openPrometheus,
  } = useMonitorData()

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <PageHeader
        title="系统监控"
        description="实时查看系统健康状态和性能指标"
        actions={
          <>
            <div className="hidden lg:flex gap-2">
              <Button
                variant="outline"
                onClick={openPrometheus}
                size="sm"
              >
                <BarChart3 className="h-4 w-4 mr-2" />
                Prometheus
              </Button>
              <Button
                variant="default"
                onClick={openGrafana}
                size="sm"
              >
                <LineChart className="h-4 w-4 mr-2" />
                Grafana
              </Button>
              <Button
                variant={autoRefresh ? "default" : "outline"}
                onClick={() => setAutoRefresh(!autoRefresh)}
                size="sm"
              >
                <Activity className={`h-4 w-4 mr-2 ${autoRefresh ? 'animate-pulse' : ''}`} />
                {autoRefresh ? '自动' : '手动'}
              </Button>
              <Button onClick={loadMonitorData} disabled={isLoading} size="sm">
                <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                刷新
              </Button>
            </div>
            <div className="flex lg:hidden gap-2">
              <Button
                variant={autoRefresh ? "default" : "outline"}
                onClick={() => setAutoRefresh(!autoRefresh)}
                size="sm"
                className="flex-1"
              >
                <Activity className={`h-4 w-4 mr-2 ${autoRefresh ? 'animate-pulse' : ''}`} />
                {autoRefresh ? '自动' : '手动'}
              </Button>
              <Button onClick={loadMonitorData} disabled={isLoading} size="sm" className="flex-1">
                <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                刷新
              </Button>
            </div>
          </>
        }
      />

      {/* 最后更新时间 */}
      {lastUpdate && (
        <div className="text-sm text-gray-600 dark:text-gray-400 flex items-center gap-2">
          <Clock className="h-4 w-4" />
          最后更新: {lastUpdate.toLocaleString('zh-CN')}
        </div>
      )}

      {/* 系统总体状态 */}
      <OverallStatusCard
        health={health}
        overallStatus={overallStatus}
        error={error}
      />

      {/* 监控工具链接 */}
      <MonitoringToolsCard
        openGrafana={openGrafana}
        openPrometheus={openPrometheus}
      />

      {/* 服务详细状态 */}
      <ServiceDetailCards health={health} />

      {/* 监控说明 */}
      <MonitoringInfoCard />
    </div>
  )
}
