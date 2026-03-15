'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { useToast } from '@/hooks/use-toast'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Checkbox } from '@/components/ui/checkbox'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { NotificationSettings, REPORT_FORMAT_OPTIONS } from '@/types/notification'
import { Loader2, Save, RotateCcw, Mail, Send, Bell, Clock, Settings2 } from 'lucide-react'

/**
 * 通知设置页面
 * 允许用户配置通知订阅偏好、渠道和发送时间
 */
export default function NotificationSettingsPage() {
  const { toast } = useToast()
  const [settings, setSettings] = useState<NotificationSettings | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [errors, setErrors] = useState<Record<string, string>>({})

  // 加载用户通知配置
  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    setIsLoading(true)
    try {
      const response = await apiClient.getNotificationSettings() as any
      if (response?.code === 200 && response.data) {
        setSettings(response.data)
      } else {
        toast({
          title: '加载失败',
          description: response?.message || '无法加载通知设置',
          variant: 'destructive',
        })
      }
    } catch (error: any) {
      console.error('Failed to load notification settings:', error)
      toast({
        title: '加载失败',
        description: error.response?.data?.message || '无法加载通知设置',
        variant: 'destructive',
      })
    } finally {
      setIsLoading(false)
    }
  }

  // 验证表单
  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {}

    // Email 验证
    if (settings?.email_enabled) {
      if (!settings.email_address) {
        newErrors.email_address = '启用 Email 通知时必须填写邮箱地址'
      } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(settings.email_address)) {
        newErrors.email_address = '请输入有效的邮箱地址'
      }
    }

    // Telegram 验证
    if (settings?.telegram_enabled) {
      if (!settings.telegram_chat_id) {
        newErrors.telegram_chat_id = '启用 Telegram 通知时必须填写 Chat ID'
      } else if (!/^-?\d+$/.test(settings.telegram_chat_id)) {
        newErrors.telegram_chat_id = 'Chat ID 必须是数字或负数'
      }
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  // 保存配置
  const handleSave = async () => {
    if (!settings) return

    if (!validateForm()) {
      toast({
        title: '验证失败',
        description: '请检查表单填写是否正确',
        variant: 'destructive',
      })
      return
    }

    setIsSaving(true)
    try {
      const response = await apiClient.updateNotificationSettings(settings) as any
      if (response?.code === 200) {
        toast({
          title: '保存成功',
          description: response?.message || '通知设置已更新',
        })
        // 重新加载以获取服务器最新数据
        await loadSettings()
      } else {
        toast({
          title: '保存失败',
          description: response?.message || '无法保存通知设置',
          variant: 'destructive',
        })
      }
    } catch (error: any) {
      console.error('Failed to save settings:', error)
      toast({
        title: '保存失败',
        description: error.response?.data?.message || '无法保存通知设置',
        variant: 'destructive',
      })
    } finally {
      setIsSaving(false)
    }
  }

  // 恢复默认设置
  const handleResetToDefaults = () => {
    if (!settings) return

    setSettings({
      ...settings,
      email_enabled: false,
      telegram_enabled: false,
      in_app_enabled: true,
      subscribe_sentiment_report: true,
      subscribe_premarket_report: true,
      subscribe_backtest_report: true,
      subscribe_strategy_alert: true,
      sentiment_report_time: '18:30',
      premarket_report_time: '08:00',
      report_format: 'full',
      max_daily_notifications: 10,
    })

    toast({
      title: '已恢复默认',
      description: '请点击保存以应用更改',
    })
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!settings) {
    return (
      <div className="container mx-auto py-8">
        <div className="text-center text-muted-foreground">无法加载通知设置</div>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">通知设置</h1>
          <p className="text-muted-foreground mt-2">管理您的通知订阅偏好和接收渠道</p>
        </div>
      </div>

      {/* 通知渠道 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            通知渠道
          </CardTitle>
          <CardDescription>选择接收通知的方式</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Email 通知 */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Mail className="h-5 w-5 text-muted-foreground" />
                <Label htmlFor="email-enabled" className="text-base font-medium">Email 通知</Label>
              </div>
              <Switch
                id="email-enabled"
                checked={settings.email_enabled}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, email_enabled: checked })
                }
              />
            </div>
            {settings.email_enabled && (
              <div className="ml-8 space-y-2">
                <Label htmlFor="email-address">邮箱地址</Label>
                <Input
                  id="email-address"
                  type="email"
                  placeholder="your.email@example.com"
                  value={settings.email_address || ''}
                  onChange={(e) =>
                    setSettings({ ...settings, email_address: e.target.value })
                  }
                  className={errors.email_address ? 'border-red-500' : ''}
                />
                {errors.email_address && (
                  <p className="text-sm text-red-500">{errors.email_address}</p>
                )}
              </div>
            )}
          </div>

          {/* Telegram 通知 */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Send className="h-5 w-5 text-muted-foreground" />
                <Label htmlFor="telegram-enabled" className="text-base font-medium">
                  Telegram 通知
                </Label>
              </div>
              <Switch
                id="telegram-enabled"
                checked={settings.telegram_enabled}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, telegram_enabled: checked })
                }
              />
            </div>
            {settings.telegram_enabled && (
              <div className="ml-8 space-y-2">
                <Label htmlFor="telegram-chat-id">Chat ID</Label>
                <Input
                  id="telegram-chat-id"
                  placeholder="123456789 或 -987654321"
                  value={settings.telegram_chat_id || ''}
                  onChange={(e) =>
                    setSettings({ ...settings, telegram_chat_id: e.target.value })
                  }
                  className={errors.telegram_chat_id ? 'border-red-500' : ''}
                />
                {errors.telegram_chat_id && (
                  <p className="text-sm text-red-500">{errors.telegram_chat_id}</p>
                )}
                <details className="text-sm text-muted-foreground">
                  <summary className="cursor-pointer hover:text-foreground">
                    如何获取 Chat ID?
                  </summary>
                  <ol className="mt-2 ml-4 space-y-1 list-decimal">
                    <li>向系统配置的 Bot 发送任意消息</li>
                    <li>联系管理员获取您的 Chat ID</li>
                    <li>将 Chat ID 填入上方输入框</li>
                  </ol>
                </details>
              </div>
            )}
          </div>

          {/* 站内消息 */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Bell className="h-5 w-5 text-muted-foreground" />
              <div>
                <Label className="text-base font-medium">站内消息</Label>
                <p className="text-sm text-muted-foreground">默认启用</p>
              </div>
            </div>
            <Switch checked={settings.in_app_enabled} disabled />
          </div>
        </CardContent>
      </Card>

      {/* 订阅内容 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5" />
            订阅内容
          </CardTitle>
          <CardDescription>选择您想要接收的通知类型</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Checkbox
                id="subscribe-sentiment"
                checked={settings.subscribe_sentiment_report}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, subscribe_sentiment_report: checked as boolean })
                }
              />
              <div>
                <Label htmlFor="subscribe-sentiment" className="font-medium">
                  盘后情绪分析报告
                </Label>
                <p className="text-sm text-muted-foreground">每日交易结束后的市场情绪分析</p>
              </div>
            </div>
            {settings.subscribe_sentiment_report && (
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <Input
                  type="time"
                  value={settings.sentiment_report_time}
                  onChange={(e) =>
                    setSettings({ ...settings, sentiment_report_time: e.target.value })
                  }
                  className="w-32"
                />
              </div>
            )}
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Checkbox
                id="subscribe-premarket"
                checked={settings.subscribe_premarket_report}
                onCheckedChange={(checked) =>
                  setSettings({ ...settings, subscribe_premarket_report: checked as boolean })
                }
              />
              <div>
                <Label htmlFor="subscribe-premarket" className="font-medium">
                  盘前碰撞分析报告
                </Label>
                <p className="text-sm text-muted-foreground">开盘前的策略分析和建议</p>
              </div>
            </div>
            {settings.subscribe_premarket_report && (
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-muted-foreground" />
                <Input
                  type="time"
                  value={settings.premarket_report_time}
                  onChange={(e) =>
                    setSettings({ ...settings, premarket_report_time: e.target.value })
                  }
                  className="w-32"
                />
              </div>
            )}
          </div>

          <div className="flex items-center gap-3">
            <Checkbox
              id="subscribe-backtest"
              checked={settings.subscribe_backtest_report}
              onCheckedChange={(checked) =>
                setSettings({ ...settings, subscribe_backtest_report: checked as boolean })
              }
            />
            <div>
              <Label htmlFor="subscribe-backtest" className="font-medium">
                回测完成通知
              </Label>
              <p className="text-sm text-muted-foreground">策略回测完成后立即通知</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <Checkbox
              id="subscribe-strategy"
              checked={settings.subscribe_strategy_alert}
              onCheckedChange={(checked) =>
                setSettings({ ...settings, subscribe_strategy_alert: checked as boolean })
              }
            />
            <div>
              <Label htmlFor="subscribe-strategy" className="font-medium">
                策略审核通知
              </Label>
              <p className="text-sm text-muted-foreground">您提交的策略审核结果通知</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 偏好设置 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings2 className="h-5 w-5" />
            偏好设置
          </CardTitle>
          <CardDescription>自定义通知的格式和频率</CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-3">
            <Label className="text-base font-medium">报告格式</Label>
            <RadioGroup
              value={settings.report_format}
              onValueChange={(value) =>
                setSettings({ ...settings, report_format: value as any })
              }
            >
              {REPORT_FORMAT_OPTIONS.map((option) => (
                <div key={option.value} className="flex items-center space-x-2">
                  <RadioGroupItem value={option.value} id={`format-${option.value}`} />
                  <Label htmlFor={`format-${option.value}`} className="font-normal">
                    {option.label}
                  </Label>
                </div>
              ))}
            </RadioGroup>
          </div>

          <div className="space-y-3">
            <Label htmlFor="max-notifications" className="text-base font-medium">
              每日最大通知数
            </Label>
            <Input
              id="max-notifications"
              type="number"
              min="1"
              max="100"
              value={settings.max_daily_notifications}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  max_daily_notifications: parseInt(e.target.value) || 10,
                })
              }
              className="w-32"
            />
            <p className="text-sm text-muted-foreground">
              防止过多通知打扰,超过限制后将暂停发送
            </p>
          </div>
        </CardContent>
      </Card>

      {/* 操作按钮 */}
      <div className="flex items-center gap-4">
        <Button onClick={handleSave} disabled={isSaving} size="lg">
          {isSaving ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              保存中...
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              保存设置
            </>
          )}
        </Button>
        <Button onClick={handleResetToDefaults} variant="outline" size="lg">
          <RotateCcw className="mr-2 h-4 w-4" />
          恢复默认
        </Button>
      </div>
    </div>
  )
}
