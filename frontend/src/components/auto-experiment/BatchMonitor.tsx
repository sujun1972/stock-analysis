'use client'

import { useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Activity, CheckCircle, XCircle, Clock } from 'lucide-react'
import { useExperimentStore } from '@/store/experimentStore'

interface BatchMonitorProps {
  batchId: number
  autoRefresh?: boolean
}

export function BatchMonitor({ batchId, autoRefresh = true }: BatchMonitorProps) {
  const { currentBatch, fetchBatchInfo, subscribeToProgress, unsubscribeFromProgress } = useExperimentStore()

  useEffect(() => {
    // 初始加载
    fetchBatchInfo(batchId)

    if (autoRefresh) {
      // 订阅SSE实时更新
      subscribeToProgress(batchId)

      return () => {
        unsubscribeFromProgress()
      }
    } else {
      // 轮询模式
      const interval = setInterval(() => {
        fetchBatchInfo(batchId)
      }, 5000)

      return () => clearInterval(interval)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchId, autoRefresh])

  if (!currentBatch) {
    return <div>加载中...</div>
  }

  const progress = currentBatch.total_experiments > 0
    ? (currentBatch.completed_experiments / currentBatch.total_experiments) * 100
    : 0

  const isRunning = currentBatch.status === 'running'

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5" />
          实时监控
          {isRunning && <Badge variant="default" className="animate-pulse">运行中</Badge>}
        </CardTitle>
        <CardDescription>
          批次 #{batchId} 实时状态
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* 进度 */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-muted-foreground">整体进度</span>
            <span className="font-medium">
              {currentBatch.completed_experiments} / {currentBatch.total_experiments} ({progress.toFixed(1)}%)
            </span>
          </div>
          <Progress value={progress} className="h-3" />
        </div>

        {/* 状态统计 */}
        <div className="grid grid-cols-3 gap-4">
          <div className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-600" />
            <div>
              <div className="text-sm text-muted-foreground">已完成</div>
              <div className="text-2xl font-bold text-green-600">
                {currentBatch.completed_experiments}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Clock className="h-5 w-5 text-blue-600" />
            <div>
              <div className="text-sm text-muted-foreground">运行中</div>
              <div className="text-2xl font-bold text-blue-600">
                {currentBatch.running_experiments}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <XCircle className="h-5 w-5 text-red-600" />
            <div>
              <div className="text-sm text-muted-foreground">失败</div>
              <div className="text-2xl font-bold text-red-600">
                {currentBatch.failed_experiments}
              </div>
            </div>
          </div>
        </div>

        {/* 时间信息 */}
        <div className="space-y-2 text-sm">
          {currentBatch.started_at && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">开始时间</span>
              <span>{new Date(currentBatch.started_at).toLocaleString('zh-CN')}</span>
            </div>
          )}

          {currentBatch.completed_at && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">完成时间</span>
              <span>{new Date(currentBatch.completed_at).toLocaleString('zh-CN')}</span>
            </div>
          )}

          {currentBatch.duration_hours && currentBatch.duration_hours > 0 && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">总耗时</span>
              <span className="font-medium">{currentBatch.duration_hours.toFixed(2)} 小时</span>
            </div>
          )}

          {isRunning && currentBatch.completed_experiments > 0 && (
            <div className="flex justify-between">
              <span className="text-muted-foreground">预计剩余时间</span>
              <span className="font-medium">
                {(() => {
                  const avgTime = (currentBatch.duration_hours || 0) / currentBatch.completed_experiments
                  const remaining = (currentBatch.total_experiments - currentBatch.completed_experiments) * avgTime
                  return `${remaining.toFixed(1)} 小时`
                })()}
              </span>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
