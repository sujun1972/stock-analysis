'use client'

import { useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, AlertCircle, Mail, ArrowLeft, MailCheck } from 'lucide-react'
import { AuthLayout } from '@/components/auth/AuthLayout'
import { apiClient } from '@/lib/api-client'

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [serverMessage, setServerMessage] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      const res = await apiClient.post<any>(
        `/api/auth/forgot-password?email=${encodeURIComponent(email)}`,
      )
      if (res?.message) setServerMessage(res.message)
      setSubmitted(true)
    } catch (err: any) {
      setError(err?.response?.data?.message || err?.message || '提交失败，请稍后重试')
    } finally {
      setIsLoading(false)
    }
  }

  if (submitted) {
    return (
      <AuthLayout
        title="请查收您的邮箱"
        subtitle="我们已将密码重置指引发送到您填写的邮箱"
        footer={
          <div className="text-sm text-center text-muted-foreground">
            <Link
              href="/login"
              className="inline-flex items-center gap-1 text-primary font-medium hover:underline underline-offset-4"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              返回登录
            </Link>
          </div>
        }
      >
        <div className="rounded-xl border bg-card p-6 space-y-4">
          <div className="mx-auto w-14 h-14 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center">
            <MailCheck className="h-7 w-7 text-blue-600 dark:text-blue-400" />
          </div>
          <div className="text-center space-y-1.5">
            <p className="text-sm font-medium">
              邮件已发送至 <span className="text-foreground">{email}</span>
            </p>
            <p className="text-xs text-muted-foreground leading-relaxed">
              请在 30 分钟内点击邮件中的链接完成重置。
              <br />
              未收到？请检查垃圾邮件箱，或{' '}
              <button
                type="button"
                onClick={() => setSubmitted(false)}
                className="text-primary hover:underline underline-offset-4"
              >
                重新发送
              </button>
              。
            </p>
          </div>
          {serverMessage && (
            <Alert>
              <AlertDescription className="text-xs">{serverMessage}</AlertDescription>
            </Alert>
          )}
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title="忘记密码"
      subtitle="输入您的注册邮箱，我们将发送重置链接"
      footer={
        <div className="text-sm text-center text-muted-foreground">
          想起来了？{' '}
          <Link
            href="/login"
            className="text-primary font-medium hover:underline underline-offset-4"
          >
            返回登录
          </Link>
        </div>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-5">
        {error && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="space-y-2">
          <Label htmlFor="email">注册邮箱</Label>
          <div className="relative">
            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
            <Input
              id="email"
              type="email"
              placeholder="your@email.com"
              className="pl-9"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={isLoading}
              autoComplete="email"
              autoFocus
            />
          </div>
        </div>

        <Button type="submit" className="w-full h-11" disabled={isLoading}>
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              发送中...
            </>
          ) : (
            '发送重置邮件'
          )}
        </Button>

        <p className="text-xs text-muted-foreground text-center leading-relaxed">
          为保护账户安全，无论该邮箱是否注册，系统都会返回相同提示。
        </p>
      </form>
    </AuthLayout>
  )
}
