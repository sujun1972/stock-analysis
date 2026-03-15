'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { useToast } from '@/hooks/use-toast'
import { Mail, MessageSquare, Settings, CheckCircle2, XCircle, Clock, Loader2 } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import type { NotificationChannelConfig } from '@/types/notification-channel'
import { maskSensitiveInfo, isEmailConfig, isTelegramConfig } from '@/types/notification-channel'
import EmailConfigForm from '@/components/settings/EmailConfigForm'
import TelegramConfigForm from '@/components/settings/TelegramConfigForm'

export default function NotificationChannelsPage() {
  const { toast } = useToast()
  const [channels, setChannels] = useState<NotificationChannelConfig[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [editingChannel, setEditingChannel] = useState<NotificationChannelConfig | null>(null)
  const [togglingChannel, setTogglingChannel] = useState<string | null>(null)

  // 加载渠道配置
  const loadChannels = async () => {
    setIsLoading(true)
    try {
      const response = await apiClient.getNotificationChannels() as any
      if (response?.code === 200 && response.data) {
        setChannels(response.data)
      } else {
        toast({
          title: '加载失败',
          description: response?.message || '无法加载通知渠道配置',
          variant: 'destructive',
        })
      }
    } catch (error: any) {
      console.error('加载渠道配置失败:', error)
      toast({
        title: '加载失败',
        description: error.response?.data?.message || '无法加载通知渠道配置',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadChannels()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 切换渠道启用状态
  const handleToggleChannel = async (channelType: string) => {
    setTogglingChannel(channelType)
    try {
      const response = await apiClient.toggleNotificationChannel(channelType) as any
      if (response?.code === 200 && response.data) {
        setChannels(prev =>
          prev.map(ch => (ch.channel_type === channelType ? response.data! : ch))
        )
        toast({
          title: '更新成功',
          description: `${response.data.channel_name} 已${response.data.is_enabled ? '启用' : '禁用'}`,
        })
      } else {
        toast({
          title: '操作失败',
          description: response?.message || '无法切换渠道状态',
          variant: 'destructive',
        })
      }
    } catch (error: any) {
      console.error('切换渠道状态失败:', error)
      toast({
        title: '操作失败',
        description: error.response?.data?.message || '无法切换渠道状态',
        variant: 'destructive',
      })
    } finally {
      setTogglingChannel(null)
    }
  }

  // 保存渠道配置
  const handleSaveChannel = async (
    channelType: string,
    config: any,
    description?: string
  ) => {
    try {
      const response = await apiClient.updateNotificationChannel(channelType, {
        config,
        description,
      }) as any
      if (response?.code === 200 && response.data) {
        setChannels(prev =>
          prev.map(ch => (ch.channel_type === channelType ? response.data! : ch))
        )
        toast({
          title: '保存成功',
          description: `${response.data.channel_name} 配置已更新`,
        })
      } else {
        throw new Error(response?.message || '保存失败')
      }
    } catch (error: any) {
      console.error('保存渠道配置失败:', error)
      toast({
        title: '保存失败',
        description: error.response?.data?.message || error.message || '无法保存渠道配置',
        variant: 'destructive',
      })
      throw error
    }
  }

  // 测试渠道
  const handleTestChannel = async (channelType: string, testTarget: string) => {
    try {
      const response = await apiClient.testNotificationChannel(channelType, testTarget)
      return response.data || { success: false, message: '测试失败' }
    } catch (error: any) {
      throw error
    }
  }

  // 获取渠道图标
  const getChannelIcon = (channelType: string) => {
    switch (channelType) {
      case 'email':
        return <Mail className="h-6 w-6" />
      case 'telegram':
        return <MessageSquare className="h-6 w-6" />
      default:
        return <Settings className="h-6 w-6" />
    }
  }

  // 获取测试状态图标
  const getTestStatusIcon = (status?: string) => {
    switch (status) {
      case 'success':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />
      default:
        return <Clock className="h-4 w-4 text-gray-400" />
    }
  }

  // 格式化配置信息
  const formatConfigInfo = (channel: NotificationChannelConfig) => {
    if (isEmailConfig(channel.config)) {
      return (
        <div className="space-y-1 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">SMTP:</span>
            <span className="font-mono">{channel.config.smtp_host}:{channel.config.smtp_port}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">用户:</span>
            <span className="font-mono">{channel.config.smtp_username}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">发件人:</span>
            <span className="font-mono">{channel.config.from_email}</span>
          </div>
        </div>
      )
    }
    if (isTelegramConfig(channel.config)) {
      return (
        <div className="space-y-1 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Bot Token:</span>
            <span className="font-mono">{maskSensitiveInfo(channel.config.bot_token)}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">解析模式:</span>
            <span>{channel.config.parse_mode}</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">超时:</span>
            <span>{channel.config.timeout}s</span>
          </div>
        </div>
      )
    }
    return null
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">通知渠道配置</h1>
          <p className="text-muted-foreground mt-2">管理系统通知渠道的配置参数</p>
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          {[1, 2].map(i => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-6 w-32" />
                <Skeleton className="h-4 w-48 mt-2" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-20 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">通知渠道配置</h1>
        <p className="text-muted-foreground mt-2">
          管理系统通知渠道的配置参数，包括 Email 和 Telegram Bot
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        {channels.map(channel => (
          <Card key={channel.id} className="relative">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${
                    channel.is_enabled ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'
                  }`}>
                    {getChannelIcon(channel.channel_type)}
                  </div>
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      {channel.channel_name}
                      {channel.is_default && (
                        <Badge variant="secondary" className="text-xs">默认</Badge>
                      )}
                    </CardTitle>
                    <CardDescription className="mt-1">
                      {channel.description || '暂无描述'}
                    </CardDescription>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Switch
                    checked={channel.is_enabled}
                    onCheckedChange={() => handleToggleChannel(channel.channel_type)}
                    disabled={togglingChannel === channel.channel_type}
                  />
                  {togglingChannel === channel.channel_type && (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* 配置信息 */}
              <div className="rounded-lg border bg-muted/50 p-4">
                {formatConfigInfo(channel)}
              </div>

              {/* 最后测试状态 */}
              {channel.last_test_at && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  {getTestStatusIcon(channel.last_test_status)}
                  <span>最后测试:</span>
                  <span>{new Date(channel.last_test_at).toLocaleString('zh-CN')}</span>
                  {channel.last_test_message && (
                    <span className="text-xs">- {channel.last_test_message}</span>
                  )}
                </div>
              )}

              {/* 操作按钮 */}
              <div className="flex gap-2 pt-2">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setEditingChannel(channel)}
                >
                  <Settings className="mr-2 h-4 w-4" />
                  配置渠道
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Email 配置对话框 */}
      {editingChannel && editingChannel.channel_type === 'email' && (
        <EmailConfigForm
          channel={editingChannel}
          open={true}
          onOpenChange={(open) => {
            if (!open) {
              setEditingChannel(null)
            }
          }}
          onSave={(config, description) =>
            handleSaveChannel(editingChannel.channel_type, config, description)
          }
          onTest={(testTarget) => handleTestChannel(editingChannel.channel_type, testTarget)}
        />
      )}

      {/* Telegram 配置对话框 */}
      {editingChannel && editingChannel.channel_type === 'telegram' && (
        <TelegramConfigForm
          channel={editingChannel}
          open={true}
          onOpenChange={(open) => {
            if (!open) {
              setEditingChannel(null)
            }
          }}
          onSave={(config, description) =>
            handleSaveChannel(editingChannel.channel_type, config, description)
          }
          onTest={(testTarget) => handleTestChannel(editingChannel.channel_type, testTarget)}
        />
      )}
    </div>
  )
}
