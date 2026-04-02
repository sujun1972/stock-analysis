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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useTaskStore } from '@/stores/task-store'
import { toast } from 'sonner'
import { Play, Loader2 } from 'lucide-react'

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
  display_name?: string
  category?: string
  display_order?: number
  points_consumption?: number
}

/**
 * 获取任务的显示信息
 * 优先使用后端返回的元数据（display_name, description, category）
 * 如果后端没有提供，则使用默认值
 */
const getTaskInfo = (task: ScheduledTask) => {
  return {
    name: task.display_name || task.task_name,
    description: task.description || '',
    category: task.category || '其他'
  }
}

// 所有合法任务分类，筛选下拉和编辑弹窗共用同一份列表
const TASK_CATEGORIES = [
  '基础数据',
  '行情数据',
  '财务数据',
  '参考数据',
  '特色数据',
  '两融及转融通',
  '资金流向',
  '打板专题',
  '市场情绪',
  '盘前分析',
  '质量监控',
  '报告通知',
  '系统维护',
  '其他',
]

// 筛选下拉选项（在分类列表前插入"全部"）
const FILTER_CATEGORIES = ['全部', ...TASK_CATEGORIES]

export default function SchedulerSettingsPage() {
  const [tasks, setTasks] = useState<ScheduledTask[]>([])
  const [loading, setLoading] = useState(true)
  const [editingTask, setEditingTask] = useState<ScheduledTask | null>(null)
  const [showEditModal, setShowEditModal] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState<string>('全部')

  const loadTasks = useCallback(async () => {
    try {
      setLoading(true)
      const response = await apiClient.getScheduledTasks()
      if (response.data) {
        setTasks(response.data)
      }
    } catch (err: any) {
      toast.error('加载失败', {
        description: err.message || '加载定时任务失败'
      })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadTasks()
  }, [loadTasks])

  const handleToggle = useCallback(async (taskId: number) => {
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
      // 如果失败，回滚状态并显示错误
      await loadTasks()
      toast.error('操作失败', {
        description: err.message || '切换任务状态失败'
      })
    }
  }, [loadTasks])

  const handleEdit = (task: ScheduledTask) => {
    setEditingTask(task)
    setShowEditModal(true)
  }

  const [executingTasks, setExecutingTasks] = useState<Set<number>>(new Set())
  const { addTask, triggerPoll } = useTaskStore()

  const handleExecute = useCallback(async (task: ScheduledTask) => {
    const taskInfo = getTaskInfo(task)

    try {
      setExecutingTasks(prev => new Set(prev).add(task.id))

      const response = await apiClient.executeScheduledTask(task.id)

      // 兼容 success/code 两种响应格式
      const isSuccess = response.success || response.code === 200
      const responseData = response.data

      if (isSuccess && responseData) {
        addTask({
          taskId: responseData.celery_task_id,
          taskName: responseData.task_name,
          displayName: taskInfo.name,
          taskType: 'scheduler',
          status: 'running',
          progress: 0,
          startTime: Date.now()
        })
        triggerPoll()
        toast.success('任务已提交', {
          description: `"${taskInfo.name}" 已开始执行，可在任务面板查看进度`
        })
        // 静默刷新任务列表（延迟1s等待后端写入）
        setTimeout(async () => {
          const refreshed = await apiClient.getScheduledTasks().catch(() => null)
          if (refreshed?.data) setTasks(refreshed.data)
        }, 1000)
      } else {
        throw new Error(response.message || '执行失败')
      }
    } catch (err: any) {
      toast.error('执行失败', {
        description: err.message || '未知错误'
      })
    } finally {
      setExecutingTasks(prev => {
        const next = new Set(prev)
        next.delete(task.id)
        return next
      })
    }
  }, [addTask, triggerPoll])

  const handleSaveEdit = async () => {
    if (!editingTask) return

    try {
      await apiClient.updateScheduledTask(editingTask.id, {
        display_name: editingTask.display_name,
        description: editingTask.description,
        category: editingTask.category,
        display_order: editingTask.display_order,
        points_consumption: editingTask.points_consumption,
        cron_expression: editingTask.cron_expression,
        params: editingTask.params
      })
      setShowEditModal(false)
      setEditingTask(null)

      toast.success('更新成功', {
        description: '定时任务配置已更新'
      })

      await loadTasks()
    } catch (err: any) {
      toast.error('更新失败', {
        description: err.message || '更新任务失败'
      })
    }
  }

  const getModuleLabel = (module: string) => {
    const labels: Record<string, string> = {
      'stock_list': '股票列表',
      'new_stocks': '新股列表',
      'delisted_stocks': '退市列表',
      'daily': '日线数据',
      'minute': '分时数据',
      'realtime': '实时行情',
      // 新增扩展数据任务
      'extended.sync_daily_basic': '每日指标',
      'extended.sync_moneyflow': '资金流向',
      'tasks.sync_moneyflow': '个股资金流向（Tushare）',
      'tasks.sync_moneyflow_hsgt': '沪深港通资金',
      'moneyflow_hsgt': '沪深港通资金',
      'tasks.sync_moneyflow_mkt_dc': '大盘资金流向',
      'moneyflow_mkt_dc': '大盘资金流向',
      'tasks.sync_moneyflow_ind_dc': '板块资金流向（DC）',
      'tasks.sync_moneyflow_stock_dc': '个股资金流向（DC）',
      'extended.sync_margin': '融资融券',
      'extended.sync_stk_limit': '涨跌停价格',
      'extended.sync_block_trade': '大宗交易',
      'extended.sync_adj_factor': '复权因子',
      'extended.sync_suspend': '停复牌信息'
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

  // 各分类任务计数，避免下拉渲染时重复 filter
  const categoryCounts = useMemo(() => {
    const map: Record<string, number> = { '全部': tasks.length }
    for (const t of tasks) {
      const cat = t.category || '其他'
      map[cat] = (map[cat] ?? 0) + 1
    }
    return map
  }, [tasks])

  // 按分类过滤后的任务列表
  const filteredTasks = useMemo(() => {
    if (selectedCategory === '全部') return tasks
    return tasks.filter(t => (t.category || '其他') === selectedCategory)
  }, [tasks, selectedCategory])

  // 定义表格列配置
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
            handleToggle(item.id)
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
              handleExecute(item)
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
              handleEdit(item)
            }}
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline whitespace-nowrap"
          >
            编辑
          </button>
        </div>
      ),
      width: 120
    }
  ], [executingTasks, handleExecute, handleToggle])

  // 移动端卡片渲染
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
              handleExecute(task)
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
              handleEdit(task)
            }}
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            编辑任务
          </button>
        </div>
      </div>
    )
  }, [executingTasks, handleExecute, handleToggle])

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
        <div className="flex items-center justify-between mb-4 gap-4 flex-wrap">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            定时任务列表
          </h2>
          <Select value={selectedCategory} onValueChange={setSelectedCategory}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="选择分类" />
            </SelectTrigger>
            <SelectContent>
              {FILTER_CATEGORIES.map(cat => (
                <SelectItem key={cat} value={cat}>
                  {`${cat}（${categoryCounts[cat] ?? 0}）`}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <DataTable
          data={filteredTasks}
          columns={columns}
          loading={loading}
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
      <Dialog open={showEditModal} onOpenChange={(open) => {
        setShowEditModal(open)
        if (!open) setEditingTask(null)
      }}>
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
                  onChange={(e) => setEditingTask({ ...editingTask, display_name: e.target.value })}
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
                  onChange={(e) => setEditingTask({ ...editingTask, description: e.target.value })}
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
                    onValueChange={(value) => setEditingTask({ ...editingTask, category: value })}
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
                    onChange={(e) => setEditingTask({ ...editingTask, display_order: parseInt(e.target.value) || 9999 })}
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
                    onChange={(e) => setEditingTask({
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
                  onChange={(e) => setEditingTask({ ...editingTask, cron_expression: e.target.value })}
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