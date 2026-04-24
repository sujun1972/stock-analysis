/**
 * 我的策略页面
 * 展示当前用户创建的所有策略（包括启用和未启用的）
 */

'use client'

import { useState, useEffect, useMemo } from 'react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import {
  Plus,
  Search,
  Code,
  TrendingUp,
  TrendingDown,
  Activity,
  Filter,
  Lock,
  Unlock
} from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useToast } from '@/hooks/use-toast'
import StrategyCard from '@/components/strategies/StrategyCard'
import StrategyCategoryFilter from '@/components/strategies/StrategyCategoryFilter'
import { apiClient } from '@/lib/api-client'
import { useAuthStore, isAdmin } from '@/stores/auth-store'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import type { Strategy } from '@/types/strategy'

function MyStrategiesContent() {
  const router = useRouter()
  const { toast } = useToast()
  const { user } = useAuthStore()
  const userIsAdmin = isAdmin()
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [statusFilter, setStatusFilter] = useState<string>('all')
  const [strategyTypeFilter, setStrategyTypeFilter] = useState<string>('all')

  // 加载策略列表
  useEffect(() => {
    loadStrategies()
  }, [user])

  const loadStrategies = async () => {
    if (!user) return

    try {
      setLoading(true)
      const params: any = {
        user_id: user.id // 只获取当前用户的策略
      }

      const response = await apiClient.getStrategies(params)
      if (response.data) {
        const data = response.data as any
        setStrategies(Array.isArray(data) ? data : (data.items ?? []))
      }
    } catch (error) {
      console.error('Failed to load strategies:', error)
      toast({
        title: '加载失败',
        description: '无法加载策略列表',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  // 过滤策略
  const filteredStrategies = useMemo(() => {
    return strategies.filter(strategy => {
      const matchesSearch =
        searchQuery === '' ||
        strategy.display_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        strategy.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        strategy.tags?.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))

      const matchesCategory = categoryFilter === 'all' || strategy.category === categoryFilter
      const matchesStatus =
        statusFilter === 'all' ||
        (statusFilter === 'enabled' && strategy.is_enabled) ||
        (statusFilter === 'disabled' && !strategy.is_enabled)
      const matchesStrategyType =
        strategyTypeFilter === 'all' || strategy.strategy_type === strategyTypeFilter

      return matchesSearch && matchesCategory && matchesStatus && matchesStrategyType
    })
  }, [strategies, searchQuery, categoryFilter, statusFilter, strategyTypeFilter])

  // 统计信息
  const statistics = useMemo(() => {
    const total = strategies.length
    const enabled = strategies.filter(s => s.is_enabled).length
    const disabled = strategies.filter(s => !s.is_enabled).length
    const byType = {
      entry: strategies.filter(s => s.strategy_type === 'entry').length,
      exit: strategies.filter(s => s.strategy_type === 'exit').length,
      stock_selection: strategies.filter(s => s.strategy_type === 'stock_selection').length,
    }

    return { total, enabled, disabled, byType }
  }, [strategies])

  // 处理策略删除
  const handleDelete = async (id: number) => {
    if (!confirm('确定要删除这个策略吗？此操作不可恢复。')) {
      return
    }

    try {
      await apiClient.deleteStrategy(id)
      toast({
        title: '删除成功',
        description: '策略已被删除'
      })
      loadStrategies()
    } catch (error) {
      console.error('Failed to delete strategy:', error)
      toast({
        title: '删除失败',
        description: '无法删除策略',
        variant: 'destructive'
      })
    }
  }

  // 处理策略克隆
  const handleClone = (id: number) => {
    router.push(`/strategies/create?clone=${id}`)
  }

  // 处理策略编辑
  const handleEdit = (id: number) => {
    router.push(`/strategies/${id}/edit`)
  }

  return (
    <div className="container mx-auto py-6 px-4 max-w-7xl">
      {/* 页面标题 */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div className="min-w-0">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">我的策略</h1>
          <p className="text-muted-foreground mt-2 text-sm sm:text-base">
            管理您创建的所有交易策略
          </p>
        </div>

        {/* 创建策略按钮 */}
        <Link href="/strategies/create" className="sm:shrink-0">
          <Button className="w-full sm:w-auto">
            <Plus className="mr-2 h-4 w-4" />
            创建策略
          </Button>
        </Link>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">总策略数</p>
                <p className="text-2xl font-bold">{statistics.total}</p>
              </div>
              <Activity className="h-8 w-8 text-muted-foreground" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">已启用</p>
                <p className="text-2xl font-bold">{statistics.enabled}</p>
              </div>
              <Unlock className="h-8 w-8 text-green-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">已禁用</p>
                <p className="text-2xl font-bold">{statistics.disabled}</p>
              </div>
              <Lock className="h-8 w-8 text-gray-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">入场策略</p>
                <p className="text-2xl font-bold">{statistics.byType.entry}</p>
              </div>
              <TrendingUp className="h-8 w-8 text-green-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">离场策略</p>
                <p className="text-2xl font-bold">{statistics.byType.exit}</p>
              </div>
              <TrendingDown className="h-8 w-8 text-red-600" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 搜索和筛选 */}
      <Card className="mb-6">
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* 搜索框 */}
            <div className="relative">
              <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索策略名称、描述或标签..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>

            {/* 策略类型筛选 */}
            <Select value={strategyTypeFilter} onValueChange={setStrategyTypeFilter}>
              <SelectTrigger>
                <SelectValue placeholder="选择策略类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部类型</SelectItem>
                <SelectItem value="entry">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-4 w-4" />
                    <span>入场策略</span>
                  </div>
                </SelectItem>
                <SelectItem value="exit">
                  <div className="flex items-center gap-2">
                    <TrendingDown className="h-4 w-4" />
                    <span>离场策略</span>
                  </div>
                </SelectItem>
                <SelectItem value="stock_selection">
                  <div className="flex items-center gap-2">
                    <Filter className="h-4 w-4" />
                    <span>选股策略</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>

            {/* 状态筛选 */}
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger>
                <SelectValue placeholder="选择状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="enabled">
                  <div className="flex items-center gap-2">
                    <Unlock className="h-4 w-4 text-green-600" />
                    <span>已启用</span>
                  </div>
                </SelectItem>
                <SelectItem value="disabled">
                  <div className="flex items-center gap-2">
                    <Lock className="h-4 w-4 text-gray-600" />
                    <span>已禁用</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>

            {/* 类别筛选 */}
            <StrategyCategoryFilter
              value={categoryFilter}
              onValueChange={setCategoryFilter}
            />
          </div>

          {/* 活动筛选结果提示 */}
          {(statusFilter !== 'all' || categoryFilter !== 'all' || strategyTypeFilter !== 'all' || searchQuery) && (
            <div className="flex items-center gap-2 mt-4">
              <Badge variant="outline">
                已筛选: {filteredStrategies.length} 个策略
              </Badge>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setStatusFilter('all')
                  setCategoryFilter('all')
                  setStrategyTypeFilter('all')
                  setSearchQuery('')
                }}
              >
                清除筛选
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 策略列表 */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]" />
            <p className="mt-4 text-muted-foreground">加载中...</p>
          </div>
        </div>
      ) : filteredStrategies.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <Code className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">暂无策略</h3>
              <p className="text-muted-foreground mb-6">
                {searchQuery || statusFilter !== 'all' || categoryFilter !== 'all' || strategyTypeFilter !== 'all'
                  ? '没有找到匹配的策略，请调整筛选条件'
                  : '还没有创建任何策略，立即创建您的第一个策略'}
              </p>
              {!searchQuery && statusFilter === 'all' && categoryFilter === 'all' && strategyTypeFilter === 'all' && (
                <Link href="/strategies/create">
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    创建策略
                  </Button>
                </Link>
              )}
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredStrategies.map((strategy) => (
            <StrategyCard
              key={strategy.id}
              strategy={strategy}
              onBacktest={(id) => router.push(`/backtest?type=unified&id=${id}`)}
              onDelete={handleDelete}
              onClone={handleClone}
              onEdit={handleEdit}
              currentUserId={user?.id}
              isAdmin={userIsAdmin}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default function MyStrategiesPage() {
  return (
    <ProtectedRoute requireAuth={true}>
      <MyStrategiesContent />
    </ProtectedRoute>
  )
}
