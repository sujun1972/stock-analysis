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
  const [sourceFilter, setSourceFilter] = useState<string>('all')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [statistics, setStatistics] = useState<any>(null)

  // 加载策略列表
  useEffect(() => {
    loadStrategies()
    loadStatistics()
  }, [sourceFilter, categoryFilter])

  const loadStrategies = async () => {
    try {
      setLoading(true)
      const params: any = {}
      if (sourceFilter !== 'all') params.source_type = sourceFilter
      if (categoryFilter !== 'all') params.category = categoryFilter

      const response = await apiClient.getStrategies(params)
      if (response.data) {
        setStrategies(response.data)
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

        {/* 创建策略按钮组 */}
        <div className="flex gap-2">
          <Link href="/strategies/create?source=builtin">
            <Button variant="outline">
              <Building2 className="mr-2 h-4 w-4" />
              基于内置创建
            </Button>
          </Link>
          <Link href="/strategies/create?source=ai">
            <Button variant="outline">
              <Sparkles className="mr-2 h-4 w-4" />
              AI 生成
            </Button>
          </Link>
          <Link href="/strategies/create?source=custom">
            <Button>
              <Code className="mr-2 h-4 w-4" />
              自定义代码
            </Button>
          </Link>
        </div>
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
                  <p className="text-sm font-medium text-muted-foreground">内置策略</p>
                  <p className="text-2xl font-bold">{statistics.by_source.builtin}</p>
                </div>
                <Building2 className="h-8 w-8 text-blue-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">AI 生成</p>
                  <p className="text-2xl font-bold">{statistics.by_source.ai}</p>
                </div>
                <Sparkles className="h-8 w-8 text-purple-600" />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">自定义</p>
                  <p className="text-2xl font-bold">{statistics.by_source.custom}</p>
                </div>
                <User className="h-8 w-8 text-green-600" />
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

            {/* 来源筛选 */}
            <Select value={sourceFilter} onValueChange={setSourceFilter}>
              <SelectTrigger>
                <SelectValue placeholder="选择来源" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部来源</SelectItem>
                <SelectItem value="builtin">
                  <div className="flex items-center gap-2">
                    <Building2 className="h-4 w-4" />
                    <span>内置策略</span>
                  </div>
                </SelectItem>
                <SelectItem value="ai">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4" />
                    <span>AI 生成</span>
                  </div>
                </SelectItem>
                <SelectItem value="custom">
                  <div className="flex items-center gap-2">
                    <User className="h-4 w-4" />
                    <span>自定义</span>
                  </div>
                </SelectItem>
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
          {(sourceFilter !== 'all' || categoryFilter !== 'all' || searchQuery) && (
            <div className="flex items-center gap-2 mt-4">
              <Badge variant="outline">
                已筛选: {filteredStrategies.length} 个策略
              </Badge>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setSourceFilter('all')
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
                {searchQuery || sourceFilter !== 'all' || categoryFilter !== 'all'
                  ? '没有找到匹配的策略，请调整筛选条件'
                  : '还没有创建任何策略，立即创建您的第一个策略'}
              </p>
              {!searchQuery && sourceFilter === 'all' && categoryFilter === 'all' && (
                <div className="flex gap-2 justify-center">
                  <Link href="/strategies/create?source=builtin">
                    <Button variant="outline">
                      <Building2 className="mr-2 h-4 w-4" />
                      基于内置创建
                    </Button>
                  </Link>
                  <Link href="/strategies/create?source=custom">
                    <Button>
                      <Code className="mr-2 h-4 w-4" />
                      自定义代码
                    </Button>
                  </Link>
                </div>
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
              onBacktest={(id) => router.push(`/backtest?strategy=${id}`)}
              onDelete={handleDelete}
              onClone={handleClone}
            />
          ))}
        </div>
      )}
    </div>
  )
}
