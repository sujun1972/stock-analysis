'use client'

import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollText } from 'lucide-react'
import Link from 'next/link'

const modules = [
  {
    title: '公司公告',
    description: 'A股公司公告（年报/减持/回购/诉讼等事件面），来源：AkShare 东方财富聚合（免费，替代 Tushare anns_d）',
    icon: ScrollText,
    href: '/news-anns/stock-anns',
    color: 'text-blue-600'
  },
]

export default function NewsAnnsIndexPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="新闻公告"
        description="新闻资讯 & 公司公告数据源（Phase 1：公司公告；Phase 2 将补全财经快讯 + 新闻联播）"
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
