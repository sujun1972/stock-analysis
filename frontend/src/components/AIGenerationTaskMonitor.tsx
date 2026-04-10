'use client'

/**
 * 全局AI生成任务监控器
 * 显示在页面顶部，实时展示AI生成任务进度
 */

import { useAIGenerationTask } from '@/contexts/AIGenerationTaskContext'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Loader2, X, Sparkles } from 'lucide-react'

export function AIGenerationTaskMonitor() {
  const { activeTasks, cancelTask } = useAIGenerationTask()

  // 只显示进行中的任务
  const runningTasks = Array.from(activeTasks.values()).filter(
    (task) => task.status === 'PENDING' || task.status === 'PROGRESS'
  )

  if (runningTasks.length === 0) {
    return null
  }

  return (
    <div className="fixed top-20 right-4 z-50 max-w-md animate-in slide-in-from-right">
      {runningTasks.map((task) => (
        <Card key={task.taskId} className="mb-2 border-2 border-primary/50 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950 dark:to-purple-950 shadow-lg">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              {/* 动画图标 */}
              <div className="flex-shrink-0">
                <div className="relative">
                  <Sparkles className="h-5 w-5 text-primary animate-pulse" />
                  <Loader2 className="h-5 w-5 text-primary animate-spin absolute top-0 left-0 opacity-50" />
                </div>
              </div>

              {/* 任务信息 */}
              <div className="flex-1 space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-semibold text-primary">AI策略生成中</h4>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => cancelTask(task.taskId)}
                    className="h-6 w-6 p-0"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>

                {/* 状态文字（带动画效果） */}
                <div className="flex items-center gap-2">
                  <div className="flex gap-1">
                    <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                    <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                    <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                  </div>
                  <p className="text-xs text-muted-foreground">{task.message}</p>
                </div>

                {/* AI提供商 */}
                {task.providerUsed && (
                  <div className="flex items-center gap-1 text-xs">
                    <span className="text-muted-foreground">使用:</span>
                    <span className="text-primary font-medium">{task.providerUsed}</span>
                  </div>
                )}

                {/* 任务ID */}
                <p className="text-[10px] text-muted-foreground/60 font-mono">
                  任务ID: {task.taskId?.slice(0, 16)}...
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
