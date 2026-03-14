/**
 * Sentry Edge Runtime配置
 *
 * 用于Next.js Edge Runtime（中间件等）的错误监控
 */

import * as Sentry from '@sentry/nextjs'

Sentry.init({
  // Sentry DSN - 从环境变量读取
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN || '',

  // 环境标识
  environment: process.env.NODE_ENV || 'development',

  // 采样率设置
  tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.1 : 1.0,

  // 事件发送前的处理
  beforeSend(event) {
    // 开发环境不发送错误到Sentry
    if (process.env.NODE_ENV === 'development') {
      return null
    }
    return event
  },

  // 启用调试模式（仅开发环境）
  debug: process.env.NODE_ENV === 'development',
})
