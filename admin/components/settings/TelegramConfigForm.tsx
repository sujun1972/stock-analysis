'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, MessageSquare, Check, X, Eye, EyeOff, ExternalLink } from 'lucide-react'
import type { NotificationChannelConfig, TelegramConfig } from '@/types/notification-channel'
import { maskSensitiveInfo } from '@/types/notification-channel'

interface TelegramConfigFormProps {
  channel: NotificationChannelConfig
  open: boolean
  onOpenChange: (open: boolean) => void
  onSave: (config: Partial<TelegramConfig>, description?: string) => Promise<void>
  onTest: (testTarget: string) => Promise<{ success: boolean; message: string }>
}

export default function TelegramConfigForm({
  channel,
  open,
  onOpenChange,
  onSave,
  onTest,
}: TelegramConfigFormProps) {
  const telegramConfig = channel.config as TelegramConfig

  const [formData, setFormData] = useState({
    bot_token: '', // Token 默认为空，需要重新输入
    parse_mode: (telegramConfig.parse_mode || 'Markdown') as 'Markdown' | 'HTML',
    timeout: telegramConfig.timeout || 30,
  })

  const [description, setDescription] = useState(channel.description || '')
  const [testChatId, setTestChatId] = useState('')
  const [showToken, setShowToken] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)

  const handleInputChange = (field: keyof typeof formData, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleSave = async () => {
    setIsSaving(true)
    setTestResult(null)
    try {
      // 只有当 token 字段有输入时才更新 token
      const configUpdate: Partial<TelegramConfig> = {
        parse_mode: formData.parse_mode,
        timeout: Number(formData.timeout),
      }

      if (formData.bot_token) {
        configUpdate.bot_token = formData.bot_token
      }

      await onSave(configUpdate, description)
      onOpenChange(false)
    } catch (error: any) {
      console.error('保存失败:', error)
    } finally {
      setIsSaving(false)
    }
  }

  const handleTest = async () => {
    if (!testChatId) {
      setTestResult({ success: false, message: '请输入测试 Chat ID' })
      return
    }

    setIsTesting(true)
    setTestResult(null)
    try {
      const result = await onTest(testChatId)
      setTestResult(result)
    } catch (error: any) {
      setTestResult({
        success: false,
        message: error.response?.data?.detail || '测试失败，请检查配置'
      })
    } finally {
      setIsTesting(false)
    }
  }

  const isFormValid = formData.bot_token || telegramConfig.bot_token

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5" />
            Telegram Bot 通知渠道配置
          </DialogTitle>
          <DialogDescription>
            配置 Telegram Bot Token，用于发送 Telegram 消息通知
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* 配置指南 */}
          <Alert>
            <AlertDescription className="space-y-2">
              <p className="font-medium">配置步骤：</p>
              <ol className="list-decimal list-inside space-y-1 text-sm">
                <li>与 <a href="https://t.me/BotFather" target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline inline-flex items-center">@BotFather <ExternalLink className="h-3 w-3 ml-1" /></a> 对话创建 Bot</li>
                <li>发送 <code className="bg-muted px-1 py-0.5 rounded">/newbot</code> 命令并按提示操作</li>
                <li>获取 Bot Token（格式：1234567890:ABCDEF...）</li>
                <li>将 Token 填入下方配置</li>
                <li>用户需要向 Bot 发送消息激活，并获取自己的 Chat ID</li>
              </ol>
            </AlertDescription>
          </Alert>

          {/* Bot Token */}
          <div className="space-y-2">
            <Label htmlFor="bot_token">
              Bot Token * {telegramConfig.bot_token && '(留空保持不变)'}
            </Label>
            <div className="relative">
              <Input
                id="bot_token"
                type={showToken ? 'text' : 'password'}
                placeholder={telegramConfig.bot_token ? maskSensitiveInfo(telegramConfig.bot_token) : '1234567890:ABCDEF1234567890ABCDEF1234567890ABC'}
                value={formData.bot_token}
                onChange={(e) => handleInputChange('bot_token', e.target.value)}
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="absolute right-0 top-0 h-full px-3"
                onClick={() => setShowToken(!showToken)}
              >
                {showToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              从 @BotFather 获取的 Bot Token，格式：数字:字母数字组合
            </p>
          </div>

          {/* 消息解析模式 */}
          <div className="space-y-2">
            <Label htmlFor="parse_mode">消息解析模式</Label>
            <Select
              value={formData.parse_mode}
              onValueChange={(value: 'Markdown' | 'HTML') => handleInputChange('parse_mode', value)}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="Markdown">Markdown</SelectItem>
                <SelectItem value="HTML">HTML</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              消息格式化方式，推荐使用 Markdown
            </p>
          </div>

          {/* 超时时间 */}
          <div className="space-y-2">
            <Label htmlFor="timeout">请求超时时间（秒）</Label>
            <Input
              id="timeout"
              type="number"
              placeholder="30"
              value={formData.timeout}
              onChange={(e) => handleInputChange('timeout', e.target.value)}
              min={10}
              max={120}
            />
            <p className="text-xs text-muted-foreground">
              发送消息的超时时间，建议 30-60 秒
            </p>
          </div>

          {/* 描述信息 */}
          <div className="space-y-2">
            <Label htmlFor="description">渠道描述</Label>
            <Textarea
              id="description"
              placeholder="例如：使用 Telegram Bot 发送即时通知消息"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>

          {/* 测��连接 */}
          <div className="border-t pt-4 space-y-2">
            <Label htmlFor="test_chat_id">测试消息发送</Label>
            <div className="flex gap-2">
              <Input
                id="test_chat_id"
                placeholder="输入测试 Chat ID（例如：123456789）"
                value={testChatId}
                onChange={(e) => setTestChatId(e.target.value)}
              />
              <Button
                type="button"
                variant="outline"
                onClick={handleTest}
                disabled={isTesting || !isFormValid}
              >
                {isTesting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    发送中...
                  </>
                ) : (
                  '测试连接'
                )}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              如何获取 Chat ID：向 Bot 发送任意消息，然后访问{' '}
              <code className="bg-muted px-1 py-0.5 rounded">
                https://api.telegram.org/bot{'<YOUR_BOT_TOKEN>'}/getUpdates
              </code>
            </p>
            {testResult && (
              <Alert variant={testResult.success ? 'default' : 'destructive'}>
                <div className="flex items-start gap-2">
                  {testResult.success ? (
                    <Check className="h-4 w-4 mt-0.5" />
                  ) : (
                    <X className="h-4 w-4 mt-0.5" />
                  )}
                  <AlertDescription>{testResult.message}</AlertDescription>
                </div>
              </Alert>
            )}
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={isSaving}>
            取消
          </Button>
          <Button onClick={handleSave} disabled={!isFormValid || isSaving}>
            {isSaving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                保存中...
              </>
            ) : (
              '保存配置'
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
