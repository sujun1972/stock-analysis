/**
 * 通知渠道配置类型定义
 *
 * 用于 Admin 后台管理通知渠道配置（Email, Telegram）
 * @see /backend/app/models/notification_channel_config.py
 */

/**
 * 通知渠道配置主接口
 */
export interface NotificationChannelConfig {
  id: number
  channel_type: 'email' | 'telegram'
  channel_name: string
  is_enabled: boolean
  is_default: boolean
  priority: number
  config: EmailConfig | TelegramConfig
  description?: string
  last_test_at?: string
  last_test_status?: 'success' | 'failed'
  last_test_message?: string
  created_at: string
  updated_at: string
}

/**
 * Email SMTP 配置
 */
export interface EmailConfig {
  smtp_host: string
  smtp_port: number
  smtp_username: string
  smtp_password: string
  smtp_use_tls: boolean
  from_email: string
  from_name: string
}

/**
 * Telegram Bot 配置
 */
export interface TelegramConfig {
  bot_token: string
  parse_mode: 'Markdown' | 'HTML'
  timeout: number
}

export interface NotificationChannelUpdateRequest {
  is_enabled?: boolean
  config?: Partial<EmailConfig | TelegramConfig>
  description?: string
}

export interface TestChannelRequest {
  test_target: string  // 邮箱地址或 Telegram Chat ID
}

export interface TestChannelResponse {
  success: boolean
  message: string
  test_time: string
}

/**
 * 脱敏处理敏感信息（密码、Token 等）
 * @param value 原始值
 * @returns 脱敏后的字符串，格式：前4位 + ******** + 后4位
 * @example maskSensitiveInfo('abc123456789def') => 'abc1********9def'
 */
export function maskSensitiveInfo(value: string): string {
  if (!value || value.length < 8) {
    return '********'
  }
  return value.substring(0, 4) + '********' + value.substring(value.length - 4)
}

/**
 * 判断是否为 Email 配置
 */
export function isEmailConfig(config: any): config is EmailConfig {
  return 'smtp_host' in config
}

/**
 * 判断是否为 Telegram 配置
 */
export function isTelegramConfig(config: any): config is TelegramConfig {
  return 'bot_token' in config
}
