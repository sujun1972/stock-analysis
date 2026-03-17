/**
 * 任务面板组件
 *
 * 统一的异步任务管理面板，集成了以下功能：
 * 1. 显示所有活动任务和已完成任务
 * 2. 支持任务分组（按类型）
 * 3. 实时显示任务进度
 * 4. 自动刷新任务状态（5秒间隔）
 * 5. 手动刷新和清除已完成任务
 * 6. 显示任务错误信息
 *
 * @since 2026-03-17 合并了原有的两个任务面板，统一管理
 */

'use client'

import { useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import logger from '@/lib/logger'
import {
  RefreshCwIcon,
  CheckCircle2Icon,
  XCircleIcon,
  ClockIcon,
  Loader2Icon,
  Trash2Icon,
  DatabaseIcon,
  BrainCircuitIcon,
  TrendingUpIcon,
  ActivityIcon
} from 'lucide-react'
import { useTaskStore, TaskType } from '@/stores/task-store'
import { apiClient } from '@/lib/api-client'

interface TaskPanelProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function TaskPanel({ open, onOpenChange }: TaskPanelProps) {
  const tasks = useTaskStore((state) => Array.from(state.tasks.values()))
  const clearCompletedTasks = useTaskStore((state) => state.clearCompletedTasks)
  const activeTasks = tasks.filter((t) => t.status === 'pending' || t.status === 'running' || t.status === 'progress')
  const completedTasks = tasks.filter((t) => t.status === 'success' || t.status === 'failure')

  // 手动刷新任务列表
  const handleRefresh = async () => {
    try {
      const res = await apiClient.get('/api/sentiment/tasks/active') as any
      if (res.code === 200 && res.data?.tasks) {
        const taskStore = useTaskStore.getState()
        res.data.tasks.forEach((task: any) => {
          if (!taskStore.tasks.has(task.task_id)) {
            taskStore.addTask({
              taskId: task.task_id,
              taskName: task.task_name,
              displayName: task.display_name || task.task_name,
              taskType: task.task_type || 'other',
              status: task.status === 'running' ? 'running' : 'pending',
              startTime: Date.now(),
              worker: task.worker
            })
          } else {
            // 更新已存在的任务状态
            taskStore.updateTask(task.task_id, {
              status: task.status === 'running' ? 'running' : 'pending',
              worker: task.worker
            })
          }
        })
      }
    } catch (error) {
      logger.error('刷新任务列表失败', error)
    }
  }

  // 打开面板时自动刷新，并设置定时刷新
  useEffect(() => {
    if (open) {
      handleRefresh()

      // 每5秒自动刷新
      const interval = setInterval(handleRefresh, 5000)
      return () => clearInterval(interval)
    }
  }, [open])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
      case 'progress':
        return 'bg-blue-500'
      case 'pending':
        return 'bg-yellow-500'
      case 'success':
        return 'bg-green-500'
      case 'failure':
        return 'bg-red-500'
      default:
        return 'bg-gray-500'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'running':
      case 'progress':
        return '执行中'
      case 'pending':
        return '等待中'
      case 'success':
        return '已完成'
      case 'failure':
        return '失败'
      default:
        return '未知'
    }
  }

  const getTaskTypeIcon = (type: TaskType) => {
    switch (type) {
      case 'sync':
        return <DatabaseIcon className="h-4 w-4" />
      case 'sentiment':
        return <ActivityIcon className="h-4 w-4" />
      case 'ai_analysis':
        return <BrainCircuitIcon className="h-4 w-4" />
      case 'backtest':
        return <TrendingUpIcon className="h-4 w-4" />
      default:
        return <ClockIcon className="h-4 w-4" />
    }
  }

  const getTaskTypeLabel = (type: TaskType) => {
    switch (type) {
      case 'sync':
        return '数据同步'
      case 'sentiment':
        return '情绪数据'
      case 'ai_analysis':
        return 'AI分析'
      case 'backtest':
        return '策略回测'
      case 'premarket':
        return '盘前预期'
      default:
        return '其他'
    }
  }

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:w-[540px] sm:max-w-[90vw]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Loader2Icon className="h-5 w-5 animate-spin text-blue-600" />
            异步任务管理
          </SheetTitle>
          <SheetDescription>查看所有活动任务和历史任务</SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-4">
          {/* 操作栏 */}
          <div className="flex justify-between items-center gap-2">
            <div className="text-sm text-muted-foreground flex-shrink-0">
              <span className="hidden sm:inline">活动: {activeTasks.length} | 已完成: {completedTasks.length}</span>
              <span className="sm:hidden">{activeTasks.length} / {completedTasks.length}</span>
            </div>
            <div className="flex gap-2">
              {completedTasks.length > 0 && (
                <Button variant="outline" size="sm" onClick={clearCompletedTasks} title="清除已完成">
                  <Trash2Icon className="h-4 w-4 sm:mr-2" />
                  <span className="hidden sm:inline">清除已完成</span>
                </Button>
              )}
              <Button variant="outline" size="sm" onClick={handleRefresh} title="刷新">
                <RefreshCwIcon className="h-4 w-4 sm:mr-2" />
                <span className="hidden sm:inline">刷新</span>
              </Button>
            </div>
          </div>

          <Separator />

          {/* 任务列表 */}
          <ScrollArea className="h-[calc(100vh-220px)]">
            {tasks.length === 0 ? (
              <Card className="border-dashed">
                <CardContent className="py-12 text-center">
                  <CheckCircle2Icon className="h-12 w-12 mx-auto mb-4 text-green-500" />
                  <p className="text-muted-foreground">暂无任务</p>
                  <p className="text-sm text-muted-foreground mt-1">所有任务已完成</p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {/* 活动任务 */}
                {activeTasks.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                      活动任务 ({activeTasks.length})
                    </h3>
                    {activeTasks.map((task) => (
                      <Card key={task.taskId} className="mb-3">
                        <CardHeader className="pb-3">
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                {getTaskTypeIcon(task.taskType)}
                                <span className="text-xs text-muted-foreground">
                                  {getTaskTypeLabel(task.taskType)}
                                </span>
                              </div>
                              <CardTitle className="text-base truncate">{task.displayName}</CardTitle>
                              <CardDescription className="text-xs mt-1 font-mono truncate">
                                ID: {task.taskId.substring(0, 16)}...
                              </CardDescription>
                            </div>
                            <Badge
                              variant="outline"
                              className={`${getStatusColor(task.status)} text-white border-0 flex-shrink-0`}
                            >
                              {getStatusText(task.status)}
                            </Badge>
                          </div>
                        </CardHeader>
                        <CardContent className="py-2 px-4 bg-muted/50">
                          {task.status === 'progress' && task.progress !== undefined ? (
                            <div className="space-y-2">
                              <Progress value={task.progress} className="h-2" />
                              <div className="flex items-center justify-between text-xs text-muted-foreground">
                                <span>进度: {task.progress}%</span>
                                <Loader2Icon className="h-3 w-3 animate-spin" />
                              </div>
                            </div>
                          ) : (
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                              {task.status === 'running' ? (
                                <>
                                  <Loader2Icon className="h-3 w-3 animate-spin" />
                                  <span>正在执行...</span>
                                </>
                              ) : (
                                <>
                                  <ClockIcon className="h-3 w-3" />
                                  <span>等待执行</span>
                                </>
                              )}
                              {task.worker && (
                                <span className="ml-auto">Worker: {task.worker.split('@')[0]}</span>
                              )}
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}

                {/* 已完成任务 */}
                {completedTasks.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                      已完成任务 ({completedTasks.length})
                    </h3>
                    {completedTasks.map((task) => (
                      <Card key={task.taskId} className="mb-3 opacity-75">
                        <CardHeader className="pb-3">
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 mb-1">
                                {getTaskTypeIcon(task.taskType)}
                                <span className="text-xs text-muted-foreground">
                                  {getTaskTypeLabel(task.taskType)}
                                </span>
                              </div>
                              <CardTitle className="text-base truncate">{task.displayName}</CardTitle>
                            </div>
                            <Badge
                              variant="outline"
                              className={`${getStatusColor(task.status)} text-white border-0 flex-shrink-0`}
                            >
                              {task.status === 'success' ? (
                                <CheckCircle2Icon className="h-3 w-3 mr-1" />
                              ) : (
                                <XCircleIcon className="h-3 w-3 mr-1" />
                              )}
                              {getStatusText(task.status)}
                            </Badge>
                          </div>
                        </CardHeader>
                        {task.error && (
                          <CardContent className="py-2 px-4 bg-red-50 dark:bg-red-900/20">
                            <p className="text-xs text-red-800 dark:text-red-200 break-words">{task.error}</p>
                          </CardContent>
                        )}
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            )}
          </ScrollArea>
        </div>
      </SheetContent>
    </Sheet>
  )
}
