'use client'

import { NotificationCenter } from '@/components/notifications/NotificationCenter'

/**
 * 通知中心页面
 * 展示所有站内消息
 */
export default function NotificationsPage() {
  return (
    <div className="container mx-auto py-8">
      <NotificationCenter showHeader={true} />
    </div>
  )
}
