'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { threeLayerApi } from '@/lib/three-layer'
import type { SelectorInfo, EntryInfo, ExitInfo } from '@/lib/three-layer'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { toast } from 'sonner'
import Link from 'next/link'
import { StrategyOverview } from './StrategyOverview'
import { ParametersTable } from './ParametersTable'
import { UsageGuide } from './UsageGuide'

type StrategyComponent = (SelectorInfo | EntryInfo | ExitInfo) & {
  layer: 'selector' | 'entry' | 'exit'
}

interface StrategyDetailProps {
  strategyId: string
}

const layerConfig = {
  selector: {
    label: '选股器',
    color: 'bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20',
    icon: '🎯',
  },
  entry: {
    label: '入场策略',
    color: 'bg-green-500/10 text-green-700 dark:text-green-400 border-green-500/20',
    icon: '📈',
  },
  exit: {
    label: '退出策略',
    color: 'bg-orange-500/10 text-orange-700 dark:text-orange-400 border-orange-500/20',
    icon: '📉',
  },
}

export function StrategyDetail({ strategyId }: StrategyDetailProps) {
  const router = useRouter()
  const [component, setComponent] = useState<StrategyComponent | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const loadComponent = async () => {
      try {
        setLoading(true)
        setError(null)

        // 并行加载所有组件
        const [selectors, entries, exits] = await Promise.all([
          threeLayerApi.getSelectors(),
          threeLayerApi.getEntries(),
          threeLayerApi.getExits(),
        ])

        // 查找匹配的组件
        let found: StrategyComponent | null = null

        const selector = selectors.find((s) => s.id === strategyId)
        if (selector) {
          found = { ...selector, layer: 'selector' }
        }

        if (!found) {
          const entry = entries.find((e) => e.id === strategyId)
          if (entry) {
            found = { ...entry, layer: 'entry' }
          }
        }

        if (!found) {
          const exit = exits.find((x) => x.id === strategyId)
          if (exit) {
            found = { ...exit, layer: 'exit' }
          }
        }

        if (!found) {
          setError('策略组件未找到')
          toast.error('策略组件未找到')
          return
        }

        setComponent(found)
      } catch (err) {
        console.error('Failed to load component:', err)
        setError('加载策略组件失败')
        toast.error('加载策略组件失败')
      } finally {
        setLoading(false)
      }
    }

    loadComponent()
  }, [strategyId])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center space-y-3">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mx-auto"></div>
          <p className="text-muted-foreground">加载策略详情...</p>
        </div>
      </div>
    )
  }

  if (error || !component) {
    return (
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
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
        <h3 className="mt-4 text-lg font-medium">{error || '策略组件未找到'}</h3>
        <p className="mt-2 text-sm text-muted-foreground">
          请检查策略ID是否正确，或返回策略列表
        </p>
        <Button variant="outline" className="mt-4" asChild>
          <Link href="/strategies">返回策略列表</Link>
        </Button>
      </div>
    )
  }

  const layerInfo = layerConfig[component.layer]

  return (
    <div className="space-y-6">
      {/* 返回按钮 */}
      <div>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/strategies">
            <svg
              className="mr-2 h-4 w-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 19l-7-7m0 0l7-7m-7 7h18"
              />
            </svg>
            返回策略列表
          </Link>
        </Button>
      </div>

      {/* 头部信息 */}
      <div className="space-y-4">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <span className="text-4xl">{layerInfo.icon}</span>
              <h1 className="text-3xl font-bold tracking-tight">{component.name}</h1>
            </div>
            <p className="text-lg text-muted-foreground">{component.description}</p>
          </div>
        </div>

        {/* 标签和版本信息 */}
        <div className="flex items-center gap-3 flex-wrap">
          <Badge className={layerInfo.color} variant="outline">
            {layerInfo.label}
          </Badge>
          <Badge variant="secondary">版本 {component.version}</Badge>
          <Badge variant="outline">
            {component.parameters.length > 0
              ? `${component.parameters.length} 个参数`
              : '无需配置参数'}
          </Badge>
        </div>
      </div>

      {/* Tabs内容 */}
      <Tabs defaultValue="overview" className="space-y-6">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="overview">概览</TabsTrigger>
          <TabsTrigger value="parameters">参数配置</TabsTrigger>
          <TabsTrigger value="usage">使用指南</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <StrategyOverview component={component} />
        </TabsContent>

        <TabsContent value="parameters" className="space-y-4">
          <ParametersTable component={component} />
        </TabsContent>

        <TabsContent value="usage" className="space-y-4">
          <UsageGuide component={component} />
        </TabsContent>
      </Tabs>

      {/* 底部操作按钮 */}
      <div className="flex gap-3 pt-6 border-t">
        <Button size="lg" asChild>
          <Link href={`/backtest/three-layer?${component.layer}=${component.id}`}>
            立即回测
          </Link>
        </Button>
        <Button variant="outline" size="lg" asChild>
          <Link href="/strategies">
            浏览其他策略
          </Link>
        </Button>
      </div>
    </div>
  )
}
