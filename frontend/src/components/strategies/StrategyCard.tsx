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
  User,
  CheckCircle,
  XCircle,
  AlertCircle,
  Copy,
  Edit,
  Trash2,
  Filter,
  ExternalLink,
} from 'lucide-react'
import type { Strategy } from '@/types/strategy'

interface StrategyCardProps {
  strategy: Strategy
  onBacktest?: (id: number) => void
  onEdit?: (id: number) => void
  onDelete?: (id: number) => void
  onClone?: (id: number) => void
  currentUserId?: number  // 当前登录用户的ID
  isAdmin?: boolean       // 是否为管理员
}

const StrategyCard = memo(function StrategyCard({
  strategy,
  onBacktest,
  onEdit,
  onDelete,
  onClone,
  currentUserId,
  isAdmin = false
}: StrategyCardProps) {

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

  const isExitStrategy = strategy.strategy_type === 'exit'
  const isStockSelectionStrategy = strategy.strategy_type === 'stock_selection'

  const canModify = isAdmin || (currentUserId && strategy.user_id === currentUserId)

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <CardTitle className="text-lg break-words">{strategy.display_name}</CardTitle>
                {isStockSelectionStrategy && (
                <Badge variant="secondary" className="text-xs shrink-0">
                  选股策略
                </Badge>
              )}
              {isExitStrategy && (
                <Badge variant="secondary" className="text-xs shrink-0">
                  离场策略
                </Badge>
              )}
            </div>
            <CardDescription className="line-clamp-2 break-words">
              {strategy.description || '暂无描述'}
            </CardDescription>
          </div>
          <div className="flex flex-col items-end gap-2 shrink-0 max-w-[45%]">
            {/* 创建者信息 */}
            <Badge variant="outline" className="flex items-center gap-1 max-w-full">
              <User className="h-3 w-3 shrink-0" />
              <span className="truncate">{strategy.username || '未知用户'}</span>
            </Badge>
            {getValidationBadge()}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {/* 标签和类别 */}
        <div className="flex flex-wrap gap-2">
          {strategy.category && (
            <Badge variant="secondary" className="max-w-full truncate" title={strategy.category}>
              {strategy.category}
            </Badge>
          )}
          {strategy.tags?.map((tag, index) => (
            <Badge key={index} variant="outline" className="max-w-[140px] truncate" title={tag}>
              {tag}
            </Badge>
          ))}
        </div>

        {/* 风险等级和统计信息（选股策略不显示风险等级） */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2">
          {!isStockSelectionStrategy && (
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">风险等级:</span>
              <Badge variant={getRiskBadgeVariant() as any}>
                {getRiskLabel()}
              </Badge>
            </div>
          )}
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">使用次数:</span>
            <span className="font-medium">{strategy.usage_count || 0}</span>
          </div>
        </div>

        {/* 性能指标（选股策略不显示回测指标） */}
        {!isStockSelectionStrategy && (strategy.avg_sharpe_ratio || strategy.avg_annual_return) && (
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

        {/* 版本信息 */}
        {strategy.version && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">
              v{strategy.version}
            </span>
          </div>
        )}
      </CardContent>

      <CardFooter className="flex flex-wrap gap-2">
        {/* 主操作组：回测 / 查看选股结果（始终占第一行） */}
        <div className="flex gap-2 w-full sm:w-auto sm:flex-1 min-w-0 order-1 sm:order-2">
          {/* 选股策略：查看选股结果 */}
          {isStockSelectionStrategy ? (
            <Link href={`/stocks?stock_selection_strategy_id=${strategy.id}`} className="flex-1 min-w-0">
              <Button size="sm" className="w-full">
                <ExternalLink className="mr-1 h-3 w-3 shrink-0" />
                <span className="truncate">查看选股结果</span>
              </Button>
            </Link>
          ) : (
            <>
              {/* 回测按钮（入场策略） */}
              {onBacktest && !isExitStrategy && (
                <Link href={`/backtest?type=unified&id=${strategy.id}`} className="flex-1 min-w-0">
                  <Button size="sm" className="w-full">
                    <Play className="mr-1 h-3 w-3 shrink-0" />
                    <span className="truncate">回测</span>
                  </Button>
                </Link>
              )}
              {onBacktest && isExitStrategy && (
                <Button size="sm" className="w-full flex-1 min-w-0" disabled title="离场策略需要配合入场策略使用，不能单独回测">
                  <Play className="mr-1 h-3 w-3 shrink-0" />
                  <span className="truncate">不可回测</span>
                </Button>
              )}
            </>
          )}
        </div>

        {/* 次要操作组：代码 + 克隆 / 编辑 / 删除（手机换到第二行，桌面回到左侧） */}
        <div className="flex gap-2 items-center w-full sm:w-auto order-2 sm:order-1">
          {/* 查看代码按钮 */}
          <Link href={`/strategies/${strategy.id}/code`} className="flex-1 sm:flex-initial min-w-0">
            <Button variant="outline" size="sm" className="w-full">
              <Code className="mr-1 h-3 w-3 shrink-0" />
              <span className="truncate">代码</span>
            </Button>
          </Link>

          {/* 克隆按钮 */}
          {onClone && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onClone(strategy.id)}
              aria-label={`克隆策略 ${strategy.display_name}`}
            >
              <Copy className="h-4 w-4" />
            </Button>
          )}

          {/* 编辑按钮（用户有权限时可编辑） */}
          {onEdit && canModify && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onEdit(strategy.id)}
              aria-label={`编辑策略 ${strategy.display_name}`}
            >
              <Edit className="h-4 w-4" />
            </Button>
          )}

          {/* 删除按钮（用户有权限时可删除） */}
          {onDelete && canModify && (
            <Button
              size="sm"
              variant="destructive"
              onClick={() => onDelete(strategy.id)}
              aria-label={`删除策略 ${strategy.display_name}`}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardFooter>
    </Card>
  )
})

StrategyCard.displayName = 'StrategyCard'

export default StrategyCard
