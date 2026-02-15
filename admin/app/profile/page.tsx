'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import AdminLayout from '@/components/layouts/AdminLayout'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { useAuthStore } from '@/stores/auth-store'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Loader2, AlertCircle, User, Lock, CheckCircle2 } from 'lucide-react'
import { apiClient } from '@/lib/api-client'

export default function ProfilePage() {
  const { user, updateProfile } = useAuthStore()
  const router = useRouter()

  // 个人资料表单
  const [profileForm, setProfileForm] = useState({
    full_name: '',
    phone: '',
    avatar_url: '',
  })

  // 密码修改表单
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: '',
  })

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    if (user) {
      setProfileForm({
        full_name: user.full_name || '',
        phone: user.phone || '',
        avatar_url: user.avatar_url || '',
      })
    }
  }, [user])

  if (!user) {
    return null
  }

  // 获取角色标签
  const getRoleLabel = (role: string) => {
    const roleMap: Record<string, { label: string; variant: 'destructive' | 'default' | 'secondary' | 'outline' }> = {
      super_admin: { label: '超级管理员', variant: 'destructive' },
      admin: { label: '管理员', variant: 'default' },
      vip_user: { label: 'VIP用户', variant: 'secondary' },
      normal_user: { label: '普通用户', variant: 'outline' },
    }
    return roleMap[role] || { label: role, variant: 'outline' }
  }

  const roleInfo = getRoleLabel(user.role)

  // 获取用户名首字母
  const initials = user.full_name
    ? user.full_name.slice(0, 2).toUpperCase()
    : user.username.slice(0, 2).toUpperCase()

  // 更新个人资料
  const handleUpdateProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(null)

    try {
      await updateProfile(profileForm)
      setSuccess('个人资料更新成功')
    } catch (err: any) {
      setError(err.message || '更新失败')
    } finally {
      setLoading(false)
    }
  }

  // 修改密码
  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setSuccess(null)

    // 验证密码
    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setError('两次输入的新密码不一致')
      setLoading(false)
      return
    }

    if (passwordForm.new_password.length < 6) {
      setError('新密码长度至少为6位')
      setLoading(false)
      return
    }

    try {
      await apiClient.post('/api/auth/change-password', {
        current_password: passwordForm.current_password,
        new_password: passwordForm.new_password,
      })

      setSuccess('密码修改成功,请重新登录')
      setPasswordForm({
        current_password: '',
        new_password: '',
        confirm_password: '',
      })

      // 3秒后跳转到登录页
      setTimeout(() => {
        useAuthStore.getState().logout()
        router.push('/login')
      }, 3000)
    } catch (err: any) {
      setError(err.response?.data?.detail || '密码修改失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <ProtectedRoute requireAdmin>
      <AdminLayout>
        <div className="space-y-6 max-w-4xl">
          {/* 页面标题 */}
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              个人资料
            </h1>
            <p className="text-gray-600 dark:text-gray-300 mt-2">
              管理您的个人信息和账户设置
            </p>
          </div>

          {/* 用户基本信息卡片 */}
          <Card>
            <CardHeader>
              <CardTitle>基本信息</CardTitle>
              <CardDescription>您的账户基本信息</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-start gap-6">
                <Avatar className="h-20 w-20">
                  <AvatarImage src={user.avatar_url || '/assets/default-avatar.svg'} alt={user.username} />
                  <AvatarFallback className="text-2xl">{initials}</AvatarFallback>
                </Avatar>

                <div className="flex-1 space-y-3">
                  <div className="flex items-center gap-3">
                    <h2 className="text-2xl font-bold">{user.full_name || user.username}</h2>
                    <Badge variant={roleInfo.variant}>{roleInfo.label}</Badge>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-gray-600 dark:text-gray-400">用户名:</span>
                      <span className="ml-2 font-medium">{user.username}</span>
                    </div>
                    <div>
                      <span className="text-gray-600 dark:text-gray-400">邮箱:</span>
                      <span className="ml-2 font-medium">{user.email}</span>
                    </div>
                    <div>
                      <span className="text-gray-600 dark:text-gray-400">注册时间:</span>
                      <span className="ml-2 font-medium">
                        {new Date(user.created_at).toLocaleDateString('zh-CN')}
                      </span>
                    </div>
                    <div>
                      <span className="text-gray-600 dark:text-gray-400">登录次数:</span>
                      <span className="ml-2 font-medium">{user.login_count}</span>
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 编辑表单 */}
          <Tabs defaultValue="profile" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="profile">
                <User className="w-4 h-4 mr-2" />
                编辑资料
              </TabsTrigger>
              <TabsTrigger value="password">
                <Lock className="w-4 h-4 mr-2" />
                修改密码
              </TabsTrigger>
            </TabsList>

            {/* 编辑个人资料 */}
            <TabsContent value="profile">
              <Card>
                <CardHeader>
                  <CardTitle>编辑个人资料</CardTitle>
                  <CardDescription>更新您的个人信息</CardDescription>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleUpdateProfile} className="space-y-4">
                    {error && (
                      <Alert variant="destructive">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>{error}</AlertDescription>
                      </Alert>
                    )}

                    {success && (
                      <Alert className="bg-green-50 text-green-900 border-green-200">
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                        <AlertDescription>{success}</AlertDescription>
                      </Alert>
                    )}

                    <div className="space-y-2">
                      <Label htmlFor="full_name">姓名</Label>
                      <Input
                        id="full_name"
                        type="text"
                        placeholder="请输入您的姓名"
                        value={profileForm.full_name}
                        onChange={(e) => setProfileForm({ ...profileForm, full_name: e.target.value })}
                        disabled={loading}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="phone">手机号</Label>
                      <Input
                        id="phone"
                        type="tel"
                        placeholder="请输入手机号"
                        value={profileForm.phone}
                        onChange={(e) => setProfileForm({ ...profileForm, phone: e.target.value })}
                        disabled={loading}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="avatar_url">头像URL</Label>
                      <Input
                        id="avatar_url"
                        type="url"
                        placeholder="请输入头像图片URL"
                        value={profileForm.avatar_url}
                        onChange={(e) => setProfileForm({ ...profileForm, avatar_url: e.target.value })}
                        disabled={loading}
                      />
                      <p className="text-xs text-gray-500">
                        支持 https:// 开头的图片链接
                      </p>
                    </div>

                    <Separator />

                    <div className="flex justify-end gap-3">
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => router.back()}
                        disabled={loading}
                      >
                        取消
                      </Button>
                      <Button type="submit" disabled={loading}>
                        {loading ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            保存中...
                          </>
                        ) : (
                          '保存修改'
                        )}
                      </Button>
                    </div>
                  </form>
                </CardContent>
              </Card>
            </TabsContent>

            {/* 修改密码 */}
            <TabsContent value="password">
              <Card>
                <CardHeader>
                  <CardTitle>修改密码</CardTitle>
                  <CardDescription>为了账户安全,请定期修改密码</CardDescription>
                </CardHeader>
                <CardContent>
                  <form onSubmit={handleChangePassword} className="space-y-4">
                    {error && (
                      <Alert variant="destructive">
                        <AlertCircle className="h-4 w-4" />
                        <AlertDescription>{error}</AlertDescription>
                      </Alert>
                    )}

                    {success && (
                      <Alert className="bg-green-50 text-green-900 border-green-200">
                        <CheckCircle2 className="h-4 w-4 text-green-600" />
                        <AlertDescription>{success}</AlertDescription>
                      </Alert>
                    )}

                    <div className="space-y-2">
                      <Label htmlFor="current_password">当前密码</Label>
                      <Input
                        id="current_password"
                        type="password"
                        placeholder="请输入当前密码"
                        value={passwordForm.current_password}
                        onChange={(e) => setPasswordForm({ ...passwordForm, current_password: e.target.value })}
                        disabled={loading}
                        required
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="new_password">新密码</Label>
                      <Input
                        id="new_password"
                        type="password"
                        placeholder="请输入新密码(至少6位)"
                        value={passwordForm.new_password}
                        onChange={(e) => setPasswordForm({ ...passwordForm, new_password: e.target.value })}
                        disabled={loading}
                        required
                        minLength={6}
                      />
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="confirm_password">确认新密码</Label>
                      <Input
                        id="confirm_password"
                        type="password"
                        placeholder="请再次输入新密码"
                        value={passwordForm.confirm_password}
                        onChange={(e) => setPasswordForm({ ...passwordForm, confirm_password: e.target.value })}
                        disabled={loading}
                        required
                        minLength={6}
                      />
                    </div>

                    <Separator />

                    <div className="flex justify-end gap-3">
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => {
                          setPasswordForm({
                            current_password: '',
                            new_password: '',
                            confirm_password: '',
                          })
                          setError(null)
                          setSuccess(null)
                        }}
                        disabled={loading}
                      >
                        重置
                      </Button>
                      <Button type="submit" disabled={loading}>
                        {loading ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            修改中...
                          </>
                        ) : (
                          '修改密码'
                        )}
                      </Button>
                    </div>
                  </form>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </AdminLayout>
    </ProtectedRoute>
  )
}
