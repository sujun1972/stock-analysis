/**
 * 策略发布状态徽章组件
 *
 * 显示策略的发布状态，带有不同的颜色和图标
 */

import { FileText, Clock, CheckCircle, XCircle } from 'lucide-react'

interface PublishStatusBadgeProps {
  status: 'draft' | 'pending_review' | 'approved' | 'rejected'
  className?: string
  showIcon?: boolean
  size?: 'sm' | 'md' | 'lg'
}

const statusConfig = {
  draft: {
    label: '草稿',
    icon: FileText,
    className: 'bg-gray-100 text-gray-700 border-gray-300',
  },
  pending_review: {
    label: '待审核',
    icon: Clock,
    className: 'bg-yellow-100 text-yellow-700 border-yellow-300',
  },
  approved: {
    label: '已发布',
    icon: CheckCircle,
    className: 'bg-green-100 text-green-700 border-green-300',
  },
  rejected: {
    label: '已拒绝',
    icon: XCircle,
    className: 'bg-red-100 text-red-700 border-red-300',
  },
}

const sizeClasses = {
  sm: 'text-xs px-2 py-0.5',
  md: 'text-sm px-2.5 py-1',
  lg: 'text-base px-3 py-1.5',
}

const iconSizes = {
  sm: 'w-3 h-3',
  md: 'w-4 h-4',
  lg: 'w-5 h-5',
}

export default function PublishStatusBadge({
  status,
  className = '',
  showIcon = true,
  size = 'md',
}: PublishStatusBadgeProps) {
  const config = statusConfig[status]
  const Icon = config.icon

  return (
    <span
      className={`
        inline-flex items-center gap-1 font-medium rounded-full border
        ${config.className}
        ${sizeClasses[size]}
        ${className}
      `}
    >
      {showIcon && <Icon className={iconSizes[size]} />}
      {config.label}
    </span>
  )
}
