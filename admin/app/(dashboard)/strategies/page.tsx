/**
 * 策略管理页面
 *
 * 功能：
 * - 策略列表展示（分页、搜索、多维度筛选）
 * - 策略状态管理（启用/禁用、发布状态控制）
 * - 用户归属管理（分配策略给用户或设为系统策略）
 * - 策略审核流程（待审核列表、发布审核、取消发布）
 * - 策略操作（查看详情、编辑、删除）
 *
 * 响应式设计：
 * - 桌面端（≥768px）：表格视图，完整信息展示
 * - 移动端（<768px）：卡片视图，优化触控操作
 * - 搜索和过滤：自适应网格布局
 * - 对话框：支持小屏幕滚动，自适应高度
 */
'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Plus, Search, Filter, Edit, Trash2, Code, AlertCircle, Users, ClipboardList, Ban, MoreVertical, Info } from 'lucide-react'
import { Strategy } from '@/types/strategy'
import { apiClient } from '@/lib/api-client'
import logger from '@/lib/logger'
import PublishStatusBadge from '@/components/strategies/PublishStatusBadge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
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
  const [filterPublishStatus, setFilterPublishStatus] = useState<string>('')
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

  // 详情对话框状态
  const [isDetailDialogOpen, setIsDetailDialogOpen] = useState(false)
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null)

  // 获取策略列表
  const fetchStrategies = useCallback(async () => {
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
      if (filterPublishStatus) params.append('publish_status', filterPublishStatus)

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
      logger.error('获取策略列表失败', error)
    } finally {
      setLoading(false)
    }
  }, [currentPage, searchTerm, filterStrategyType, filterSourceType, filterUserId, filterPublishStatus])

  useEffect(() => {
    fetchStrategies()
  }, [fetchStrategies])

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

      if (response.data && 'success' in response.data && response.data.success && 'data' in response.data) {
        usersList = response.data.data?.users || []
      } else if (response.data && 'users' in response.data) {
        usersList = (response.data as any).users || []
      }

      setUsers(usersList)
    } catch (error) {
      logger.error('获取用户列表失败', error)
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
   * 打开详情对话框
   */
  const openDetailDialog = (strategy: Strategy) => {
    setSelectedStrategy(strategy)
    setIsDetailDialogOpen(true)
  }

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
      logger.error('更新策略用户失败', error)
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
      logger.error('删除策略失败', error)
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
      logger.error('切换策略状态失败', error)
      setError('切换状态失败：' + error)
    }
  }

  /**
   * 取消策略发布
   * 将已发布的策略撤回到草稿状态
   */
  const handleUnpublish = async (strategy: Strategy) => {
    if (!confirm(`确定要取消发布策略 "${strategy.display_name}" 吗？\n\n取消后策略将变为草稿状态，并自动禁用。用户需要重新申请发布。`)) {
      return
    }

    try {
      await apiClient.unpublishStrategy(strategy.id)
      alert('策略已取消发布')
      await fetchStrategies()
    } catch (error: any) {
      logger.error('取消发布失败', error)
      alert(error.response?.data?.detail || '取消发布失败，请稍后重试')
    }
  }

  return (
    <div className="p-4 sm:p-6">
      {/* 页面标题和操作按钮 */}
      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">策略管理</h1>
          <p className="mt-1 text-sm text-gray-600">
            管理选股策略、入场策略和离场策略
          </p>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row sm:gap-3">
          <button
            onClick={() => router.push('/strategies/pending-review')}
            className="flex items-center justify-center gap-2 rounded-lg bg-yellow-600 px-4 py-2 text-white hover:bg-yellow-700"
          >
            <ClipboardList className="h-5 w-5" />
            待审核列表
          </button>
          <button
            onClick={() => router.push('/strategies/new')}
            className="flex items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
          >
            <Plus className="h-5 w-5" />
            创建策略
          </button>
        </div>
      </div>

      {/* 搜索和过滤 */}
      <div className="mb-6 space-y-3">
        {/* 搜索框 */}
        <div className="relative">
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

        {/* 过滤器 - 响应式网格布局 */}
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
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

          {/* 发布状态过滤 */}
          <Select
            value={filterPublishStatus || 'all'}
            onValueChange={(value) => {
              setFilterPublishStatus(value === 'all' ? '' : value)
              setCurrentPage(1)
            }}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="所有发布状态" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">所有发布状态</SelectItem>
              <SelectItem value="draft">草稿</SelectItem>
              <SelectItem value="pending_review">待审核</SelectItem>
              <SelectItem value="approved">已发布</SelectItem>
              <SelectItem value="rejected">已拒绝</SelectItem>
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
        <>
          {/* 桌面端表格视图 - 隐藏在小屏幕 */}
          <div className="hidden md:block overflow-hidden rounded-lg border border-gray-200 bg-white shadow">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 w-[25%]">
                    策略名称
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 whitespace-nowrap">
                    类型
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 whitespace-nowrap">
                    用户
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 whitespace-nowrap">
                    验证状态
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 whitespace-nowrap">
                    风险等级
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 whitespace-nowrap">
                    发布状态
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 whitespace-nowrap">
                    启用
                  </th>
                  <th className="px-3 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 whitespace-nowrap">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {strategies.map((strategy) => (
                  <tr key={strategy.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3">
                      <div className="flex flex-col max-w-md">
                        <div className="font-medium text-sm text-gray-900 truncate">
                          {strategy.display_name}
                        </div>
                        <div className="text-xs text-gray-500 truncate">{strategy.name}</div>
                        {strategy.description && (
                          <div className="mt-1 text-xs text-gray-600 line-clamp-2">
                            {strategy.description}
                          </div>
                        )}
                        {strategy.tags && strategy.tags.length > 0 && (
                          <div className="mt-1 flex flex-wrap gap-1">
                            {strategy.tags.slice(0, 3).map((tag, index) => (
                              <span
                                key={index}
                                className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
                              >
                                {tag}
                              </span>
                            ))}
                            {strategy.tags.length > 3 && (
                              <span className="text-xs text-gray-500">+{strategy.tags.length - 3}</span>
                            )}
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap">
                      <span
                        className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold whitespace-nowrap ${
                          strategyTypeColors[strategy.strategy_type as keyof typeof strategyTypeColors] || 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {strategyTypeNames[strategy.strategy_type as keyof typeof strategyTypeNames] || strategy.strategy_type}
                      </span>
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap">
                      <div className="text-sm text-gray-900">
                        {strategy.username || (
                          <span className="text-gray-500 italic">系统</span>
                        )}
                      </div>
                      {strategy.user_id && (
                        <div className="text-xs text-gray-500">ID: {strategy.user_id}</div>
                      )}
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap">
                      <span
                        className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold whitespace-nowrap ${
                          validationStatusColors[strategy.validation_status as keyof typeof validationStatusColors] || 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {strategy.validation_status}
                      </span>
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap">
                      <span
                        className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold whitespace-nowrap ${
                          riskLevelColors[strategy.risk_level as keyof typeof riskLevelColors] || 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {strategy.risk_level}
                      </span>
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap">
                      <PublishStatusBadge
                        status={strategy.publish_status as any}
                        size="sm"
                      />
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap">
                      <Switch
                        checked={strategy.is_enabled}
                        onCheckedChange={() => handleToggleEnabled(strategy)}
                      />
                    </td>
                    <td className="px-3 py-3 whitespace-nowrap">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => openDetailDialog(strategy)}>
                            <Info className="mr-2 h-4 w-4" />
                            详情
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => router.push(`/strategies/${strategy.id}`)}>
                            <Code className="mr-2 h-4 w-4" />
                            查看代码
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => router.push(`/strategies/${strategy.id}/edit`)}>
                            <Edit className="mr-2 h-4 w-4" />
                            编辑
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleEditUser(strategy)}>
                            <Users className="mr-2 h-4 w-4" />
                            修改用户
                          </DropdownMenuItem>
                          {strategy.publish_status === 'approved' && (
                            <DropdownMenuItem onClick={() => handleUnpublish(strategy)}>
                              <Ban className="mr-2 h-4 w-4" />
                              取消发布
                            </DropdownMenuItem>
                          )}
                          {strategy.source_type !== 'builtin' && (
                            <DropdownMenuItem
                              onClick={() => handleDelete(strategy.id)}
                              className="text-red-600 focus:text-red-600"
                            >
                              <Trash2 className="mr-2 h-4 w-4" />
                              删除
                            </DropdownMenuItem>
                          )}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 移动端卡片视图 - 仅在小屏幕显示 */}
          <div className="md:hidden space-y-4">
            {strategies.map((strategy) => (
              <div key={strategy.id} className="border rounded-lg p-4 bg-white space-y-3 shadow">
                {/* 顶部：策略名称 */}
                <div className="space-y-1">
                  <div className="font-semibold text-base text-gray-900">
                    {strategy.display_name}
                  </div>
                  <div className="text-sm text-gray-500">{strategy.name}</div>
                  {strategy.description && (
                    <div className="text-sm text-gray-600 mt-2">
                      {strategy.description}
                    </div>
                  )}
                </div>

                {/* 标签 */}
                {strategy.tags && strategy.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1">
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

                {/* 徽章组：类型、验证状态、风险、发布状态 */}
                <div className="flex flex-wrap gap-2">
                  <span
                    className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
                      strategyTypeColors[strategy.strategy_type as keyof typeof strategyTypeColors] || 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {strategyTypeNames[strategy.strategy_type as keyof typeof strategyTypeNames] || strategy.strategy_type}
                  </span>
                  <span
                    className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
                      validationStatusColors[strategy.validation_status as keyof typeof validationStatusColors] || 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {strategy.validation_status}
                  </span>
                  <span
                    className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
                      riskLevelColors[strategy.risk_level as keyof typeof riskLevelColors] || 'bg-gray-100 text-gray-800'
                    }`}
                  >
                    {strategy.risk_level}
                  </span>
                  <PublishStatusBadge
                    status={strategy.publish_status as any}
                    size="sm"
                  />
                </div>

                {/* 用户信息 */}
                <div className="text-sm bg-gray-50 rounded p-2">
                  <span className="text-gray-600">用户：</span>
                  <span className="font-medium text-gray-900 ml-1">
                    {strategy.username || <span className="text-gray-500 italic">系统</span>}
                  </span>
                  {strategy.user_id && (
                    <span className="text-xs text-gray-500 ml-2">ID: {strategy.user_id}</span>
                  )}
                </div>

                {/* 启用状态 */}
                <div className="flex items-center justify-between bg-gray-50 rounded p-2">
                  <span className="text-sm text-gray-600">启用状态</span>
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={strategy.is_enabled}
                      onCheckedChange={() => handleToggleEnabled(strategy)}
                    />
                    <span className="text-sm text-gray-600">
                      {strategy.is_enabled ? '已启用' : '已禁用'}
                    </span>
                  </div>
                </div>

                {/* 统计信息 */}
                <div className="text-sm space-y-1 bg-blue-50 rounded p-2">
                  <div className="font-medium text-gray-700">统计数据</div>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-600">
                    <div>使用: {strategy.usage_count}次</div>
                    <div>回测: {strategy.backtest_count}次</div>
                    {strategy.avg_sharpe_ratio && (
                      <div>夏普比率: {Number(strategy.avg_sharpe_ratio).toFixed(2)}</div>
                    )}
                  </div>
                </div>

                {/* 操作按钮 */}
                <div className="flex flex-wrap gap-2 pt-2 border-t">
                  <button
                    onClick={() => router.push(`/strategies/${strategy.id}`)}
                    className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-blue-50 px-3 py-2 text-sm font-medium text-blue-600 hover:bg-blue-100"
                  >
                    <Code className="h-4 w-4" />
                    详情
                  </button>
                  <button
                    onClick={() => router.push(`/strategies/${strategy.id}/edit`)}
                    className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-yellow-50 px-3 py-2 text-sm font-medium text-yellow-600 hover:bg-yellow-100"
                  >
                    <Edit className="h-4 w-4" />
                    编辑
                  </button>
                  <button
                    onClick={() => handleEditUser(strategy)}
                    className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-purple-50 px-3 py-2 text-sm font-medium text-purple-600 hover:bg-purple-100"
                  >
                    <Users className="h-4 w-4" />
                    用户
                  </button>
                  {strategy.publish_status === 'approved' && (
                    <button
                      onClick={() => handleUnpublish(strategy)}
                      className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-orange-50 px-3 py-2 text-sm font-medium text-orange-600 hover:bg-orange-100"
                    >
                      <Ban className="h-4 w-4" />
                      取消发布
                    </button>
                  )}
                  {strategy.source_type !== 'builtin' && (
                    <button
                      onClick={() => handleDelete(strategy.id)}
                      className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-red-50 px-3 py-2 text-sm font-medium text-red-600 hover:bg-red-100"
                    >
                      <Trash2 className="h-4 w-4" />
                      删除
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* 分页 */}
      {totalPages > 1 && (
        <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="text-sm text-gray-600 order-2 sm:order-1">
            第 {currentPage} 页，共 {totalPages} 页
          </div>
          <div className="flex gap-2 order-1 sm:order-2">
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
        <DialogContent className="max-w-md max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>修改策略用户</DialogTitle>
            <DialogDescription>
              为策略 &ldquo;{editingStrategy?.display_name}&rdquo; 分配或修改用户
            </DialogDescription>
          </DialogHeader>

          <div className="py-4 px-2 overflow-y-auto flex-1">
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
                <div className="max-h-[250px] overflow-y-auto rounded-lg border border-gray-300">
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
                          className={`h-4 w-4 shrink-0 ${
                            selectedUserId === 'system' ? 'text-blue-600 opacity-100' : 'opacity-0'
                          }`}
                        />
                        <div className="min-w-0">
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
                              className={`h-4 w-4 shrink-0 ${
                                selectedUserId === user.id.toString()
                                  ? 'text-blue-600 opacity-100'
                                  : 'opacity-0'
                              }`}
                            />
                            <div className="flex-1 min-w-0">
                              <div className="font-medium text-gray-900 truncate">{user.username}</div>
                              <div className="text-xs text-gray-500 truncate">
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
                <div className="mt-1 break-all">
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

          <DialogFooter className="flex-row gap-2">
            <button
              type="button"
              onClick={() => setEditUserDialogOpen(false)}
              disabled={updatingUser}
              className="flex-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              取消
            </button>
            <button
              type="button"
              onClick={handleUpdateUser}
              disabled={updatingUser || loadingUsers}
              className="flex-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {updatingUser ? '保存中...' : '保存'}
            </button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 策略详情对话框 */}
      <Dialog open={isDetailDialogOpen} onOpenChange={setIsDetailDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>策略详情</DialogTitle>
            <DialogDescription>
              查看策略的完整信息
            </DialogDescription>
          </DialogHeader>
          {selectedStrategy && (
            <div className="space-y-6 py-4 overflow-y-auto flex-1">
              {/* 基本信息 */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-gray-900 border-b pb-2">基本信息</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs text-gray-500">策略ID</Label>
                    <div className="mt-1 font-mono text-sm">{selectedStrategy.id}</div>
                  </div>
                  <div>
                    <Label className="text-xs text-gray-500">显示名称</Label>
                    <div className="mt-1 font-medium text-sm">{selectedStrategy.display_name}</div>
                  </div>
                  <div>
                    <Label className="text-xs text-gray-500">策略名称</Label>
                    <div className="mt-1 text-sm font-mono">{selectedStrategy.name}</div>
                  </div>
                  <div>
                    <Label className="text-xs text-gray-500">策略类型</Label>
                    <div className="mt-1">
                      <span
                        className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
                          strategyTypeColors[selectedStrategy.strategy_type as keyof typeof strategyTypeColors] || 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {strategyTypeNames[selectedStrategy.strategy_type as keyof typeof strategyTypeNames] || selectedStrategy.strategy_type}
                      </span>
                    </div>
                  </div>
                  <div className="sm:col-span-2">
                    <Label className="text-xs text-gray-500">描述</Label>
                    <div className="mt-1 text-sm">{selectedStrategy.description || '-'}</div>
                  </div>
                  {selectedStrategy.tags && selectedStrategy.tags.length > 0 && (
                    <div className="sm:col-span-2">
                      <Label className="text-xs text-gray-500">标签</Label>
                      <div className="mt-1 flex flex-wrap gap-1">
                        {selectedStrategy.tags.map((tag, index) => (
                          <span
                            key={index}
                            className="rounded bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* 状态信息 */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-gray-900 border-b pb-2">状态信息</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs text-gray-500">发布状态</Label>
                    <div className="mt-1">
                      <PublishStatusBadge
                        status={selectedStrategy.publish_status as any}
                        size="sm"
                      />
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs text-gray-500">启用状态</Label>
                    <div className="mt-1 text-sm">
                      {selectedStrategy.is_enabled ? '已启用' : '已禁用'}
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs text-gray-500">验证状态</Label>
                    <div className="mt-1">
                      <span
                        className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
                          validationStatusColors[selectedStrategy.validation_status as keyof typeof validationStatusColors] || 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {selectedStrategy.validation_status}
                      </span>
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs text-gray-500">风险等级</Label>
                    <div className="mt-1">
                      <span
                        className={`inline-flex rounded-full px-2 py-1 text-xs font-semibold ${
                          riskLevelColors[selectedStrategy.risk_level as keyof typeof riskLevelColors] || 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {selectedStrategy.risk_level}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* 用户信息 */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-gray-900 border-b pb-2">用户信息</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs text-gray-500">归属用户</Label>
                    <div className="mt-1 text-sm">
                      {selectedStrategy.username || <span className="text-gray-500 italic">系统策略</span>}
                    </div>
                  </div>
                  {selectedStrategy.user_id && (
                    <div>
                      <Label className="text-xs text-gray-500">用户ID</Label>
                      <div className="mt-1 font-mono text-sm">{selectedStrategy.user_id}</div>
                    </div>
                  )}
                </div>
              </div>

              {/* 统计信息 */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-gray-900 border-b pb-2">统计数据</h3>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <div className="bg-blue-50 rounded-lg p-4">
                    <Label className="text-xs text-gray-500">使用次数</Label>
                    <div className="mt-2 text-2xl font-semibold text-blue-700">
                      {selectedStrategy.usage_count}
                    </div>
                  </div>
                  <div className="bg-green-50 rounded-lg p-4">
                    <Label className="text-xs text-gray-500">回测次数</Label>
                    <div className="mt-2 text-2xl font-semibold text-green-700">
                      {selectedStrategy.backtest_count}
                    </div>
                  </div>
                  {selectedStrategy.avg_sharpe_ratio && (
                    <div className="bg-purple-50 rounded-lg p-4">
                      <Label className="text-xs text-gray-500">平均夏普比率</Label>
                      <div className="mt-2 text-2xl font-semibold text-purple-700">
                        {Number(selectedStrategy.avg_sharpe_ratio).toFixed(2)}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* 时间信息 */}
              {selectedStrategy.created_at && (
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold text-gray-900 border-b pb-2">时间信息</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div>
                      <Label className="text-xs text-gray-500">创建时间</Label>
                      <div className="mt-1 text-sm">
                        {new Date(selectedStrategy.created_at).toLocaleString('zh-CN')}
                      </div>
                    </div>
                    {selectedStrategy.updated_at && (
                      <div>
                        <Label className="text-xs text-gray-500">更新时间</Label>
                        <div className="mt-1 text-sm">
                          {new Date(selectedStrategy.updated_at).toLocaleString('zh-CN')}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
          <DialogFooter className="gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setIsDetailDialogOpen(false)
                setSelectedStrategy(null)
              }}
              className="w-full sm:w-auto"
            >
              关闭
            </Button>
            <Button
              onClick={() => {
                setIsDetailDialogOpen(false)
                if (selectedStrategy) {
                  router.push(`/strategies/${selectedStrategy.id}/edit`)
                }
              }}
              className="w-full sm:w-auto"
            >
              <Edit className="mr-2 h-4 w-4" />
              编辑策略
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
