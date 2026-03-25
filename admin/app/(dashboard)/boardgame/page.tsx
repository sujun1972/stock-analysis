'use client'

import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Flame,
  Building2,
  TrendingUp,
  BarChart3,
  Layers,
  LineChart
} from 'lucide-react'
import Link from 'next/link'

const modules = [
  {
    title: '龙虎榜每日明细',
    description: '龙虎榜每日交易明细',
    icon: Flame,
    href: '/boardgame/top-list',
    color: 'text-orange-500'
  },
  {
    title: '龙虎榜机构明细',
    description: '龙虎榜机构成交明细',
    icon: Building2,
    href: '/boardgame/top-inst',
    color: 'text-blue-600'
  },
  {
    title: '涨跌停列表',
    description: '获取A股每日涨跌停、炸板数据情况，数据从2020年开始（不提供ST股票的统计）',
    icon: TrendingUp,
    href: '/boardgame/limit-list',
    color: 'text-red-500'
  },
  {
    title: '连板天梯',
    description: '获取每天连板个数晋级的股票，可以分析出每天连续涨停进阶个数，判断强势热度',
    icon: TrendingUp,
    href: '/boardgame/limit-step',
    color: 'text-red-600'
  },
  {
    title: '最强板块统计',
    description: '获取每天涨停股票最多最强的概念板块，可以分析强势板块的轮动，判断资金动向',
    icon: TrendingUp,
    href: '/boardgame/limit-cpt',
    color: 'text-purple-600'
  },
  {
    title: '东方财富概念板块',
    description: '获取东方财富每个交易日的概念板块数据，支持按日期查询',
    icon: BarChart3,
    href: '/boardgame/dc-index',
    color: 'text-green-600'
  },
  {
    title: '东方财富板块成分',
    description: '获取东方财富板块每日成分数据，可以根据概念板块代码和交易日期，获取历史成分',
    icon: Layers,
    href: '/boardgame/dc-member',
    color: 'text-green-500'
  },
  {
    title: '东财概念板块行情',
    description: '获取东财概念板块、行业指数板块、地域板块行情数据，历史数据开始于2020年',
    icon: LineChart,
    href: '/boardgame/dc-daily',
    color: 'text-teal-600'
  },
]

export default function BoardGamePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="打板专题"
        description="打板相关数据和分析工具"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {modules.map((module) => {
          const Icon = module.icon
          return (
            <Link key={module.href} href={module.href}>
              <Card className="h-full hover:shadow-lg transition-shadow cursor-pointer">
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg bg-gray-100 dark:bg-gray-800 ${module.color}`}>
                      <Icon className="h-6 w-6" />
                    </div>
                    <CardTitle className="text-lg">{module.title}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <CardDescription>{module.description}</CardDescription>
                </CardContent>
              </Card>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
