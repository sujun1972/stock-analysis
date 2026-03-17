/**
 * 日志管理页面
 *
 * 展示所有日志相关的子菜单项
 */
'use client'

import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useRouter } from 'next/navigation'
import {
  ScrollText,
  Brain,
  ArrowRight,
  FileText,
  AlertTriangle,
  Info,
  Bug
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { Progress } from '@/components/ui/progress'

interface LogItem {
  title: string
  description: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  color: string
  stats?: {
    today: number
    total: number
    growth: number
  }
}

const logItems: LogItem[] = [
  {
    title: '系统日志',
    description: '系统运行日志，包括错误、警告、调试信息等',
    href: '/logs/system',
    icon: ScrollText,
    color: 'text-blue-500',
    stats: {
      today: 12456,
      total: 5234567,
      growth: 12.5
    }
  },
  {
    title: 'LLM调用日志',
    description: '大语言模型调用记录，Token使用统计，响应分析',
    href: '/logs/llm-calls',
    icon: Brain,
    color: 'text-purple-500',
    stats: {
      today: 856,
      total: 123456,
      growth: -5.2
    }
  }
]

// 日志级别统计组件
const LogLevelStats = () => {
  const levels = [
    { name: 'ERROR', count: 23, color: 'bg-red-500', percentage: 2 },
    { name: 'WARN', count: 156, color: 'bg-yellow-500', percentage: 8 },
    { name: 'INFO', count: 1834, color: 'bg-blue-500', percentage: 45 },
    { name: 'DEBUG', count: 2456, color: 'bg-gray-500', percentage: 45 }
  ]

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">今日日志级别分布</CardTitle>
        <CardDescription>最近24小时</CardDescription>
      </CardHeader>
      <div className="px-6 pb-6 space-y-3">
        {levels.map((level) => (
          <div key={level.name} className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">{level.name}</span>
              <span className="text-muted-foreground">{level.count}</span>
            </div>
            <Progress value={level.percentage} className="h-2" />
          </div>
        ))}
      </div>
    </Card>
  )
}

// 磁盘使用情况组件
const DiskUsage = () => {
  const used = 45.6
  const total = 100
  const percentage = (used / total) * 100

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">日志存储空间</CardTitle>
        <CardDescription>磁盘使用情况</CardDescription>
      </CardHeader>
      <div className="px-6 pb-6">
        <div className="relative w-32 h-32 mx-auto">
          <svg className="w-32 h-32 transform -rotate-90">
            <circle
              cx="64"
              cy="64"
              r="56"
              stroke="currentColor"
              strokeWidth="12"
              fill="none"
              className="text-gray-200 dark:text-gray-700"
            />
            <circle
              cx="64"
              cy="64"
              r="56"
              stroke="currentColor"
              strokeWidth="12"
              fill="none"
              strokeDasharray={`${2 * Math.PI * 56}`}
              strokeDashoffset={`${2 * Math.PI * 56 * (1 - percentage / 100)}`}
              className="text-blue-500 transition-all duration-300"
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="text-center">
              <div className="text-2xl font-bold">{percentage.toFixed(1)}%</div>
              <div className="text-xs text-muted-foreground">{used}GB / {total}GB</div>
            </div>
          </div>
        </div>
        <div className="mt-4 text-center">
          <button className="text-sm text-blue-500 hover:underline">
            清理旧日志
          </button>
        </div>
      </div>
    </Card>
  )
}

export default function LogsPage() {
  const router = useRouter()

  return (
    <div className="space-y-6">
      <PageHeader
        title="日志管理"
        description="查看和分析系统运行日志"
      />

      {/* 统计概览 */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-red-500" />
              <CardDescription>错误日志</CardDescription>
            </div>
            <CardTitle className="text-2xl">23</CardTitle>
            <p className="text-xs text-muted-foreground">较昨日 +5</p>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <Info className="h-4 w-4 text-blue-500" />
              <CardDescription>今日日志总数</CardDescription>
            </div>
            <CardTitle className="text-2xl">13,312</CardTitle>
            <p className="text-xs text-muted-foreground">较昨日 +12.5%</p>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center gap-2">
              <Bug className="h-4 w-4 text-yellow-500" />
              <CardDescription>待处理警告</CardDescription>
            </div>
            <CardTitle className="text-2xl">156</CardTitle>
            <p className="text-xs text-muted-foreground">需要关注</p>
          </CardHeader>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* 日志类型卡片 */}
        <div className="lg:col-span-2 space-y-4">
          {logItems.map((item) => {
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
                        {item.stats && (
                          <div className="flex items-center gap-6 text-sm">
                            <div>
                              <span className="text-muted-foreground">今日: </span>
                              <span className="font-medium">{item.stats.today.toLocaleString()}</span>
                            </div>
                            <div>
                              <span className="text-muted-foreground">总计: </span>
                              <span className="font-medium">{item.stats.total.toLocaleString()}</span>
                            </div>
                            <div className={cn(
                              "flex items-center gap-1",
                              item.stats.growth > 0 ? "text-red-500" : "text-green-500"
                            )}>
                              <span>{item.stats.growth > 0 ? "↑" : "↓"}</span>
                              <span>{Math.abs(item.stats.growth)}%</span>
                            </div>
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

        {/* 右侧统计 */}
        <div className="space-y-4">
          <LogLevelStats />
          <DiskUsage />
        </div>
      </div>

      <div className="mt-8 p-6 bg-muted/50 rounded-lg">
        <h3 className="text-sm font-medium mb-2">日志保留策略</h3>
        <ul className="text-sm text-muted-foreground space-y-1">
          <li>• 系统日志保留30天，之后自动归档</li>
          <li>• LLM调用日志保留90天，用于成本分析</li>
          <li>• 错误日志永久保留，定期人工审核</li>
        </ul>
      </div>
    </div>
  )
}