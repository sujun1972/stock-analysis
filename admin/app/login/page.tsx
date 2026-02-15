'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/stores/auth-store'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Loader2, AlertCircle } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const { login, isAuthenticated, isLoading, error, clearError, user } = useAuthStore()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  // 已登录用户重定向
  useEffect(() => {
    if (isAuthenticated && user) {
      // 检查是否为管理员
      if (user.role === 'super_admin' || user.role === 'admin') {
        router.push('/')
      } else {
        // 非管理员，清除登录状态并显示错误
        useAuthStore.getState().logout()
        clearError()
        alert('您没有访问管理后台的权限')
      }
    }
  }, [isAuthenticated, user, router])

  // 清除错误
  useEffect(() => {
    return () => clearError()
  }, [clearError])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    clearError()

    try {
      await login(email, password)

      // 等待状态更新后再跳转
      // useEffect会处理跳转逻辑
    } catch (err) {
      // 错误已经在store中处理
      console.error('Login failed:', err)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 px-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <CardTitle className="text-3xl font-bold">管理后台登录</CardTitle>
          <CardDescription>
            请使用管理员账户登录
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="email">邮箱</Label>
              <Input
                id="email"
                type="email"
                placeholder="admin@stock-analysis.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                disabled={isLoading}
                autoComplete="email"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">密码</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
                autoComplete="current-password"
              />
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  登录中...
                </>
              ) : (
                '登录'
              )}
            </Button>
          </form>

          <div className="mt-6 text-center text-sm text-gray-600 dark:text-gray-400">
            <p>默认管理员账户：</p>
            <p className="font-mono text-xs mt-1">
              admin@stock-analysis.com / admin123
            </p>
            <p className="text-xs text-red-500 mt-2">
              ⚠️ 首次登录后请立即修改密码
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
