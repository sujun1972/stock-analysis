'use client'

import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Activity, PauseCircle } from 'lucide-react'
import Link from 'next/link'

export default function MarketPage() {
  const features = [
    {
      title: '每日停复牌信息',
      description: '查询股票每日停复牌情况，包括停牌时间段和复牌信息',
      icon: PauseCircle,
      href: '/market/suspend',
      color: 'text-orange-600'
    }
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="行情数据"
        description="股票行情相关数据，包括停复牌、涨跌停等信息"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {features.map((feature) => {
          const Icon = feature.icon
          return (
            <Link key={feature.href} href={feature.href}>
              <Card className="hover:shadow-lg transition-shadow cursor-pointer h-full">
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg bg-gray-100 dark:bg-gray-800`}>
                      <Icon className={`h-6 w-6 ${feature.color}`} />
                    </div>
                    <CardTitle className="text-lg">{feature.title}</CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <CardDescription className="text-sm">
                    {feature.description}
                  </CardDescription>
                </CardContent>
              </Card>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
