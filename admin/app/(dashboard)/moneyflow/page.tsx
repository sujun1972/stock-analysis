'use client'

import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Activity,
  TrendingUp,
  BarChart3,
  LineChart,
  ArrowUpDown
} from 'lucide-react'
import Link from 'next/link'

const modules = [
  {
    title: '个股资金流向',
    description: '基于主动买卖单统计的个股资金流向，包含小单/中单/大单/特大单的买卖量和买卖额，数据来源 Tushare',
    icon: Activity,
    href: '/moneyflow/stock',
    color: 'text-blue-500'
  },
  {
    title: '个股资金流向（DC）',
    description: '东方财富个股资金流向，包含个股主力资金（超大单、大单、中单、小单）流入流出情况',
    icon: ArrowUpDown,
    href: '/moneyflow/stock-dc',
    color: 'text-orange-500'
  },
  {
    title: '板块资金流向（DC）',
    description: '东方财富板块资金流向，包含行业、概念、地域板块的主力资金流入流出情况',
    icon: BarChart3,
    href: '/moneyflow/ind-dc',
    color: 'text-purple-500'
  },
  {
    title: '大盘资金流向（DC）',
    description: '东方财富大盘资金流向，包含上证/深证指数及主力资金（超大单、大单、中单、小单）流入流出情况',
    icon: LineChart,
    href: '/moneyflow/mkt-dc',
    color: 'text-green-500'
  },
  {
    title: '沪深港通资金流向',
    description: '沪股通、深股通、港股通（上海）、港股通（深圳）的每日资金流向，数据来源 Tushare Pro',
    icon: TrendingUp,
    href: '/moneyflow/hsgt',
    color: 'text-red-500'
  },
]

export default function MoneyflowPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="资金流向"
        description="A股各维度资金流向数据，涵盖个股、板块、大盘及沪深港通"
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
