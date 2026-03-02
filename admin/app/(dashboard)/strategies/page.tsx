'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Plus, Search, Filter, Edit, Trash2, Play, Code, AlertCircle, Users } from 'lucide-react'
import { Strategy } from '@/types/strategy'
import { apiClient } from '@/lib/api-client'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { Switch } from '@/components/ui/switch'
import { Check } from 'lucide-react'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

// 策略类型标签颜色
const strategyTypeColors = {
  stock_selection: 'bg-blue-100 text-blue-800',
  entry: 'bg-green-100 text-green-800',
  exit: 'bg-red-100 text-red-800',
}

// 策略类型显示名称
const strategyTypeNames = {
  stock_selection: '选股策略',
  entry: '入场策略',
  exit: '离场策略',
}

// 来源类型标签颜色
const sourceTypeColors = {
  builtin: 'bg-gray-100 text-gray-800',
  ai: 'bg-purple-100 text-purple-800',
  custom: 'bg-yellow-100 text-yellow-800',
}

// 来源类型显示名称
const sourceTypeNames = {
  builtin: '系统内置',
  ai: 'AI生成',
  custom: '用户自定义',
}

// 验证状态标签颜色
const validationStatusColors = {
  pending: 'bg-gray-100 text-gray-800',
  passed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  validating: 'bg-yellow-100 text-yellow-800',
}

// 风险等级标签颜色
const riskLevelColors = {
  safe: 'bg-green-100 text-green-800',
  low: 'bg-blue-100 text-blue-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-red-100 text-red-800',
}

interface User {
  id: number
  username: string
  email: string
  full_name?: string
}

