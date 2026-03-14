/**
 * Sentry服务端配置
 *
 * 用于Next.js服务器端和Edge Runtime的错误监控
 */

import * as Sentry from '@sentry/nextjs'

Sentry.init({
  // Sentry DSN - 从环境变量读取
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN || '',

  // 环境标识
  environment: process.env.NODE_ENV || 'development',

  // 采样率设置
  tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.1 : 1.0,

  // 忽略特定错误
  ignoreErrors: [
    'ECONNREFUSED',
    'ETIMEDOUT',
    'Request failed with status code 404',
  ],

  // 事件发送前的处理
  beforeSend(event) {
    // 开发环境不发送错误到Sentry
    if (process.env.NODE_ENV === 'development') {
      console.log('Sentry Event (dev mode, not sent):', event)
      return null
    }

    // 过滤敏感信息
    if (event.request?.headers) {
      delete event.request.headers['authorization']
      delete event.request.headers['cookie']
    }

    return event
  },

  // 启用调试模式（仅开发环境）
  debug: process.env.NODE_ENV === 'development',
})
