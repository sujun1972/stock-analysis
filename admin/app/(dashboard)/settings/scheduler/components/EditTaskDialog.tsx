import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { ScheduledTask } from './constants'
import { TASK_CATEGORIES } from './constants'

interface EditTaskDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  editingTask: ScheduledTask | null
  onEditingTaskChange: (task: ScheduledTask) => void
  onSave: () => void
}

export function EditTaskDialog({
  open,
  onOpenChange,
  editingTask,
  onEditingTaskChange,
  onSave,
}: EditTaskDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>编辑定时任务</DialogTitle>
        </DialogHeader>

        {editingTask && (
          <div className="space-y-4 py-4">
            {/* 任务显示名称 */}
            <div>
              <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                任务显示名称
              </label>
              <input
                type="text"
                value={editingTask.display_name || ''}
                onChange={(e) => onEditingTaskChange({ ...editingTask, display_name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="例：每日股票列表"
              />
            </div>

            {/* 任务描述 */}
            <div>
              <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                任务描述
              </label>
              <textarea
                value={editingTask.description}
                onChange={(e) => onEditingTaskChange({ ...editingTask, description: e.target.value })}
                rows={2}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="任务的详细描述"
              />
            </div>

            {/* 分类、排序和积分 - 使用网格布局 */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {/* 任务分类 */}
              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                  任务分类
                </label>
                <Select
                  value={editingTask.category || '其他'}
                  onValueChange={(value) => onEditingTaskChange({ ...editingTask, category: value })}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择任务分类" />
                  </SelectTrigger>
                  <SelectContent>
                    {TASK_CATEGORIES.map(cat => (
                      <SelectItem key={cat} value={cat}>{cat}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* 显示顺序 */}
              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                  显示顺序
                </label>
                <input
                  type="number"
                  value={editingTask.display_order || 9999}
                  onChange={(e) => onEditingTaskChange({ ...editingTask, display_order: parseInt(e.target.value) || 9999 })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="100"
                  min="0"
                />
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  数字越小越靠前
                </p>
              </div>

              {/* 积分消耗 */}
              <div>
                <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                  积分消耗
                </label>
                <input
                  type="number"
                  // 处理 null/undefined 的显示：空字符串表示未设置
                  value={editingTask.points_consumption !== null && editingTask.points_consumption !== undefined ? editingTask.points_consumption : ''}
                  onChange={(e) => onEditingTaskChange({
                    ...editingTask,
                    // 空字符串转为 undefined，允许清空积分值
                    points_consumption: e.target.value === '' ? undefined : parseInt(e.target.value)
                  })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="留空表示不消耗"
                  min="0"
                />
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Tushare 接口调用消耗的积分数（可为空）
                </p>
              </div>
            </div>

            {/* Cron表达式 */}
            <div>
              <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                Cron 表达式
              </label>
              <input
                type="text"
                value={editingTask.cron_expression}
                onChange={(e) => onEditingTaskChange({ ...editingTask, cron_expression: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white font-mono focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="0 1 * * *"
              />
            </div>

            {/* 任务参数 */}
            <div>
              <label className="block text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">
                任务参数 (JSON)
              </label>
              <textarea
                value={JSON.stringify(editingTask.params, null, 2)}
                onChange={(e) => {
                  try {
                    const params = JSON.parse(e.target.value)
                    onEditingTaskChange({ ...editingTask, params })
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
            onClick={() => onOpenChange(false)}
          >
            取消
          </Button>
          <Button
            onClick={onSave}
            className="bg-blue-600 hover:bg-blue-700"
          >
            保存
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
