'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useAuthStore } from '@/stores/auth-store'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, AlertCircle, CheckCircle2, Mail, Lock, User, IdCard } from 'lucide-react'
import { AuthLayout } from '@/components/auth/AuthLayout'

export default function RegisterPage() {
  const router = useRouter()
  const { register, isAuthenticated, isLoading, error, clearError } = useAuthStore()

  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [success, setSuccess] = useState(false)
  const [validationError, setValidationError] = useState('')

  useEffect(() => {
    if (isAuthenticated) {
      router.push('/')
    }
  }, [isAuthenticated, router])

  useEffect(() => {
    return () => clearError()
  }, [clearError])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()
    setValidationError('')

    if (password !== confirmPassword) {
      setValidationError('两次输入的密码不一致')
      return
    }

    if (password.length < 6) {
      setValidationError('密码长度至少为6个字符')
      return
    }

    try {
      await register({
        email,
        username,
        password,
        full_name: fullName || undefined,
      })

      setSuccess(true)

      setTimeout(() => {
        router.push('/login?message=' + encodeURIComponent('注册成功，请登录'))
      }, 3000)
    } catch (err) {
      console.error('Registration failed:', err)
    }
  }

  if (success) {
    return (
      <AuthLayout title="注册成功" subtitle="3 秒后将自动跳转到登录页面">
        <div className="rounded-xl border bg-card p-6 text-center space-y-4">
          <div className="mx-auto w-14 h-14 rounded-full bg-green-100 dark:bg-green-900/40 flex items-center justify-center">
            <CheckCircle2 className="h-7 w-7 text-green-600 dark:text-green-400" />
          </div>
          <p className="text-sm text-muted-foreground">您已获得试用账户权限：</p>
          <ul className="text-sm text-left space-y-1.5 max-w-xs mx-auto">
            <li className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400 shrink-0" />
              回测配额：5 次 / 月
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400 shrink-0" />
              ML 预测配额：2 次 / 月
            </li>
            <li className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-green-600 dark:text-green-400 shrink-0" />
              最多创建 3 个策略
            </li>
          </ul>
          <Button className="w-full h-11 mt-2" onClick={() => router.push('/login')}>
            立即登录
          </Button>
        </div>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title="创建账户"
      subtitle="开启您的 AI 量化投资之旅"
      footer={
        <div className="text-sm text-center text-muted-foreground">
          已有账户？{' '}
          <Link
            href="/login"
            className="text-primary font-medium hover:underline underline-offset-4"
          >
            立即登录
          </Link>
        </div>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {(error || validationError) && (
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error || validationError}</AlertDescription>
          </Alert>
        )}

        <div className="space-y-2">
          <Label htmlFor="email">
            邮箱 <span className="text-destructive">*</span>
          </Label>
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
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="username">
            用户名 <span className="text-destructive">*</span>
          </Label>
          <div className="relative">
            <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
            <Input
              id="username"
              type="text"
              placeholder="3-50 个字符"
              className="pl-9"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              disabled={isLoading}
              minLength={3}
              maxLength={50}
              autoComplete="username"
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="fullName">
            真实姓名 <span className="text-muted-foreground text-xs font-normal">（可选）</span>
          </Label>
          <div className="relative">
            <IdCard className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
            <Input
              id="fullName"
              type="text"
              placeholder="张三"
              className="pl-9"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              disabled={isLoading}
              maxLength={100}
            />
          </div>
        </div>

        <div className="grid sm:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label htmlFor="password">
              密码 <span className="text-destructive">*</span>
            </Label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
              <Input
                id="password"
                type="password"
                placeholder="至少 6 位"
                className="pl-9"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
                minLength={6}
                autoComplete="new-password"
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirmPassword">
              确认密码 <span className="text-destructive">*</span>
            </Label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
              <Input
                id="confirmPassword"
                type="password"
                placeholder="再输一次"
                className="pl-9"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                disabled={isLoading}
                minLength={6}
                autoComplete="new-password"
              />
            </div>
          </div>
        </div>

        <Button type="submit" className="w-full h-11" disabled={isLoading}>
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              注册中...
            </>
          ) : (
            '创建账户'
          )}
        </Button>

        <div className="rounded-lg border border-blue-200 dark:border-blue-900/50 bg-blue-50/60 dark:bg-blue-950/30 px-4 py-3">
          <p className="text-xs font-semibold text-blue-900 dark:text-blue-300 mb-1.5">
            试用账户权益
          </p>
          <ul className="text-xs text-blue-800/90 dark:text-blue-400/90 space-y-0.5 leading-relaxed">
            <li>• 每月 5 次回测配额</li>
            <li>• 每月 2 次 ML 预测配额</li>
            <li>• 最多创建 3 个策略</li>
          </ul>
        </div>
      </form>
    </AuthLayout>
  )
}
