/**
 * Sentry客户端配置
 *
 * 用于浏览器端错误监控和性能追踪
 */

import * as Sentry from '@sentry/nextjs'

Sentry.init({
  // Sentry DSN - 从环境变量读取
  // 生产环境请设置 NEXT_PUBLIC_SENTRY_DSN 环境变量
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN || '',

  // 环境标识
  environment: process.env.NODE_ENV || 'development',

  // 采样率设置
  tracesSampleRate: process.env.NODE_ENV === 'production' ? 0.1 : 1.0, // 生产环境10%，开发环境100%

  // Session Replay 采样率
  replaysSessionSampleRate: 0.1, // 10%的正常会话
  replaysOnErrorSampleRate: 1.0, // 100%的错误会话

  // 启用的集成
  integrations: [
    Sentry.replayIntegration({
      maskAllText: true,
      blockAllMedia: true,
    }),
  ],

  // 忽略特定错误
  ignoreErrors: [
    // 浏览器扩展错误
    'Non-Error promise rejection captured',
    /Failed to connect to MetaMask/i,
    /chrome-extension/i,
    /moz-extension/i,
    /safari-extension/i,
    // 网络错误
    'NetworkError',
    'Network request failed',
    // 取消的请求
    'AbortError',
    'Request aborted',
    // 404错误（业务正常）
    'Request failed with status code 404',
  ],

  // 过滤面包屑
  beforeBreadcrumb(breadcrumb) {
    // 忽略404请求的面包屑
    if (breadcrumb.category === 'fetch' && breadcrumb.data?.status_code === 404) {
      return null
    }
    return breadcrumb
  },

  // 事件发送前的处理
  beforeSend(event) {
    // 开发环境不发送错误到Sentry
    if (process.env.NODE_ENV === 'development') {
      console.log('Sentry Event (dev mode, not sent):', event)
      return null
    }

    // 忽略浏览器扩展错误
    if (event.exception?.values) {
      const extensionError = event.exception.values.some(exception => {
        const stacktrace = exception.stacktrace?.frames || []
        return stacktrace.some(frame =>
          frame.filename?.includes('chrome-extension://') ||
          frame.filename?.includes('moz-extension://') ||
          frame.filename?.includes('safari-extension://')
        )
      })
      if (extensionError) {
        return null
      }
    }

    // 过滤敏感信息
    if (event.request?.headers) {
      delete event.request.headers['Authorization']
      delete event.request.headers['Cookie']
    }

    return event
  },

  // 启用调试模式（仅开发环境）
  debug: process.env.NODE_ENV === 'development',
})
