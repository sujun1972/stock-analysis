'use client'

import { useState, useEffect, useMemo } from 'react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { StrategyCard, type StrategyComponent } from './StrategyCard'
import { threeLayerApi } from '@/lib/three-layer'
import type { SelectorInfo, EntryInfo, ExitInfo } from '@/lib/three-layer'
import { toast } from 'sonner'

type LayerFilter = 'all' | 'selector' | 'entry' | 'exit'

export function StrategyList() {
  const [components, setComponents] = useState<StrategyComponent[]>([])
  const [loading, setLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [layerFilter, setLayerFilter] = useState<LayerFilter>('all')

  // 加载所有组件
  useEffect(() => {
    const loadComponents = async () => {
      try {
        setLoading(true)
        const [selectors, entries, exits] = await Promise.all([
          threeLayerApi.getSelectors(),
          threeLayerApi.getEntries(),
          threeLayerApi.getExits(),
        ])

        const allComponents: StrategyComponent[] = [
          ...selectors.map((s: SelectorInfo) => ({ ...s, layer: 'selector' as const })),
          ...entries.map((e: EntryInfo) => ({ ...e, layer: 'entry' as const })),
          ...exits.map((x: ExitInfo) => ({ ...x, layer: 'exit' as const })),
        ]

        setComponents(allComponents)
      } catch (error) {
        console.error('Failed to load components:', error)
        toast.error('加载策略组件失败')
      } finally {
        setLoading(false)
      }
    }

    loadComponents()
  }, [])

  // 搜索和筛选逻辑
  const filteredComponents = useMemo(() => {
    let result = components

    // 按层级筛选
    if (layerFilter !== 'all') {
      result = result.filter((c) => c.layer === layerFilter)
    }

    // 按搜索词筛选
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase().trim()
      result = result.filter(
        (c) =>
          c.name.toLowerCase().includes(query) ||
          c.description.toLowerCase().includes(query) ||
          c.id.toLowerCase().includes(query)
      )
    }

    return result
  }, [components, layerFilter, searchQuery])

  // 统计数据
  const stats = useMemo(() => {
    return {
      total: components.length,
      selectors: components.filter((c) => c.layer === 'selector').length,
      entries: components.filter((c) => c.layer === 'entry').length,
      exits: components.filter((c) => c.layer === 'exit').length,
    }
  }, [components])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center space-y-3">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="text-muted-foreground">加载策略组件中...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* 搜索和筛选区域 */}
      <div className="space-y-4">
        {/* 搜索框 */}
        <div className="relative">
          <Input
            type="text"
            placeholder="搜索策略名称或描述..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
        </div>

        {/* 筛选按钮 */}
        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-sm font-medium text-muted-foreground">筛选:</span>
          <Button
            variant={layerFilter === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setLayerFilter('all')}
          >
            全部 ({stats.total})
          </Button>
          <Button
            variant={layerFilter === 'selector' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setLayerFilter('selector')}
          >
            🎯 选股器 ({stats.selectors})
          </Button>
          <Button
            variant={layerFilter === 'entry' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setLayerFilter('entry')}
          >
            📈 入场策略 ({stats.entries})
          </Button>
          <Button
            variant={layerFilter === 'exit' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setLayerFilter('exit')}
          >
            📉 退出策略 ({stats.exits})
          </Button>

          {(searchQuery || layerFilter !== 'all') && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setSearchQuery('')
                setLayerFilter('all')
              }}
              className="ml-auto"
            >
              清除筛选
            </Button>
          )}
        </div>
      </div>

      {/* 结果统计 */}
      {filteredComponents.length > 0 && (
        <div className="flex items-center gap-2">
          <p className="text-sm text-muted-foreground">
            显示 <strong className="text-foreground">{filteredComponents.length}</strong> 个策略组件
          </p>
          {(searchQuery || layerFilter !== 'all') && (
            <Badge variant="secondary">已筛选</Badge>
          )}
        </div>
      )}

      {/* 策略卡片网格 */}
      {filteredComponents.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredComponents.map((component) => (
            <StrategyCard key={component.id} component={component} />
          ))}
        </div>
      ) : (
        <div className="text-center py-12">
          <svg
            className="mx-auto h-12 w-12 text-muted-foreground"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          <h3 className="mt-4 text-lg font-medium">未找到匹配的策略</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            试试修改搜索条件或清除筛选
          </p>
          {(searchQuery || layerFilter !== 'all') && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setSearchQuery('')
                setLayerFilter('all')
              }}
              className="mt-4"
            >
              清除所有筛选
            </Button>
          )}
        </div>
      )}

      {/* 策略组合提示 */}
      {filteredComponents.length > 0 && (
        <div className="rounded-lg border bg-muted/50 p-4">
          <h3 className="font-semibold mb-2">💡 提示</h3>
          <p className="text-sm text-muted-foreground">
            这些组件可以自由组合成策略。例如：选择一个选股器 + 一个入场策略 + 一个退出策略 =
            一个完整的回测策略。共有 <strong className="text-foreground">{stats.selectors} × {stats.entries} × {stats.exits} = {stats.selectors * stats.entries * stats.exits}</strong> 种可能的组合！
          </p>
        </div>
      )}
    </div>
  )
}
