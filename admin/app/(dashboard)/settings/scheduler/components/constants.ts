export interface ScheduledTask {
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

// 所有合法任务分类，筛选下拉和编辑弹窗共用同一份列表
export const TASK_CATEGORIES = [
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
export const FILTER_CATEGORIES = ['全部', ...TASK_CATEGORIES]

/**
 * 获取任务的显示信息
 * 优先使用后端返回的元数据（display_name, description, category）
 * 如果后端没有提供，则使用默认值
 */
export const getTaskInfo = (task: ScheduledTask) => {
  return {
    name: task.display_name || task.task_name,
    description: task.description || '',
    category: task.category || '其他'
  }
}

export const getModuleLabel = (module: string) => {
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

export const getStatusColor = (status: string | null) => {
  if (!status) return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
  switch (status) {
    case 'success': return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
    case 'failed': return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
    default: return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200'
  }
}
