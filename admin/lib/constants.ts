/**
 * @file lib/constants.ts
 * @description 全局常量定义文件，包含颜色映射、状态定义、选项列表等
 * @author Claude
 * @created 2024-03-16
 * @updated 2024-03-16
 */

// ============== 颜色映射 ==============

/**
 * 策略类型颜色映射
 */
export const STRATEGY_TYPE_COLORS = {
  stock_selection: 'bg-blue-100 text-blue-800',
  timing: 'bg-green-100 text-green-800',
  risk_control: 'bg-red-100 text-red-800',
  position_management: 'bg-purple-100 text-purple-800',
  market_analysis: 'bg-yellow-100 text-yellow-800',
  sector_rotation: 'bg-indigo-100 text-indigo-800',
  arbitrage: 'bg-pink-100 text-pink-800',
  high_frequency: 'bg-orange-100 text-orange-800',
  quantitative: 'bg-teal-100 text-teal-800',
  fundamental: 'bg-cyan-100 text-cyan-800',
  technical: 'bg-lime-100 text-lime-800',
  hybrid: 'bg-amber-100 text-amber-800',
  other: 'bg-gray-100 text-gray-800',
} as const

/**
 * 策略来源类型颜色映射
 */
export const SOURCE_TYPE_COLORS = {
  builtin: 'bg-gray-100 text-gray-800',
  user: 'bg-blue-100 text-blue-800',
  community: 'bg-green-100 text-green-800',
  official: 'bg-purple-100 text-purple-800',
  ai_generated: 'bg-yellow-100 text-yellow-800',
  imported: 'bg-orange-100 text-orange-800',
  other: 'bg-gray-100 text-gray-800',
} as const

/**
 * 用户角色颜色映射
 */
export const USER_ROLE_COLORS = {
  super_admin: 'bg-purple-100 text-purple-800',
  admin: 'bg-blue-100 text-blue-800',
  vip_user: 'bg-yellow-100 text-yellow-800',
  normal_user: 'bg-green-100 text-green-800',
  trial_user: 'bg-gray-100 text-gray-800',
} as const

/**
 * 任务状态颜色映射
 */
export const TASK_STATUS_COLORS = {
  pending: 'bg-gray-100 text-gray-800',
  running: 'bg-blue-100 text-blue-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  cancelled: 'bg-yellow-100 text-yellow-800',
} as const

/**
 * 股票状态颜色映射
 */
export const STOCK_STATUS_COLORS = {
  active: 'bg-green-100 text-green-800',
  suspended: 'bg-yellow-100 text-yellow-800',
  delisted: 'bg-red-100 text-red-800',
  pre_ipo: 'bg-blue-100 text-blue-800',
} as const

// ============== 标签映射 ==============

/**
 * 策略类型标签
 */
export const STRATEGY_TYPE_LABELS = {
  stock_selection: '选股策略',
  timing: '择时策略',
  risk_control: '风控策略',
  position_management: '仓位管理',
  market_analysis: '市场分析',
  sector_rotation: '板块轮动',
  arbitrage: '套利策略',
  high_frequency: '高频交易',
  quantitative: '量化策略',
  fundamental: '基本面分析',
  technical: '技术分析',
  hybrid: '混合策略',
  other: '其他',
} as const

/**
 * 策略来源标签
 */
export const SOURCE_TYPE_LABELS = {
  builtin: '内置',
  user: '用户',
  community: '社区',
  official: '官方',
  ai_generated: 'AI生成',
  imported: '导入',
  other: '其他',
} as const

/**
 * 用户角色标签
 */
export const USER_ROLE_LABELS = {
  super_admin: '超级管理员',
  admin: '管理员',
  vip_user: 'VIP用户',
  normal_user: '普通用户',
  trial_user: '试用用户',
} as const

/**
 * 任务状态标签
 */
export const TASK_STATUS_LABELS = {
  pending: '等待中',
  running: '运行中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消',
} as const

/**
 * 股票状态标签
 */
export const STOCK_STATUS_LABELS = {
  active: '正常交易',
  suspended: '停牌',
  delisted: '退市',
  pre_ipo: '待上市',
} as const

/**
 * 市场类型标签
 */
export const MARKET_LABELS = {
  sh: '上海',
  sz: '深圳',
  bj: '北京',
  hk: '香港',
  us: '美国',
} as const

// ============== 选项列表 ==============

/**
 * 策略类型选项
 */
export const STRATEGY_TYPE_OPTIONS = Object.entries(STRATEGY_TYPE_LABELS).map(
  ([value, label]) => ({ value, label })
)

/**
 * 策略来源选项
 */
export const SOURCE_TYPE_OPTIONS = Object.entries(SOURCE_TYPE_LABELS).map(
  ([value, label]) => ({ value, label })
)

