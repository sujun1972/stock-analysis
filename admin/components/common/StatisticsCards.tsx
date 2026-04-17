/**
 * StatisticsCards — 统计卡片网格组件
 *
 * 从 70+ 数据页面中提取的公共统计卡片组件。
 * 标准布局：左文字右图标，4列响应式网格。
 */

'use client'

import { Card, CardContent } from '@/components/ui/card'
import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

export interface StatisticsCardItem {
  label: string
  value: ReactNode
  subValue?: ReactNode
  icon: LucideIcon
  iconColor?: string
}

export interface StatisticsCardsProps {
  items: StatisticsCardItem[]
  className?: string
}

export function StatisticsCards({ items, className }: StatisticsCardsProps) {
  if (items.length === 0) return null

  return (
    <div className={className ?? 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4'}>
      {items.map((item) => {
        const Icon = item.icon
        return (
          <Card key={item.label}>
            <CardContent className="p-4 sm:p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">{item.label}</p>
                  <p className="text-xl sm:text-2xl font-bold mt-1">{item.value}</p>
                  {item.subValue && (
                    <p className="text-xs text-gray-500 mt-1">{item.subValue}</p>
                  )}
                </div>
                <Icon className={`h-6 w-6 sm:h-8 sm:w-8 ${item.iconColor ?? 'text-blue-600'}`} />
              </div>
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
