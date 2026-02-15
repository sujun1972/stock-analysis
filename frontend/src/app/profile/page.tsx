'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/stores/auth-store'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Loader2, User, Mail, Calendar, TrendingUp, LogOut, Crown, ShieldCheck } from 'lucide-react'
import { apiClient } from '@/lib/api-client'

interface UserQuota {
  backtest_quota_total: number
  backtest_quota_used: number
  backtest_quota_reset_at: string
  ml_prediction_quota_total: number
  ml_prediction_quota_used: number
  ml_prediction_quota_reset_at: string
  max_strategies: number
  current_strategies: number
}

export default function ProfilePage() {
  const router = useRouter()
  const { user, isAuthenticated, isLoading: authLoading, logout } = useAuthStore()
  const [quota, setQuota] = useState<UserQuota | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push('/login')
    }
  }, [authLoading, isAuthenticated, router])

  useEffect(() => {
    if (isAuthenticated && user) {
      loadQuota()
    }
  }, [isAuthenticated, user])

  const loadQuota = async () => {
    try {
      setLoading(true)
      const response = await apiClient.getQuota()
      setQuota(response.data)
    } catch (error) {
      console.error('Failed to load quota:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = async () => {
    await logout()
    router.push('/login')
  }

  const getRoleInfo = (role: string) => {
    const roleMap: Record<string, { label: string; icon: any; color: string }> = {
      super_admin: { label: '超级管理员', icon: Crown, color: 'text-red-600' },
      admin: { label: '管理员', icon: ShieldCheck, color: 'text-blue-600' },
      vip_user: { label: 'VIP用户', icon: Crown, color: 'text-purple-600' },
      normal_user: { label: '普通用户', icon: User, color: 'text-gray-600' },
      trial_user: { label: '试用用户', icon: User, color: 'text-gray-500' },
    }
    return roleMap[role] || roleMap.trial_user
  }

  const calculateProgress = (used: number, total: number) => {
    if (total === 0) return 0
    return Math.min((used / total) * 100, 100)
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-CN')
  }

  if (authLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  if (!user) {
    return null
  }

  const roleInfo = getRoleInfo(user.role)
  const RoleIcon = roleInfo.icon

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 p-6">
      <div className="max-w-4xl mx-auto space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h1 className="text-3xl font-bold">个人中心</h1>
          <Button variant="outline" onClick={handleLogout}>
            <LogOut className="mr-2 h-4 w-4" />
            登出
          </Button>
        </div>

        {/* 用户信息 */}
        <Card>
          <CardHeader>
            <CardTitle>基本信息</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white text-2xl font-bold">
                {user.username.slice(0, 2).toUpperCase()}
              </div>
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <h2 className="text-xl font-bold">{user.full_name || user.username}</h2>
                  <Badge variant="secondary" className={roleInfo.color}>
                    <RoleIcon className="mr-1 h-3 w-3" />
                    {roleInfo.label}
                  </Badge>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">@{user.username}</p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t">
              <div className="flex items-center gap-2 text-sm">
                <Mail className="h-4 w-4 text-gray-400" />
                <span className="text-gray-600 dark:text-gray-400">邮箱：</span>
                <span className="font-medium">{user.email}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <Calendar className="h-4 w-4 text-gray-400" />
                <span className="text-gray-600 dark:text-gray-400">注册时间：</span>
                <span className="font-medium">{formatDate(user.created_at)}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <TrendingUp className="h-4 w-4 text-gray-400" />
                <span className="text-gray-600 dark:text-gray-400">登录次数：</span>
                <span className="font-medium">{user.login_count}次</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* 配额信息 */}
        {quota && (user.role === 'normal_user' || user.role === 'trial_user') && (
          <Card>
            <CardHeader>
              <CardTitle>使用配额</CardTitle>
              <CardDescription>
                您当前的使用配额和剩余次数
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* 回测配额 */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">回测配额</span>
                  <span className="text-sm text-gray-600">
                    {quota.backtest_quota_used} / {quota.backtest_quota_total}
                  </span>
                </div>
                <Progress value={calculateProgress(quota.backtest_quota_used, quota.backtest_quota_total)} />
                <p className="text-xs text-gray-500 mt-1">
                  重置时间：{formatDate(quota.backtest_quota_reset_at)}
                </p>
              </div>

              {/* ML预测配额 */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">ML预测配额</span>
                  <span className="text-sm text-gray-600">
                    {quota.ml_prediction_quota_used} / {quota.ml_prediction_quota_total}
                  </span>
                </div>
                <Progress value={calculateProgress(quota.ml_prediction_quota_used, quota.ml_prediction_quota_total)} />
                <p className="text-xs text-gray-500 mt-1">
                  重置时间：{formatDate(quota.ml_prediction_quota_reset_at)}
                </p>
              </div>

              {/* 策略数量 */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">策略数量</span>
                  <span className="text-sm text-gray-600">
                    {quota.current_strategies} / {quota.max_strategies}
                  </span>
                </div>
                <Progress value={calculateProgress(quota.current_strategies, quota.max_strategies)} />
              </div>

              {/* 升级提示 */}
              <div className="mt-4 p-4 bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 border border-purple-200 dark:border-purple-800 rounded-lg">
                <h4 className="font-semibold text-purple-900 dark:text-purple-300 mb-2">
                  升级为VIP，解锁无限配额
                </h4>
                <ul className="text-sm text-purple-800 dark:text-purple-400 space-y-1 mb-3">
                  <li>✓ 无限回测次数</li>
                  <li>✓ 无限ML预测</li>
                  <li>✓ 无限策略创建</li>
                  <li>✓ 优先客服支持</li>
                </ul>
                <Button className="w-full bg-gradient-to-r from-purple-600 to-blue-600">
                  立即升级
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* VIP/管理员提示 */}
        {(user.role === 'vip_user' || user.role === 'admin' || user.role === 'super_admin') && (
          <Card className="bg-gradient-to-r from-purple-50 to-blue-50 dark:from-purple-900/20 dark:to-blue-900/20 border-purple-200 dark:border-purple-800">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <Crown className="h-8 w-8 text-purple-600 dark:text-purple-400" />
                <div>
                  <h3 className="font-semibold text-purple-900 dark:text-purple-300">
                    {user.role === 'vip_user' ? 'VIP用户特权' : '管理员特权'}
                  </h3>
                  <p className="text-sm text-purple-800 dark:text-purple-400">
                    您享有无限配额，可以无限制使用所有功能
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
