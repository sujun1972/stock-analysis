'use client'

import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ListOrdered, TrendingUp } from 'lucide-react'
import Link from 'next/link'

export default function BoardGamePage() {
  const modules = [
    {
      title: '龙虎榜每日明细',
      description: '查看涨跌幅偏离值达7%、连续涨跌、换手率达20%等上榜股票及席位信息',
      icon: ListOrdered,
      href: '/boardgame/top-list',
      color: 'text-blue-600'
    },
    // 未来可以添加更多打板相关功能
    // {
    //   title: '涨停板分析',
    //   description: '涨停板数据分析和连板天梯',
    //   icon: TrendingUp,
    //   href: '/boardgame/limit-up',
    //   color: 'text-red-600'
    // }
  ]

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
