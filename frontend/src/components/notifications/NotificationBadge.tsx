'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface NotificationBadgeProps {
  /** 自定义类名 */
  className?: string
  /** 未读数量（如果提供则不自动获取） */
  count?: number
  /** 轮询间隔（毫秒），默认 30000（30秒） */
  pollingInterval?: number
  /** 是否启用轮询 */
  enablePolling?: boolean
}

/**
 * 未读消息角标组件
 * 显示未读消息数量,支持自动轮询更新
 */
export function NotificationBadge({
  className,
  count: externalCount,
  pollingInterval = 30000,
  enablePolling = true,
}: NotificationBadgeProps) {
  const [unreadCount, setUnreadCount] = useState<number>(externalCount ?? 0)

  useEffect(() => {
    // 如果提供了外部 count,使用外部值
    if (externalCount !== undefined) {
      setUnreadCount(externalCount)
      return
    }

    // 立即获取一次未读数量
    fetchUnreadCount()

    // 如果启用轮询,设置定时器
    if (!enablePolling) return

    const intervalId = setInterval(() => {
      fetchUnreadCount()
    }, pollingInterval)

    return () => clearInterval(intervalId)
  }, [externalCount, enablePolling, pollingInterval])

  const fetchUnreadCount = async () => {
    try {
      const response = await apiClient.getUnreadCount()
      if (response.success && response.data) {
        setUnreadCount(response.data.unread_count)
      }
    } catch (error) {
      // 静默失败,不影响用户体验
      console.error('Failed to fetch unread count:', error)
    }
  }

  // 无未读消息时不显示
  if (unreadCount === 0) {
    return null
  }

  return (
    <Badge
      variant="destructive"
      className={cn(
        'h-5 min-w-[1.25rem] px-1 flex items-center justify-center text-xs font-semibold',
        className
      )}
    >
      {unreadCount > 99 ? '99+' : unreadCount}
    </Badge>
  )
}
