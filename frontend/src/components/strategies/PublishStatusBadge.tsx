'use client'

import { Badge } from '@/components/ui/badge'
import { FileText, Clock, CheckCircle, XCircle } from 'lucide-react'

interface PublishStatusBadgeProps {
  status: 'draft' | 'pending_review' | 'approved' | 'rejected'
  className?: string
  showIcon?: boolean
}

const statusConfig = {
  draft: {
    label: '草稿',
    variant: 'secondary' as const,
    icon: FileText,
    className: 'bg-gray-100 text-gray-700 hover:bg-gray-200'
  },
  pending_review: {
    label: '待审核',
    variant: 'default' as const,
    icon: Clock,
    className: 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200'
  },
  approved: {
    label: '已发布',
    variant: 'default' as const,
    icon: CheckCircle,
    className: 'bg-green-100 text-green-700 hover:bg-green-200'
  },
  rejected: {
    label: '已拒绝',
    variant: 'destructive' as const,
    icon: XCircle,
    className: 'bg-red-100 text-red-700 hover:bg-red-200'
  }
}

export default function PublishStatusBadge({
  status,
  className = '',
  showIcon = true
}: PublishStatusBadgeProps) {
  const config = statusConfig[status]
  const Icon = config.icon

  return (
    <Badge
      variant={config.variant}
      className={`${config.className} ${className}`}
    >
      {showIcon && <Icon className="w-3 h-3 mr-1" />}
      {config.label}
    </Badge>
  )
}
