/**
 * 统一日志管理系统
 *
 * 功能：
 * - 分级日志（debug, info, warn, error）
 * - 开发环境控制台输出
 * - 生产环境集成Sentry
 * - 自动错误上报
 * - 性能监控支持
 */

import * as Sentry from '@sentry/nextjs'

export enum LogLevel {
  DEBUG = 'debug',
  INFO = 'info',
  WARN = 'warn',
  ERROR = 'error',
}

interface LogContext {
  [key: string]: any
}

class Logger {
  private isDevelopment: boolean

  constructor() {
    this.isDevelopment = process.env.NODE_ENV === 'development'
  }

  /**
   * Debug级别日志 - 仅开发环境输出
   */
  debug(message: string, context?: LogContext): void {
    if (this.isDevelopment) {
      console.debug(`[DEBUG] ${message}`, context || '')
    }
  }

  /**
   * Info级别日志
   */
  info(message: string, context?: LogContext): void {
    if (this.isDevelopment) {
      console.info(`[INFO] ${message}`, context || '')
    }

    // 生产环境可选择性上报重要信息
    if (!this.isDevelopment && context?.important) {
      Sentry.captureMessage(message, {
        level: 'info',
        extra: context,
      })
    }
  }

  /**
   * Warn级别日志
   */
  warn(message: string, context?: LogContext): void {
    if (this.isDevelopment) {
      console.warn(`[WARN] ${message}`, context || '')
    }

    // 生产环境上报警告
    Sentry.captureMessage(message, {
      level: 'warning',
      extra: context,
    })
  }

  /**
   * Error级别日志 - 自动上报Sentry
   */
  error(message: string, error?: Error | unknown, context?: LogContext): void {
    if (this.isDevelopment) {
      console.error(`[ERROR] ${message}`, error, context || '')
    }

    // 上报到Sentry
    if (error instanceof Error) {
      Sentry.captureException(error, {
        extra: {
          message,
          ...context,
        },
      })
    } else {
      Sentry.captureMessage(message, {
        level: 'error',
        extra: {
          error,
          ...context,
        },
      })
    }
  }

  /**
   * 记录性能指标
   */
  performance(metric: string, value: number, unit: string = 'ms', context?: LogContext): void {
    if (this.isDevelopment) {
      console.info(`[PERF] ${metric}: ${value}${unit}`, context || '')
    }

    // 发送性能指标到Sentry
    Sentry.metrics.distribution(metric, value, {
      unit,
      tags: context as Record<string, string>,
    } as any)
  }

  /**
   * 记录用户行为（用于追踪用户操作流程）
   */
  track(event: string, properties?: LogContext): void {
    if (this.isDevelopment) {
      console.info(`[TRACK] ${event}`, properties || '')
    }

    // 添加面包屑到Sentry
    Sentry.addBreadcrumb({
      category: 'user-action',
      message: event,
      level: 'info',
      data: properties,
    })
  }

  /**
   * 设置用户上下文
   */
  setUser(userId: string, email?: string, username?: string): void {
    Sentry.setUser({
      id: userId,
      email,
      username,
    })
  }

  /**
   * 清除用户上下文（登出时调用）
   */
  clearUser(): void {
    Sentry.setUser(null)
  }

  /**
   * 添加上下文标签
   */
  setContext(key: string, context: LogContext): void {
    Sentry.setContext(key, context)
  }

  /**
   * 添加标签
   */
  setTag(key: string, value: string): void {
    Sentry.setTag(key, value)
  }
}

// 导出单例
export const logger = new Logger()

// 便捷导出
export default logger
