/**
 * 通知系统类型定义
 *
 * 定义用户通知配置、站内消息、通知日志等数据结构
 */

/**
 * 用户通知配置接口
 */
export interface NotificationSettings {
  // 渠道启用状态
  email_enabled: boolean
  telegram_enabled: boolean
  in_app_enabled: boolean

  // 联系方式
  email_address?: string
  telegram_chat_id?: string
  telegram_username?: string

  // 订阅偏好
  subscribe_sentiment_report: boolean
  subscribe_premarket_report: boolean
  subscribe_backtest_report: boolean
  subscribe_strategy_alert: boolean

  // 发送时间
  sentiment_report_time: string  // "18:30"
  premarket_report_time: string  // "08:00"

  // 报告格式
  report_format: 'full' | 'summary' | 'action_only'

  // 频率控制
  max_daily_notifications: number

  created_at: string
  updated_at: string
}

/**
 * 站内消息接口
 */
export interface InAppNotification {
  id: number
  title: string
  content: string
  notification_type: string
  is_read: boolean
  read_at?: string
  priority: 'high' | 'normal' | 'low'
  business_date?: string
  reference_id?: string
  metadata?: Record<string, any>
  created_at: string
}

/**
 * 未读数量响应
 */
export interface UnreadCountResponse {
  unread_count: number
}

/**
 * 通知日志
 */
export interface NotificationLog {
  id: number
  notification_type: string
  channel: 'email' | 'telegram' | 'in_app'
  status: 'pending' | 'sent' | 'failed' | 'skipped'
  title: string
  sent_at?: string
  failed_reason?: string
  created_at: string
}

/**
 * 报告格式选项
 */
export const REPORT_FORMAT_OPTIONS = [
  { value: 'full', label: '完整报告' },
  { value: 'summary', label: '摘要' },
  { value: 'action_only', label: '仅行动指令' },
] as const

/**
 * 优先级配置
 */
export const PRIORITY_CONFIG = {
  high: {
    label: '高',
    color: 'text-red-500',
    bgColor: 'bg-red-50',
    icon: '🔴',
  },
  normal: {
    label: '普通',
    color: 'text-blue-500',
    bgColor: 'bg-blue-50',
    icon: '●',
  },
  low: {
    label: '低',
    color: 'text-gray-400',
    bgColor: 'bg-gray-50',
    icon: '○',
  },
} as const
