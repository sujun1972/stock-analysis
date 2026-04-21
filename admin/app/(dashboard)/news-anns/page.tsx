'use client'

import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ScrollText, Newspaper, Tv, BarChart3 } from 'lucide-react'
import Link from 'next/link'

const modules = [
  {
    title: '公司公告',
    description: 'A股公司公告（年报/减持/回购/诉讼等事件面），来源：AkShare 东方财富聚合（免费，替代 Tushare anns_d）',
    icon: ScrollText,
    href: '/news-anns/stock-anns',
    color: 'text-blue-600'
  },
  {
    title: '财经快讯',
    description: '财新要闻精选（宏观/产业快讯）+ 东财个股新闻，带关联股票反查。免费替代 Tushare news / major_news',
    icon: Newspaper,
    href: '/news-anns/news-flash',
    color: 'text-orange-600'
  },
  {
    title: '新闻联播',
    description: 'CCTV 新闻联播文字稿（按自然日），宏观政策信号背景。免费替代 Tushare cctv_news',
    icon: Tv,
    href: '/news-anns/cctv-news',
    color: 'text-red-600'
  },
  {
    title: '宏观经济指标',
    description: 'CPI / PPI / PMI / M2 / 社融 / GDP / Shibor 等量化宏观指标，供宏观风险专家 + CIO 引用。免费替代 Tushare eco_cal',
    icon: BarChart3,
    href: '/news-anns/macro-indicators',
    color: 'text-green-600'
  },
]

export default function NewsAnnsIndexPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="新闻公告"
        description="新闻资讯 & 公司公告数据源（公告 / 快讯 / 新闻联播 / 宏观指标，全部基于 AkShare 免费接口）"
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
