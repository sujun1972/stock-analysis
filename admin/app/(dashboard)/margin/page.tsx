'use client'

import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  BarChart3,
  FileText,
  Activity,
  TrendingUp
} from 'lucide-react'
import Link from 'next/link'

const modules = [
  {
    title: '融资融券交易汇总',
    description: '查看和分析融资融券交易汇总数据（按交易所统计）',
    icon: BarChart3,
    href: '/margin/summary',
    color: 'text-blue-500'
  },
  {
    title: '融资融券交易明细',
    description: '个股融资融券交易明细数据（Tushare接口，2000积分/次，单次最大6000行）',
    icon: FileText,
    href: '/margin/detail',
    color: 'text-orange-500'
  },
  {
    title: '融资融券标的（盘前）',
    description: '查询和管理融资融券标的数据（盘前更新）',
    icon: Activity,
    href: '/margin/secs',
    color: 'text-green-500'
  },
  {
    title: '转融资交易汇总',
    description: '转融通融资汇总数据（期初余额、竞价成交、再借成交、偿还、期末余额）',
    icon: TrendingUp,
    href: '/margin/slb-len',
    color: 'text-purple-500'
  },
]

export default function MarginPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="两融数据"
        description="融资融券及转融通相关数据，涵盖交易汇总、明细、标的及转融资"
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
