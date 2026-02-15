'use client'

import { useEffect, useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'

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
      await apiClient.toggleScheduledTask(taskId)
      await loadTasks()
    } catch (err: any) {
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

  return (
    <ProtectedRoute requireAdmin>
      <div className="space-y-6">
      {/* 页面标题 */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
          ⏰ 定时任务配置
        </h1>
        <p className="text-gray-600 dark:text-gray-300 mt-2">
          配置自动化数据同步任务，支持 Cron 表达式定时执行
        </p>
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

        {loading ? (
          <div className="text-center py-8 text-gray-600 dark:text-gray-400">
            加载中...
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-800">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    任务名称
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    模块
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Cron 表达式
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    上次运行
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    状态
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    启用
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    操作
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {tasks.map((task) => (
                  <tr key={task.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-4 py-3">
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {task.description || task.task_name}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {task.task_name}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                        {getModuleLabel(task.module)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <code className="text-sm text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded">
                        {task.cron_expression}
                      </code>
                    </td>
                    <td className="px-4 py-3">
                      <div className="text-sm text-gray-900 dark:text-white">
                        {task.last_run_at || '未运行'}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        运行 {task.run_count} 次
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      {task.last_status && (
                        <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(task.last_status)}`}>
                          {task.last_status}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleToggle(task.id)}
                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
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
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleEdit(task)}
                        className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
                      >
                        编辑
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Cron 表达式说明 */}
      <div className="card bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
        <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-200 mb-3">
          📖 Cron 表达式说明
        </h3>
        <div className="text-sm text-blue-800 dark:text-blue-300 space-y-2">
          <p>格式: <code className="bg-white dark:bg-gray-800 px-2 py-1 rounded">分 时 日 月 周</code></p>
          <div className="grid grid-cols-2 gap-4 mt-3">
            <div>
              <p className="font-medium mb-1">常用示例:</p>
              <ul className="space-y-1 text-xs">
                <li><code className="bg-white dark:bg-gray-800 px-1.5 py-0.5 rounded">0 1 * * *</code> - 每天凌晨1点</li>
                <li><code className="bg-white dark:bg-gray-800 px-1.5 py-0.5 rounded">0 */2 * * *</code> - 每2小时</li>
                <li><code className="bg-white dark:bg-gray-800 px-1.5 py-0.5 rounded">0 9 * * 1-5</code> - 工作日早上9点</li>
              </ul>
            </div>
            <div>
              <p className="font-medium mb-1">字段说明:</p>
              <ul className="space-y-1 text-xs">
                <li>分钟: 0-59</li>
                <li>小时: 0-23</li>
                <li>日: 1-31</li>
                <li>月: 1-12</li>
                <li>周: 0-6 (0=周日)</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      {/* 编辑模态框 */}
      {showEditModal && editingTask && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-lg w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              编辑定时任务
            </h3>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  任务描述
                </label>
                <input
                  type="text"
                  value={editingTask.description}
                  onChange={(e) => setEditingTask({ ...editingTask, description: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Cron 表达式
                </label>
                <input
                  type="text"
                  value={editingTask.cron_expression}
                  onChange={(e) => setEditingTask({ ...editingTask, cron_expression: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono"
                  placeholder="0 1 * * *"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
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
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white font-mono text-sm"
                />
              </div>
            </div>

            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => {
                  setShowEditModal(false)
                  setEditingTask(null)
                }}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-600"
              >
                取消
              </button>
              <button
                onClick={handleSaveEdit}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
              >
                保存
              </button>
            </div>
          </div>
        </div>
      )}
      </div>
    </ProtectedRoute>
  )
}