export default function StrategiesPage() {
  const router = useRouter()
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStrategyType, setFilterStrategyType] = useState<string>('')
  const [filterSourceType, setFilterSourceType] = useState<string>('')
  const [filterUserId, setFilterUserId] = useState<string>('')
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [totalCount, setTotalCount] = useState(0)

  // 用户编辑对话框状态
  const [editUserDialogOpen, setEditUserDialogOpen] = useState(false)
  const [editingStrategy, setEditingStrategy] = useState<Strategy | null>(null)
  const [selectedUserId, setSelectedUserId] = useState<string>('')
  const [users, setUsers] = useState<User[]>([])
  const [loadingUsers, setLoadingUsers] = useState(false)
  const [updatingUser, setUpdatingUser] = useState(false)
  const [userSearchTerm, setUserSearchTerm] = useState('')

  // 获取策略列表
  const fetchStrategies = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        page_size: '20',
      })

      if (searchTerm) params.append('search', searchTerm)
      if (filterStrategyType) params.append('strategy_type', filterStrategyType)
      if (filterSourceType) params.append('source_type', filterSourceType)
      if (filterUserId) params.append('user_id', filterUserId)

      const response = await fetch(`${API_BASE_URL}/api/strategies?${params}`, {
        headers: {
          'Content-Type': 'application/json',
        },
      })

      if (!response.ok) {
        throw new Error('获取策略列表失败')
      }

      const result = await response.json()
      if (result.success) {
        setStrategies(result.data)
        setTotalPages(result.meta.total_pages)
        setTotalCount(result.meta.total)
      }
    } catch (error) {
      console.error('获取策略列表失败:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStrategies()
  }, [currentPage, searchTerm, filterStrategyType, filterSourceType, filterUserId])

  /**
   * 获取用户列表（支持后端搜索）
   * @param searchQuery 搜索关键字，支持用户名、邮箱、全名搜索
   */
  const fetchUsers = async (searchQuery: string = '') => {
    setLoadingUsers(true)
    try {
      const params = new URLSearchParams({
        page: '1',
        page_size: '50',
      })

      if (searchQuery) {
        params.append('search', searchQuery)
      }

      const response = await apiClient.get<{
        success: boolean
        data: {
          users: User[]
          total: number
          page: number
          page_size: number
        }
      }>(`/api/users?${params}`)

      // 处理两种可能的API响应格式
      // 格式 1: { success: true, data: { users: [...] } }
      // 格式 2: { users: [...], total: ..., page: ... }
      let usersList: User[] = []

      if ('success' in response.data && response.data.success && 'data' in response.data) {
        usersList = response.data.data?.users || []
      } else if ('users' in response.data) {
        usersList = (response.data as any).users || []
      }

      setUsers(usersList)
    } catch (error) {
      console.error('获取用户列表失败:', error)
      setError('获取用户列表失败：' + error)
    } finally {
      setLoadingUsers(false)
    }
  }

  /**
   * 防抖搜索用户（300ms延迟）
   * 当用户输入搜索关键字时，延迟300ms后再发起API请求，避免频繁请求
   */
  useEffect(() => {
    if (!editUserDialogOpen) return

    const timer = setTimeout(() => {
      fetchUsers(userSearchTerm)
    }, 300)

    return () => clearTimeout(timer)
  }, [userSearchTerm, editUserDialogOpen])

  /**
   * 打开编辑用户对话框
   * 用户列表会由 useEffect 自动加载
   */
  const handleEditUser = (strategy: Strategy) => {
    setEditingStrategy(strategy)
    setSelectedUserId(strategy.user_id?.toString() || 'system')
    setUserSearchTerm('')
    setEditUserDialogOpen(true)
  }

  /**
   * 更新策略的用户归属
   * 支持分配给用户或设置为系统策略（user_id = null）
   */
  const handleUpdateUser = async () => {
    if (!editingStrategy) return

    setUpdatingUser(true)
    try {
      const userId = selectedUserId === 'system' ? null : parseInt(selectedUserId)

      await apiClient.put(`/api/strategies/${editingStrategy.id}`, {
        user_id: userId,
      })

      await fetchStrategies()
      setEditUserDialogOpen(false)
      setEditingStrategy(null)
    } catch (error) {
      console.error('更新策略用户失败:', error)
      setError('更新失败：' + error)
    } finally {
      setUpdatingUser(false)
    }
  }

  // 删除策略
  const handleDelete = async (id: number) => {
    if (!confirm('确定要删除这个策略吗？')) return

    try {
      const response = await fetch(`${API_BASE_URL}/api/strategies/${id}`, {
        method: 'DELETE',
      })

      if (!response.ok) {
        throw new Error('删除策略失败')
      }

      // 刷新列表
      fetchStrategies()
    } catch (error) {
      console.error('删除策略失败:', error)
      setError('删除失败：' + error)
    }
  }

  /**
   * 切换策略启用/禁用状态
   * 只有管理员可以控制策略的启用状态
   * 禁用的策略不会在前端策略中心显示
   */
  const handleToggleEnabled = async (strategy: Strategy) => {
    try {
      await apiClient.put(`/api/strategies/${strategy.id}`, {
        is_enabled: !strategy.is_enabled,
      })

      // 刷新列表以显示最新状态
      await fetchStrategies()
    } catch (error) {
      console.error('切换策略状态失败:', error)
      setError('切换状态失败：' + error)
    }
  }

  return (
    <div className="p-6">
      {/* 页面标题和操作按钮 */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">策略管理</h1>
          <p className="mt-1 text-sm text-gray-600">
            管理选股策略、入场策略和离场策略
          </p>
        </div>
        <button
          onClick={() => router.push('/strategies/new')}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
        >
          <Plus className="h-5 w-5" />
          创建策略
        </button>
      </div>

      {/* 搜索和过滤 */}
      <div className="mb-6 grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        {/* 搜索框 */}
        <div className="relative lg:col-span-2">
          <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            placeholder="搜索策略名称或描述..."
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value)
              setCurrentPage(1)
            }}
            className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>

        {/* 策略类型过滤 */}
        <Select
          value={filterStrategyType || 'all'}
          onValueChange={(value) => {
            setFilterStrategyType(value === 'all' ? '' : value)
            setCurrentPage(1)
          }}
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="所有策略类型" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">所有策略类型</SelectItem>
            <SelectItem value="stock_selection">选股策略</SelectItem>
            <SelectItem value="entry">入场策略</SelectItem>
            <SelectItem value="exit">离场策略</SelectItem>
          </SelectContent>
        </Select>

        {/* 来源类型过滤 */}
        <Select
          value={filterSourceType || 'all'}
          onValueChange={(value) => {
            setFilterSourceType(value === 'all' ? '' : value)
            setCurrentPage(1)
          }}
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="所有来源" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">所有来源</SelectItem>
            <SelectItem value="builtin">系统内置</SelectItem>
            <SelectItem value="ai">AI生成</SelectItem>
            <SelectItem value="custom">用户自定义</SelectItem>
          </SelectContent>
        </Select>

        {/* 用户ID过滤 */}
        <input
          type="text"
          placeholder="用户ID（空=系统策略）"
          value={filterUserId}
          onChange={(e) => {
            setFilterUserId(e.target.value)
            setCurrentPage(1)
          }}
          className="rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 p-4">
          <div className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-red-600" />
            <p className="text-red-800">{error}</p>
          </div>
        </div>
      )}

      {/* 统计信息 */}
      <div className="mb-4 text-sm text-gray-600">
        共找到 <span className="font-semibold">{totalCount}</span> 个策略
      </div>

      {/* 策略列表 */}
      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <div className="text-gray-500">加载中...</div>
        </div>
      ) : strategies.length === 0 ? (
        <div className="flex h-64 flex-col items-center justify-center text-gray-500">
          <Filter className="mb-2 h-12 w-12" />
          <p>未找到符合条件的策略</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  策略名称
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  类型
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  用户
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  验证状态
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  风险等级
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  启用状态
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  统计
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 bg-white">
              {strategies.map((strategy) => (
                <tr key={strategy.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex flex-col">
                      <div className="font-medium text-gray-900">
                        {strategy.display_name}
                      </div>
                      <div className="text-sm text-gray-500">{strategy.name}</div>
                      {strategy.description && (
                        <div className="mt-1 text-sm text-gray-600">
                          {strategy.description}
                        </div>
                      )}
                      {strategy.tags && strategy.tags.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {strategy.tags.map((tag, index) => (
                            <span
                              key={index}
                              className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
                        strategyTypeColors[strategy.strategy_type as keyof typeof strategyTypeColors] || 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {strategyTypeNames[strategy.strategy_type as keyof typeof strategyTypeNames] || strategy.strategy_type}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-sm text-gray-900">
                      {strategy.username || (
                        <span className="text-gray-500 italic">系统</span>
                      )}
                    </div>
                    {strategy.user_id && (
                      <div className="text-xs text-gray-500">ID: {strategy.user_id}</div>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
                        validationStatusColors[strategy.validation_status as keyof typeof validationStatusColors] || 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {strategy.validation_status}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
                        riskLevelColors[strategy.risk_level as keyof typeof riskLevelColors] || 'bg-gray-100 text-gray-800'
                      }`}
                    >
                      {strategy.risk_level}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <Switch
                        checked={strategy.is_enabled}
                        onCheckedChange={() => handleToggleEnabled(strategy)}
                      />
                      <span className="text-sm text-gray-600">
                        {strategy.is_enabled ? '已启用' : '已禁用'}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    <div>使用: {strategy.usage_count}</div>
                    <div>回测: {strategy.backtest_count}</div>
                    {strategy.avg_sharpe_ratio && (
                      <div>夏普: {Number(strategy.avg_sharpe_ratio).toFixed(2)}</div>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex gap-2">
                      <button
                        onClick={() => router.push(`/strategies/${strategy.id}`)}
                        className="text-blue-600 hover:text-blue-800"
                        title="查看详情"
                      >
                        <Code className="h-5 w-5" />
                      </button>
                      <button
                        onClick={() => router.push(`/strategies/${strategy.id}/edit`)}
                        className="text-yellow-600 hover:text-yellow-800"
                        title="编辑"
                      >
                        <Edit className="h-5 w-5" />
                      </button>
                      <button
                        onClick={() => handleEditUser(strategy)}
                        className="text-purple-600 hover:text-purple-800"
                        title="修改用户"
                      >
                        <Users className="h-5 w-5" />
                      </button>
                      {strategy.source_type !== 'builtin' && (
                        <button
                          onClick={() => handleDelete(strategy.id)}
                          className="text-red-600 hover:text-red-800"
                          title="删除"
                        >
                          <Trash2 className="h-5 w-5" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="mt-6 flex items-center justify-between">
          <div className="text-sm text-gray-600">
            第 {currentPage} 页，共 {totalPages} 页
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              上一页
            </button>
            <button
              onClick={() =>
                setCurrentPage((prev) => Math.min(totalPages, prev + 1))
              }
              disabled={currentPage === totalPages}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              下一页
            </button>
          </div>
        </div>
      )}

      {/* 编辑用户对话框 */}
      <Dialog open={editUserDialogOpen} onOpenChange={setEditUserDialogOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>修改策略用户</DialogTitle>
            <DialogDescription>
              为策略 "{editingStrategy?.display_name}" 分配或修改用户
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <div className="space-y-4">
              <div>
                <label className="mb-2 block text-sm font-medium text-gray-700">
                  选择用户（支持后端搜索）
                </label>

                {/* 搜索输入框 */}
                <div className="relative mb-2">
                  <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                  <input
                    type="text"
                    placeholder="搜索用户名、邮箱或全名..."
                    value={userSearchTerm}
                    onChange={(e) => setUserSearchTerm(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 py-2 pl-10 pr-4 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>

                {/* 用户列表 */}
                <div className="max-h-[300px] overflow-y-auto rounded-lg border border-gray-300">
                  {loadingUsers ? (
                    <div className="flex items-center justify-center py-8">
                      <div className="text-sm text-gray-500">搜索中...</div>
                    </div>
                  ) : (
                    <div className="divide-y divide-gray-200">
                      {/* 系统策略选项 */}
                      <div
                        onClick={() => setSelectedUserId('system')}
                        className={`flex cursor-pointer items-center gap-3 px-4 py-3 hover:bg-gray-50 ${
                          selectedUserId === 'system' ? 'bg-blue-50' : ''
                        }`}
                      >
                        <Check
                          className={`h-4 w-4 ${
                            selectedUserId === 'system' ? 'text-blue-600 opacity-100' : 'opacity-0'
                          }`}
                        />
                        <div>
                          <div className="font-medium text-gray-900">系统策略</div>
                          <div className="text-xs text-gray-500">无用户归属</div>
                        </div>
                      </div>

                      {/* 用户列表 */}
                      {users.length === 0 ? (
                        <div className="px-4 py-8 text-center text-sm text-gray-500">
                          {userSearchTerm ? '未找到匹配的用户' : '暂无用户'}
                        </div>
                      ) : (
                        users.map((user) => (
                          <div
                            key={user.id}
                            onClick={() => setSelectedUserId(user.id.toString())}
                            className={`flex cursor-pointer items-center gap-3 px-4 py-3 hover:bg-gray-50 ${
                              selectedUserId === user.id.toString() ? 'bg-blue-50' : ''
                            }`}
                          >
                            <Check
                              className={`h-4 w-4 ${
                                selectedUserId === user.id.toString()
                                  ? 'text-blue-600 opacity-100'
                                  : 'opacity-0'
                              }`}
                            />
                            <div className="flex-1">
                              <div className="font-medium text-gray-900">{user.username}</div>
                              <div className="text-xs text-gray-500">
                                {user.email}
                                {user.full_name && ` · ${user.full_name}`}
                              </div>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  )}
                </div>
              </div>

              <div className="rounded-lg bg-blue-50 p-3 text-sm text-blue-800">
                <div className="font-medium">当前选择：</div>
                <div className="mt-1">
                  {selectedUserId === 'system' ? (
                    <span className="italic">系统策略（无用户）</span>
                  ) : (
                    <>
                      {users.find(u => u.id.toString() === selectedUserId)?.username || '未选择'}
                      {selectedUserId && selectedUserId !== 'system' && ` (ID: ${selectedUserId})`}
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>

          <DialogFooter>
            <button
              type="button"
              onClick={() => setEditUserDialogOpen(false)}
              disabled={updatingUser}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              取消
            </button>
            <button
              type="button"
              onClick={handleUpdateUser}
              disabled={updatingUser || loadingUsers}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {updatingUser ? '保存中...' : '保存'}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
