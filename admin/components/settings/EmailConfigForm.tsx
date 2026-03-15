'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, Mail, Check, X, Eye, EyeOff } from 'lucide-react'
import type { NotificationChannelConfig, EmailConfig } from '@/types/notification-channel'
import { maskSensitiveInfo } from '@/types/notification-channel'

interface EmailConfigFormProps {
  channel: NotificationChannelConfig
  open: boolean
  onOpenChange: (open: boolean) => void
  onSave: (config: Partial<EmailConfig>, description?: string) => Promise<void>
  onTest: (testTarget: string) => Promise<{ success: boolean; message: string }>
}

export default function EmailConfigForm({
  channel,
  open,
  onOpenChange,
  onSave,
  onTest,
}: EmailConfigFormProps) {
  const emailConfig = channel.config as EmailConfig

  const [formData, setFormData] = useState({
    smtp_host: emailConfig.smtp_host || '',
    smtp_port: emailConfig.smtp_port || 587,
    smtp_username: emailConfig.smtp_username || '',
    smtp_password: '', // 密码默认为空，需要重新输入
    smtp_use_tls: emailConfig.smtp_use_tls ?? true,
    from_email: emailConfig.from_email || '',
    from_name: emailConfig.from_name || '股票分析系统',
  })

  const [description, setDescription] = useState(channel.description || '')
  const [testEmail, setTestEmail] = useState('')
  const [showPassword, setShowPassword] = useState(false)
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
      // 只有当密码字段有输入时才更新密码
      const configUpdate: Partial<EmailConfig> = {
        smtp_host: formData.smtp_host,
        smtp_port: Number(formData.smtp_port),
        smtp_username: formData.smtp_username,
        smtp_use_tls: formData.smtp_use_tls,
        from_email: formData.from_email,
        from_name: formData.from_name,
      }

      if (formData.smtp_password) {
        configUpdate.smtp_password = formData.smtp_password
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
    if (!testEmail) {
      setTestResult({ success: false, message: '请输入测试邮箱地址' })
      return
    }

    setIsTesting(true)
    setTestResult(null)
    try {
      const result = await onTest(testEmail)
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

  const isFormValid =
    formData.smtp_host &&
    formData.smtp_port &&
    formData.smtp_username &&
    formData.from_email

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5" />
            Email 通知渠道配置
          </DialogTitle>
          <DialogDescription>
            配置 SMTP 服务器参数，用于发送邮件通知
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* SMTP 服务器 */}
          <div className="space-y-2">
            <Label htmlFor="smtp_host">SMTP 服务器地址 *</Label>
            <Input
              id="smtp_host"
              placeholder="smtp.gmail.com"
              value={formData.smtp_host}
              onChange={(e) => handleInputChange('smtp_host', e.target.value)}
            />
          </div>

          {/* SMTP 端口 */}
          <div className="space-y-2">
            <Label htmlFor="smtp_port">SMTP 端口 *</Label>
            <Input
              id="smtp_port"
              type="number"
              placeholder="587"
              value={formData.smtp_port}
              onChange={(e) => handleInputChange('smtp_port', e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              常用端口：587 (TLS), 465 (SSL), 25 (无加密)
            </p>
          </div>

          {/* 启用 TLS */}
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>启用 TLS 加密</Label>
              <p className="text-xs text-muted-foreground">
                推荐开启，提高邮件传输安全性
              </p>
            </div>
            <Switch
              checked={formData.smtp_use_tls}
              onCheckedChange={(checked) => handleInputChange('smtp_use_tls', checked)}
            />
          </div>

          {/* SMTP 用户名 */}
          <div className="space-y-2">
            <Label htmlFor="smtp_username">SMTP 用户名 *</Label>
            <Input
              id="smtp_username"
              placeholder="your_email@gmail.com"
              value={formData.smtp_username}
              onChange={(e) => handleInputChange('smtp_username', e.target.value)}
            />
          </div>

          {/* SMTP 密码 */}
          <div className="space-y-2">
            <Label htmlFor="smtp_password">
              SMTP 密码 {emailConfig.smtp_password && '(留空保持不变)'}
            </Label>
            <div className="relative">
              <Input
                id="smtp_password"
                type={showPassword ? 'text' : 'password'}
                placeholder={emailConfig.smtp_password ? maskSensitiveInfo(emailConfig.smtp_password) : '输入SMTP密码'}
                value={formData.smtp_password}
                onChange={(e) => handleInputChange('smtp_password', e.target.value)}
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="absolute right-0 top-0 h-full px-3"
                onClick={() => setShowPassword(!showPassword)}
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Gmail 用户需要使用应用专用密码（App Password）
            </p>
          </div>

          {/* 发件人邮箱 */}
          <div className="space-y-2">
            <Label htmlFor="from_email">发件人邮箱地址 *</Label>
            <Input
              id="from_email"
              type="email"
              placeholder="noreply@example.com"
              value={formData.from_email}
              onChange={(e) => handleInputChange('from_email', e.target.value)}
            />
          </div>

          {/* 发件人名称 */}
          <div className="space-y-2">
            <Label htmlFor="from_name">发件人名称</Label>
            <Input
              id="from_name"
              placeholder="股票分析系统"
              value={formData.from_name}
              onChange={(e) => handleInputChange('from_name', e.target.value)}
            />
          </div>

          {/* 描述信息 */}
          <div className="space-y-2">
            <Label htmlFor="description">渠道描述</Label>
            <Textarea
              id="description"
              placeholder="例如：使用 Gmail SMTP 服务发送邮件通知"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>

          {/* 测试连接 */}
          <div className="border-t pt-4 space-y-2">
            <Label htmlFor="test_email">测试邮件发送</Label>
            <div className="flex gap-2">
              <Input
                id="test_email"
                type="email"
                placeholder="输入测试邮箱地址"
                value={testEmail}
                onChange={(e) => setTestEmail(e.target.value)}
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
