'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Play, Pause, X, MoreVertical, TrendingUp, Eye, Trash2, FileText } from 'lucide-react'
import { ExperimentBatch } from '@/store/experimentStore'
import { useRouter } from 'next/navigation'

interface BatchCardProps {
  batch: ExperimentBatch
  onStart?: () => void
  onCancel?: () => void
  onDelete?: () => void
  onViewDetails?: () => void
}

export function BatchCard({ batch, onStart, onCancel, onDelete, onViewDetails }: BatchCardProps) {
  const router = useRouter()

  const getStatusConfig = (status: string) => {
    const configs: Record<string, { variant: any; label: string; color: string }> = {
      pending: { variant: 'secondary', label: '待运行', color: 'text-gray-600' },
      running: { variant: 'default', label: '运行中', color: 'text-blue-600' },
      completed: { variant: 'success' as any, label: '已完成', color: 'text-green-600' },
      failed: { variant: 'destructive', label: '失败', color: 'text-red-600' },
      cancelled: { variant: 'outline', label: '已取消', color: 'text-gray-400' },
    }
    return configs[status] || configs.pending
  }

  const statusConfig = getStatusConfig(batch.status)
  const progress = batch.total_experiments > 0
    ? (batch.completed_experiments / batch.total_experiments) * 100
    : 0

  const handleViewDetails = () => {
    if (onViewDetails) {
      onViewDetails()
    } else {
      router.push(`/auto-experiment/batch/${batch.batch_id}`)
    }
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="text-lg flex items-center gap-2">
              {batch.batch_name}
              <Badge variant={statusConfig.variant}>{statusConfig.label}</Badge>
            </CardTitle>
            <CardDescription>
              批次 #{batch.batch_id} · {batch.strategy === 'grid' ? '网格搜索' : '随机采样'} ·
              创建于 {new Date(batch.created_at).toLocaleString('zh-CN')}
            </CardDescription>
          </div>

          {/* 操作菜单 */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>操作</DropdownMenuLabel>
              <DropdownMenuSeparator />

              <DropdownMenuItem onClick={handleViewDetails}>
                <Eye className="mr-2 h-4 w-4" />
                查看详情
              </DropdownMenuItem>

              <DropdownMenuItem onClick={() => router.push(`/auto-experiment/batch/${batch.batch_id}#top-models`)}>
                <TrendingUp className="mr-2 h-4 w-4" />
                Top模型
              </DropdownMenuItem>

              <DropdownMenuItem onClick={() => router.push(`/auto-experiment/batch/${batch.batch_id}#report`)}>
                <FileText className="mr-2 h-4 w-4" />
                实验报告
              </DropdownMenuItem>

              <DropdownMenuSeparator />

              {batch.status === 'pending' && onStart && (
                <DropdownMenuItem onClick={onStart}>
                  <Play className="mr-2 h-4 w-4" />
                  启动批次
                </DropdownMenuItem>
              )}

              {batch.status === 'running' && onCancel && (
                <DropdownMenuItem onClick={onCancel} className="text-orange-600">
                  <Pause className="mr-2 h-4 w-4" />
                  取消运行
                </DropdownMenuItem>
              )}

              {(batch.status === 'completed' || batch.status === 'failed' || batch.status === 'cancelled') && onDelete && (
                <DropdownMenuItem onClick={onDelete} className="text-red-600">
                  <Trash2 className="mr-2 h-4 w-4" />
                  删除批次
                </DropdownMenuItem>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* 描述 */}
        {batch.description && (
          <p className="text-sm text-muted-foreground">{batch.description}</p>
        )}

        {/* 进度条 */}
        {batch.status === 'running' && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">进度</span>
              <span className="font-medium">{progress.toFixed(1)}%</span>
            </div>
            <Progress value={progress} className="h-2" />
          </div>
        )}

        {/* 统计信息 */}
        <div className="grid grid-cols-4 gap-4">
          <div>
            <div className="text-xs text-muted-foreground">总实验数</div>
            <div className="text-2xl font-bold">{batch.total_experiments}</div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">已完成</div>
            <div className="text-2xl font-bold text-green-600">
              {batch.completed_experiments}
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">失败</div>
            <div className="text-2xl font-bold text-red-600">
              {batch.failed_experiments}
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">成功率</div>
            <div className="text-2xl font-bold">
              {batch.success_rate_pct.toFixed(0)}%
            </div>
          </div>
        </div>

        {/* 性能指标（如果已完成） */}
        {batch.status === 'completed' && batch.max_rank_score && (
          <div className="pt-2 border-t">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">最高评分: </span>
                <span className="font-bold">{batch.max_rank_score.toFixed(2)}</span>
              </div>
              {batch.avg_rank_score && (
                <div>
                  <span className="text-muted-foreground">平均评分: </span>
                  <span className="font-bold">{batch.avg_rank_score.toFixed(2)}</span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* 耗时信息 */}
        {batch.duration_hours && batch.duration_hours > 0 && (
          <div className="text-xs text-muted-foreground">
            耗时: {batch.duration_hours.toFixed(2)} 小时
          </div>
        )}

        {/* 快速操作按钮 */}
        <div className="flex gap-2 pt-2">
          <Button size="sm" variant="outline" onClick={handleViewDetails} className="flex-1">
            <Eye className="mr-2 h-4 w-4" />
            查看详情
          </Button>

          {batch.status === 'completed' && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => router.push(`/auto-experiment/batch/${batch.batch_id}#top-models`)}
              className="flex-1"
            >
              <TrendingUp className="mr-2 h-4 w-4" />
              Top模型
            </Button>
          )}

          {batch.status === 'pending' && onStart && (
            <Button size="sm" onClick={onStart} className="flex-1">
              <Play className="mr-2 h-4 w-4" />
              启动
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
