/**
 * 策略中心页面 (V2.0)
 *
 * 功能:
 * - Tab 导航切换入场/离场策略
 * - 全宽列表卡片展示策略详情
 * - 分页功能(每页10条)
 * - 搜索和筛选功能
 * - 支持查看代码、回测、克隆、编辑、删除等操作
 *
 * URL 参数:
 * - type: entry(入场策略) | exit(离场策略), 默认为 entry
 *
 * @version 2.0
 * @date 2026-03-07
 */

'use client'

import { useState, useEffect, useMemo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
  PaginationEllipsis
} from '@/components/ui/pagination'
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
import { useRouter, useSearchParams } from 'next/navigation'
import { useToast } from '@/hooks/use-toast'
import StrategyListCard from '@/components/strategies/StrategyListCard'
import StrategyCategoryFilter from '@/components/strategies/StrategyCategoryFilter'
import { apiClient } from '@/lib/api-client'
import type { Strategy } from '@/types/strategy'
import { useAuthStore, isAdmin } from '@/stores/auth-store'

export default function StrategiesPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { toast } = useToast()
  const { user } = useAuthStore()
  const userIsAdmin = isAdmin()
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [userFilter, setUserFilter] = useState<string>('all')
  const [categoryFilter, setCategoryFilter] = useState<string>('all')
  const [statistics, setStatistics] = useState<any>(null)
  const [users, setUsers] = useState<Array<{id: number, username: string}>>([])

  // 分页状态
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10

  // 从 URL 获取策略类型（entry/exit）
  const strategyType = searchParams.get('type') || 'entry'

  // 加载策略列表
  useEffect(() => {
    loadStrategies()
    loadStatistics()
    setCurrentPage(1) // 重置分页
  }, [userFilter, categoryFilter, strategyType])

  const loadStrategies = async () => {
    try {
      setLoading(true)

      let allStrategies: Strategy[] = []

      // 构建通用筛选参数
      const buildCommonParams = () => ({
        strategy_type: strategyType,
        category: categoryFilter !== 'all' ? categoryFilter : undefined
      })

      if (user?.id && userFilter === 'all') {
        // 已登录用户：同时获取"我的策略"和"已发布的策略"
        const [myStrategiesResponse, publishedResponse] = await Promise.all([
          // 我的所有策略（包含草稿状态）
          apiClient.getStrategies({
            user_id: user.id,
            ...buildCommonParams()
          }),
          // 其他人已发布的策略
          apiClient.getStrategies({
            publish_status: 'approved',
            is_enabled: true,
            ...buildCommonParams()
          })
        ])

        // 合并并去重（我的策略优先）
        const myStrategies: Strategy[] = (myStrategiesResponse.data as any)?.items ?? myStrategiesResponse.data ?? []
        const publishedStrategies: Strategy[] = (publishedResponse.data as any)?.items ?? publishedResponse.data ?? []

        const strategyMap = new Map<number, Strategy>()
        myStrategies.forEach(s => strategyMap.set(s.id, s))
        publishedStrategies.forEach(s => {
          if (!strategyMap.has(s.id)) {
            strategyMap.set(s.id, s)
          }
        })

        allStrategies = Array.from(strategyMap.values())
      } else {
        // 未登录用户或应用了用户筛选
        const params: any = buildCommonParams()

        if (userFilter !== 'all') {
          params.user_id = parseInt(userFilter)
        } else if (!user?.id) {
          // 未登录用户只能看已发布的策略
          params.publish_status = 'approved'
          params.is_enabled = true
        }

        const response = await apiClient.getStrategies(params)
        allStrategies = (response.data as any)?.items ?? response.data ?? []
      }

      setStrategies(allStrategies)

      // 提取唯一的用户列表用于筛选
      const uniqueUsers = Array.from(
        new Map(
          allStrategies
            .filter(s => s.user_id && s.username)
            .map(s => [s.user_id, { id: s.user_id!, username: s.username! }])
        ).values()
      )
      setUsers(uniqueUsers)
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

  // 分页处理
  const totalPages = Math.ceil(filteredStrategies.length / itemsPerPage)
  const paginatedStrategies = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage
    const endIndex = startIndex + itemsPerPage
    return filteredStrategies.slice(startIndex, endIndex)
  }, [filteredStrategies, currentPage, itemsPerPage])

  /**
   * 处理 Tab 切换
   * 通过更新 URL 参数来切换策略类型
   */
  const handleTabChange = (value: string) => {
    router.push(`/strategies?type=${value}`)
  }

  /**
   * 处理分页切换
   * 切换页面并滚动到顶部
   */
  const handlePageChange = (page: number) => {
    setCurrentPage(page)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  /**
   * 生成分页页码数组
   * 智能显示页码,超过7页时使用省略号
   * @returns 页码数组,包含数字和 'ellipsis'
   */
  const getPageNumbers = () => {
    const pages: (number | 'ellipsis')[] = []
    const maxVisible = 7

    if (totalPages <= maxVisible) {
      for (let i = 1; i <= totalPages; i++) {
        pages.push(i)
      }
    } else {
      if (currentPage <= 3) {
        for (let i = 1; i <= 4; i++) {
          pages.push(i)
        }
        pages.push('ellipsis')
        pages.push(totalPages)
      } else if (currentPage >= totalPages - 2) {
        pages.push(1)
        pages.push('ellipsis')
        for (let i = totalPages - 3; i <= totalPages; i++) {
          pages.push(i)
        }
      } else {
        pages.push(1)
        pages.push('ellipsis')
        for (let i = currentPage - 1; i <= currentPage + 1; i++) {
          pages.push(i)
        }
        pages.push('ellipsis')
        pages.push(totalPages)
      }
    }

    return pages
  }

  /**
   * 处理策略删除
   * 删除后重新加载策略列表和统计信息
   */
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

  /**
   * 处理策略克隆
   * 跳转到创建页面并携带克隆ID
   */
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
            浏览所有已启用的交易策略
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

      {/* Tab 导航 */}
      <Tabs value={strategyType} onValueChange={handleTabChange} className="mb-6">
        <TabsList className="grid w-full max-w-md grid-cols-2">
          <TabsTrigger value="entry" className="flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            入场策略
            {statistics?.by_strategy_type?.entry && (
              <Badge variant="secondary" className="ml-1">
                {statistics.by_strategy_type.entry}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="exit" className="flex items-center gap-2">
            <TrendingDown className="h-4 w-4" />
            离场策略
            {statistics?.by_strategy_type?.exit && (
              <Badge variant="secondary" className="ml-1">
                {statistics.by_strategy_type.exit}
              </Badge>
            )}
          </TabsTrigger>
        </TabsList>
      </Tabs>


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
            <StrategyCategoryFilter
              value={categoryFilter}
              onValueChange={setCategoryFilter}
            />
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
                  : `还没有创建任何${strategyType === 'entry' ? '入场' : '离场'}策略，立即创建您的第一个策略`}
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
        <>
          {/* 策略列表（全宽卡片） */}
          <div className="space-y-4 mb-6">
            {paginatedStrategies.map((strategy) => (
              <StrategyListCard
                key={strategy.id}
                strategy={strategy}
                onBacktest={(id) => router.push(`/backtest?type=unified&id=${id}`)}
                onEdit={(id) => router.push(`/strategies/${id}/edit`)}
                onDelete={handleDelete}
                onClone={handleClone}
                currentUserId={user?.id}
                isAdmin={userIsAdmin}
              />
            ))}
          </div>

          {/* 分页控件 */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between">
              <div className="text-sm text-muted-foreground">
                显示 {Math.min((currentPage - 1) * itemsPerPage + 1, filteredStrategies.length)} -{' '}
                {Math.min(currentPage * itemsPerPage, filteredStrategies.length)} 条，共 {filteredStrategies.length} 条
              </div>

              <Pagination>
                <PaginationContent>
                  <PaginationItem>
                    <PaginationPrevious
                      onClick={() => currentPage > 1 && handlePageChange(currentPage - 1)}
                      className={currentPage === 1 ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                    />
                  </PaginationItem>

                  {getPageNumbers().map((page, index) => {
                    if (page === 'ellipsis') {
                      return (
                        <PaginationItem key={`ellipsis-${index}`}>
                          <PaginationEllipsis />
                        </PaginationItem>
                      )
                    }

                    return (
                      <PaginationItem key={page}>
                        <PaginationLink
                          onClick={() => handlePageChange(page as number)}
                          isActive={currentPage === page}
                          className="cursor-pointer"
                        >
                          {page}
                        </PaginationLink>
                      </PaginationItem>
                    )
                  })}

                  <PaginationItem>
                    <PaginationNext
                      onClick={() => currentPage < totalPages && handlePageChange(currentPage + 1)}
                      className={currentPage === totalPages ? 'pointer-events-none opacity-50' : 'cursor-pointer'}
                    />
                  </PaginationItem>
                </PaginationContent>
              </Pagination>
            </div>
          )}
        </>
      )}
    </div>
  )
}
