/**
 * 系统监控页面
 *
 * 展示所有监控相关的子菜单项
 */
'use client'

import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useRouter } from 'next/navigation'
import {
  Activity,
  Bell,
  ArrowRight,
  Server,
  Cpu,
  HardDrive,
  Network,
  TrendingUp,
  AlertTriangle
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Progress } from '@/components/ui/progress'

interface MonitorItem {
  title: string
  description: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  color: string
  metrics?: {
    current: string
    status: 'healthy' | 'warning' | 'critical'
  }
}

const monitorItems: MonitorItem[] = [
  {
    title: '性能监控',
    description: 'CPU、内存、磁盘、网络等系统资源监控',
    href: '/monitoring/performance',
    icon: Activity,
    color: 'text-green-500',
    metrics: {
      current: '系统正常',
      status: 'healthy'
    }
  },
  {
    title: '通知监控',
    description: '通知发送状态、失败重试、渠道健康度监控',
    href: '/monitoring/notifications',
    icon: Bell,
    color: 'text-blue-500',
    metrics: {
      current: '3个待发送',
      status: 'warning'
    }
  }
]

// 实时指标卡片组件
const MetricCard = ({
  title,
  value,
  unit,
  percentage,
  icon: Icon,
  color
}: {
  title: string
  value: string | number
  unit?: string
  percentage: number
  icon: React.ComponentType<{ className?: string }>
  color: string
}) => {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <CardDescription className="flex items-center gap-2">
              <Icon className={cn("h-4 w-4", color)} />
              {title}
            </CardDescription>
            <CardTitle className="text-2xl">
              {value}{unit && <span className="text-lg text-muted-foreground ml-1">{unit}</span>}
            </CardTitle>
          </div>
          <div className="text-right">
            <Progress value={percentage} className="w-16 h-2" />
            <p className="text-xs text-muted-foreground mt-1">{percentage}%</p>
          </div>
        </div>
      </CardHeader>
    </Card>
  )
}

