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
}

/**
 * 任务名称映射表
 * 将后端的技术性任务名称映射为用户友好的中文名称
 * 包含任务名称、描述和分类信息
 */
const TASK_NAME_MAP: Record<string, { name: string; description: string; category: string }> = {
  // 股票数据同步任务
  'daily_stock_list_sync': {
    name: '每日股票列表',
    description: '每日同步A股所有股票的基础信息',
    category: '基础数据'
  },
  'daily_new_stocks_sync': {
    name: '每日新股同步',
    description: '同步最近上市的新股信息',
    category: '基础数据'
  },
  'weekly_delisted_stocks_sync': {
    name: '每周退市同步',
    description: '同步退市股票列表',
    category: '基础数据'
  },
  'daily_data_sync': {
    name: '每日行情同步',
    description: '同步股票日K线数据',
    category: '行情数据'
  },

  // 行情数据同步
  'sync_daily_batch': {
    name: '日线数据批量同步',
    description: '批量同步股票的日K线数据',
    category: '行情数据'
  },
  'sync_minute_data': {
    name: '分钟数据同步',
    description: '同步股票的分钟级K线数据',
    category: '行情数据'
  },
  'sync_realtime_quotes': {
    name: '实时行情同步',
    description: '同步股票的实时报价数据',
    category: '行情数据'
  },

  // 扩展数据同步
  'sync_daily_basic': {
    name: '每日指标同步',
    description: '同步市盈率、市净率等每日指标数据',
    category: '扩展数据'
  },
  'sync_moneyflow': {
    name: '资金流向同步',
    description: '同步个股资金流向数据（高积分消耗）',
    category: '扩展数据'
  },
  'sync_moneyflow_hsgt': {
    name: '沪深港通资金流向',
    description: '同步沪深港通资金流向数据（北向+南向）',
    category: '扩展数据'
  },
  'sync_moneyflow_mkt_dc': {
    name: '大盘资金流向',
    description: '同步大盘资金流向数据（东方财富DC）',
    category: '扩展数据'
  },
  'sync_margin': {
    name: '融资融券同步',
    description: '同步两融余额和明细数据',
    category: '扩展数据'
  },
  'sync_stk_limit': {
    name: '涨跌停价格同步',
    description: '同步股票涨跌停价格信息',
    category: '扩展数据'
  },
  'sync_block_trade': {
    name: '大宗交易同步',
    description: '同步大宗交易明细数据',
    category: '扩展数据'
  },
  'sync_adj_factor': {
    name: '复权因子同步',
    description: '同步股票复权因子数据',
    category: '扩展数据'
  },
  'sync_suspend': {
    name: '停复牌信息同步',
    description: '同步股票停复牌公告',
    category: '扩展数据'
  },

  // 市场情绪相关
  'daily_sentiment_sync': {
    name: '市场情绪抓取',
    description: '市场情绪数据抓取（17:30）- 包含交易日历、涨停板池、龙虎榜',
    category: '市场情绪'
  },
  'sentiment.ai_analysis_18_00': {
    name: '情绪AI分析',
    description: '市场情绪AI分析（18:00）- 基于17:30数据生成盘后分析报告',
    category: '市场情绪'
  },
  'manual_sentiment_sync': {
    name: '手动情绪同步',
    description: '手动触发情绪数据同步',
    category: '市场情绪'
  },
  'batch_sentiment_sync': {
    name: '批量情绪同步',
    description: '批量同步历史情绪数据',
    category: '市场情绪'
  },
  'sync_trading_calendar': {
    name: '交易日历同步',
    description: '同步股市交易日历',
    category: '市场情绪'
  },
  'daily_sentiment_ai_analysis': {
    name: 'AI情绪分析',
    description: '使用AI分析市场情绪和热点板块',
    category: '市场情绪'
  },

  // 盘前分析
  'premarket_expectation_8_00': {
    name: '盘前预期分析',
    description: '盘前预期管理系统(8:00) - 抓取外盘数据+过滤新闻+AI分析',
    category: '盘前分析'
  },
  'premarket_full_workflow': {
    name: '盘前完整分析',
    description: '执行完整的盘前数据同步和AI分析流程',
    category: '盘前分析'
  },
  'sync_premarket_data': {
    name: '盘前数据同步',
    description: '同步盘前所需的各项数据',
    category: '盘前分析'
  },
  'generate_analysis': {
    name: '生成AI分析',
    description: '生成盘前AI分析报告',
    category: '盘前分析'
  },

  // 数据质量监控
  'generate_daily_quality_report': {
    name: '每日质量报告',
    description: '生成每日数据质量报告',
    category: '质量监控'
  },
  'generate_weekly_quality_report': {
    name: '周度质量报告',
    description: '生成周度数据质量趋势报告',
    category: '质量监控'
  },
  'real_time_quality_check': {
    name: '实时质量检查',
    description: '实时数据质量检查，发现异常立即告警',
    category: '质量监控'
  },
  'data_integrity_check': {
    name: '数据完整性检查',
    description: '检查数据完整性，修复缺失数据',
    category: '质量监控'
  },
  'quality_trend_analysis': {
    name: '质量趋势分析',
    description: '分析数据质量趋势，预测潜在问题',
    category: '质量监控'
  },
  'cleanup_old_alerts': {
    name: '清理过期告警',
    description: '清理过期的质量告警记录',
    category: '质量监控'
  },

  // 报告和通知
  'generate_daily_report': {
    name: '每日市场报告',
    description: '生成每日市场分析报告',
    category: '报告通知'
  },
  'send_email_notification': {
    name: '邮件通知',
    description: '发送邮件通知',
    category: '报告通知'
  },
  'send_telegram_notification': {
    name: 'Telegram通知',
    description: '发送Telegram消息通知',
    category: '报告通知'
  },
  'schedule_report_notification': {
    name: '定时报告通知',
    description: '定时发送报告通知',
    category: '报告通知'
  },

  // 系统维护
  'cleanup_expired_notifications': {
    name: '清理过期通知',
    description: '清理过期的通知记录',
    category: '系统维护'
  },
  'notification_health_check': {
    name: '通知系统健康检查',
    description: '检查通知系统运行状态',
    category: '系统维护'
  },
  'reset_daily_rate_limits': {
    name: '重置速率限制',
    description: '重置每日API调用速率限制',
    category: '系统维护'
  },
  'database_cleanup': {
    name: '数据库清理',
    description: '清理过期数据和优化表',
    category: '系统维护'
  },
  'backup_database': {
    name: '数据库备份',
    description: '执行数据库备份任务',
    category: '系统维护'
  }
}

