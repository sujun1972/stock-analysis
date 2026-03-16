'use client'

import { useEffect, useState, useMemo, useCallback } from 'react'
import { apiClient } from '@/lib/api-client'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, Column } from '@/components/common/DataTable'

interface ScheduledTask {
  id: number
  task_name: string
  module: string
  description: string
  cron_expression: string
  enabled: boolean
  params: any
  last_run_at: string | null
  next_run_at: string | null
  last_status: string | null
  last_error: string | null
  run_count: number
}

export default function SchedulerSettingsPage() {
  const [tasks, setTasks] = useState<ScheduledTask[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingTask, setEditingTask] = useState<ScheduledTask | null>(null)
  const [showEditModal, setShowEditModal] = useState(false)

  useEffect(() => {
    loadTasks()
  }, [])

  const loadTasks = async () => {
    try {
      setLoading(true)
      const response = await apiClient.getScheduledTasks()
      if (response.data) {
        setTasks(response.data)
      }
    } catch (err: any) {
      setError(err.message || '加载定时任务失败')
    } finally {
      setLoading(false)
    }
  }

  const handleToggle = async (taskId: number) => {
    try {
      // 乐观更新UI，立即切换状态
      setTasks(prevTasks =>
        prevTasks.map(task =>
          task.id === taskId
            ? { ...task, enabled: !task.enabled }
            : task
        )
      )

      // 调用API更新后端
      await apiClient.toggleScheduledTask(taskId)

      // 静默刷新，只更新数据不影响UI状态
      const response = await apiClient.getScheduledTasks()
      if (response.data) {
        setTasks(response.data)
      }
    } catch (err: any) {
      // 如果失败，回滚状态
      await loadTasks()
      setError(err.message || '切换任务状态失败')
    }
  }

  const handleEdit = (task: ScheduledTask) => {
    setEditingTask(task)
    setShowEditModal(true)
  }

  const handleSaveEdit = async () => {
    if (!editingTask) return

    try {
      await apiClient.updateScheduledTask(editingTask.id, {
        description: editingTask.description,
        cron_expression: editingTask.cron_expression,
        params: editingTask.params
      })
      setShowEditModal(false)
      setEditingTask(null)
      await loadTasks()
    } catch (err: any) {
      setError(err.message || '更新任务失败')
    }
  }

  const getModuleLabel = (module: string) => {
    const labels: Record<string, string> = {
      'stock_list': '股票列表',
      'new_stocks': '新股列表',
      'delisted_stocks': '退市列表',
      'daily': '日线数据',
      'minute': '分时数据',
      'realtime': '实时行情'
    }
    return labels[module] || module
  }

  const getStatusColor = (status: string | null) => {
    if (!status) return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
    switch (status) {
      case 'success': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
      case 'failed': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
      default: return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
    }
  }

  // 定义表格列配置
  const columns: Column<ScheduledTask>[] = useMemo(() => [
    {
      key: 'task_name',
      header: '任务名称',
      render: (value: string, item: ScheduledTask) => (
        <div>
          <div className="text-sm font-medium text-gray-900 dark:text-white truncate" title={item.description || value}>
            {item.description || value}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 truncate" title={value}>
            {value}
          </div>
        </div>
      ),
      width: 200
    },
    {
      key: 'module',
      header: '模块',
      render: (value: string) => (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 whitespace-nowrap">
          {getModuleLabel(value)}
        </span>
      )
    },
    {
      key: 'cron_expression',
      header: 'Cron 表达式',
      render: (value: string) => (
        <code className="text-xs text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded whitespace-nowrap">
          {value}
        </code>
      )
    },
    {
      key: 'next_run_at',
      header: '执行时间',
      render: (value: string | null, item: ScheduledTask) => (
        <div className="text-xs space-y-1">
          {item.last_run_at && (
            <div className="text-gray-700 dark:text-gray-300 truncate" title={`上次: ${item.last_run_at}`}>
              <span className="text-gray-500 dark:text-gray-400">上次: </span>
              {item.last_run_at}
            </div>
          )}
          {value && (
            <div className="text-blue-700 dark:text-blue-300 truncate" title={`下次: ${value}`}>
              <span className="text-gray-500 dark:text-gray-400">下次: </span>
              {value}
            </div>
          )}
          <div className="text-gray-500 dark:text-gray-400">
            已运行 {item.run_count} 次
          </div>
        </div>
      ),
      width: 250
    },
    {
      key: 'last_status',
      header: '运行状态',
      render: (value: string | null) => value ? (
        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${getStatusColor(value)}`}>
          {value}
        </span>
      ) : null
    },
    {
      key: 'enabled',
      header: '启用',
      render: (value: boolean, item: ScheduledTask) => (
        <button
          onClick={(e) => {
            e.stopPropagation()
            handleToggle(item.id)
          }}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            value
              ? 'bg-blue-600'
              : 'bg-gray-200 dark:bg-gray-700'
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              value ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      )
    },
    {
      key: 'id',
      header: '操作',
      render: (_value: number, item: ScheduledTask) => (
        <button
          onClick={(e) => {
            e.stopPropagation()
            handleEdit(item)
          }}
          className="text-sm text-blue-600 dark:text-blue-400 hover:underline whitespace-nowrap"
        >
          编辑
        </button>
      )
    }
  ], [])

  // 移动端卡片渲染
  const mobileCard = useCallback((task: ScheduledTask) => (
    <div className="space-y-3">
      {/* 任务名称和开关 */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="text-sm font-medium text-gray-900 dark:text-white">
            {task.description || task.task_name}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {task.task_name}
          </div>
        </div>
        <button
          onClick={(e) => {
            e.stopPropagation()
            handleToggle(task.id)
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

      {/* 模块和状态 */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
          {getModuleLabel(task.module)}
        </span>
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
      <div className="pt-2 border-t border-gray-200 dark:border-gray-700">
        <button
          onClick={(e) => {
            e.stopPropagation()
            handleEdit(task)
          }}
          className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
        >
          编辑任务
        </button>
      </div>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <PageHeader
        title="定时任务配置"
        description="配置自动化数据同步任务，支持 Cron 表达式定时执行"
      />

      {/* 动态配置说明 */}
      <div className="rounded-lg bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 p-5">
        <div className="flex items-start gap-4">
          <div className="text-green-600 dark:text-green-400 text-3xl flex-shrink-0">🚀</div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-green-900 dark:text-green-200 mb-3">
              动态配置说明
            </h3>
            <div className="text-sm text-green-800 dark:text-green-300 space-y-2">
              <p>• 定时任务配置支持<strong>实时生效</strong>，修改后约30秒内自动同步，无需重启服务</p>
              <p>• 启用/禁用任务、修改Cron表达式或参数后，系统会自动加载新配置</p>
              <p>• 时间使用UTC标准时区，北京时间需减8小时（例：北京9点 = UTC 1点）</p>
            </div>
          </div>
        </div>
      </div>

      {/* 错误提示 */}
      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-800 dark:text-red-200">{error}</p>
        </div>
      )}

      {/* 任务列表 */}
      <div className="card">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          定时任务列表
        </h2>

        <DataTable
          data={tasks}
          columns={columns}
          loading={loading}
          mobileCard={mobileCard}
          showPagination={false}
        />
      </div>

      {/* Cron 表达式说明 */}
      <div className="rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-5">
        <div className="flex items-start gap-3 mb-4">
          <div className="text-blue-600 dark:text-blue-400 text-2xl flex-shrink-0">📖</div>
          <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-200">
            Cron 表达式说明
          </h3>
        </div>
        <div className="text-sm text-blue-800 dark:text-blue-300 space-y-3">
          <p>格式: <code className="bg-white dark:bg-gray-800 px-2 py-1 rounded">分 时 日 月 周</code></p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
            <div className="bg-white/50 dark:bg-gray-800/50 rounded-lg p-4">
              <p className="font-semibold mb-2 text-blue-900 dark:text-blue-200">常用示例:</p>
              <ul className="space-y-2 text-xs">
                <li><code className="bg-white dark:bg-gray-800 px-1.5 py-0.5 rounded">0 1 * * *</code> - 每天凌晨1点</li>
                <li><code className="bg-white dark:bg-gray-800 px-1.5 py-0.5 rounded">0 */2 * * *</code> - 每2小时</li>
                <li><code className="bg-white dark:bg-gray-800 px-1.5 py-0.5 rounded">0 9 * * 1-5</code> - 工作日早上9点</li>
              </ul>
            </div>
            <div className="bg-white/50 dark:bg-gray-800/50 rounded-lg p-4">
              <p className="font-semibold mb-2 text-blue-900 dark:text-blue-200">字段说明:</p>
              <ul className="space-y-1.5 text-xs">
                <li><span className="font-medium">分钟:</span> 0-59</li>
                <li><span className="font-medium">小时:</span> 0-23</li>
                <li><span className="font-medium">日:</span> 1-31</li>
                <li><span className="font-medium">月:</span> 1-12</li>
                <li><span className="font-medium">周:</span> 0-6 (0=周日)</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* 编辑模态框 */}
      <Dialog open={showEditModal} onOpenChange={(open) => {
        setShowEditModal(open)
        if (!open) setEditingTask(null)
      }}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>编辑定时任务</DialogTitle>
          </DialogHeader>

          {editingTask && (
            <div className="space-y-4 py-4">
              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                  任务描述
                </label>
                <input
                  type="text"
                  value={editingTask.description}
                  onChange={(e) => setEditingTask({ ...editingTask, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                  Cron 表达式
                </label>
                <input
                  type="text"
                  value={editingTask.cron_expression}
                  onChange={(e) => setEditingTask({ ...editingTask, cron_expression: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="0 1 * * *"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                  任务参数 (JSON)
                </label>
                <textarea
                  value={JSON.stringify(editingTask.params, null, 2)}
                  onChange={(e) => {
                    try {
                      const params = JSON.parse(e.target.value)
                      setEditingTask({ ...editingTask, params })
                    } catch (err) {
                      // 忽略 JSON 解析错误
                    }
                  }}
                  rows={4}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setShowEditModal(false)
                setEditingTask(null)
              }}
            >
              取消
            </Button>
            <Button
              onClick={handleSaveEdit}
              className="bg-blue-600 hover:bg-blue-700"
            >
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}