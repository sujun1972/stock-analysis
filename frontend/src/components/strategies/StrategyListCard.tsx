/**
 * 全宽策略列表卡片组件 (V2.0)
 *
 * 用于在策略中心页面以列表形式展示策略
 * 特点:
 * - 横向全宽布局,充分利用屏幕空间
 * - 左侧图标区分入场/离场策略类型
 * - 中间展示完整策略信息(名称、描述、标签、性能指标等)
 * - 右侧操作按钮区(代码、回测、克隆、编辑、删除)
 * - 支持深色模式和响应式设计
 *
 * @version 2.0
 * @date 2026-03-07
 */

'use client'

import { memo } from 'react'
import Link from 'next/link'
import { Card, CardContent } from '@/components/ui/card'
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
  TrendingUp,
  TrendingDown
} from 'lucide-react'
import type { Strategy } from '@/types/strategy'

interface StrategyListCardProps {
  /** 策略对象 */
  strategy: Strategy
  /** 回测回调函数 */
  onBacktest?: (id: number) => void
  /** 编辑回调函数 */
  onEdit?: (id: number) => void
  /** 删除回调函数 */
  onDelete?: (id: number) => void
  /** 克隆回调函数 */
  onClone?: (id: number) => void
  /** 当前登录用户ID */
  currentUserId?: number
  /** 是否为管理员 */
  isAdmin?: boolean
}

const StrategyListCard = memo(function StrategyListCard({
  strategy,
  onBacktest,
  onEdit,
  onDelete,
  onClone,
  currentUserId,
  isAdmin = false
}: StrategyListCardProps) {
  /**
   * 获取验证状态徽章
   * @returns 验证状态徽章组件或 null
   */
  const getValidationBadge = () => {
    const variants = {
      passed: { variant: 'default' as const, icon: CheckCircle, label: '已验证', color: 'text-green-600' },
      failed: { variant: 'destructive' as const, icon: XCircle, label: '验证失败', color: 'text-red-600' },
      pending: { variant: 'secondary' as const, icon: AlertCircle, label: '待验证', color: 'text-yellow-600' },
      validating: { variant: 'outline' as const, icon: AlertCircle, label: '验证中', color: 'text-blue-600' }
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

  /**
   * 获取风险等级徽章变体
   * @returns 徽章变体类型
   */
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

  /**
   * 获取风险等级中文标签
   * @returns 风险等级中文文本
   */
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

  // 判断当前用户是否有权限编辑/删除该策略
  const canModify = isAdmin || (currentUserId && strategy.user_id === currentUserId)

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-6">
        <div className="flex items-start gap-6">
          {/* 左侧：策略类型图标 */}
          <div className="flex-shrink-0">
            <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
              isExitStrategy ? 'bg-red-100 dark:bg-red-950' : 'bg-green-100 dark:bg-green-950'
            }`}>
              {isExitStrategy ? (
                <TrendingDown className="h-6 w-6 text-red-600 dark:text-red-400" />
              ) : (
                <TrendingUp className="h-6 w-6 text-green-600 dark:text-green-400" />
              )}
            </div>
          </div>

          {/* 中间：策略信息 */}
          <div className="flex-1 min-w-0 space-y-3">
            {/* 标题行 */}
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-lg font-semibold truncate">{strategy.display_name}</h3>
                  <Badge variant="secondary" className="text-xs flex-shrink-0">
                    {isExitStrategy ? '离场策略' : '入场策略'}
                  </Badge>
                  {strategy.version && (
                    <span className="text-xs text-muted-foreground flex-shrink-0">
                      v{strategy.version}
                    </span>
                  )}
                </div>
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {strategy.description || '暂无描述'}
                </p>
              </div>

              {/* 验证状态 */}
              <div className="flex-shrink-0">
                {getValidationBadge()}
              </div>
            </div>

            {/* 标签和元信息行 */}
            <div className="flex flex-wrap items-center gap-2">
              {/* 创建者 */}
              <Badge variant="outline" className="flex items-center gap-1">
                <User className="h-3 w-3" />
                <span>{strategy.username || '未知用户'}</span>
              </Badge>

              {/* 类别 */}
              {strategy.category && (
                <Badge variant="secondary">{strategy.category}</Badge>
              )}

              {/* 风险等级 */}
              <Badge variant={getRiskBadgeVariant() as any}>
                {getRiskLabel()}
              </Badge>

              {/* 使用次数 */}
              <span className="text-xs text-muted-foreground">
                使用 {strategy.usage_count || 0} 次
              </span>

              {/* 标签 */}
              {strategy.tags?.slice(0, 3).map((tag, index) => (
                <Badge key={index} variant="outline" className="text-xs">
                  {tag}
                </Badge>
              ))}
              {strategy.tags && strategy.tags.length > 3 && (
                <span className="text-xs text-muted-foreground">
                  +{strategy.tags.length - 3}
                </span>
              )}
            </div>

            {/* 性能指标 */}
            {(strategy.avg_sharpe_ratio || strategy.avg_annual_return) && (
              <div className="flex items-center gap-6 text-sm">
                {strategy.avg_sharpe_ratio !== null && strategy.avg_sharpe_ratio !== undefined && (
                  <div>
                    <span className="text-muted-foreground">夏普率: </span>
                    <span className="font-medium">{Number(strategy.avg_sharpe_ratio).toFixed(2)}</span>
                  </div>
                )}
                {strategy.avg_annual_return !== null && strategy.avg_annual_return !== undefined && (
                  <div>
                    <span className="text-muted-foreground">年化收益: </span>
                    <span className={`font-medium ${
                      Number(strategy.avg_annual_return) > 0 ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {(Number(strategy.avg_annual_return) * 100).toFixed(2)}%
                    </span>
                  </div>
                )}
              </div>
            )}

            {/* 验证错误提示 */}
            {strategy.validation_status === 'failed' && strategy.validation_errors && (
              <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-2">
                <p className="text-xs text-destructive line-clamp-1">
                  验证错误: {JSON.stringify(strategy.validation_errors)}
                </p>
              </div>
            )}
          </div>

          {/* 右侧：操作按钮 */}
          <div className="flex-shrink-0 flex items-center gap-2">
            {/* 查看代码 */}
            <Link href={`/strategies/${strategy.id}/code`}>
              <Button variant="outline" size="sm">
                <Code className="mr-1 h-4 w-4" />
                代码
              </Button>
            </Link>

            {/* 回测按钮 */}
            {onBacktest && !isExitStrategy && (
              <Link href={`/backtest?type=unified&id=${strategy.id}`}>
                <Button size="sm">
                  <Play className="mr-1 h-4 w-4" />
                  回测
                </Button>
              </Link>
            )}
            {onBacktest && isExitStrategy && (
              <Button
                size="sm"
                disabled
                title="离场策略需要配合入场策略使用，不能单独回测"
              >
                <Play className="mr-1 h-4 w-4" />
                不可回测
              </Button>
            )}

            {/* 克隆 */}
            {onClone && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => onClone(strategy.id)}
                title="克隆策略"
              >
                <Copy className="h-4 w-4" />
              </Button>
            )}

            {/* 编辑 */}
            {onEdit && canModify && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => onEdit(strategy.id)}
                title="编辑策略"
              >
                <Edit className="h-4 w-4" />
              </Button>
            )}

            {/* 删除 */}
            {onDelete && canModify && (
              <Button
                size="sm"
                variant="destructive"
                onClick={() => onDelete(strategy.id)}
                title="删除策略"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
})

StrategyListCard.displayName = 'StrategyListCard'

export default StrategyListCard
