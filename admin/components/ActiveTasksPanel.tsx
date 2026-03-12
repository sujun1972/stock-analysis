'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle, SheetTrigger } from '@/components/ui/sheet'
import { ScrollArea } from '@/components/ui/scroll-area'
import { RefreshCwIcon, ListIcon, CheckCircle2Icon, XCircleIcon, ClockIcon } from 'lucide-react'
import { apiClient } from '@/lib/api-client'

interface ActiveTask {
  task_id: string
  task_name: string
  display_name: string
  status: 'pending' | 'running'
  worker?: string
}

/**
 * 活动任务面板组件
 *
 * 显示所有正在执行的异步任务，可通过右下角浮动按钮打开
 */
export function ActiveTasksPanel() {
  const [tasks, setTasks] = useState<ActiveTask[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isOpen, setIsOpen] = useState(false)

  // 加载活动任务
  const loadActiveTasks = async () => {
    setIsLoading(true)
    try {
      const response = await apiClient.get('/api/sentiment/tasks/active')

      if (response.code === 200 && response.data?.tasks) {
        setTasks(response.data.tasks)
      } else {
        setTasks([])
      }
    } catch (error) {
      console.error('加载活动任务失败:', error)
      setTasks([])
    } finally {
      setIsLoading(false)
    }
  }

  // 打开面板时加载任务
  useEffect(() => {
    if (isOpen) {
      loadActiveTasks()

      // 每5秒自动刷新
      const interval = setInterval(loadActiveTasks, 5000)
      return () => clearInterval(interval)
    }
  }, [isOpen])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'bg-blue-500'
      case 'pending':
        return 'bg-yellow-500'
      default:
        return 'bg-gray-500'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'running':
        return '执行中'
      case 'pending':
        return '等待中'
      default:
        return '未知'
    }
  }

  return (
    <Sheet open={isOpen} onOpenChange={setIsOpen}>
      <SheetTrigger asChild>
        <Button
          variant="outline"
          size="icon"
          className="fixed bottom-6 right-6 h-14 w-14 rounded-full shadow-lg z-50 hover:scale-110 transition-transform"
          title="查看活动任务"
        >
          <div className="relative">
            <ListIcon className="h-6 w-6" />
            {tasks.length > 0 && (
              <Badge
                variant="destructive"
                className="absolute -top-2 -right-2 h-5 w-5 flex items-center justify-center p-0 text-xs"
              >
                {tasks.length}
              </Badge>
            )}
          </div>
        </Button>
      </SheetTrigger>

      <SheetContent className="w-[400px] sm:w-[540px]">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <RefreshCwIcon className={`h-5 w-5 ${isLoading ? 'animate-spin' : ''}`} />
            活动任务
          </SheetTitle>
          <SheetDescription>
            当前正在执行的异步任务列表
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-4">
          {/* 刷新按钮 */}
          <div className="flex justify-between items-center">
            <div className="text-sm text-muted-foreground">
              共 {tasks.length} 个任务
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={loadActiveTasks}
              disabled={isLoading}
            >
              <RefreshCwIcon className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
              刷新
            </Button>
          </div>

          {/* 任务列表 */}
          <ScrollArea className="h-[calc(100vh-200px)]">
            {tasks.length === 0 ? (
              <Card className="border-dashed">
                <CardContent className="py-12 text-center">
                  <CheckCircle2Icon className="h-12 w-12 mx-auto mb-4 text-green-500" />
                  <p className="text-muted-foreground">暂无活动任务</p>
                  <p className="text-sm text-muted-foreground mt-1">
                    所有任务已完成
                  </p>
                </CardContent>
              </Card>
            ) : (
              <div className="space-y-3">
                {tasks.map((task) => (
                  <Card key={task.task_id} className="overflow-hidden">
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <CardTitle className="text-base">
                            {task.display_name}
                          </CardTitle>
                          <CardDescription className="text-xs mt-1 font-mono">
                            ID: {task.task_id}
                          </CardDescription>
                        </div>
                        <Badge
                          variant="outline"
                          className={`${getStatusColor(task.status)} text-white border-0`}
                        >
                          {getStatusText(task.status)}
                        </Badge>
                      </div>
                    </CardHeader>
                    <CardContent className="py-2 px-4 bg-muted/50">
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        {task.status === 'running' ? (
                          <>
                            <RefreshCwIcon className="h-3 w-3 animate-spin" />
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
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </ScrollArea>
        </div>
      </SheetContent>
    </Sheet>
  )
}
