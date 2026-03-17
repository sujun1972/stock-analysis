/**
 * 系统设置页面
 *
 * 展示所有设置相关的子菜单项
 */
'use client'

import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useRouter } from 'next/navigation'
import {
  Wrench,
  Database,
  Sparkles,
  FileText,
  Clock,
  Bell,
  ArrowRight
} from 'lucide-react'
import { cn } from '@/lib/utils'

interface SettingItem {
  title: string
  description: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  color: string
}

const settingItems: SettingItem[] = [
  {
    title: '系统配置',
    description: '配置系统基础参数，包括站点信息、安全设置等',
    href: '/settings/system',
    icon: Wrench,
    color: 'text-blue-500'
  },
  {
    title: '数据源设置',
    description: '管理数据接口配置，包括股票数据API、行情源等',
    href: '/settings/datasource',
    icon: Database,
    color: 'text-green-500'
  },
  {
    title: 'AI配置',
    description: '配置AI模型参数，包括大语言模型、算法策略等',
    href: '/settings/ai-config',
    icon: Sparkles,
    color: 'text-purple-500'
  },
  {
    title: '提示词管理',
    description: '管理AI提示词模板，优化模型输出效果',
    href: '/settings/prompt-templates',
    icon: FileText,
    color: 'text-orange-500'
  },
  {
    title: '定时任务',
    description: '配置和管理系统定时任务，包括数据同步、报告生成等',
    href: '/settings/scheduler',
    icon: Clock,
    color: 'text-cyan-500'
  },
  {
    title: '通知渠道',
    description: '设置通知推送渠道，包括邮件、微信、钉钉等',
    href: '/settings/notification-channels',
    icon: Bell,
    color: 'text-red-500'
  }
]

export default function SettingsPage() {
  const router = useRouter()

  return (
    <div className="space-y-6">
      <PageHeader
        title="系统设置"
        description="管理和配置系统各项参数"
      />

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {settingItems.map((item) => {
          const Icon = item.icon
          return (
            <Card
              key={item.href}
              className="cursor-pointer hover:shadow-lg transition-all duration-200 hover:-translate-y-1 group"
              onClick={() => router.push(item.href)}
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4">
                    <div className={cn(
                      "p-3 rounded-lg bg-gray-50 dark:bg-gray-800 group-hover:scale-110 transition-transform",
                      item.color
                    )}>
                      <Icon className="h-6 w-6" />
                    </div>
                    <div className="space-y-1">
                      <CardTitle className="text-base flex items-center gap-2">
                        {item.title}
                        <ArrowRight className="h-4 w-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                      </CardTitle>
                      <CardDescription className="text-sm">
                        {item.description}
                      </CardDescription>
                    </div>
                  </div>
                </div>
              </CardHeader>
            </Card>
          )
        })}
      </div>

      <div className="mt-8 p-6 bg-muted/50 rounded-lg">
        <h3 className="text-sm font-medium mb-2">提示</h3>
        <p className="text-sm text-muted-foreground">
          点击上方卡片进入相应的配置页面。系统设置的更改可能需要重启服务才能生效。
        </p>
      </div>
    </div>
  )
}