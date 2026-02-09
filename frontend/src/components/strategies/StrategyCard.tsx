/**
 * 策略卡片组件
 * 用于展示策略配置或动态策略的卡片
 */

'use client'

import { memo } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Edit, Trash2, Play, Code, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import type { StrategyConfig, DynamicStrategy } from '@/types/strategy'

interface StrategyCardProps {
  type: 'config' | 'dynamic'
  data: StrategyConfig | DynamicStrategy
  onEdit?: (id: number) => void
  onDelete?: (id: number) => void
  onTest?: (id: number) => void
  onView?: (id: number) => void
}

const StrategyCard = memo(function StrategyCard({
  type,
  data,
  onEdit,
  onDelete,
  onTest,
  onView
}: StrategyCardProps) {
  const isConfig = type === 'config'
  const config = isConfig ? (data as StrategyConfig) : null
  const dynamic = !isConfig ? (data as DynamicStrategy) : null

  const getValidationStatusBadge = (status?: string) => {
    if (!status) return null

    const variants = {
      passed: { variant: 'default' as const, icon: CheckCircle, label: '验证通过' },
      failed: { variant: 'destructive' as const, icon: XCircle, label: '验证失败' },
      warning: { variant: 'outline' as const, icon: AlertCircle, label: '有警告' },
      pending: { variant: 'secondary' as const, icon: AlertCircle, label: '待验证' }
    }

    const info = variants[status as keyof typeof variants]
    if (!info) return null

    const Icon = info.icon

    return (
      <Badge variant={info.variant} className="flex items-center gap-1">
        <Icon className="h-3 w-3" />
        {info.label}
      </Badge>
    )
  }

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg">
              {isConfig ? config?.name : dynamic?.display_name}
            </CardTitle>
            <CardDescription className="mt-1">
              {isConfig ? (
                <>
                  类型: {config?.strategy_type} | 创建于{' '}
                  {new Date(config!.created_at).toLocaleDateString()}
                </>
              ) : (
                <>
                  策略名: {dynamic?.strategy_name} | 版本 {dynamic?.version || 1}
                </>
              )}
            </CardDescription>
          </div>
          <div className="flex flex-col items-end gap-2">
            {isConfig ? (
              <Badge variant={config?.is_active ? 'default' : 'secondary'}>
                {config?.is_active ? '启用' : '禁用'}
              </Badge>
            ) : (
              <>
                {getValidationStatusBadge(dynamic?.validation_status)}
                <Badge variant={dynamic?.is_enabled ? 'default' : 'secondary'}>
                  {dynamic?.is_enabled ? '启用' : '禁用'}
                </Badge>
              </>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* 描述 */}
        {(config?.description || dynamic?.description) && (
          <p className="text-sm text-muted-foreground line-clamp-2">
            {isConfig ? config?.description : dynamic?.description}
          </p>
        )}

        {/* 配置详情 */}
        {isConfig && config?.config && (
          <div className="bg-muted/50 rounded-lg p-3">
            <p className="text-xs font-medium text-muted-foreground mb-2">配置参数</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(config.config).slice(0, 3).map(([key, value]) => (
                <Badge key={key} variant="outline" className="text-xs">
                  {key}: {JSON.stringify(value)}
                </Badge>
              ))}
              {Object.keys(config.config).length > 3 && (
                <Badge variant="outline" className="text-xs">
                  +{Object.keys(config.config).length - 3} 个参数
                </Badge>
              )}
            </div>
          </div>
        )}

        {/* 动态策略验证信息 */}
        {!isConfig && dynamic?.validation_errors && dynamic.validation_errors.length > 0 && (
          <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-3">
            <p className="text-xs font-medium text-destructive mb-1">验证错误</p>
            <p className="text-xs text-destructive/80">
              {dynamic.validation_errors[0].message}
              {dynamic.validation_errors.length > 1 && ` (+${dynamic.validation_errors.length - 1} 个)`}
            </p>
          </div>
        )}

        {/* 操作按钮 */}
        <div className="flex gap-2 pt-2">
          {onView && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onView(data.id)}
              className="flex-1"
            >
              <Code className="h-4 w-4 mr-1" />
              查看
            </Button>
          )}
          {onTest && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onTest(data.id)}
              className="flex-1"
            >
              <Play className="h-4 w-4 mr-1" />
              测试
            </Button>
          )}
          {onEdit && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => onEdit(data.id)}
            >
              <Edit className="h-4 w-4" />
            </Button>
          )}
          {onDelete && (
            <Button
              size="sm"
              variant="destructive"
              onClick={() => onDelete(data.id)}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
})

StrategyCard.displayName = 'StrategyCard'

export default StrategyCard
