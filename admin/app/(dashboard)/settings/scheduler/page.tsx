'use client'

import { PageHeader } from '@/components/common/PageHeader'
import { useSchedulerData, useSchedulerActions } from './hooks'
import {
  TaskFilters,
  TaskTable,
  EditTaskDialog,
  useTaskMobileCard,
} from './components'

export default function SchedulerSettingsPage() {
  const {
    tasks,
    setTasks,
    loading,
    loadTasks,
    selectedCategory,
    setSelectedCategory,
    categoryCounts,
    filteredTasks,
  } = useSchedulerData()

  const {
    editingTask,
    setEditingTask,
    showEditModal,
    executingTasks,
    handleToggle,
    handleEdit,
    handleExecute,
    handleSaveEdit,
    handleCloseEditModal,
  } = useSchedulerActions({ tasks, setTasks, loadTasks })

  const mobileCard = useTaskMobileCard({
    executingTasks,
    onToggle: handleToggle,
    onEdit: handleEdit,
    onExecute: handleExecute,
  })

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

      {/* 任务列表 */}
      <div className="card">
        <TaskFilters
          selectedCategory={selectedCategory}
          onCategoryChange={setSelectedCategory}
          categoryCounts={categoryCounts}
        />

        <TaskTable
          data={filteredTasks}
          loading={loading}
          executingTasks={executingTasks}
          onToggle={handleToggle}
          onEdit={handleEdit}
          onExecute={handleExecute}
          mobileCard={mobileCard}
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
      <EditTaskDialog
        open={showEditModal}
        onOpenChange={handleCloseEditModal}
        editingTask={editingTask}
        onEditingTaskChange={setEditingTask}
        onSave={handleSaveEdit}
      />
    </div>
  )
}
