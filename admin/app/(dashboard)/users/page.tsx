/**
 * 用户管理页面
 *
 * 功能：
 * - 用户列表展示（分页、搜索、筛选）
 * - 创建新用户（含表单验证）
 * - 编辑用户信息（邮箱、角色、邮箱验证状态等）
 * - 删除用户（含二次确认）
 * - 显示用户配额使用情况
 */
'use client'

import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Plus, Search, RefreshCw, User, ShieldCheck, Crown, Pencil, Trash2 } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { toast } from 'sonner'

/**
 * 用户数据接口
 */
interface User {
  id: number
  email: string
  username: string
  role: string
  is_active: boolean
  is_email_verified: boolean
  created_at: string
  full_name: string | null
  login_count: number
  quota?: {
    backtest_quota_total: number
    backtest_quota_used: number
    ml_prediction_quota_total: number
    ml_prediction_quota_used: number
  }
}

/**
 * 表单数据接口
 */
interface UserFormData {
  email: string
  username: string
  password: string
  full_name: string
  phone: string
  role: string
  is_email_verified: boolean
}

export default function UsersPage() {
  // 列表状态
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState<string>('all')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const pageSize = 20

  // 对话框状态
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [selectedUser, setSelectedUser] = useState<User | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // 表单数据
  const [formData, setFormData] = useState<UserFormData>({
    email: '',
    username: '',
    password: '',
    full_name: '',
    phone: '',
    role: 'normal_user',
    is_email_verified: false,
  })

  // 加载用户列表
  const loadUsers = async () => {
    setLoading(true)
    try {
      const params: any = {
        page,
        page_size: pageSize,
      }

      if (search) params.search = search
      if (roleFilter !== 'all') params.role = roleFilter

      const response = await apiClient.getUsers(params)
      setUsers(response.data?.users || [])
      setTotal(response.data?.total || 0)
    } catch (error: any) {
      toast.error('加载用户列表失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadUsers()
  }, [page, roleFilter])

  // 搜索
  const handleSearch = () => {
    setPage(1)
    loadUsers()
  }

  // 重置表单
  const resetForm = () => {
    setFormData({
      email: '',
      username: '',
      password: '',
      full_name: '',
      phone: '',
      role: 'normal_user',
      is_email_verified: false,
    })
  }

  // 验证邮箱格式
  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
    return emailRegex.test(email)
  }

  /**
   * 验证密码强度
   * 要求：至少8位，包含大小写字母和数字
   */
  const validatePassword = (password: string): { valid: boolean; message: string } => {
    if (password.length < 8) {
      return { valid: false, message: '密码长度至少8位' }
    }
    if (!/[A-Z]/.test(password)) {
      return { valid: false, message: '密码需包含大写字母' }
    }
    if (!/[a-z]/.test(password)) {
      return { valid: false, message: '密码需包含小写字母' }
    }
    if (!/[0-9]/.test(password)) {
      return { valid: false, message: '密码需包含数字' }
    }
    return { valid: true, message: '' }
  }

  // 创建用户
  const handleCreate = async () => {
    // 验证必填字段
    if (!formData.email || !formData.username || !formData.password) {
      toast.error('请填写所有必填字段')
      return
    }

    // 验证邮箱格式
    if (!validateEmail(formData.email)) {
      toast.error('请输入有效的邮箱地址')
      return
    }

    // 验证密码强度
    const passwordValidation = validatePassword(formData.password)
    if (!passwordValidation.valid) {
      toast.error(passwordValidation.message)
      return
    }

    setSubmitting(true)
    try {
      await apiClient.createUser({
        email: formData.email,
        username: formData.username,
        password: formData.password,
        role: formData.role,
        full_name: formData.full_name || undefined,
        phone: formData.phone || undefined,
      })
      toast.success('用户创建成功')
      setIsCreateDialogOpen(false)
      resetForm()
      loadUsers()
    } catch (error: any) {
      toast.error('创建用户失败: ' + (error.response?.data?.detail || error.message || '未知错误'))
    } finally {
      setSubmitting(false)
    }
  }

  // 打开编辑对话框
  const openEditDialog = (user: User) => {
    setSelectedUser(user)
    setFormData({
      email: user.email,
      username: user.username,
      password: '', // 密码保持为空，只在需要修改时填写
      full_name: user.full_name || '',
      phone: '',
      role: user.role,
      is_email_verified: user.is_email_verified,
    })
    setIsEditDialogOpen(true)
  }

  /**
   * 编辑用户
   * 支持修改：邮箱、全名、角色、邮箱验证状态
   */
  const handleEdit = async () => {
    if (!selectedUser) return

    // 验证邮箱格式
    if (formData.email && !validateEmail(formData.email)) {
      toast.error('请输入有效的邮箱地址')
      return
    }

    // 如果修改了密码，验证密码强度（注意：当前版本不支持修改密码）
    if (formData.password) {
      const passwordValidation = validatePassword(formData.password)
      if (!passwordValidation.valid) {
        toast.error(passwordValidation.message)
        return
      }
    }

    setSubmitting(true)
    try {
      // 构建更新数据（只发送变更的字段）
      const updateData: Record<string, any> = {
        role: formData.role,
      }

      if (formData.email && formData.email !== selectedUser.email) {
        updateData.email = formData.email
      }
      if (formData.full_name !== selectedUser.full_name) {
        updateData.full_name = formData.full_name || null
      }
      if (formData.is_email_verified !== selectedUser.is_email_verified) {
        updateData.is_email_verified = formData.is_email_verified
      }

      await apiClient.updateUser(selectedUser.id, updateData)
      toast.success('用户更新成功')
      setIsEditDialogOpen(false)
      setSelectedUser(null)
      resetForm()
      loadUsers()
    } catch (error: any) {
      toast.error('更新用户失败: ' + (error.response?.data?.detail || error.message || '未知错误'))
    } finally {
      setSubmitting(false)
    }
  }

  // 打开删除对话框
  const openDeleteDialog = (user: User) => {
    setSelectedUser(user)
    setIsDeleteDialogOpen(true)
  }

  // 删除用户
  const handleDelete = async () => {
    if (!selectedUser) return

    setSubmitting(true)
    try {
      await apiClient.deleteUser(selectedUser.id)
      toast.success('用户删除成功')
      setIsDeleteDialogOpen(false)
      setSelectedUser(null)
      loadUsers()
    } catch (error: any) {
      toast.error('删除用户失败: ' + (error.response?.data?.detail || error.message || '未知错误'))
    } finally {
      setSubmitting(false)
    }
  }

  /**
   * 渲染角色徽章
   * 根据不同角色显示不同颜色和图标
   */
  const getRoleBadge = (role: string) => {
    const config: Record<string, { label: string; variant: any; icon: any }> = {
      super_admin: { label: '超级管理员', variant: 'destructive', icon: Crown },
      admin: { label: '管理员', variant: 'default', icon: ShieldCheck },
      vip_user: { label: 'VIP用户', variant: 'secondary', icon: User },
      normal_user: { label: '普通用户', variant: 'outline', icon: User },
      trial_user: { label: '试用用户', variant: 'outline', icon: User },
    }

    const { label, variant, icon: Icon } = config[role] || config.normal_user

    return (
      <Badge variant={variant} className="gap-1">
        <Icon className="h-3 w-3" />
        {label}
      </Badge>
    )
  }

  /**
   * 格式化日期为本地时间字符串
   */
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN')
  }

  return (
    <>
        <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-2xl">用户管理</CardTitle>
                  <CardDescription>
                    管理系统用户和权限 ({total} 个用户)
                  </CardDescription>
                </div>
                <Button onClick={() => setIsCreateDialogOpen(true)}>
                  <Plus className="mr-2 h-4 w-4" />
                  创建用户
                </Button>
              </div>
            </CardHeader>

            <CardContent>
              {/* 搜索和筛选 */}
              <div className="flex gap-4 mb-6">
                <div className="flex-1 flex gap-2">
                  <Input
                    placeholder="搜索用户名或邮箱..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  />
                  <Button onClick={handleSearch} variant="secondary">
                    <Search className="h-4 w-4" />
                  </Button>
                </div>

                <Select value={roleFilter} onValueChange={setRoleFilter}>
                  <SelectTrigger className="w-40">
                    <SelectValue placeholder="角色筛选" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">全部角色</SelectItem>
                    <SelectItem value="super_admin">超级管理员</SelectItem>
                    <SelectItem value="admin">管理员</SelectItem>
                    <SelectItem value="vip_user">VIP用户</SelectItem>
                    <SelectItem value="normal_user">普通用户</SelectItem>
                    <SelectItem value="trial_user">试用用户</SelectItem>
                  </SelectContent>
                </Select>

                <Button onClick={loadUsers} variant="outline" size="icon">
                  <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                </Button>
              </div>

              {/* 用户表格 */}
              <div className="border rounded-lg">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>ID</TableHead>
                      <TableHead>用户名</TableHead>
                      <TableHead>邮箱</TableHead>
                      <TableHead>角色</TableHead>
                      <TableHead>状态</TableHead>
                      <TableHead>邮箱验证</TableHead>
                      <TableHead>配额</TableHead>
                      <TableHead>登录次数</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {loading ? (
                      <TableRow>
                        <TableCell colSpan={10} className="text-center py-8 text-gray-500">
                          加载中...
                        </TableCell>
                      </TableRow>
                    ) : users.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={10} className="text-center py-8 text-gray-500">
                          暂无用户数据
                        </TableCell>
                      </TableRow>
                    ) : (
                      users.map((user) => (
                        <TableRow key={user.id}>
                          <TableCell className="font-mono text-sm">{user.id}</TableCell>
                          <TableCell>
                            <div className="font-medium">{user.username}</div>
                            {user.full_name && (
                              <div className="text-xs text-gray-500">{user.full_name}</div>
                            )}
                          </TableCell>
                          <TableCell className="text-sm">{user.email}</TableCell>
                          <TableCell>{getRoleBadge(user.role)}</TableCell>
                          <TableCell>
                            {user.is_active ? (
                              <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                                活跃
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="bg-gray-50 text-gray-700 border-gray-200">
                                禁用
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            {user.is_email_verified ? (
                              <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                                已验证
                              </Badge>
                            ) : (
                              <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
                                未验证
                              </Badge>
                            )}
                          </TableCell>
                          <TableCell>
                            {user.quota ? (
                              <div className="text-xs space-y-1">
                                <div>回测: {user.quota.backtest_quota_used}/{user.quota.backtest_quota_total}</div>
                                <div>ML: {user.quota.ml_prediction_quota_used}/{user.quota.ml_prediction_quota_total}</div>
                              </div>
                            ) : (
                              <span className="text-gray-400">-</span>
                            )}
                          </TableCell>
                          <TableCell className="text-sm">{user.login_count}</TableCell>
                          <TableCell className="text-xs text-gray-500">
                            {formatDate(user.created_at)}
                          </TableCell>
                          <TableCell>
                            <div className="flex gap-2">
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => openEditDialog(user)}
                              >
                                <Pencil className="h-4 w-4 mr-1" />
                                编辑
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => openDeleteDialog(user)}
                                className="text-red-600 hover:text-red-700 hover:bg-red-50"
                              >
                                <Trash2 className="h-4 w-4 mr-1" />
                                删除
                              </Button>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))
                    )}
                  </TableBody>
                </Table>
              </div>

              {/* 分页 */}
              {total > pageSize && (
                <div className="flex items-center justify-between mt-4">
                  <div className="text-sm text-gray-600">
                    显示 {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, total)} / {total}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => Math.max(1, p - 1))}
                      disabled={page === 1}
                    >
                      上一页
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setPage(p => p + 1)}
                      disabled={page * pageSize >= total}
                    >
                      下一页
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* 创建用户对话框 */}
          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>创建新用户</DialogTitle>
                <DialogDescription>
                  填写用户的基本信息。密码需要至少8位，包含大小写字母和数字。
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="create-email">
                    邮箱 <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="create-email"
                    type="email"
                    placeholder="user@example.com"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="create-username">
                    用户名 <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="create-username"
                    placeholder="输入用户名"
                    value={formData.username}
                    onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="create-password">
                    密码 <span className="text-red-500">*</span>
                  </Label>
                  <Input
                    id="create-password"
                    type="password"
                    placeholder="至少8位，含大小写字母和数字"
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="create-full-name">全名</Label>
                  <Input
                    id="create-full-name"
                    placeholder="输入用户全名"
                    value={formData.full_name}
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="create-phone">手机号</Label>
                  <Input
                    id="create-phone"
                    placeholder="输入手机号"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="create-role">角色</Label>
                  <Select
                    value={formData.role}
                    onValueChange={(value) => setFormData({ ...formData, role: value })}
                  >
                    <SelectTrigger id="create-role">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="super_admin">超级管理员</SelectItem>
                      <SelectItem value="admin">管理员</SelectItem>
                      <SelectItem value="vip_user">VIP用户</SelectItem>
                      <SelectItem value="normal_user">普通用户</SelectItem>
                      <SelectItem value="trial_user">试用用户</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => {
                    setIsCreateDialogOpen(false)
                    resetForm()
                  }}
                  disabled={submitting}
                >
                  取消
                </Button>
                <Button onClick={handleCreate} disabled={submitting}>
                  {submitting ? '创建中...' : '创建'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          {/* 编辑用户对话框 */}
          <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>编辑用户</DialogTitle>
                <DialogDescription>
                  修改用户信息。用户名不可修改。
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-username">用户名</Label>
                  <Input
                    id="edit-username"
                    value={formData.username}
                    disabled
                    className="bg-gray-50"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-email">邮箱</Label>
                  <Input
                    id="edit-email"
                    type="email"
                    placeholder="user@example.com"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-full-name">全名</Label>
                  <Input
                    id="edit-full-name"
                    placeholder="输入用户全名"
                    value={formData.full_name}
                    onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-role">角色</Label>
                  <Select
                    value={formData.role}
                    onValueChange={(value) => setFormData({ ...formData, role: value })}
                  >
                    <SelectTrigger id="edit-role">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="super_admin">超级管理员</SelectItem>
                      <SelectItem value="admin">管理员</SelectItem>
                      <SelectItem value="vip_user">VIP用户</SelectItem>
                      <SelectItem value="normal_user">普通用户</SelectItem>
                      <SelectItem value="trial_user">试用用户</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex items-center justify-between space-x-2 py-2">
                  <div className="space-y-0.5">
                    <Label htmlFor="edit-email-verified">邮箱验证状态</Label>
                    <p className="text-sm text-gray-500">
                      是否已验证该用户的邮箱地址
                    </p>
                  </div>
                  <Switch
                    id="edit-email-verified"
                    checked={formData.is_email_verified}
                    onCheckedChange={(checked) =>
                      setFormData({ ...formData, is_email_verified: checked })
                    }
                  />
                </div>
              </div>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => {
                    setIsEditDialogOpen(false)
                    setSelectedUser(null)
                    resetForm()
                  }}
                  disabled={submitting}
                >
                  取消
                </Button>
                <Button onClick={handleEdit} disabled={submitting}>
                  {submitting ? '保存中...' : '保存'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          {/* 删除用户确认对话框 */}
          <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
            <DialogContent className="max-w-md">
              <DialogHeader>
                <DialogTitle>确认删除用户？</DialogTitle>
                <DialogDescription>
                  您即将删除用户 <span className="font-semibold">{selectedUser?.username}</span> ({selectedUser?.email})。
                  <br />
                  <span className="text-red-600 font-medium">此操作无法撤销，请谨慎操作。</span>
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button
                  variant="outline"
                  onClick={() => {
                    setIsDeleteDialogOpen(false)
                    setSelectedUser(null)
                  }}
                  disabled={submitting}
                >
                  取消
                </Button>
                <Button
                  onClick={handleDelete}
                  disabled={submitting}
                  className="bg-red-600 hover:bg-red-700"
                >
                  {submitting ? '删除中...' : '确认删除'}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
    </>
  )
}