// 服务状态组件
const ServiceStatus = () => {
  const services = [
    { name: 'API服务', status: 'running', uptime: '15天3小时' },
    { name: '数据库', status: 'running', uptime: '30天12小时' },
    { name: '消息队列', status: 'running', uptime: '7天8小时' },
    { name: '缓存服务', status: 'warning', uptime: '2天5小时' },
    { name: '定时任务', status: 'running', uptime: '10天0小时' }
  ]

  const getStatusColor = (status: string) => {
    switch(status) {
      case 'running': return 'bg-green-500'
      case 'warning': return 'bg-yellow-500'
      case 'stopped': return 'bg-red-500'
      default: return 'bg-gray-500'
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">服务状态</CardTitle>
        <CardDescription>核心服务运行状况</CardDescription>
      </CardHeader>
      <div className="px-6 pb-6 space-y-3">
        {services.map((service) => (
          <div key={service.name} className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={cn("w-2 h-2 rounded-full animate-pulse", getStatusColor(service.status))} />
              <span className="text-sm font-medium">{service.name}</span>
            </div>
            <span className="text-xs text-muted-foreground">运行时长: {service.uptime}</span>
          </div>
        ))}
      </div>
    </Card>
  )
}

// 告警信息组件
const AlertsInfo = () => {
  const alerts = [
    { level: 'critical', message: '磁盘空间即将耗尽 (剩余8%)', time: '5分钟前' },
    { level: 'warning', message: '内存使用率超过80%', time: '15分钟前' },
    { level: 'info', message: 'API响应时间略有增加', time: '1小时前' }
  ]

  const getLevelIcon = (level: string) => {
    switch(level) {
      case 'critical': return { icon: AlertTriangle, color: 'text-red-500' }
      case 'warning': return { icon: AlertTriangle, color: 'text-yellow-500' }
      default: return { icon: AlertTriangle, color: 'text-blue-500' }
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">最新告警</CardTitle>
        <CardDescription>需要关注的系统事件</CardDescription>
      </CardHeader>
      <div className="px-6 pb-6 space-y-3">
        {alerts.map((alert, index) => {
          const { icon: Icon, color } = getLevelIcon(alert.level)
          return (
            <div key={index} className="flex items-start gap-3">
              <Icon className={cn("h-4 w-4 mt-0.5", color)} />
              <div className="flex-1 space-y-1">
                <p className="text-sm">{alert.message}</p>
                <p className="text-xs text-muted-foreground">{alert.time}</p>
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}

export default function MonitoringPage() {
  const router = useRouter()

  return (
    <div className="space-y-6">
      <PageHeader
        title="系统监控"
        description="实时监控系统运行状态和性能指标"
      />

      {/* 实时指标 */}
      <div className="grid gap-4 md:grid-cols-4">
        <MetricCard
          title="CPU使用率"
          value={45}
          unit="%"
          percentage={45}
          icon={Cpu}
          color="text-blue-500"
        />
        <MetricCard
          title="内存使用"
          value="12.5"
          unit="GB"
          percentage={78}
          icon={Server}
          color="text-green-500"
        />
        <MetricCard
          title="磁盘使用"
          value="456"
          unit="GB"
          percentage={65}
          icon={HardDrive}
          color="text-orange-500"
        />
        <MetricCard
          title="网络流量"
          value="1.2"
          unit="Gbps"
          percentage={30}
          icon={Network}
          color="text-purple-500"
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* 监控功能卡片 */}
        <div className="lg:col-span-2 space-y-4">
          {monitorItems.map((item) => {
            const Icon = item.icon
            return (
              <Card
                key={item.href}
                className="cursor-pointer hover:shadow-lg transition-all duration-200 group"
                onClick={() => router.push(item.href)}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-start gap-4 flex-1">
                      <div className={cn(
                        "p-3 rounded-lg bg-gray-50 dark:bg-gray-800 group-hover:scale-110 transition-transform",
                        item.color
                      )}>
                        <Icon className="h-6 w-6" />
                      </div>
                      <div className="space-y-2 flex-1">
                        <CardTitle className="text-base flex items-center gap-2">
                          {item.title}
                          <ArrowRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </CardTitle>
                        <CardDescription className="text-sm">
                          {item.description}
                        </CardDescription>
                        {item.metrics && (
                          <div className="flex items-center gap-2">
                            <span className={cn(
                              "inline-flex items-center px-2 py-1 rounded-full text-xs font-medium",
                              item.metrics.status === 'healthy' && "bg-green-100 text-green-700",
                              item.metrics.status === 'warning' && "bg-yellow-100 text-yellow-700",
                              item.metrics.status === 'critical' && "bg-red-100 text-red-700"
                            )}>
                              {item.metrics.current}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </CardHeader>
              </Card>
            )
          })}

          {/* 性能图表预览 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center justify-between">
                系统负载趋势
                <span className="text-xs font-normal text-muted-foreground">最近1小时</span>
              </CardTitle>
            </CardHeader>
            <div className="px-6 pb-6">
              <div className="h-32 flex items-end justify-between gap-1">
                {Array.from({ length: 20 }, (_, i) => {
                  const height = Math.random() * 100
                  return (
                    <div
                      key={i}
                      className="flex-1 bg-gradient-to-t from-blue-500 to-blue-300 rounded-t"
                      style={{ height: `${height}%` }}
                    />
                  )
                })}
              </div>
            </div>
          </Card>
        </div>

        {/* 右侧状态信息 */}
        <div className="space-y-4">
          <ServiceStatus />
          <AlertsInfo />
        </div>
      </div>

      <div className="mt-8 p-6 bg-muted/50 rounded-lg">
        <h3 className="text-sm font-medium mb-2">监控说明</h3>
        <ul className="text-sm text-muted-foreground space-y-1">
          <li>• 系统指标每5秒自动刷新</li>
          <li>• 告警会通过配置的渠道实时推送</li>
          <li>• 历史数据保留7天，可导出分析</li>
        </ul>
      </div>
    </div>
  )
}