'use client'

import { useState, useEffect } from 'react'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import AdminLayout from '@/components/layouts/AdminLayout'
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
import { Plus, Search, RefreshCw, User, ShieldCheck, Crown } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { toast } from 'sonner'

interface User {
  id: number
  email: string
  username: string
  role: string
  is_active: boolean
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

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState<string>('all')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const pageSize = 20

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

  // 角色徽章
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

  // 格式化日期
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('zh-CN')
  }

  return (
    <ProtectedRoute requireAdmin>
      <AdminLayout>
        <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-2xl">用户管理</CardTitle>
                  <CardDescription>
                    管理系统用户和权限 ({total} 个用户)
                  </CardDescription>
                </div>
                <Button>
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
                      <TableHead>配额</TableHead>
                      <TableHead>登录次数</TableHead>
                      <TableHead>创建时间</TableHead>
                      <TableHead>操作</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {loading ? (
                      <TableRow>
                        <TableCell colSpan={9} className="text-center py-8 text-gray-500">
                          加载中...
                        </TableCell>
                      </TableRow>
                    ) : users.length === 0 ? (
                      <TableRow>
                        <TableCell colSpan={9} className="text-center py-8 text-gray-500">
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
                            <Button variant="ghost" size="sm">
                              查看
                            </Button>
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
      </AdminLayout>
    </ProtectedRoute>
  )
}
