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
  TrendingDown,
  Filter,
  ExternalLink,
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

  // 策略类型判断
  const isExitStrategy = strategy.strategy_type === 'exit'
  const isStockSelectionStrategy = strategy.strategy_type === 'stock_selection'

  // 判断当前用户是否有权限编辑/删除该策略
  const canModify = isAdmin || (currentUserId && strategy.user_id === currentUserId)

  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardContent className="p-4 sm:p-6">
        {/* 主区（图标 + 信息）+ 操作区：手机上下分，桌面左右分 */}
        <div className="flex flex-col lg:flex-row lg:items-start gap-4 lg:gap-6">
          {/* 主区：图标 + 策略信息（始终并排） */}
          <div className="flex items-start gap-3 sm:gap-4 flex-1 min-w-0">
            {/* 策略类型图标 */}
            <div className="flex-shrink-0">
              <div className={`w-10 h-10 sm:w-12 sm:h-12 rounded-lg flex items-center justify-center ${
                isStockSelectionStrategy
                  ? 'bg-blue-100 dark:bg-blue-950'
                  : isExitStrategy
                  ? 'bg-red-100 dark:bg-red-950'
                  : 'bg-green-100 dark:bg-green-950'
              }`}>
                {isStockSelectionStrategy ? (
                  <Filter className="h-5 w-5 sm:h-6 sm:w-6 text-blue-600 dark:text-blue-400" />
                ) : isExitStrategy ? (
                  <TrendingDown className="h-5 w-5 sm:h-6 sm:w-6 text-red-600 dark:text-red-400" />
                ) : (
                  <TrendingUp className="h-5 w-5 sm:h-6 sm:w-6 text-green-600 dark:text-green-400" />
                )}
              </div>
            </div>

            {/* 中间：策略信息 */}
            <div className="flex-1 min-w-0 space-y-3">
              {/* 标题行 */}
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 mb-1">
                    <h3 className="text-base sm:text-lg font-semibold break-words min-w-0">{strategy.display_name}</h3>
                    <Badge variant="secondary" className="text-xs flex-shrink-0">
                      {isStockSelectionStrategy ? '选股策略' : isExitStrategy ? '离场策略' : '入场策略'}
                    </Badge>
                    {strategy.version && (
                      <span className="text-xs text-muted-foreground flex-shrink-0 tabular-nums">
                        v{strategy.version}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground line-clamp-2 break-words">
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
                <Badge variant="outline" className="flex items-center gap-1 max-w-[180px]">
                  <User className="h-3 w-3 shrink-0" />
                  <span className="truncate">{strategy.username || '未知用户'}</span>
                </Badge>

                {/* 类别 */}
                {strategy.category && (
                  <Badge variant="secondary" className="max-w-[140px] truncate" title={strategy.category}>
                    {strategy.category}
                  </Badge>
                )}

                {/* 风险等级（选股策略不显示） */}
                {!isStockSelectionStrategy && (
                  <Badge variant={getRiskBadgeVariant() as any}>
                    {getRiskLabel()}
                  </Badge>
                )}

                {/* 使用次数 */}
                <span className="text-xs text-muted-foreground tabular-nums">
                  使用 {strategy.usage_count || 0} 次
                </span>

                {/* 标签 */}
                {strategy.tags?.slice(0, 3).map((tag, index) => (
                  <Badge key={index} variant="outline" className="text-xs max-w-[140px] truncate" title={tag}>
                    {tag}
                  </Badge>
                ))}
                {strategy.tags && strategy.tags.length > 3 && (
                  <span className="text-xs text-muted-foreground tabular-nums">
                    +{strategy.tags.length - 3}
                  </span>
                )}
              </div>

              {/* 性能指标（选股策略不显示回测类指标） */}
              {!isStockSelectionStrategy && (strategy.avg_sharpe_ratio || strategy.avg_annual_return) && (
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 sm:gap-6 text-sm">
                  {strategy.avg_sharpe_ratio !== null && strategy.avg_sharpe_ratio !== undefined && (
                    <div>
                      <span className="text-muted-foreground">夏普率: </span>
                      <span className="font-medium tabular-nums">{Number(strategy.avg_sharpe_ratio).toFixed(2)}</span>
                    </div>
                  )}
                  {strategy.avg_annual_return !== null && strategy.avg_annual_return !== undefined && (
                    <div>
                      <span className="text-muted-foreground">年化收益: </span>
                      <span className={`font-medium tabular-nums ${
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
                  <p className="text-xs text-destructive line-clamp-1 break-words">
                    验证错误: {JSON.stringify(strategy.validation_errors)}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* 右侧（桌面）/ 底部（手机、平板）：操作按钮 */}
          <div className="flex flex-wrap items-center gap-2 lg:flex-shrink-0 lg:flex-nowrap pt-2 lg:pt-0 border-t lg:border-t-0 -mx-4 lg:mx-0 px-4 lg:px-0">
            {/* 主操作组：代码 + 回测/查看选股结果 */}
            <div className="flex gap-2 flex-1 lg:flex-initial min-w-0">
              {/* 查看代码 */}
              <Link href={`/strategies/${strategy.id}/code`} className="flex-1 lg:flex-initial">
                <Button variant="outline" size="sm" className="w-full">
                  <Code className="mr-1 h-4 w-4 shrink-0" />
                  <span className="truncate">代码</span>
                </Button>
              </Link>

              {/* 选股策略：跳转到股票列表 */}
              {isStockSelectionStrategy ? (
                <Link href={`/stocks?stock_selection_strategy_id=${strategy.id}`} className="flex-1 lg:flex-initial min-w-0">
                  <Button size="sm" className="w-full">
                    <ExternalLink className="mr-1 h-4 w-4 shrink-0" />
                    <span className="truncate">查看选股结果</span>
                  </Button>
                </Link>
              ) : (
                <>
                  {/* 回测按钮（入场策略） */}
                  {onBacktest && !isExitStrategy && (
                    <Link href={`/backtest?type=unified&id=${strategy.id}`} className="flex-1 lg:flex-initial">
                      <Button size="sm" className="w-full">
                        <Play className="mr-1 h-4 w-4 shrink-0" />
                        <span className="truncate">回测</span>
                      </Button>
                    </Link>
                  )}
                  {onBacktest && isExitStrategy && (
                    <Button size="sm" className="flex-1 lg:flex-initial" disabled title="离场策略需要配合入场策略使用，不能单独回测">
                      <Play className="mr-1 h-4 w-4 shrink-0" />
                      <span className="truncate">不可回测</span>
                    </Button>
                  )}
                </>
              )}
            </div>

            {/* 次要操作组：克隆 / 编辑 / 删除 */}
            {(onClone || (onEdit && canModify) || (onDelete && canModify)) && (
              <div className="flex items-center gap-2 ml-auto lg:ml-0 shrink-0">
                {/* 克隆 */}
                {onClone && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onClone(strategy.id)}
                    aria-label={`克隆策略 ${strategy.display_name}`}
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
                    aria-label={`编辑策略 ${strategy.display_name}`}
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
                    aria-label={`删除策略 ${strategy.display_name}`}
                    title="删除策略"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                )}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
})

StrategyListCard.displayName = 'StrategyListCard'

export default StrategyListCard