/**
 * 获取任务的友好名称和描述
 * @param taskName - 原始任务名称
 * @param backendDescription - 后端返回的描述信息
 * @returns 包含友好名称、描述和分类的对象
 */
const getTaskInfo = (taskName: string, backendDescription?: string) => {
  // 优先使用映射表中的信息
  const mappedInfo = TASK_NAME_MAP[taskName]

  if (mappedInfo) {
    return mappedInfo
  }

  // 如果映射表中没有，使用后端提供的描述
  if (backendDescription) {
    // 尝试从后端描述中提取更友好的名称（截取括号或破折号前的内容）
    const name = backendDescription.split('（')[0].split('-')[0].trim() || taskName

    // 根据任务名称关键词推断分类
    let category = '其他'
    if (taskName.includes('sync') || taskName.includes('data')) {
      category = '数据同步'
    } else if (taskName.includes('quality') || taskName.includes('check')) {
      category = '质量监控'
    } else if (taskName.includes('report')) {
      category = '报告通知'
    } else if (taskName.includes('sentiment')) {
      category = '市场情绪'
    } else if (taskName.includes('premarket')) {
      category = '盘前分析'
    }

    return {
      name,
      description: backendDescription,
      category
    }
  }

  // 默认返回原始任务名称
  return {
    name: taskName,
    description: '',
    category: '其他'
  }
}

