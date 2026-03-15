'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { useToast } from '@/hooks/use-toast'
import { InAppNotification, PRIORITY_CONFIG } from '@/types/notification'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Label } from '@/components/ui/label'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Separator } from '@/components/ui/separator'
import { Badge } from '@/components/ui/badge'
import { Loader2, CheckCheck, ChevronDown, ChevronUp } from 'lucide-react'
import { cn } from '@/lib/utils'

interface NotificationCenterProps {
  /** 限制显示的消息数量,用于下拉菜单场景 */
  limit?: number
  /** 是否显示标题 */
  showHeader?: boolean
  /** 自定义类名 */
  className?: string
  /** 消息更新回调 */
  onUpdate?: () => void
}

/**
 * 站内消息中心组件
 * 显示消息列表、支持标记已读、筛选未读消息
 */
export function NotificationCenter({
  limit,
  showHeader = true,
  className,
  onUpdate,
}: NotificationCenterProps) {
  const { toast } = useToast()
  const [notifications, setNotifications] = useState<InAppNotification[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [expandedIds, setExpandedIds] = useState<Set<number>>(new Set())

  useEffect(() => {
    loadNotifications()
  }, [unreadOnly, limit])

  const loadNotifications = async () => {
    setIsLoading(true)
    try {
      const response = await apiClient.getInAppNotifications({
        unread_only: unreadOnly,
        limit: limit || 50,
      })
      if (response.success && response.data) {
        setNotifications(response.data)
      }
    } catch (error: any) {
      console.error('Failed to load notifications:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleMarkAsRead = async (id: number) => {
    try {
      await apiClient.markNotificationAsRead(id)
      // 更新本地状态
      setNotifications((prev) =>
        prev.map((notif) =>
          notif.id === id ? { ...notif, is_read: true, read_at: new Date().toISOString() } : notif
        )
      )
      onUpdate?.()
    } catch (error: any) {
      console.error('Failed to mark as read:', error)
      toast({
        title: '操作失败',
        description: '无法标记为已读',
        variant: 'destructive',
      })
    }
  }

  const handleMarkAllAsRead = async () => {
    try {
      const response = await apiClient.markAllNotificationsAsRead()
      if (response.success) {
        toast({
          title: '操作成功',
          description: `已标记 ${response.data?.count || 0} 条消息为已读`,
        })
        await loadNotifications()
        onUpdate?.()
      }
    } catch (error: any) {
      console.error('Failed to mark all as read:', error)
      toast({
        title: '操作失败',
        description: '无法全部标记为已读',
        variant: 'destructive',
      })
    }
  }

  const toggleExpand = (id: number) => {
    setExpandedIds((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(id)) {
        newSet.delete(id)
      } else {
        newSet.add(id)
      }
      return newSet
    })
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return '刚刚'
    if (diffMins < 60) return `${diffMins} 分钟前`
    if (diffHours < 24) return `${diffHours} 小时前`
    if (diffDays < 7) return `${diffDays} 天前`

    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  if (isLoading) {
    return (
      <div className={cn('flex items-center justify-center p-8', className)}>
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* 头部 */}
      {showHeader && (
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold">通知中心</h2>
          <div className="flex items-center gap-4">
            <Button onClick={handleMarkAllAsRead} variant="outline" size="sm">
              <CheckCheck className="mr-2 h-4 w-4" />
              全部已读
            </Button>
            <div className="flex items-center gap-2">
              <Checkbox
                id="unread-only"
                checked={unreadOnly}
                onCheckedChange={(checked) => setUnreadOnly(checked as boolean)}
              />
              <Label htmlFor="unread-only" className="text-sm font-normal">
                仅显示未读
              </Label>
            </div>
          </div>
        </div>
      )}

      {/* 消息列表 */}
      {notifications.length === 0 ? (
        <Card className="p-8 text-center text-muted-foreground">
          {unreadOnly ? '暂无未读消息' : '暂无通知'}
        </Card>
      ) : (
        <ScrollArea className="h-[600px]">
          <div className="space-y-2">
            {notifications.map((notification, index) => {
              const isExpanded = expandedIds.has(notification.id)
              const priorityConfig = PRIORITY_CONFIG[notification.priority]

              return (
                <div key={notification.id}>
                  <Card
                    className={cn(
                      'p-4 transition-colors cursor-pointer hover:bg-muted/50',
                      !notification.is_read && 'bg-muted/30',
                      priorityConfig.bgColor
                    )}
                    onClick={() => {
                      if (!notification.is_read) {
                        handleMarkAsRead(notification.id)
                      }
                      toggleExpand(notification.id)
                    }}
                  >
                    <div className="flex items-start gap-3">
                      {/* 优先级图标 */}
                      <span className={cn('text-lg', priorityConfig.color)}>
                        {priorityConfig.icon}
                      </span>

                      {/* 消息内容 */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2">
                          <div className="flex items-center gap-2 flex-1">
                            <h3
                              className={cn(
                                'text-base',
                                !notification.is_read && 'font-semibold'
                              )}
                            >
                              {notification.title}
                            </h3>
                            <Badge variant="outline" className="text-xs">
                              {priorityConfig.label}
                            </Badge>
                            {notification.is_read && (
                              <span className="text-xs text-muted-foreground">✓已读</span>
                            )}
                          </div>
                          {isExpanded ? (
                            <ChevronUp className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          ) : (
                            <ChevronDown className="h-4 w-4 text-muted-foreground flex-shrink-0" />
                          )}
                        </div>

                        {/* 消息摘要（折叠时） */}
                        {!isExpanded && (
                          <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                            {notification.content}
                          </p>
                        )}

                        {/* 消息详情（展开时） */}
                        {isExpanded && (
                          <div className="mt-2 space-y-2">
                            <p className="text-sm whitespace-pre-wrap">{notification.content}</p>
                            {notification.business_date && (
                              <div className="text-xs text-muted-foreground">
                                业务日期: {notification.business_date}
                              </div>
                            )}
                            {notification.metadata && Object.keys(notification.metadata).length > 0 && (
                              <details className="text-xs text-muted-foreground">
                                <summary className="cursor-pointer">更多信息</summary>
                                <pre className="mt-2 p-2 bg-muted rounded text-xs overflow-x-auto">
                                  {JSON.stringify(notification.metadata, null, 2)}
                                </pre>
                              </details>
                            )}
                          </div>
                        )}

                        {/* 时间 */}
                        <div className="text-xs text-muted-foreground mt-2">
                          {formatDate(notification.created_at)}
                        </div>
                      </div>
                    </div>
                  </Card>
                  {index < notifications.length - 1 && <Separator className="my-2" />}
                </div>
              )
            })}
          </div>
        </ScrollArea>
      )}
    </div>
  )
}
