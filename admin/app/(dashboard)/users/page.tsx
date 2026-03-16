/**
 * 用户管理页面
 *
 * 功能：
 * - 用户列表展示（分页、搜索、筛选）
 * - 创建新用户（含表单验证）
 * - 编辑用户信息（邮箱、角色、邮箱验证状态等）
 * - 删除用户（含二次确认）
 * - 查看用户详细信息（配额使用情况、登录统计等）
 *
 * 响应式设计：
 * - 使用 DataTable 组件自动处理桌面/移动端切换
 * - 桌面端（≥768px）：表格视图
 * - 移动端（<768px）：卡片视图
 *
 * 优化：使用 React Query 管理数据状态
 */
'use client'

import { useState, useMemo, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, type Column } from '@/components/common/DataTable'
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Label } from '@/components/ui/label'
import { Plus, Search, RefreshCw, User as UserIcon, ShieldCheck, Crown, Pencil, Trash2, MoreVertical, Info } from 'lucide-react'
import { toast } from 'sonner'
import { useDebounce } from '@/hooks/use-debounce'
import {
  useUserList,
  useCreateUser,
  useUpdateUser,
  useDeleteUser,
  useToggleUserStatus,
  type User,
  type CreateUserDto,
  type UpdateUserDto,
} from '@/hooks/queries/use-users'

/**
 * 表单数据接口
 */
interface UserFormData {
  email: string
  username: string
  password: string
  full_name: string
  phone: string
  role: 'super_admin' | 'admin' | 'vip_user' | 'normal_user' | 'trial_user'
  is_email_verified: boolean
}

