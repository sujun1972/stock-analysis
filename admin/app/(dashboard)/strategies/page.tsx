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
 * - 使用 DataTable 组件自动处理桌面/移动端切换
 * - 桌面端（≥768px）：表格视图
 * - 移动端（<768px）：卡片视图
 */
'use client'

import { useEffect, useState, useCallback, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { Plus, Search, Edit, Trash2, AlertCircle, Users, ClipboardList, Ban, MoreVertical, Info, Check } from 'lucide-react'
import { Strategy } from '@/types/strategy'
import { apiClient } from '@/lib/api-client'
import logger from '@/lib/logger'
import { DataTable, type Column } from '@/components/common/DataTable'
import { PageHeader } from '@/components/common/PageHeader'
import PublishStatusBadge from '@/components/strategies/PublishStatusBadge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
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
import { toast } from 'sonner'

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
  const [searchTerm, setSearchTerm] = useState('')
  const [filterStrategyType, setFilterStrategyType] = useState<string>('all')
  const [filterSourceType, setFilterSourceType] = useState<string>('all')
  const [filterUserId, setFilterUserId] = useState<string>('all')
  const [filterPublishStatus, setFilterPublishStatus] = useState<string>('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [totalCount, setTotalCount] = useState(0)
  const pageSize = 20

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

  // 删除确认对话框
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deletingStrategy, setDeletingStrategy] = useState<Strategy | null>(null)

  // 获取策略列表
  const fetchStrategies = useCallback(async () => {
    setLoading(true)
    try {
      const params: any = {
        page: currentPage,
        page_size: pageSize,
      }

      if (searchTerm) params.search = searchTerm
      if (filterStrategyType && filterStrategyType !== 'all') params.strategy_type = filterStrategyType
      if (filterSourceType && filterSourceType !== 'all') params.source_type = filterSourceType
      if (filterUserId && filterUserId !== 'all') params.user_id = filterUserId
      if (filterPublishStatus && filterPublishStatus !== 'all') params.publish_status = filterPublishStatus

      const response = await apiClient.get('/api/strategies', { params }) as any

      if (response?.code === 200 && response.data) {
        const { items, total } = response.data
        if (items && Array.isArray(items)) {
          setStrategies(items)
          setTotalCount(total || 0)
        }
      }
    } catch (error) {
      logger.error('获取策略列表失败', error)
      toast.error('获取策略列表失败')
    } finally {
      setLoading(false)
    }
  }, [currentPage, searchTerm, filterStrategyType, filterSourceType, filterUserId, filterPublishStatus])

  useEffect(() => {
    fetchStrategies()
  }, [fetchStrategies])

  // 获取用户列表
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

      const response = await apiClient.get(`/api/users?${params}`) as any

      if (response?.code === 200 && response.data?.users) {
        setUsers(response.data.users)
      } else {
        setUsers([])
      }
    } catch (error) {
      logger.error('获取用户列表失败', error)
      setUsers([])
    } finally {
      setLoadingUsers(false)
    }
  }

  // 打开用户编辑对话框
  const openEditUserDialog = async (strategy: Strategy) => {
    setEditingStrategy(strategy)
    setSelectedUserId(strategy.user_id?.toString() || '')
    setUserSearchTerm('')
    setEditUserDialogOpen(true)
    await fetchUsers()
  }

  // 更新策略用户归属
  const handleUpdateStrategyUser = async () => {
    if (!editingStrategy) return

    setUpdatingUser(true)
    try {
      const userId = selectedUserId ? parseInt(selectedUserId) : null
      await apiClient.put(`/api/strategies/${editingStrategy.id}`, {
        user_id: userId
      })
      toast.success('用户归属更新成功')
      setEditUserDialogOpen(false)
      fetchStrategies()
    } catch (error) {
      logger.error('更新策略用户归属失败', error)
      toast.error('更新失败')
    } finally {
      setUpdatingUser(false)
    }
  }

  // 切换策略启用状态
  const toggleStrategyStatus = async (strategy: Strategy) => {
    try {
      await apiClient.put(`/api/strategies/${strategy.id}`, {
        is_enabled: !strategy.is_enabled
      })
      toast.success(strategy.is_enabled ? '策略已禁用' : '策略已启用')
      fetchStrategies()
    } catch (error) {
      logger.error('更新策略状态失败', error)
      toast.error('更新失败')
    }
  }

  // 删除策略
  const handleDeleteStrategy = async () => {
    if (!deletingStrategy) return

    try {
      await apiClient.deleteStrategy(deletingStrategy.id)
      toast.success('策略删除成功')
      setDeleteDialogOpen(false)
      fetchStrategies()
    } catch (error) {
      logger.error('删除策略失败', error)
      toast.error('删除失败')
    }
  }

  // 取消发布策略
  const handleUnpublish = async (strategy: Strategy) => {
    try {
      await apiClient.unpublishStrategy(strategy.id)
      toast.success('策略已取消发布')
      fetchStrategies()
    } catch (error) {
      logger.error('取消发布失败', error)
      toast.error('取消发布失败')
    }
  }

  // 重置筛选器
  const handleResetFilters = () => {
    setSearchTerm('')
    setFilterStrategyType('all')
    setFilterSourceType('all')
    setFilterUserId('all')
    setFilterPublishStatus('all')
    setCurrentPage(1)
  }

  // 定义表格列
  const columns: Column<Strategy>[] = useMemo(() => [
    {
      key: 'name',
      header: '策略名称',
      accessor: (strategy) => (
        <div className="space-y-1">
          <div className="font-medium">{strategy.display_name || strategy.name}</div>
          {strategy.description && (
            <div className="text-xs text-muted-foreground truncate max-w-xs">
              {strategy.description}
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'type',
      header: '类型',
      accessor: (strategy) => (
        <div className="flex flex-col gap-1">
          <Badge className={strategyTypeColors[strategy.strategy_type as keyof typeof strategyTypeColors] || 'bg-gray-100 text-gray-800'}>
            {strategyTypeNames[strategy.strategy_type as keyof typeof strategyTypeNames] || strategy.strategy_type}
          </Badge>
          <Badge className={sourceTypeColors[strategy.source_type as keyof typeof sourceTypeColors] || 'bg-gray-100 text-gray-800'}>
            {sourceTypeNames[strategy.source_type as keyof typeof sourceTypeNames] || strategy.source_type}
          </Badge>
        </div>
      ),
      hideOnMobile: true,
    },
    {
      key: 'user',
      header: '用户',
      accessor: (strategy) => (
        <div className="text-sm">
          {strategy.username || (strategy.user_id ? `用户#${strategy.user_id}` : '系统')}
        </div>
      ),
      hideOnMobile: true,
    },
    {
      key: 'validation',
      header: '验证状态',
      accessor: (strategy) => (
        <Badge className={validationStatusColors[strategy.validation_status as keyof typeof validationStatusColors] || 'bg-gray-100 text-gray-800'}>
          {strategy.validation_status === 'pending' && '待验证'}
          {strategy.validation_status === 'passed' && '已通过'}
          {strategy.validation_status === 'failed' && '未通过'}
          {strategy.validation_status === 'validating' && '验证中'}
        </Badge>
      ),
    },
    {
      key: 'risk',
      header: '风险等级',
      accessor: (strategy) => (
        <Badge className={riskLevelColors[strategy.risk_level as keyof typeof riskLevelColors] || 'bg-gray-100 text-gray-800'}>
          {strategy.risk_level || '未知'}
        </Badge>
      ),
      hideOnMobile: true,
    },
    {
      key: 'publish',
      header: '发布状态',
      accessor: (strategy) => <PublishStatusBadge status={strategy.publish_status || 'draft'} />,
    },
    {
      key: 'enabled',
      header: '启用状态',
      accessor: (strategy) => (
        <Switch
          checked={strategy.is_enabled}
          onCheckedChange={() => toggleStrategyStatus(strategy)}
          className="data-[state=checked]:bg-green-600"
        />
      ),
    },
  ], [])

  // 移动端卡片渲染
  const mobileCard = useCallback((strategy: Strategy) => (
    <div className="border rounded-lg p-4 bg-white space-y-3">
      {/* 策略名称和操作 */}
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-base">{strategy.display_name || strategy.name}</div>
          {strategy.description && (
            <div className="text-sm text-gray-500 mt-1">{strategy.description}</div>
          )}
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="shrink-0">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => {
              setSelectedStrategy(strategy)
              setIsDetailDialogOpen(true)
            }}>
              <Info className="mr-2 h-4 w-4" />
              查看详情
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push(`/strategies/edit/${strategy.id}`)}>
              <Edit className="mr-2 h-4 w-4" />
              编辑
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push(`/strategies/validate/${strategy.id}`)}>
              <AlertCircle className="mr-2 h-4 w-4" />
              验证
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => openEditUserDialog(strategy)}>
              <Users className="mr-2 h-4 w-4" />
              分配用户
            </DropdownMenuItem>
            {strategy.publish_status !== 'approved' && (
              <DropdownMenuItem onClick={() => router.push(`/strategies/publish/${strategy.id}`)}>
                <ClipboardList className="mr-2 h-4 w-4" />
                发布管理
              </DropdownMenuItem>
            )}
            {strategy.publish_status === 'approved' && (
              <DropdownMenuItem onClick={() => handleUnpublish(strategy)}>
                <Ban className="mr-2 h-4 w-4" />
                取消发布
              </DropdownMenuItem>
            )}
            <DropdownMenuItem
              onClick={() => {
                setDeletingStrategy(strategy)
                setDeleteDialogOpen(true)
              }}
              className="text-red-600"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              删除
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* 类型和状态标签 */}
      <div className="flex flex-wrap gap-2">
        <Badge className={strategyTypeColors[strategy.strategy_type as keyof typeof strategyTypeColors] || 'bg-gray-100 text-gray-800'}>
          {strategyTypeNames[strategy.strategy_type as keyof typeof strategyTypeNames] || strategy.strategy_type}
        </Badge>
        <Badge className={sourceTypeColors[strategy.source_type as keyof typeof sourceTypeColors] || 'bg-gray-100 text-gray-800'}>
          {sourceTypeNames[strategy.source_type as keyof typeof sourceTypeNames] || strategy.source_type}
        </Badge>
        <PublishStatusBadge status={strategy.publish_status || 'draft'} />
      </div>

      {/* 验证和风险信息 */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          <Badge className={validationStatusColors[strategy.validation_status as keyof typeof validationStatusColors] || 'bg-gray-100 text-gray-800'}>
            {strategy.validation_status === 'pending' && '待验证'}
            {strategy.validation_status === 'passed' && '已通过'}
            {strategy.validation_status === 'failed' && '未通过'}
            {strategy.validation_status === 'validating' && '验证中'}
          </Badge>
          <Badge className={riskLevelColors[strategy.risk_level as keyof typeof riskLevelColors] || 'bg-gray-100 text-gray-800'}>
            风险: {strategy.risk_level || '未知'}
          </Badge>
        </div>
        <Switch
          checked={strategy.is_enabled}
          onCheckedChange={() => toggleStrategyStatus(strategy)}
          className="data-[state=checked]:bg-green-600"
        />
      </div>

      {/* 用户信息 */}
      <div className="text-sm text-gray-500 pt-2 border-t">
        用户: {strategy.username || (strategy.user_id ? `用户#${strategy.user_id}` : '系统')}
      </div>
    </div>
  ), [router])

  // 操作列
  const actions = useCallback((strategy: Strategy) => (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <MoreVertical className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => {
          setSelectedStrategy(strategy)
          setIsDetailDialogOpen(true)
        }}>
          <Info className="mr-2 h-4 w-4" />
          查看详情
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push(`/strategies/edit/${strategy.id}`)}>
          <Edit className="mr-2 h-4 w-4" />
          编辑
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push(`/strategies/validate/${strategy.id}`)}>
          <AlertCircle className="mr-2 h-4 w-4" />
          验证
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => openEditUserDialog(strategy)}>
          <Users className="mr-2 h-4 w-4" />
          分配用户
        </DropdownMenuItem>
        {strategy.publish_status !== 'approved' && (
          <DropdownMenuItem onClick={() => router.push(`/strategies/publish/${strategy.id}`)}>
            <ClipboardList className="mr-2 h-4 w-4" />
            发布管理
          </DropdownMenuItem>
        )}
        {strategy.publish_status === 'approved' && (
          <DropdownMenuItem onClick={() => handleUnpublish(strategy)}>
            <Ban className="mr-2 h-4 w-4" />
            取消发布
          </DropdownMenuItem>
        )}
        <DropdownMenuItem
          onClick={() => {
            setDeletingStrategy(strategy)
            setDeleteDialogOpen(true)
          }}
          className="text-red-600"
        >
          <Trash2 className="mr-2 h-4 w-4" />
          删除
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  ), [router])

  return (
    <div className="container mx-auto p-4 space-y-6">
      {/* 页面标题 */}
      <PageHeader
        title="策略管理"
        description="管理和监控所有交易策略"
        actions={
          <Button onClick={() => router.push('/strategies/create')}>
            <Plus className="mr-2 h-4 w-4" />
            创建策略
          </Button>
        }
      />

      {/* 筛选器 */}
      <Card>
        <CardHeader>
          <CardTitle>筛选和搜索</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* 搜索框 */}
          <div className="flex gap-2">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索策略名称或描述..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <Button onClick={handleResetFilters} variant="outline">
              重置
            </Button>
          </div>

          {/* 筛选选项 */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Select value={filterStrategyType} onValueChange={setFilterStrategyType}>
              <SelectTrigger>
                <SelectValue placeholder="策略类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部类型</SelectItem>
                <SelectItem value="stock_selection">选股策略</SelectItem>
                <SelectItem value="entry">入场策略</SelectItem>
                <SelectItem value="exit">离场策略</SelectItem>
              </SelectContent>
            </Select>

            <Select value={filterSourceType} onValueChange={setFilterSourceType}>
              <SelectTrigger>
                <SelectValue placeholder="来源类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部来源</SelectItem>
                <SelectItem value="builtin">系统内置</SelectItem>
                <SelectItem value="ai">AI生成</SelectItem>
                <SelectItem value="custom">用户自定义</SelectItem>
              </SelectContent>
            </Select>

            <Select value={filterPublishStatus} onValueChange={setFilterPublishStatus}>
              <SelectTrigger>
                <SelectValue placeholder="发布状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="draft">草稿</SelectItem>
                <SelectItem value="pending_review">待审核</SelectItem>
                <SelectItem value="approved">已发布</SelectItem>
                <SelectItem value="rejected">已拒绝</SelectItem>
              </SelectContent>
            </Select>

            <Select value={filterUserId} onValueChange={setFilterUserId}>
              <SelectTrigger>
                <SelectValue placeholder="用户筛选" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部用户</SelectItem>
                <SelectItem value="system">系统策略</SelectItem>
                {/* 这里可以加载用户列表 */}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* 策略列表 */}
      <Card>
        <CardHeader>
          <CardTitle>策略列表</CardTitle>
          <CardDescription>
            共 {totalCount} 个策略
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DataTable
            data={strategies}
            columns={columns}
            loading={loading}
            emptyMessage="暂无策略数据"
            loadingMessage="加载中..."
            pagination={{
              page: currentPage,
              pageSize,
              total: totalCount,
              onPageChange: setCurrentPage,
            }}
            actions={actions}
            mobileCard={mobileCard}
            rowKey={(strategy) => strategy.id}
          />
        </CardContent>
      </Card>

      {/* 用户编辑对话框 */}
      <Dialog open={editUserDialogOpen} onOpenChange={setEditUserDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>分配用户</DialogTitle>
            <DialogDescription>
              为策略 "{editingStrategy?.display_name || editingStrategy?.name}" 分配用户归属
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>选择用户</Label>
              <Command className="rounded-lg border shadow-md">
                <CommandInput
                  placeholder="搜索用户..."
                  value={userSearchTerm}
                  onValueChange={setUserSearchTerm}
                />
                <CommandList>
                  {loadingUsers ? (
                    <CommandEmpty>加载中...</CommandEmpty>
                  ) : (
                    <>
                      <CommandEmpty>没有找到用户</CommandEmpty>
                      <CommandGroup>
                        <CommandItem
                          value=""
                          onSelect={() => setSelectedUserId('')}
                          className="cursor-pointer"
                        >
                          <Check className={`mr-2 h-4 w-4 ${selectedUserId === '' ? 'opacity-100' : 'opacity-0'}`} />
                          系统策略（无用户归属）
                        </CommandItem>
                        {users.map((user) => (
                          <CommandItem
                            key={user.id}
                            value={user.id.toString()}
                            onSelect={() => setSelectedUserId(user.id.toString())}
                            className="cursor-pointer"
                          >
                            <Check
                              className={`mr-2 h-4 w-4 ${
                                selectedUserId === user.id.toString() ? 'opacity-100' : 'opacity-0'
                              }`}
                            />
                            <div className="flex flex-col">
                              <span>{user.username}</span>
                              <span className="text-sm text-muted-foreground">{user.email}</span>
                            </div>
                          </CommandItem>
                        ))}
                      </CommandGroup>
                    </>
                  )}
                </CommandList>
              </Command>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditUserDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleUpdateStrategyUser} disabled={updatingUser}>
              {updatingUser ? '更新中...' : '确认'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 策略详情对话框 */}
      <Dialog open={isDetailDialogOpen} onOpenChange={setIsDetailDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>策略详情</DialogTitle>
            <DialogDescription>
              {selectedStrategy?.display_name || selectedStrategy?.name}
            </DialogDescription>
          </DialogHeader>
          {selectedStrategy && (
            <div className="space-y-6">
              {/* 基本信息 */}
              <div>
                <h3 className="text-lg font-semibold mb-3">基本信息</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-muted-foreground">策略ID</Label>
                    <p className="font-mono">{selectedStrategy.id}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">内部名称</Label>
                    <p>{selectedStrategy.name}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">显示名称</Label>
                    <p>{selectedStrategy.display_name || '-'}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">策略类型</Label>
                    <p>{strategyTypeNames[selectedStrategy.strategy_type as keyof typeof strategyTypeNames]}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">来源类型</Label>
                    <p>{sourceTypeNames[selectedStrategy.source_type as keyof typeof sourceTypeNames]}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">风险等级</Label>
                    <p>{selectedStrategy.risk_level || '未评估'}</p>
                  </div>
                </div>
              </div>

              {/* 描述 */}
              {selectedStrategy.description && (
                <div>
                  <Label className="text-muted-foreground">策略描述</Label>
                  <p className="mt-1">{selectedStrategy.description}</p>
                </div>
              )}

              {/* 状态信息 */}
              <div>
                <h3 className="text-lg font-semibold mb-3">状态信息</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-muted-foreground">验证状态</Label>
                    <Badge className={validationStatusColors[selectedStrategy.validation_status as keyof typeof validationStatusColors] || 'bg-gray-100'}>
                      {selectedStrategy.validation_status}
                    </Badge>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">发布状态</Label>
                    <PublishStatusBadge status={selectedStrategy.publish_status || 'draft'} />
                  </div>
                  <div>
                    <Label className="text-muted-foreground">启用状态</Label>
                    <p>{selectedStrategy.is_enabled ? '已启用' : '已禁用'}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">用户归属</Label>
                    <p>{selectedStrategy.username || (selectedStrategy.user_id ? `用户#${selectedStrategy.user_id}` : '系统')}</p>
                  </div>
                </div>
              </div>

              {/* 统计信息 */}
              <div>
                <h3 className="text-lg font-semibold mb-3">使用统计</h3>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <Label className="text-muted-foreground">使用次数</Label>
                    <p className="text-2xl font-semibold">{selectedStrategy.usage_count || 0}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">回测次数</Label>
                    <p className="text-2xl font-semibold">{selectedStrategy.backtest_count || 0}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">平均夏普比率</Label>
                    <p className="text-2xl font-semibold">
                      {selectedStrategy.avg_sharpe_ratio ? selectedStrategy.avg_sharpe_ratio.toFixed(2) : '-'}
                    </p>
                  </div>
                </div>
              </div>

              {/* 标签 */}
              {selectedStrategy.tags && selectedStrategy.tags.length > 0 && (
                <div>
                  <Label className="text-muted-foreground">标签</Label>
                  <div className="flex flex-wrap gap-2 mt-2">
                    {selectedStrategy.tags.map((tag, index) => (
                      <Badge key={index} variant="secondary">{tag}</Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* 时间信息 */}
              <div>
                <h3 className="text-lg font-semibold mb-3">时间信息</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-muted-foreground">创建时间</Label>
                    <p>{new Date(selectedStrategy.created_at).toLocaleString('zh-CN')}</p>
                  </div>
                  <div>
                    <Label className="text-muted-foreground">更新时间</Label>
                    <p>{new Date(selectedStrategy.updated_at).toLocaleString('zh-CN')}</p>
                  </div>
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setIsDetailDialogOpen(false)}>关闭</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 删除确认对话框 */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>
              您确定要删除策略 "{deletingStrategy?.display_name || deletingStrategy?.name}" 吗？此操作无法撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialogOpen(false)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDeleteStrategy}>
              确认删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}