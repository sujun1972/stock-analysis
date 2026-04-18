'use client'

import { Strategy } from '@/types/strategy'
import PublishStatusBadge from '@/components/strategies/PublishStatusBadge'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

// 策略类型显示名称
const strategyTypeNames = {
  stock_selection: '选股策略',
  entry: '入场策略',
  exit: '离场策略',
}

// 来源类型显示名称
const sourceTypeNames = {
  builtin: '系统内置',
  ai: 'AI生成',
  custom: '用户自定义',
}

// 验证状态标签颜色
const validationStatusColors = {
  pending: 'bg-gray-100 text-gray-800',
  passed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  validating: 'bg-yellow-100 text-yellow-800',
}

interface StrategyDetailDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  strategy: Strategy | null
}

export function StrategyDetailDialog({
  open,
  onOpenChange,
  strategy,
}: StrategyDetailDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>策略详情</DialogTitle>
          <DialogDescription>
            {strategy?.display_name || strategy?.name}
          </DialogDescription>
        </DialogHeader>
        {strategy && (
          <div className="space-y-6">
            {/* 基本信息 */}
            <div>
              <h3 className="text-lg font-semibold mb-3">基本信息</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-muted-foreground">策略ID</Label>
                  <p className="font-mono">{strategy.id}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">内部名称</Label>
                  <p>{strategy.name}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">显示名称</Label>
                  <p>{strategy.display_name || '-'}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">策略类型</Label>
                  <p>{strategyTypeNames[strategy.strategy_type as keyof typeof strategyTypeNames]}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">来源类型</Label>
                  <p>{sourceTypeNames[strategy.source_type as keyof typeof sourceTypeNames]}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">风险等级</Label>
                  <p>{strategy.risk_level || '未评估'}</p>
                </div>
              </div>
            </div>

            {/* 描述 */}
            {strategy.description && (
              <div>
                <Label className="text-muted-foreground">策略描述</Label>
                <p className="mt-1">{strategy.description}</p>
              </div>
            )}

            {/* 状态信息 */}
            <div>
              <h3 className="text-lg font-semibold mb-3">状态信息</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-muted-foreground">验证状态</Label>
                  <Badge className={validationStatusColors[strategy.validation_status as keyof typeof validationStatusColors] || 'bg-gray-100'}>
                    {strategy.validation_status}
                  </Badge>
                </div>
                <div>
                  <Label className="text-muted-foreground">发布状态</Label>
                  <PublishStatusBadge status={strategy.publish_status || 'draft'} />
                </div>
                <div>
                  <Label className="text-muted-foreground">启用状态</Label>
                  <p>{strategy.is_enabled ? '已启用' : '已禁用'}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">用户归属</Label>
                  <p>{strategy.username || (strategy.user_id ? `用户#${strategy.user_id}` : '系统')}</p>
                </div>
              </div>
            </div>

            {/* 统计信息 */}
            <div>
              <h3 className="text-lg font-semibold mb-3">使用统计</h3>
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <Label className="text-muted-foreground">使用次数</Label>
                  <p className="text-2xl font-semibold">{strategy.usage_count || 0}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">回测次数</Label>
                  <p className="text-2xl font-semibold">{strategy.backtest_count || 0}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">平均夏普比率</Label>
                  <p className="text-2xl font-semibold">
                    {strategy.avg_sharpe_ratio ? strategy.avg_sharpe_ratio.toFixed(2) : '-'}
                  </p>
                </div>
              </div>
            </div>

            {/* 标签 */}
            {strategy.tags && strategy.tags.length > 0 && (
              <div>
                <Label className="text-muted-foreground">标签</Label>
                <div className="flex flex-wrap gap-2 mt-2">
                  {strategy.tags.map((tag, index) => (
                    <Badge key={index} variant="secondary">{tag}</Badge>
                  ))}
                </div>
              </div>
            )}

            {/* 时间信息 */}
            <div>
              <h3 className="text-lg font-semibold mb-3">时间信息</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label className="text-muted-foreground">创建时间</Label>
                  <p>{new Date(strategy.created_at).toLocaleString('zh-CN')}</p>
                </div>
                <div>
                  <Label className="text-muted-foreground">更新时间</Label>
                  <p>{new Date(strategy.updated_at).toLocaleString('zh-CN')}</p>
                </div>
              </div>
            </div>
          </div>
        )}
        <DialogFooter>
          <Button onClick={() => onOpenChange(false)}>关闭</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
