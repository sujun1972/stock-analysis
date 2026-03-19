/**
 * 任务面板组件
 *
 * 统一的异步任务管理面板，集成了以下功能：
 * 1. 显示所有活动任务和已完成任务
 * 2. 支持任务分组（按类型）
 * 3. 实时显示任务进度
 * 4. 手动刷新和清除已完成任务
 * 5. 显示任务错误信息
 *
 * 注意：
 * - 任务状态轮询由 Header 组件全局处理（每5秒）
 * - 任务历史同步由 Header 组件全局处理（每30秒）
 * - 本组件仅提供展示和手动刷新功能，不做自动轮询
 *
 * @since 2026-03-17 合并了原有的两个任务面板，统一管理
 * @since 2026-03-18 移除重复轮询，改为依赖全局轮询
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
  ActivityIcon,
  CalendarIcon
} from 'lucide-react'
import { useTaskStore, TaskType } from '@/stores/task-store'
import { apiClient } from '@/lib/api-client'

interface TaskPanelProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function TaskPanel({ open, onOpenChange }: TaskPanelProps) {
  const tasks = useTaskStore((state) => Array.from(state.tasks.values()))
  const setTasks = useTaskStore((state) => state.setTasks)
  const removeTask = useTaskStore((state) => state.removeTask)
  const clearCompletedTasks = useTaskStore((state) => state.clearCompletedTasks)
  const triggerPoll = useTaskStore((state) => state.triggerPoll)

  // 任务状态轮询由 Header 组件全局处理，这里不再重复轮询
  // 但在面板打开时，立即触发一次轮询以获取最新状态
  useEffect(() => {
    if (open) {
      logger.info('[TaskPanel] 面板打开，立即触发一次轮询')
      triggerPoll()
    }
  }, [open, triggerPoll])

  const activeTasks = tasks.filter((t) => t.status === 'pending' || t.status === 'running' || t.status === 'progress')
  const completedTasks = tasks.filter((t) => t.status === 'success' || t.status === 'failure')
    .sort((a, b) => (b.endTime || b.startTime) - (a.endTime || a.startTime)) // 按完成时间倒序排列

  // 手动刷新任务列表（从API重新加载）
  const handleRefresh = async () => {
    try {
      const response = await apiClient.get('/api/celery/task-history?limit=100') as any
      if (response.code === 200 && response.data?.tasks) {
        const historyTasks = response.data.tasks.map((t: any) => ({
          taskId: t.celery_task_id,
          taskName: t.task_name,
          displayName: t.display_name || t.task_name,
          taskType: t.task_type || 'other',
          status: t.status,
          progress: t.progress || 0,
          startTime: t.started_at ? new Date(t.started_at).getTime() : new Date(t.created_at).getTime(),
          endTime: t.completed_at ? new Date(t.completed_at).getTime() : undefined,
          result: t.result,
          error: t.error,
          worker: t.worker
        }))

        // 合并历史任务和当前任务
        const currentTasks = useTaskStore.getState().tasks
        const mergedTasks = new Map(currentTasks)
        historyTasks.forEach((task: any) => {
          if (!mergedTasks.has(task.taskId)) {
            mergedTasks.set(task.taskId, task)
          }
        })

        setTasks(Array.from(mergedTasks.values()))
        logger.info(`[TaskPanel] 手动刷新了 ${historyTasks.length} 条任务历史记录`)
      }
    } catch (error) {
      logger.error('[TaskPanel] 手动刷新任务失败', error)
    }
  }

  // 清理僵尸任务（运行中但超过1小时未完成的任务）
  const handleCleanupStale = async () => {
    try {
      const response = await apiClient.post('/api/celery/task-history/cleanup-stale') as any
      if (response.code === 200) {
        logger.info(`[TaskPanel] 清理了 ${response.data.deleted_count} 个僵尸任务`)
        // 重新加载任务列表
        await handleRefresh()
      }
    } catch (error) {
      logger.error('[TaskPanel] 清理僵尸任务失败', error)
    }
  }

  // 删除单个任务
  const handleDeleteTask = async (taskId: string) => {
    try {
      const response = await apiClient.delete(`/api/celery/task-history/${taskId}`) as any
      if (response.code === 200) {
        logger.info(`[TaskPanel] 删除任务 ${taskId.substring(0, 8)}... 成功`)
        // 从本地store移除
        removeTask(taskId)
      }
    } catch (error) {
      logger.error('[TaskPanel] 删除任务失败', error)
    }
  }

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
      case 'scheduler':
        return '定时任务'
      default:
        return '其他'
    }
  }

  const formatDuration = (startTime: number, endTime?: number) => {
    const end = endTime || Date.now()
    const duration = Math.floor((end - startTime) / 1000) // 秒

    if (duration < 60) {
      // 小于1秒显示为1秒
      return `${Math.max(1, duration)}秒`
    } else if (duration < 3600) {
      return `${Math.floor(duration / 60)}分钟`
    } else {
      const hours = Math.floor(duration / 3600)
      const minutes = Math.floor((duration % 3600) / 60)
      return `${hours}小时${minutes}分钟`
    }
  }

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp)
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const taskDate = new Date(date.getFullYear(), date.getMonth(), date.getDate())

    const timeStr = date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })

    if (taskDate.getTime() === today.getTime()) {
      return `今天 ${timeStr}`
    } else if (taskDate.getTime() === today.getTime() - 86400000) {
      return `昨天 ${timeStr}`
    } else {
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
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
              {activeTasks.length > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCleanupStale}
                  title="清理僵尸任务（运行超过5分钟的任务）"
                  className="text-orange-600 hover:text-orange-700"
                >
                  <XCircleIcon className="h-4 w-4 sm:mr-2" />
                  <span className="hidden sm:inline">清理僵尸</span>
                </Button>
              )}
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
                  <CheckCircle2Icon className="h-12 w-12 mx-auto mb-4 text-gray-400 dark:text-gray-600" />
                  <p className="text-muted-foreground font-medium">暂无任务记录</p>
                  <p className="text-sm text-muted-foreground mt-2">
                    执行数据同步、AI分析或回测任务后
                  </p>
                  <p className="text-sm text-muted-foreground">
                    任务状态将在这里显示
                  </p>
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
                            <div className="flex items-center gap-2 flex-shrink-0">
                              <Badge
                                variant="outline"
                                className={`${getStatusColor(task.status)} text-white border-0`}
                              >
                                {getStatusText(task.status)}
                              </Badge>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 w-6 p-0 hover:bg-red-100 hover:text-red-600"
                                onClick={() => handleDeleteTask(task.taskId)}
                                title="删除任务"
                              >
                                <XCircleIcon className="h-4 w-4" />
                              </Button>
                            </div>
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
                              <CardDescription className="text-xs mt-1 flex items-center gap-2">
                                <CalendarIcon className="h-3 w-3" />
                                <span>{formatTime(task.endTime || task.startTime)}</span>
                                <span className="text-muted-foreground">·</span>
                                <span>耗时 {formatDuration(task.startTime, task.endTime)}</span>
                              </CardDescription>
                            </div>
                            <div className="flex items-center gap-2 flex-shrink-0">
                              <Badge
                                variant="outline"
                                className={`${getStatusColor(task.status)} text-white border-0`}
                              >
                                {task.status === 'success' ? (
                                  <CheckCircle2Icon className="h-3 w-3 mr-1" />
                                ) : (
                                  <XCircleIcon className="h-3 w-3 mr-1" />
                                )}
                                {getStatusText(task.status)}
                              </Badge>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-6 w-6 p-0 hover:bg-red-100 hover:text-red-600"
                                onClick={() => handleDeleteTask(task.taskId)}
                                title="删除任务"
                              >
                                <Trash2Icon className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>
                        </CardHeader>
                        {task.error && (
                          <CardContent className="py-2 px-4 bg-red-50 dark:bg-red-900/20">
                            <p className="text-xs text-red-800 dark:text-red-200 break-words">{task.error}</p>
                          </CardContent>
                        )}
                        {task.result && task.status === 'success' && (
                          <CardContent className="py-2 px-4 bg-green-50 dark:bg-green-900/20">
                            <p className="text-xs text-green-800 dark:text-green-200">
                              {typeof task.result === 'object'
                                ? JSON.stringify(task.result, null, 2).substring(0, 200)
                                : String(task.result).substring(0, 200)
                              }
                            </p>
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
