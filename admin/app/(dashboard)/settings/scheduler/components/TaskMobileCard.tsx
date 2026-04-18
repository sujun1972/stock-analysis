import { useCallback } from 'react'
import { Play, Loader2 } from 'lucide-react'
import type { ScheduledTask } from './constants'
import { getTaskInfo, getModuleLabel, getStatusColor } from './constants'

interface TaskMobileCardProps {
  executingTasks: Set<number>
  onToggle: (taskId: number) => void
  onEdit: (task: ScheduledTask) => void
  onExecute: (task: ScheduledTask) => void
}

export function useTaskMobileCard({
  executingTasks,
  onToggle,
  onEdit,
  onExecute,
}: TaskMobileCardProps) {
  const mobileCard = useCallback((task: ScheduledTask) => {
    const taskInfo = getTaskInfo(task)
    return (
      <div className="space-y-3">
        {/* 任务名称和开关 */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-gray-900 dark:text-white">
              {taskInfo.name}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              {taskInfo.description}
            </div>
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation()
              onToggle(task.id)
            }}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors flex-shrink-0 ${
              task.enabled
                ? 'bg-blue-600'
                : 'bg-gray-200 dark:bg-gray-700'
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                task.enabled ? 'translate-x-6' : 'translate-x-1'
              }`}
            />
          </button>
        </div>

        {/* 分类和模块 */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
            {taskInfo.category}
          </span>
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
            {getModuleLabel(task.module)}
          </span>
          {task.points_consumption !== null && task.points_consumption !== undefined && task.points_consumption > 0 && (
            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
              task.points_consumption >= 1000
                ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
            }`}>
              {task.points_consumption} 积分
            </span>
          )}
          {task.last_status && (
            <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${getStatusColor(task.last_status)}`}>
              {task.last_status}
            </span>
          )}
        </div>

        {/* Cron表达式 */}
        <div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">Cron 表达式</div>
          <code className="text-xs text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
            {task.cron_expression}
          </code>
        </div>

        {/* 执行时间 */}
        <div className="text-xs space-y-1">
          {task.last_run_at && (
            <div className="text-gray-700 dark:text-gray-300">
              <span className="text-gray-500 dark:text-gray-400">上次: </span>
              {task.last_run_at}
            </div>
          )}
          {task.next_run_at && (
            <div className="text-blue-700 dark:text-blue-300">
              <span className="text-gray-500 dark:text-gray-400">下次: </span>
              {task.next_run_at}
            </div>
          )}
          <div className="text-gray-500 dark:text-gray-400">
            已运行 {task.run_count} 次
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="pt-2 border-t border-gray-200 dark:border-gray-700 flex items-center gap-3">
          <button
            onClick={(e) => {
              e.stopPropagation()
              onExecute(task)
            }}
            disabled={executingTasks.has(task.id)}
            className="inline-flex items-center gap-1 text-sm text-green-600 dark:text-green-400 hover:underline disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span className="inline-flex w-3 h-3 items-center justify-center">
              {executingTasks.has(task.id) ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <Play className="w-3 h-3" />
              )}
            </span>
            立即执行
          </button>
          <span className="text-gray-400">|</span>
          <button
            onClick={(e) => {
              e.stopPropagation()
              onEdit(task)
            }}
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            编辑任务
          </button>
        </div>
      </div>
    )
  }, [executingTasks, onExecute, onToggle, onEdit])

  return mobileCard
}
