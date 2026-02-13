/**
 * 离场策略选择器组件
 *
 * 功能:
 * - 从后端加载所有启用的离场策略
 * - 支持多选（可同时选择多个离场策略）
 * - 显示策略详情（描述、风险等级、标签）
 * - 默认折叠状态，不影响页面布局
 *
 * 使用场景:
 * - 在回测页面配置离场策略
 * - 离场策略与入场策略组合使用
 */

'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Checkbox } from '@/components/ui/checkbox'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Loader2, Info, ChevronDown, ChevronUp } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import type { Strategy } from '@/types/strategy'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

interface ExitStrategySelectorProps {
  selectedIds: number[]
  onChange: (ids: number[]) => void
}

export default function ExitStrategySelector({ selectedIds, onChange }: ExitStrategySelectorProps) {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    loadExitStrategies()
  }, [])

  const loadExitStrategies = async () => {
    setIsLoading(true)
    setError(null)
    try {
      const response = await apiClient.getStrategies({
        strategy_type: 'exit',
        is_enabled: true
      })

      if (response.success && response.data) {
        setStrategies(response.data)
      } else {
        setError(response.error || '加载离场策略失败')
      }
    } catch (err: any) {
      setError(err.message || '网络错误')
    } finally {
      setIsLoading(false)
    }
  }

  const handleToggle = (strategyId: number) => {
    const newSelectedIds = selectedIds.includes(strategyId)
      ? selectedIds.filter(id => id !== strategyId)
      : [...selectedIds, strategyId]
    onChange(newSelectedIds)
  }

  const handleSelectAll = () => {
    onChange(strategies.map(s => s.id))
  }

  const handleClearAll = () => {
    onChange([])
  }

  const getRiskBadgeVariant = (riskLevel: string) => {
    switch (riskLevel) {
      case 'safe':
      case 'low':
        return 'default'
      case 'medium':
        return 'outline'
      case 'high':
        return 'destructive'
      default:
        return 'secondary'
    }
  }

  const getRiskLabel = (riskLevel: string) => {
    const labels: Record<string, string> = {
      safe: '安全',
      low: '低风险',
      medium: '中等风险',
      high: '高风险'
    }
    return labels[riskLevel] || riskLevel
  }

  return (
    <Card>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex-1">
              <CardTitle className="flex items-center gap-2">
                离场策略
                {selectedIds.length > 0 && (
                  <Badge variant="secondary">{selectedIds.length} 个已选</Badge>
                )}
              </CardTitle>
              <CardDescription>
                选择一个或多个离场策略（可选）。若不选择，将使用默认的重新平衡策略
              </CardDescription>
            </div>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm">
                {isOpen ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </CollapsibleTrigger>
          </div>
        </CardHeader>

        <CollapsibleContent>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                <span className="ml-2 text-sm text-muted-foreground">加载离场策略...</span>
              </div>
            ) : error ? (
              <div className="flex items-center gap-2 py-4 text-sm text-destructive">
                <Info className="h-4 w-4" />
                <span>{error}</span>
                <Button variant="outline" size="sm" onClick={loadExitStrategies}>
                  重试
                </Button>
              </div>
            ) : strategies.length === 0 ? (
              <div className="py-4 text-center text-sm text-muted-foreground">
                暂无可用的离场策略
              </div>
            ) : (
              <div className="space-y-4">
                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={handleSelectAll}>
                    全选
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleClearAll}>
                    清空
                  </Button>
                  <div className="flex-1" />
                  <span className="text-xs text-muted-foreground">
                    共 {strategies.length} 个离场策略
                  </span>
                </div>

                <ScrollArea className="h-[300px] rounded-md border p-4">
                  <div className="space-y-3">
                    {strategies.map((strategy) => (
                      <div
                        key={strategy.id}
                        className={`flex items-start gap-3 rounded-lg border p-3 transition-colors ${
                          selectedIds.includes(strategy.id)
                            ? 'border-primary bg-primary/5'
                            : 'border-border hover:bg-accent'
                        }`}
                      >
                        <Checkbox
                          id={`exit-strategy-${strategy.id}`}
                          checked={selectedIds.includes(strategy.id)}
                          onCheckedChange={() => handleToggle(strategy.id)}
                          className="mt-1"
                        />
                        <label
                          htmlFor={`exit-strategy-${strategy.id}`}
                          className="flex-1 cursor-pointer space-y-2"
                        >
                          <div className="flex items-center gap-2">
                            <span className="font-medium">{strategy.display_name}</span>
                            <Badge variant="secondary" className="text-xs">
                              {strategy.category}
                            </Badge>
                            <Badge variant={getRiskBadgeVariant(strategy.risk_level) as any}>
                              {getRiskLabel(strategy.risk_level)}
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground">
                            {strategy.description}
                          </p>
                          {strategy.tags && strategy.tags.length > 0 && (
                            <div className="flex flex-wrap gap-1">
                              {strategy.tags.map((tag, index) => (
                                <Badge key={index} variant="outline" className="text-xs">
                                  {tag}
                                </Badge>
                              ))}
                            </div>
                          )}
                        </label>
                      </div>
                    ))}
                  </div>
                </ScrollArea>

                {selectedIds.length > 0 && (
                  <div className="rounded-lg bg-muted/50 p-3">
                    <p className="text-sm font-medium text-muted-foreground mb-2">已选择的策略:</p>
                    <div className="flex flex-wrap gap-2">
                      {selectedIds.map(id => {
                        const strategy = strategies.find(s => s.id === id)
                        return strategy ? (
                          <Badge key={id} variant="secondary">
                            {strategy.display_name}
                          </Badge>
                        ) : null
                      })}
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}
