/**
 * 统一策略列表页面 (V2.0)
 * 展示所有类型的策略（内置/AI/自定义）
 */

'use client'

import { useState, useEffect, useMemo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import {
  Plus,
  Search,
  Code,
  Sparkles,
  Building2,
  User,
  TrendingUp,
  TrendingDown,
  Activity,
  Filter
} from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useToast } from '@/hooks/use-toast'
import StrategyCard from '@/components/strategies/StrategyCard'
import { apiClient } from '@/lib/api-client'
import type { Strategy } from '@/types/strategy'

export default function StrategiesPage() {
  const router = useRouter()
  const { toast } = useToast()
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [userFilter, setUserFilter] = useState<string>('all')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [statistics, setStatistics] = useState<any>(null)
  const [users, setUsers] = useState<Array<{id: number, username: string}>>([])

  // 加载策略列表
  useEffect(() => {
    loadStrategies()
    loadStatistics()
  }, [userFilter, categoryFilter])

  const loadStrategies = async () => {
    try {
      setLoading(true)
      const params: any = {}
      if (userFilter !== 'all') params.user_id = parseInt(userFilter)
      if (categoryFilter !== 'all') params.category = categoryFilter

      const response = await apiClient.getStrategies(params)
      if (response.data) {
        setStrategies(response.data)

        // 提取唯一的用户列表
        const uniqueUsers = Array.from(
          new Map(
            response.data
              .filter((s: any) => s.user_id && s.username)
              .map((s: any) => [s.user_id, { id: s.user_id, username: s.username }])
          ).values()
        )
        setUsers(uniqueUsers)
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

  const loadStatistics = async () => {
    try {
      const response = await apiClient.getStrategyStatistics()
      if (response.data) {
        setStatistics(response.data)
      }
    } catch (error) {
      console.error('Failed to load statistics:', error)
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

      return matchesSearch
    })
  }, [strategies, searchQuery])

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
      loadStatistics()
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

  return (
    <div className="container mx-auto py-6 px-4 max-w-7xl">
      {/* 页面标题 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">策略中心</h1>
          <p className="text-muted-foreground mt-2">
            管理和创建您的交易策略
          </p>
        </div>

        {/* 创建策略按钮 */}
        <Link href="/strategies/create">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            创建策略
          </Button>
        </Link>
      </div>

      {/* 统计卡片 */}
      {statistics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
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
                  <p className="text-sm font-medium text-muted-foreground">入场策略</p>
                  <p className="text-2xl font-bold">{statistics.by_strategy_type?.entry || 0}</p>
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
                  <p className="text-2xl font-bold">{statistics.by_strategy_type?.exit || 0}</p>
                </div>
                <TrendingDown className="h-8 w-8 text-red-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">选股策略</p>
                  <p className="text-2xl font-bold">{statistics.by_strategy_type?.stock_selection || 0}</p>
                </div>
                <Filter className="h-8 w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* 搜索和筛选 */}
      <Card className="mb-6">
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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

            {/* 用户筛选 */}
            <Select value={userFilter} onValueChange={setUserFilter}>
              <SelectTrigger>
                <SelectValue placeholder="选择创建者" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部创建者</SelectItem>
                {users.map((user) => (
                  <SelectItem key={user.id} value={user.id.toString()}>
                    <div className="flex items-center gap-2">
                      <User className="h-4 w-4" />
                      <span>{user.username}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* 类别筛选 */}
            <Select value={categoryFilter} onValueChange={setCategoryFilter}>
              <SelectTrigger>
                <SelectValue placeholder="选择类别" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部类别</SelectItem>
                <SelectItem value="momentum">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-4 w-4" />
                    <span>动量策略</span>
                  </div>
                </SelectItem>
                <SelectItem value="reversal">
                  <div className="flex items-center gap-2">
                    <TrendingDown className="h-4 w-4" />
                    <span>反转策略</span>
                  </div>
                </SelectItem>
                <SelectItem value="factor">
                  <div className="flex items-center gap-2">
                    <Filter className="h-4 w-4" />
                    <span>因子策略</span>
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* 活动筛选结果提示 */}
          {(userFilter !== 'all' || categoryFilter !== 'all' || searchQuery) && (
            <div className="flex items-center gap-2 mt-4">
              <Badge variant="outline">
                已筛选: {filteredStrategies.length} 个策略
              </Badge>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setUserFilter('all')
                  setCategoryFilter('all')
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
                {searchQuery || userFilter !== 'all' || categoryFilter !== 'all'
                  ? '没有找到匹配的策略，请调整筛选条件'
                  : '还没有创建任何策略，立即创建您的第一个策略'}
              </p>
              {!searchQuery && userFilter === 'all' && categoryFilter === 'all' && (
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
            />
          ))}
        </div>
      )}
    </div>
  )
}