export default function UsersPage() {
  // 筛选和分页状态
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState<string>('all')
  const [page, setPage] = useState(1)
  const pageSize = 20

  // 使用防抖的搜索词
  const debouncedSearch = useDebounce(search, 500)

  // 构建查询参数
  const queryParams = useMemo(() => ({
    page,
    page_size: pageSize,
    search: debouncedSearch || undefined,
    role: roleFilter !== 'all' ? roleFilter as any : undefined,
  }), [page, debouncedSearch, roleFilter])

  // 使用 React Query Hooks
  const { data, isLoading, error, refetch } = useUserList(queryParams)
  const createUserMutation = useCreateUser()
  const updateUserMutation = useUpdateUser()
  const deleteUserMutation = useDeleteUser()
  const toggleStatusMutation = useToggleUserStatus()

  // 从 data 中提取用户列表和总数
  const users = data?.items || []
  const total = data?.total || 0

  // 对话框状态
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [isDetailDialogOpen, setIsDetailDialogOpen] = useState(false)
  const [selectedUser, setSelectedUser] = useState<User | null>(null)

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

  // 搜索
  const handleSearch = () => {
    setPage(1)
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

    const createData: CreateUserDto = {
      email: formData.email,
      username: formData.username,
      password: formData.password,
      role: formData.role as 'admin' | 'user',
      is_active: true,
    }

    createUserMutation.mutate(createData, {
      onSuccess: () => {
        setIsCreateDialogOpen(false)
        resetForm()
      }
    })
  }

  // 打开详情对话框
  const openDetailDialog = (user: User) => {
    setSelectedUser(user)
    setIsDetailDialogOpen(true)
  }

  // 打开编辑对话框
  const openEditDialog = (user: User) => {
    setSelectedUser(user)
    setFormData({
      email: user.email,
      username: user.username,
      password: '', // 密码保持为空，只在需要修改时填写
      full_name: '',
      phone: '',
      role: user.role as any,
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

    // 如果修改了密码，验证密码强度
    if (formData.password) {
      const passwordValidation = validatePassword(formData.password)
      if (!passwordValidation.valid) {
        toast.error(passwordValidation.message)
        return
      }
    }

    // 构建更新数据（只发送变更的字段）
    const updateData: UpdateUserDto = {
      role: formData.role,
    }

    if (formData.email && formData.email !== selectedUser.email) {
      updateData.email = formData.email
    }
    if (formData.password) {
      updateData.password = formData.password
    }

    updateUserMutation.mutate(
      { id: selectedUser.id, data: updateData },
      {
        onSuccess: () => {
          setIsEditDialogOpen(false)
          setSelectedUser(null)
          resetForm()
        }
      }
    )
  }

  // 打开删除对话框
  const openDeleteDialog = (user: User) => {
    setSelectedUser(user)
    setIsDeleteDialogOpen(true)
  }

  // 删除用户
  const handleDelete = async () => {
    if (!selectedUser) return

    deleteUserMutation.mutate(selectedUser.id, {
      onSuccess: () => {
        setIsDeleteDialogOpen(false)
        setSelectedUser(null)
      }
    })
  }

  // 切换用户状态
  const handleToggleStatus = useCallback((user: User) => {
    toggleStatusMutation.mutate({
      id: user.id,
      is_active: !user.is_active
    })
  }, [toggleStatusMutation])

  /**
   * 渲染角色徽章
   * 根据不同角色显示不同颜色和图标
   */
  const getRoleBadge = (role: string) => {
    const config: Record<string, { label: string; variant: any; icon: any }> = {
      super_admin: { label: '超级管理员', variant: 'destructive', icon: Crown },
      admin: { label: '管理员', variant: 'default', icon: ShieldCheck },
      vip_user: { label: 'VIP用户', variant: 'secondary', icon: UserIcon },
      user: { label: '普通用户', variant: 'outline', icon: UserIcon },
      normal_user: { label: '普通用户', variant: 'outline', icon: UserIcon },
      trial_user: { label: '试用用户', variant: 'outline', icon: UserIcon },
    }

    const { label, variant, icon: Icon } = config[role] || config.user

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

  // 定义表格列
  const columns: Column<User>[] = useMemo(() => [
    {
      key: 'id',
      header: 'ID',
      cellClassName: 'font-mono text-sm',
      width: 80,
    },
    {
      key: 'username',
      header: '用户名',
      accessor: (user) => (
        <div className="font-medium">{user.username}</div>
      ),
    },
    {
      key: 'email',
      header: '邮箱',
      cellClassName: 'text-sm',
    },
    {
      key: 'role',
      header: '角色',
      accessor: (user) => getRoleBadge(user.role),
    },
    {
      key: 'is_active',
      header: '状态',
      accessor: (user) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.stopPropagation()
            handleToggleStatus(user)
          }}
          disabled={toggleStatusMutation.isPending}
        >
          {user.is_active ? (
            <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
              活跃
            </Badge>
          ) : (
            <Badge variant="outline" className="bg-gray-50 text-gray-700 border-gray-200">
              禁用
            </Badge>
          )}
        </Button>
      ),
    },
    {
      key: 'is_email_verified',
      header: '邮箱验证',
      accessor: (user) => (
        user.is_email_verified ? (
          <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
            已验证
          </Badge>
        ) : (
          <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
            未验证
          </Badge>
        )
      ),
      hideOnMobile: true,
    },
  ], [toggleStatusMutation.isPending, handleToggleStatus])

  // 移动端卡片渲染
  const mobileCard = useCallback((user: User) => (
    <div className="border rounded-lg p-4 bg-white space-y-3">
      {/* 顶部：用户名和操作按钮 */}
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-base truncate">{user.username}</div>
        </div>
        <div className="flex gap-1 ml-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => openEditDialog(user)}
            className="h-8 w-8 shrink-0"
          >
            <Pencil className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => openDeleteDialog(user)}
            className="h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50 shrink-0"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* 邮箱 */}
      <div className="text-sm text-gray-600 break-all">{user.email}</div>

      {/* 徽章：角色、状态、邮箱验证 */}
      <div className="flex flex-wrap gap-2">
        {getRoleBadge(user.role)}
        {user.is_active ? (
          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
            活跃
          </Badge>
        ) : (
          <Badge variant="outline" className="bg-gray-50 text-gray-700 border-gray-200">
            禁用
          </Badge>
        )}
        {user.is_email_verified ? (
          <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
            已验证
          </Badge>
        ) : (
          <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
            未验证
          </Badge>
        )}
      </div>

      {/* 配额信息 */}
      {user.quota && (
        <div className="text-sm space-y-1 bg-gray-50 rounded p-2">
          <div className="font-medium text-gray-700">配额使用情况</div>
          <div className="text-xs text-gray-600">
            配额: {user.quota.backtest_quota_used}/{user.quota.backtest_quota_total}
          </div>
        </div>
      )}

      {/* 底部信息：ID、创建时间 */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 pt-2 border-t">
        <div>ID: <span className="font-mono">{user.id}</span></div>
        <div className="w-full sm:w-auto">创建于: {formatDate(user.created_at)}</div>
      </div>
    </div>
  ), [])

  // 操作列渲染
  const actions = useCallback((user: User) => (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <MoreVertical className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => openDetailDialog(user)}>
          <Info className="mr-2 h-4 w-4" />
          详情
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => openEditDialog(user)}>
          <Pencil className="mr-2 h-4 w-4" />
          编辑
        </DropdownMenuItem>
        <DropdownMenuItem
          onClick={() => openDeleteDialog(user)}
          className="text-red-600 focus:text-red-600"
        >
          <Trash2 className="mr-2 h-4 w-4" />
          删除
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  ), [])

  // 处理错误
  if (error) {
    toast.error('加载用户列表失败: ' + error.message)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="用户管理"
        description={`管理系统用户和权限 (${total} 个用户)`}
        actions={
          <Button onClick={() => setIsCreateDialogOpen(true)} className="w-full sm:w-auto">
            <Plus className="mr-2 h-4 w-4" />
            创建用户
          </Button>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle>用户列表</CardTitle>
        </CardHeader>

        <CardContent>
          {/* 搜索和筛选 */}
          <div className="flex flex-col sm:flex-row gap-3 mb-6">
            <div className="flex-1 flex gap-2">
              <Input
                placeholder="搜索用户名或邮箱..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              />
              <Button onClick={handleSearch} variant="secondary" size="icon" className="shrink-0">
                <Search className="h-4 w-4" />
              </Button>
            </div>

            <div className="flex gap-2">
              <Select value={roleFilter} onValueChange={setRoleFilter}>
                <SelectTrigger className="w-full sm:w-40">
                  <SelectValue placeholder="角色筛选" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部角色</SelectItem>
                  <SelectItem value="admin">管理员</SelectItem>
                  <SelectItem value="user">普通用户</SelectItem>
                </SelectContent>
              </Select>

              <Button
                onClick={() => refetch()}
                variant="outline"
                size="icon"
                className="shrink-0"
                disabled={isLoading}
              >
                <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
              </Button>
            </div>
          </div>

          {/* 用户列表 - 使用 DataTable 组件 */}
          <DataTable
            data={users}
            columns={columns}
            loading={isLoading}
            emptyMessage="暂无用户数据"
            loadingMessage="加载中..."
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: setPage,
            }}
            actions={actions}
            mobileCard={mobileCard}
            rowKey={(user) => user.id}
          />
        </CardContent>
      </Card>

      {/* 创建用户对话框 */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-md max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>创建新用户</DialogTitle>
            <DialogDescription>
              填写用户的基本信息。密码需要至少8位，包含大小写字母和数字。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4 px-2 overflow-y-auto flex-1">
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
              <Label htmlFor="create-role">角色</Label>
              <Select
                value={formData.role}
                onValueChange={(value: any) => setFormData({ ...formData, role: value })}
              >
                <SelectTrigger id="create-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">管理员</SelectItem>
                  <SelectItem value="user">普通用户</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter className="flex-row gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setIsCreateDialogOpen(false)
                resetForm()
              }}
              disabled={createUserMutation.isPending}
              className="flex-1"
            >
              取消
            </Button>
            <Button
              onClick={handleCreate}
              disabled={createUserMutation.isPending}
              className="flex-1"
            >
              {createUserMutation.isPending ? '创建中...' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 编辑用户对话框 */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-md max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>编辑用户</DialogTitle>
            <DialogDescription>
              修改用户信息。用户名不可修改。
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4 px-2 overflow-y-auto flex-1">
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
              <Label htmlFor="edit-password">新密码（留空表示不修改）</Label>
              <Input
                id="edit-password"
                type="password"
                placeholder="至少8位，含大小写字母和数字"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-role">角色</Label>
              <Select
                value={formData.role}
                onValueChange={(value: any) => setFormData({ ...formData, role: value })}
              >
                <SelectTrigger id="edit-role">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="admin">管理员</SelectItem>
                  <SelectItem value="user">普通用户</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter className="flex-row gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setIsEditDialogOpen(false)
                setSelectedUser(null)
                resetForm()
              }}
              disabled={updateUserMutation.isPending}
              className="flex-1"
            >
              取消
            </Button>
            <Button
              onClick={handleEdit}
              disabled={updateUserMutation.isPending}
              className="flex-1"
            >
              {updateUserMutation.isPending ? '保存中...' : '保存'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 删除用户确认对话框 */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>确认删除用户？</DialogTitle>
            <DialogDescription className="space-y-2">
              <span className="block">
                您即将删除用户 <span className="font-semibold">{selectedUser?.username}</span>
              </span>
              <span className="block text-sm break-all">({selectedUser?.email})</span>
              <span className="block text-red-600 font-medium mt-2">
                此操作无法撤销，请谨慎操作。
              </span>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setIsDeleteDialogOpen(false)
                setSelectedUser(null)
              }}
              disabled={deleteUserMutation.isPending}
              className="w-full sm:w-auto"
            >
              取消
            </Button>
            <Button
              onClick={handleDelete}
              disabled={deleteUserMutation.isPending}
              className="bg-red-600 hover:bg-red-700 w-full sm:w-auto"
            >
              {deleteUserMutation.isPending ? '删除中...' : '确认删除'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 用户详情对话框 */}
      <Dialog open={isDetailDialogOpen} onOpenChange={setIsDetailDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>用户详情</DialogTitle>
            <DialogDescription>
              查看用户的完整信息
            </DialogDescription>
          </DialogHeader>
          {selectedUser && (
            <div className="space-y-6 py-4 overflow-y-auto flex-1">
              {/* 基本信息 */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-gray-900 border-b pb-2">基本信息</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs text-gray-500">用户ID</Label>
                    <div className="mt-1 font-mono text-sm">{selectedUser.id}</div>
                  </div>
                  <div>
                    <Label className="text-xs text-gray-500">用户名</Label>
                    <div className="mt-1 font-medium text-sm">{selectedUser.username}</div>
                  </div>
                  <div>
                    <Label className="text-xs text-gray-500">邮箱</Label>
                    <div className="mt-1 text-sm break-all">{selectedUser.email}</div>
                  </div>
                  <div>
                    <Label className="text-xs text-gray-500">角色</Label>
                    <div className="mt-1">{getRoleBadge(selectedUser.role)}</div>
                  </div>
                  <div>
                    <Label className="text-xs text-gray-500">账号状态</Label>
                    <div className="mt-1">
                      {selectedUser.is_active ? (
                        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                          活跃
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="bg-gray-50 text-gray-700 border-gray-200">
                          禁用
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs text-gray-500">邮箱验证</Label>
                    <div className="mt-1">
                      {selectedUser.is_email_verified ? (
                        <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                          已验证
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
                          未验证
                        </Badge>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* 配额信息 */}
              {selectedUser.quota && (
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-gray-900 border-b pb-2">配额使用情况</h3>
                  <div className="bg-gray-50 rounded-lg p-4">
                    <Label className="text-xs text-gray-500">配额使用情况</Label>
                    <div className="mt-2 space-y-3">
                      <div className="space-y-2">
                        <div className="flex justify-between items-baseline">
                          <span className="text-sm text-gray-600">回测配额</span>
                          <span className="text-sm font-semibold">
                            {selectedUser.quota.backtest_quota_used || 0}/{selectedUser.quota.backtest_quota_total || 0}
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-500 h-2 rounded-full"
                            style={{
                              width: `${Math.min(((selectedUser.quota.backtest_quota_used || 0) / (selectedUser.quota.backtest_quota_total || 1)) * 100, 100)}%`
                            }}
                          ></div>
                        </div>
                      </div>
                      <div className="space-y-2">
                        <div className="flex justify-between items-baseline">
                          <span className="text-sm text-gray-600">预测配额</span>
                          <span className="text-sm font-semibold">
                            {selectedUser.quota.ml_prediction_quota_used || 0}/{selectedUser.quota.ml_prediction_quota_total || 0}
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-green-500 h-2 rounded-full"
                            style={{
                              width: `${Math.min(((selectedUser.quota.ml_prediction_quota_used || 0) / (selectedUser.quota.ml_prediction_quota_total || 1)) * 100, 100)}%`
                            }}
                          ></div>
                        </div>
                      </div>
                      <div className="space-y-2">
                        <div className="flex justify-between items-baseline">
                          <span className="text-sm text-gray-600">策略数量</span>
                          <span className="text-sm font-semibold">
                            {selectedUser.quota.current_strategies || 0}/{selectedUser.quota.max_strategies || 0}
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-purple-500 h-2 rounded-full"
                            style={{
                              width: `${Math.min(((selectedUser.quota.current_strategies || 0) / (selectedUser.quota.max_strategies || 1)) * 100, 100)}%`
                            }}
                          ></div>
                        </div>
                      </div>
                      <div className="text-xs text-gray-500 mt-2">
                        {selectedUser.quota.backtest_quota_reset_at && (
                          <div>回测配额重置: {new Date(selectedUser.quota.backtest_quota_reset_at).toLocaleString('zh-CN')}</div>
                        )}
                        {selectedUser.quota.ml_prediction_quota_reset_at && (
                          <div>预测配额重置: {new Date(selectedUser.quota.ml_prediction_quota_reset_at).toLocaleString('zh-CN')}</div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* 时间信息 */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-gray-900 border-b pb-2">时间信息</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs text-gray-500">创建时间</Label>
                    <div className="mt-1 text-sm">{formatDate(selectedUser.created_at)}</div>
                  </div>
                  <div>
                    <Label className="text-xs text-gray-500">更新时间</Label>
                    <div className="mt-1 text-sm">{formatDate(selectedUser.updated_at)}</div>
                  </div>
                  {selectedUser.last_login_at && (
                    <div>
                      <Label className="text-xs text-gray-500">最后登录</Label>
                      <div className="mt-1 text-sm">{formatDate(selectedUser.last_login_at)}</div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setIsDetailDialogOpen(false)
                setSelectedUser(null)
              }}
              className="w-full sm:w-auto"
            >
              关闭
            </Button>
            <Button
              onClick={() => {
                setIsDetailDialogOpen(false)
                if (selectedUser) {
                  openEditDialog(selectedUser)
                }
              }}
              className="w-full sm:w-auto"
            >
              <Pencil className="mr-2 h-4 w-4" />
              编辑用户
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}