'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader } from '@/components/common/PageHeader'
import { TrendingUp } from 'lucide-react'
import Link from 'next/link'

export default function FinancialPage() {
  const features = [
    {
      title: '利润表',
      description: '上市公司利润表数据查询与同步（营业收入、净利润、每股收益等）',
      href: '/financial/income',
      icon: TrendingUp,
      color: 'text-green-600'
    }
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="财务数据"
        description="上市公司财务报表数据查询与分析"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {features.map((feature) => {
          const Icon = feature.icon
          return (
            <Link key={feature.href} href={feature.href}>
              <Card className="hover:shadow-lg transition-shadow cursor-pointer h-full">
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg bg-muted ${feature.color}`}>
                      <Icon className="h-6 w-6" />
                    </div>
                    <CardTitle>{feature.title}</CardTitle>
                  </div>
                  <CardDescription className="mt-2">
                    {feature.description}
                  </CardDescription>
                </CardHeader>
              </Card>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
