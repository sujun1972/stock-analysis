/**
 * 统一策略卡片组件 (V2.0)
 * 用于展示所有类型的策略（内置/AI/自定义）
 */

'use client'

import { memo } from 'react'
import Link from 'next/link'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Code,
  Play,
  Building2,
  Sparkles,
  User,
  CheckCircle,
  XCircle,
  AlertCircle,
  Copy,
  Edit,
  Trash2
} from 'lucide-react'
import type { Strategy } from '@/types/strategy'

interface StrategyCardProps {
  strategy: Strategy
  onBacktest?: (id: number) => void
  onEdit?: (id: number) => void
  onDelete?: (id: number) => void
  onClone?: (id: number) => void
}

const StrategyCard = memo(function StrategyCard({
  strategy,
  onBacktest,
  onEdit,
  onDelete,
  onClone
}: StrategyCardProps) {

  // 获取来源类型图标
  const getSourceIcon = () => {
    switch (strategy.source_type) {
      case 'builtin':
        return <Building2 className="h-4 w-4" />
      case 'ai':
        return <Sparkles className="h-4 w-4" />
      case 'custom':
        return <User className="h-4 w-4" />
    }
  }

  // 获取来源类型标签
  const getSourceLabel = () => {
    switch (strategy.source_type) {
      case 'builtin':
        return '内置'
      case 'ai':
        return 'AI生成'
      case 'custom':
        return '自定义'
    }
  }

  // 获取验证状态徽章
  const getValidationBadge = () => {
    const variants = {
      passed: { variant: 'default' as const, icon: CheckCircle, label: '已验证' },
      failed: { variant: 'destructive' as const, icon: XCircle, label: '验证失败' },
      pending: { variant: 'secondary' as const, icon: AlertCircle, label: '待验证' },
      validating: { variant: 'outline' as const, icon: AlertCircle, label: '验证中' }
    }

    const info = variants[strategy.validation_status]
    if (!info) return null

    const Icon = info.icon

    return (
      <Badge variant={info.variant} className="flex items-center gap-1">
        <Icon className="h-3 w-3" />
        {info.label}
      </Badge>
    )
  }

  // 获取风险等级徽章颜色
  const getRiskBadgeVariant = () => {
    switch (strategy.risk_level) {
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

  // 获取风险等级标签
  const getRiskLabel = () => {
    const labels = {
      safe: '安全',
      low: '低风险',
      medium: '中等风险',
      high: '高风险'
    }
    return labels[strategy.risk_level] || strategy.risk_level
  }

  // 判断是否为离场策略
  const isExitStrategy = strategy.strategy_type === 'exit'

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <CardTitle className="text-lg">{strategy.display_name}</CardTitle>
              {/* 离场策略标识 */}
              {isExitStrategy && (
                <Badge variant="secondary" className="text-xs">
                  离场策略
                </Badge>
              )}
            </div>
            <CardDescription>
              {strategy.description || '暂无描述'}
            </CardDescription>
          </div>
          <div className="flex flex-col items-end gap-2">
            <Badge variant="outline" className="flex items-center gap-1">
              {getSourceIcon()}
              <span>{getSourceLabel()}</span>
            </Badge>
            {getValidationBadge()}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* 标签和类别 */}
        <div className="flex flex-wrap gap-2">
          {strategy.category && (
            <Badge variant="secondary">{strategy.category}</Badge>
          )}
          {strategy.tags?.map((tag, index) => (
            <Badge key={index} variant="outline">{tag}</Badge>
          ))}
        </div>

        {/* 风险等级和统计信息 */}
        <div className="grid grid-cols-2 gap-2 pt-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">风险等级:</span>
            <Badge variant={getRiskBadgeVariant() as any}>
              {getRiskLabel()}
            </Badge>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">使用次数:</span>
            <span className="font-medium">{strategy.usage_count || 0}</span>
          </div>
        </div>

        {/* 性能指标（如果有） */}
        {(strategy.avg_sharpe_ratio || strategy.avg_annual_return) && (
          <div className="bg-muted/50 rounded-lg p-3 space-y-1">
            <p className="text-xs font-medium text-muted-foreground">平均表现</p>
            <div className="grid grid-cols-2 gap-2 text-xs">
              {strategy.avg_sharpe_ratio !== null && strategy.avg_sharpe_ratio !== undefined && (
                <div>
                  <span className="text-muted-foreground">夏普率: </span>
                  <span className="font-medium">{Number(strategy.avg_sharpe_ratio).toFixed(2)}</span>
                </div>
              )}
              {strategy.avg_annual_return !== null && strategy.avg_annual_return !== undefined && (
                <div>
                  <span className="text-muted-foreground">年化收益: </span>
                  <span className="font-medium">
                    {(Number(strategy.avg_annual_return) * 100).toFixed(2)}%
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 验证错误提示 */}
        {strategy.validation_status === 'failed' && strategy.validation_errors && (
          <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-3">
            <p className="text-xs font-medium text-destructive mb-1">验证错误</p>
            <p className="text-xs text-destructive/80 line-clamp-2">
              {JSON.stringify(strategy.validation_errors)}
            </p>
          </div>
        )}

        {/* 状态标签 */}
        <div className="flex items-center gap-2">
          <Badge variant={strategy.is_enabled ? 'default' : 'secondary'}>
            {strategy.is_enabled ? '已启用' : '已禁用'}
          </Badge>
          <span className="text-xs text-muted-foreground">
            v{strategy.version}
          </span>
        </div>
      </CardContent>

      <CardFooter className="flex gap-2">
        {/* 查看代码按钮 */}
        <Link href={`/strategies/${strategy.id}/code`} className="flex-1">
          <Button variant="outline" size="sm" className="w-full">
            <Code className="mr-1 h-3 w-3" />
            代码
          </Button>
        </Link>

        {/* 回测按钮（离场策略不能单独回测） */}
        {onBacktest && !isExitStrategy && (
          <Link href={`/backtest?type=unified&id=${strategy.id}`} className="flex-1">
            <Button size="sm" className="w-full">
              <Play className="mr-1 h-3 w-3" />
              回测
            </Button>
          </Link>
        )}
        {onBacktest && isExitStrategy && (
          <Button size="sm" className="w-full flex-1" disabled title="离场策略需要配合入场策略使用，不能单独回测">
            <Play className="mr-1 h-3 w-3" />
            不可回测
          </Button>
        )}

        {/* 克隆按钮 */}
        {onClone && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => onClone(strategy.id)}
          >
            <Copy className="h-4 w-4" />
          </Button>
        )}

        {/* 编辑按钮（仅自定义和AI策略） */}
        {strategy.source_type !== 'builtin' && onEdit && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => onEdit(strategy.id)}
          >
            <Edit className="h-4 w-4" />
          </Button>
        )}

        {/* 删除按钮（仅自定义和AI策略） */}
        {strategy.source_type !== 'builtin' && onDelete && (
          <Button
            size="sm"
            variant="destructive"
            onClick={() => onDelete(strategy.id)}
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        )}
      </CardFooter>
    </Card>
  )
})

StrategyCard.displayName = 'StrategyCard'

export default StrategyCard
