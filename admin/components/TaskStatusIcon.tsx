/**
 * 任务状态图标组件
 *
 * 显示活动任务数量的徽章图标，点击打开任务面板
 */

'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ListTodoIcon, Loader2Icon } from 'lucide-react'
import { useTaskStore } from '@/stores/task-store'
import { TaskPanel } from '@/components/TaskPanel'

export function TaskStatusIcon() {
  const [isPanelOpen, setIsPanelOpen] = useState(false)
  const activeTaskCount = useTaskStore((state) => state.getActiveTaskCount())

  return (
    <>
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setIsPanelOpen(true)}
        className="relative"
        title="查看活动任务"
      >
        {activeTaskCount > 0 ? (
          <Loader2Icon className="h-5 w-5 animate-spin text-blue-600" />
        ) : (
          <ListTodoIcon className="h-5 w-5" />
        )}
        {activeTaskCount > 0 && (
          <Badge
            variant="destructive"
            className="absolute -top-1 -right-1 h-5 w-5 flex items-center justify-center p-0 text-xs"
          >
            {activeTaskCount}
          </Badge>
        )}
      </Button>

      {/* 任务面板 */}
      <TaskPanel open={isPanelOpen} onOpenChange={setIsPanelOpen} />
    </>
  )
}
