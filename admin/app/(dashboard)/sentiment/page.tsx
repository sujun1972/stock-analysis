/**
 * 市场情绪页面
 *
 * 展示所有市场情绪相关的子菜单项
 */
'use client'

import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useRouter } from 'next/navigation'
import {
  Activity,
  Flame,
  ArrowUpCircle,
  TrendingUp,
  Sparkles,
  Clock,
  ArrowRight,
  ChartBar
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface SentimentItem {
  title: string
  description: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  color: string
  badge?: string
}

const sentimentItems: SentimentItem[] = [
  {
    title: '情绪数据',
    description: '市场整体情绪指标，包括涨跌分布、成交量、换手率等',
    href: '/sentiment/data',
    icon: ChartBar,
    color: 'text-blue-500'
  },
  {
    title: '龙虎榜',
    description: '游资和机构动向，营业部买卖数据分析',
    href: '/sentiment/dragon-tiger',
    icon: Flame,
    color: 'text-red-500',
    badge: '热门'
  },
  {
    title: '涨停板池',
    description: '今日涨停股票池，连板梯队，涨停原因分析',
    href: '/sentiment/limit-up',
    icon: ArrowUpCircle,
    color: 'text-green-500'
  },
  {
    title: '情绪周期',
    description: '市场情绪周期判断，赚钱效应指数计算',
    href: '/sentiment/cycle',
    icon: TrendingUp,
    color: 'text-orange-500'
  },
  {
    title: 'AI分析',
    description: '基于AI的市场情绪分析，热点题材挖掘',
    href: '/sentiment/ai-analysis',
    icon: Sparkles,
    color: 'text-purple-500',
    badge: 'AI'
  },
  {
    title: '盘前预期',
    description: '盘前市场预期分析，开盘策略推荐',
    href: '/sentiment/premarket',
    icon: Clock,
    color: 'text-cyan-500'
  }
]

export default function SentimentPage() {
  const router = useRouter()

  return (
    <div className="space-y-6">
      <PageHeader
        title="市场情绪"
        description="实时跟踪市场情绪变化，把握市场节奏"
      />

      {/* 实时指标卡片 */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>涨停家数</CardDescription>
            <CardTitle className="text-2xl text-red-500">68</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>跌停家数</CardDescription>
            <CardTitle className="text-2xl text-green-500">12</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>赚钱效应</CardDescription>
            <CardTitle className="text-2xl text-orange-500">72%</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>市场温度</CardDescription>
            <CardTitle className="text-2xl text-blue-500">偏热</CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* 功能导航卡片 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {sentimentItems.map((item) => {
          const Icon = item.icon
          return (
            <Card
              key={item.href}
              className="cursor-pointer hover:shadow-lg transition-all duration-200 hover:-translate-y-1 group relative"
              onClick={() => router.push(item.href)}
            >
              {item.badge && (
                <div className="absolute top-4 right-4">
                  <span className="px-2 py-1 text-xs font-medium bg-gradient-to-r from-purple-500 to-pink-500 text-white rounded-full">
                    {item.badge}
                  </span>
                </div>
              )}
              <CardHeader>
                <div className="flex items-start gap-4">
                  <div className={cn(
                    "p-3 rounded-lg bg-gray-50 dark:bg-gray-800 group-hover:scale-110 transition-transform",
                    item.color
                  )}>
                    <Icon className="h-6 w-6" />
                  </div>
                  <div className="space-y-1 flex-1">
                    <CardTitle className="text-base flex items-center gap-2">
                      {item.title}
                      <ArrowRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                    </CardTitle>
                    <CardDescription className="text-sm">
                      {item.description}
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
            </Card>
          )
        })}
      </div>

      <div className="mt-8 p-6 bg-muted/50 rounded-lg">
        <h3 className="text-sm font-medium mb-2">数据更新时间</h3>
        <p className="text-sm text-muted-foreground">
          市场情绪数据每5分钟自动更新，龙虎榜数据每日收盘后17:00更新。
        </p>
      </div>
    </div>
  )
}