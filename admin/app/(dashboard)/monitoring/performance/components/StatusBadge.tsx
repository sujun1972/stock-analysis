'use client'

import { Badge } from '@/components/ui/badge'
import { CheckCircle2, XCircle, AlertTriangle } from 'lucide-react'

const STATUS_CONFIG = {
  healthy: {
    icon: CheckCircle2,
    text: '正常',
    className: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
  },
  degraded: {
    icon: AlertTriangle,
    text: '降级',
    className: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
  },
  unhealthy: {
    icon: XCircle,
    text: '异常',
    className: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
  }
} as const

export const StatusBadge = ({ status }: { status: string }) => {
  const config = STATUS_CONFIG[status as keyof typeof STATUS_CONFIG] || STATUS_CONFIG.unhealthy
  const Icon = config.icon
  return (
    <Badge className={`${config.className} flex items-center gap-1`}>
      <Icon className="h-3 w-3" />
      {config.text}
    </Badge>
  )
}
