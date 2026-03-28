'use client'

import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  TrendingUp,
  BarChart3,
  PieChart,
  Database,
  Clock,
  Activity,
  Users,
} from 'lucide-react'
import Link from 'next/link'

const modules = [
  {
    title: '卖方盈利预测',
    description: '券商研报盈利预测、评级、目标价等数据（6000积分/次，单次最大1000行）',
    icon: TrendingUp,
    href: '/features/report-rc',
    color: 'text-blue-500'
  },
  {
    title: '每日筹码及胜率',
    description: '每日获利比例、成本分布、获利盘/亏损盘比例（2000积分/次）',
    icon: BarChart3,
    href: '/features/cyq-perf',
    color: 'text-orange-500'
  },
  {
    title: '每日筹码分布',
    description: '筹码价格-持仓比例分布数据（2000积分/次，单次最大1000行）',
    icon: PieChart,
    href: '/features/cyq-chips',
    color: 'text-green-500'
  },
  {
    title: '中央结算系统持股汇总',
    description: '港股通持股数量、持股比例等汇总数据（5000积分/次）',
    icon: Database,
    href: '/features/ccass-hold',
    color: 'text-purple-500'
  },
  {
    title: '中央结算系统持股明细',
    description: 'CCASS参与者持股明细，机构席位持股数据（8000积分/次）',
    icon: Database,
    href: '/features/ccass-hold-detail',
    color: 'text-indigo-500'
  },
  {
    title: '北向资金持股',
    description: '沪深港股通持股明细，北向资金持股情况（2000积分/次，2024年8月起季度披露）',
    icon: TrendingUp,
    href: '/features/hk-hold',
    color: 'text-red-500'
  },
  {
    title: '股票开盘集合竞价',
    description: '开盘9:30集合竞价数据（需要股票分钟权限，每次最大10000行）',
    icon: Clock,
    href: '/features/stk-auction-o',
    color: 'text-yellow-500'
  },
  {
    title: '股票收盘集合竞价',
    description: '收盘15:00集合竞价数据（需要股票分钟权限，每次最大10000行）',
    icon: Clock,
    href: '/features/stk-auction-c',
    color: 'text-cyan-500'
  },
  {
    title: '神奇九转指标',
    description: '基于技术分析的趋势反转指标，识别连续9天特定走势（6000积分/次，2023年起）',
    icon: Activity,
    href: '/features/stk-nineturn',
    color: 'text-pink-500'
  },
  {
    title: 'AH股比价',
    description: 'AH股价格比价数据，包括溢价率、比价等（5000积分/次，2025-08-12起）',
    icon: TrendingUp,
    href: '/features/stk-ah-comparison',
    color: 'text-teal-500'
  },
  {
    title: '机构调研表',
    description: '上市公司机构调研记录，调研日期、参与机构、接待方式等（5000积分/次）',
    icon: Users,
    href: '/features/stk-surv',
    color: 'text-emerald-500'
  },
  {
    title: '券商每月荐股',
    description: '券商月度金股推荐数据，每月1-3日更新（6000积分/次，单次最大1000行）',
    icon: BarChart3,
    href: '/features/broker-recommend',
    color: 'text-violet-500'
  },
]

export default function FeaturesPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="特色数据"
        description="涵盖筹码分布、北向持股、集合竞价、技术指标、机构调研等特色数据"
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