/**
 * 用户角色选项
 */
export const USER_ROLE_OPTIONS = Object.entries(USER_ROLE_LABELS).map(
  ([value, label]) => ({ value, label })
)

/**
 * 任务状态选项
 */
export const TASK_STATUS_OPTIONS = Object.entries(TASK_STATUS_LABELS).map(
  ([value, label]) => ({ value, label })
)

/**
 * 股票状态选项
 */
export const STOCK_STATUS_OPTIONS = Object.entries(STOCK_STATUS_LABELS).map(
  ([value, label]) => ({ value, label })
)

/**
 * 市场类型选项
 */
export const MARKET_OPTIONS = Object.entries(MARKET_LABELS).map(
  ([value, label]) => ({ value, label })
)

// ============== 配置常量 ==============

/**
 * 分页配置
 */
export const PAGINATION = {
  DEFAULT_PAGE: 1,
  DEFAULT_PAGE_SIZE: 20,
  PAGE_SIZE_OPTIONS: [10, 20, 50, 100],
} as const

/**
 * API 配置
 */
export const API_CONFIG = {
  TIMEOUT: 600000, // 10分钟
  RETRY_COUNT: 1,
  CACHE_DURATION: 5 * 60 * 1000, // 5分钟
} as const

/**
 * 日期格式
 */
export const DATE_FORMATS = {
  DATE: 'yyyy-MM-dd',
  TIME: 'HH:mm:ss',
  DATETIME: 'yyyy-MM-dd HH:mm:ss',
  DATETIME_SHORT: 'MM-dd HH:mm',
  MONTH: 'yyyy-MM',
  YEAR: 'yyyy',
} as const

/**
 * 文件上传配置
 */
export const UPLOAD_CONFIG = {
  MAX_FILE_SIZE: 10 * 1024 * 1024, // 10MB
  ALLOWED_IMAGE_TYPES: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
  ALLOWED_FILE_TYPES: ['text/csv', 'application/json', 'text/plain'],
} as const

/**
 * 图表配置
 */
export const CHART_CONFIG = {
  DEFAULT_HEIGHT: 400,
  MOBILE_HEIGHT: 300,
  COLORS: [
    '#3b82f6', // blue-500
    '#10b981', // green-500
    '#f59e0b', // amber-500
    '#ef4444', // red-500
    '#8b5cf6', // violet-500
    '#ec4899', // pink-500
    '#06b6d4', // cyan-500
    '#14b8a6', // teal-500
  ],
} as const

/**
 * 表格配置
 */
export const TABLE_CONFIG = {
  MOBILE_BREAKPOINT: 768,
  DEFAULT_EMPTY_MESSAGE: '暂无数据',
  DEFAULT_LOADING_MESSAGE: '加载中...',
  DEFAULT_ERROR_MESSAGE: '加载失败，请重试',
} as const

/**
 * 通知配置
 */
export const NOTIFICATION_CONFIG = {
  SUCCESS_DURATION: 3000,
  ERROR_DURATION: 5000,
  INFO_DURATION: 4000,
  WARNING_DURATION: 4000,
} as const

// ============== 验证规则 ==============

/**
 * 表单验证规则
 */
export const VALIDATION_RULES = {
  EMAIL: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  PASSWORD_MIN_LENGTH: 8,
  USERNAME_MIN_LENGTH: 3,
  USERNAME_MAX_LENGTH: 20,
  PHONE: /^1[3-9]\d{9}$/,
  URL: /^https?:\/\/.+/,
  STOCK_CODE: /^\d{6}$/,
} as const

/**
 * 错误消息
 */
export const ERROR_MESSAGES = {
  REQUIRED: '此字段必填',
  INVALID_EMAIL: '请输入有效的邮箱地址',
  INVALID_PASSWORD: '密码长度至少8位',
  INVALID_USERNAME: '用户名长度应在3-20个字符之间',
  INVALID_PHONE: '请输入有效的手机号码',
  INVALID_URL: '请输入有效的URL',
  INVALID_STOCK_CODE: '请输入6位股票代码',
  NETWORK_ERROR: '网络连接失败，请检查网络设置',
  SERVER_ERROR: '服务器错误，请稍后重试',
  UNAUTHORIZED: '未授权，请重新登录',
  FORBIDDEN: '没有权限执行此操作',
} as const

// ============== 导出类型 ==============

export type StrategyType = keyof typeof STRATEGY_TYPE_LABELS
export type SourceType = keyof typeof SOURCE_TYPE_LABELS
export type UserRole = keyof typeof USER_ROLE_LABELS
export type TaskStatus = keyof typeof TASK_STATUS_LABELS
export type StockStatus = keyof typeof STOCK_STATUS_LABELS
export type MarketType = keyof typeof MARKET_LABELS