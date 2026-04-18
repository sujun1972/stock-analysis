import { useMemo } from 'react'
import { DataTable, Column } from '@/components/common/DataTable'
import { Play, Loader2 } from 'lucide-react'
import type { ScheduledTask } from './constants'
import { getTaskInfo, getModuleLabel, getStatusColor } from './constants'

interface TaskTableProps {
  data: ScheduledTask[]
  loading: boolean
  executingTasks: Set<number>
  onToggle: (taskId: number) => void
  onEdit: (task: ScheduledTask) => void
  onExecute: (task: ScheduledTask) => void
  mobileCard: (task: ScheduledTask) => React.ReactNode
}

export function TaskTable({
  data,
  loading,
  executingTasks,
  onToggle,
  onEdit,
  onExecute,
  mobileCard,
}: TaskTableProps) {
  const columns: Column<ScheduledTask>[] = useMemo(() => [
    {
      key: 'task_name',
      header: '任务名称',
      accessor: (item: ScheduledTask) => {
        const taskInfo = getTaskInfo(item)
        return (
          <div className="max-w-[280px]">
            <div className="text-sm font-medium text-gray-900 dark:text-white truncate" title={taskInfo.name}>
              {taskInfo.name}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2" title={taskInfo.description}>
              {taskInfo.description}
            </div>
            <div className="mt-1">
              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200">
                {taskInfo.category}
              </span>
            </div>
          </div>
        )
      },
      width: 280
    },
    {
      key: 'module',
      header: '模块',
      accessor: (item: ScheduledTask) => (
        <div className="space-y-1 max-w-[160px]">
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 whitespace-nowrap">
            {getModuleLabel(item.module)}
          </span>
          {item.points_consumption !== null && item.points_consumption !== undefined && item.points_consumption > 0 && (
            <div>
              <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap ${
                item.points_consumption >= 1000
                  ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
                  : 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
              }`}>
                {item.points_consumption} 积分
              </span>
            </div>
          )}
        </div>
      ),
      width: 160
    },
    {
      key: 'cron_expression',
      header: 'Cron 表达式',
      accessor: (item: ScheduledTask) => (
        <code className="text-xs text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded whitespace-nowrap">
          {item.cron_expression}
        </code>
      ),
      width: 140
    },
    {
      key: 'next_run_at',
      header: '执行时间',
      accessor: (item: ScheduledTask) => {
        // 获取本地时区
        const localTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone
        const isBeijingTime = localTimeZone === 'Asia/Shanghai' || localTimeZone === 'Asia/Beijing'

        // 格式化时间为北京时间
        const formatBeijingTime = (dateStr: string) => {
          if (!dateStr) return null
          try {
            const date = new Date(dateStr)
            return date.toLocaleString('zh-CN', {
              timeZone: 'Asia/Shanghai',
              year: 'numeric',
              month: '2-digit',
              day: '2-digit',
              hour: '2-digit',
              minute: '2-digit',
              second: '2-digit',
              hour12: false
            })
          } catch {
            return dateStr
          }
        }

        return (
          <div className="text-xs space-y-1 max-w-[200px]">
            {item.next_run_at ? (
              <>
                <div className="text-blue-700 dark:text-blue-300 truncate" title={`下次执行: ${item.next_run_at}`}>
                  <span className="text-gray-500 dark:text-gray-400">下次: </span>
                  {item.next_run_at}
                </div>
                {!isBeijingTime && (
                  <div className="text-orange-600 dark:text-orange-400 truncate" title="北京时间">
                    <span className="text-gray-500 dark:text-gray-400">北京: </span>
                    {formatBeijingTime(item.next_run_at)}
                  </div>
                )}
              </>
            ) : (
              <div className="text-gray-500 dark:text-gray-400">
                待计算下次执行时间
              </div>
            )}
            {item.last_run_at && (
              <div className="text-gray-600 dark:text-gray-400 truncate" title={`上次执行: ${item.last_run_at}`}>
                <span className="text-gray-500 dark:text-gray-500">上次: </span>
                {item.last_run_at}
              </div>
            )}
            {item.run_count > 0 && (
              <div className="text-gray-500 dark:text-gray-500 text-xs">
                已执行 {item.run_count} 次
              </div>
            )}
          </div>
        )
      },
      width: 200
    },
    {
      key: 'last_status',
      header: '运行状态',
      accessor: (item: ScheduledTask) => item.last_status ? (
        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${getStatusColor(item.last_status)}`}>
          {item.last_status}
        </span>
      ) : null,
      width: 100
    },
    {
      key: 'enabled',
      header: '启用',
      accessor: (item: ScheduledTask) => (
        <button
          onClick={(e) => {
            e.stopPropagation()
            onToggle(item.id)
          }}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            item.enabled
              ? 'bg-blue-600'
              : 'bg-gray-200 dark:bg-gray-700'
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              item.enabled ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      ),
      width: 80
    },
    {
      key: 'id',
      header: '操作',
      accessor: (item: ScheduledTask) => (
        <div className="flex items-center gap-2">
          <button
            onClick={(e) => {
              e.stopPropagation()
              onExecute(item)
            }}
            disabled={executingTasks.has(item.id)}
            className="inline-flex items-center gap-1 text-sm text-green-600 dark:text-green-400 hover:underline whitespace-nowrap disabled:opacity-50 disabled:cursor-not-allowed"
            title="立即执行该任务"
          >
            <span className="inline-flex w-3 h-3 items-center justify-center">
              {executingTasks.has(item.id) ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <Play className="w-3 h-3" />
              )}
            </span>
            执行
          </button>
          <span className="text-gray-400">|</span>
          <button
            onClick={(e) => {
              e.stopPropagation()
              onEdit(item)
            }}
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline whitespace-nowrap"
          >
            编辑
          </button>
        </div>
      ),
      width: 120
    }
  ], [executingTasks, onExecute, onToggle, onEdit])

  return (
    <DataTable
      data={data}
      columns={columns}
      loading={loading}
      mobileCard={mobileCard}
    />
  )
}
