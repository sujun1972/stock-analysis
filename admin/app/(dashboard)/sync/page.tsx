/**
 * 数据同步页面
 *
 * 展示所有数据同步相关的子菜单项
 */
'use client'

import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useRouter } from 'next/navigation'
import {
  RefreshCw,
  PackagePlus,
  TrendingUp,
  ArrowRight,
  CheckCircle,
  AlertCircle,
  Clock,
  Activity
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'

interface SyncItem {
  title: string
  description: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  color: string
  status?: 'running' | 'idle' | 'error'
  lastRun?: string
}

const syncItems: SyncItem[] = [
  {
    title: '数据初始化',
    description: '初始化系统基础数据，包括股票列表、行业分类等',
    href: '/sync/initialize',
    icon: RefreshCw,
    color: 'text-blue-500',
    status: 'idle',
    lastRun: '2024-03-17 09:00:00'
  },
  {
    title: '新股列表同步',
    description: '同步最新上市的股票信息，更新股票池',
    href: '/sync/new-stocks',
    icon: PackagePlus,
    color: 'text-green-500',
    status: 'idle',
    lastRun: '2024-03-17 06:00:00'
  },
  {
    title: '实时行情同步',
    description: '实时同步股票行情数据，包括价格、成交量等',
    href: '/sync/realtime',
    icon: TrendingUp,
    color: 'text-purple-500',
    status: 'running',
    lastRun: '实时运行中'
  }
]

const StatusBadge = ({ status }: { status?: string }) => {
  if (!status) return null

  const statusConfig = {
    running: { label: '运行中', variant: 'default' as const, Icon: Activity },
    idle: { label: '空闲', variant: 'secondary' as const, Icon: CheckCircle },
    error: { label: '错误', variant: 'destructive' as const, Icon: AlertCircle }
  }

  const config = statusConfig[status as keyof typeof statusConfig]
  if (!config) return null

  const { Icon } = config

  return (
    <Badge variant={config.variant} className="gap-1">
      <Icon className="h-3 w-3" />
      {config.label}
    </Badge>
  )
}

export default function SyncPage() {
  const router = useRouter()

  return (
    <div className="space-y-6">
      <PageHeader
        title="数据同步"
        description="管理和监控各类数据同步任务"
      />

      {/* 同步状态概览 */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>今日同步次数</CardDescription>
            <CardTitle className="text-2xl">1,234</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>活跃任务</CardDescription>
            <CardTitle className="text-2xl text-green-500">3</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>失败任务</CardDescription>
            <CardTitle className="text-2xl text-red-500">0</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>数据延迟</CardDescription>
            <CardTitle className="text-2xl text-blue-500">&lt;1s</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* 同步任务卡片 */}
      <div className="grid gap-4 md:grid-cols-2">
        {syncItems.map((item) => {
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
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-base flex items-center gap-2">
                          {item.title}
                          <ArrowRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                        </CardTitle>
                        <StatusBadge status={item.status} />
                      </div>
                      <CardDescription className="text-sm">
                        {item.description}
                      </CardDescription>
                      {item.lastRun && (
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          <span>最后运行: {item.lastRun}</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </CardHeader>
            </Card>
          )
        })}
      </div>

      {/* 快速操作 */}
      <Card>
        <CardHeader>
          <CardTitle>快速操作</CardTitle>
          <CardDescription>常用的批量同步操作</CardDescription>
        </CardHeader>
        <div className="p-6 pt-0 space-x-4">
          <button className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors">
            全量同步
          </button>
          <button className="px-4 py-2 text-sm font-medium bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/80 transition-colors">
            增量同步
          </button>
          <button className="px-4 py-2 text-sm font-medium border border-input rounded-lg hover:bg-accent transition-colors">
            停止所有任务
          </button>
        </div>
      </Card>

      <div className="mt-8 p-6 bg-muted/50 rounded-lg">
        <h3 className="text-sm font-medium mb-2">注意事项</h3>
        <ul className="text-sm text-muted-foreground space-y-1">
          <li>• 数据初始化会清空现有数据，请谨慎操作</li>
          <li>• 实时行情同步会消耗较多系统资源</li>
          <li>• 建议在非交易时间进行大批量数据同步</li>
        </ul>
      </div>
    </div>
  )
}