export default function SchedulerSettingsPage() {
  const [tasks, setTasks] = useState<ScheduledTask[]>([])
  const [loading, setLoading] = useState(true)
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
      toast.error('加载失败', {
        description: err.message || '加载定时任务失败'
      })
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
      // 如果失败，回滚状态并显示错误
      await loadTasks()
      toast.error('操作失败', {
        description: err.message || '切换任务状态失败'
      })
    }
  }

  const handleEdit = (task: ScheduledTask) => {
    setEditingTask(task)
    setShowEditModal(true)
  }

  const [executingTasks, setExecutingTasks] = useState<Set<number>>(new Set())
  const { addTask, triggerPoll } = useTaskStore()

  const handleExecute = async (task: ScheduledTask) => {
    const taskInfo = getTaskInfo(task.task_name, task.description)

    try {
      // 添加到执行中列表（按钮变为 disabled 状态）
      setExecutingTasks(prev => new Set(prev).add(task.id))

      // 调用执行API
      const response = await apiClient.executeScheduledTask(task.id)

      // 检查响应是否成功（兼容两种响应格式）
      const isSuccess = response.success || response.code === 200
      const responseData = response.data

      if (isSuccess && responseData) {
        // 添加到任务存储
        addTask({
          taskId: responseData.celery_task_id,
          taskName: responseData.task_name,
          displayName: taskInfo.name,
          taskType: 'scheduler',
          status: 'running',
          progress: 0,
          startTime: Date.now()
        })

        // 立即触发一次轮询，让 Header 图标即时更新
        triggerPoll()

        // 显示 toast 通知
        toast.success('任务已提交', {
          description: `"${taskInfo.name}" 已开始执行，可在任务面板查看进度`
        })

        // 静默刷新任务列表（不触发 loading 状态，避免页面跳动）
        setTimeout(async () => {
          try {
            const response = await apiClient.getScheduledTasks()
            if (response.data) {
              setTasks(response.data)
            }
          } catch (err) {
            // 静默失败，不打断用户
            console.error('静默刷新任务列表失败:', err)
          }
        }, 1000)
      } else {
        throw new Error(response.message || '执行失败')
      }
    } catch (err: any) {
      // 显示错误 toast
      toast.error('执行失败', {
        description: err.message || '未知错误'
      })
    } finally {
      // 从执行中列表移除（按钮恢复正常状态）
      setExecutingTasks(prev => {
        const next = new Set(prev)
        next.delete(task.id)
        return next
      })
    }
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
      'tasks.sync_moneyflow_hsgt': '沪深港通资金',
      'moneyflow_hsgt': '沪深港通资金',
      'tasks.sync_moneyflow_mkt_dc': '大盘资金流向',
      'moneyflow_mkt_dc': '大盘资金流向',
      'extended.sync_margin': '融资融券',
      'extended.sync_stk_limit': '涨跌停价格',
      'extended.sync_block_trade': '大宗交易',
      'extended.sync_adj_factor': '复权因子',
      'extended.sync_suspend': '停复牌信息'
    }
    return labels[module] || module
  }

  const getPointsConsumption = (module: string) => {
    const points: Record<string, number> = {
      'extended.sync_daily_basic': 120,
      'extended.sync_moneyflow': 2000,  // 高消耗
      'tasks.sync_moneyflow_hsgt': 2000,  // 高消耗
      'moneyflow_hsgt': 2000,  // 高消耗
      'tasks.sync_moneyflow_mkt_dc': 120,
      'moneyflow_mkt_dc': 120,
      'extended.sync_margin': 300,
      'extended.sync_stk_limit': 120,
      'extended.sync_block_trade': 300,
      'extended.sync_adj_factor': 120,
      'extended.sync_suspend': 120
    }
    return points[module] || 0
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
      accessor: (item: ScheduledTask) => {
        const taskInfo = getTaskInfo(item.task_name, item.description)
        return (
          <div>
            <div className="text-sm font-medium text-gray-900 dark:text-white truncate" title={taskInfo.description}>
              {taskInfo.name}
            </div>
            <div className="text-xs text-gray-500 dark:text-gray-400 truncate" title={taskInfo.description}>
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
      width: 250
    },
    {
      key: 'module',
      header: '模块',
      accessor: (item: ScheduledTask) => (
        <div className="space-y-1">
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200 whitespace-nowrap">
            {getModuleLabel(item.module)}
          </span>
          {getPointsConsumption(item.module) > 0 && (
            <div>
              <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium whitespace-nowrap ${
                getPointsConsumption(item.module) >= 1000
                  ? 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
                  : 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200'
              }`}>
                {getPointsConsumption(item.module) >= 1000 ? '⚠️ ' : ''}
                {getPointsConsumption(item.module)} 积分
              </span>
            </div>
          )}
        </div>
      )
    },
    {
      key: 'cron_expression',
      header: 'Cron 表达式',
      accessor: (item: ScheduledTask) => (
        <code className="text-xs text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded whitespace-nowrap">
          {item.cron_expression}
        </code>
      )
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
          <div className="text-xs space-y-1">
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
      width: 250
    },
    {
      key: 'last_status',
      header: '运行状态',
      accessor: (item: ScheduledTask) => item.last_status ? (
        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium whitespace-nowrap ${getStatusColor(item.last_status)}`}>
          {item.last_status}
        </span>
      ) : null
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
      )
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
      )
    }
  ], [executingTasks, handleExecute, handleToggle])

  // 移动端卡片渲染
  const mobileCard = useCallback((task: ScheduledTask) => {
    const taskInfo = getTaskInfo(task.task_name, task.description)
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
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">
          定时任务列表
        </h2>

        <DataTable
          data={tasks}
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