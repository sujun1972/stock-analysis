'use client'

/**
 * 全局错误边界组件
 *
 * 功能：
 * - 捕获React组件树中的JavaScript错误
 * - 显示优雅的错误UI
 * - 自动上报错误到Sentry
 * - 提供重试和返回首页选项
 * - 开发环境显示详细错误信息
 */

import React, { Component, ErrorInfo, ReactNode } from 'react'
import { AlertTriangle, RefreshCw, Home } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import logger from '@/lib/logger'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onReset?: () => void
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    }
  }

  static getDerivedStateFromError(error: Error): State {
    // 更新 state 使下一次渲染能够显示降级后的 UI
    return {
      hasError: true,
      error,
      errorInfo: null,
    }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    // 记录错误到日志系统
    logger.error('React Error Boundary caught an error', error, {
      componentStack: errorInfo.componentStack,
      errorBoundary: true,
    })

    this.setState({
      error,
      errorInfo,
    })
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    })

    // 调用自定义重置回调
    if (this.props.onReset) {
      this.props.onReset()
    }
  }

  handleGoHome = (): void => {
    window.location.href = '/'
  }

  render(): ReactNode {
    if (this.state.hasError) {
      // 如果提供了自定义降级UI，使用它
      if (this.props.fallback) {
        return this.props.fallback
      }

      const isDevelopment = process.env.NODE_ENV === 'development'

      // 默认错误UI
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
          <Card className="max-w-2xl w-full">
            <CardHeader>
              <div className="flex items-center gap-3">
                <AlertTriangle className="h-8 w-8 text-red-500" />
                <div>
                  <CardTitle className="text-2xl">应用程序出错</CardTitle>
                  <CardDescription>
                    抱歉，应用程序遇到了意外错误。错误已自动上报，我们会尽快修复。
                  </CardDescription>
                </div>
              </div>
            </CardHeader>

            <CardContent className="space-y-4">
              {/* 生产环境显示简要错误信息 */}
              <Alert variant="destructive">
                <AlertTitle>错误信息</AlertTitle>
                <AlertDescription className="font-mono text-sm">
                  {this.state.error?.message || '未知错误'}
                </AlertDescription>
              </Alert>

              {/* 开发环境显示详细堆栈信息 */}
              {isDevelopment && this.state.errorInfo && (
                <details className="mt-4">
                  <summary className="cursor-pointer font-semibold text-sm text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-gray-100">
                    查看详细错误堆栈（开发模式）
                  </summary>
                  <pre className="mt-2 p-4 bg-gray-100 dark:bg-gray-800 rounded text-xs overflow-auto max-h-96 border border-gray-300 dark:border-gray-700">
                    {this.state.error?.stack}
                    {'\n\n'}
                    {this.state.errorInfo.componentStack}
                  </pre>
                </details>
              )}

              {/* 建议操作 */}
              <div className="text-sm text-gray-600 dark:text-gray-400">
                <p className="font-semibold mb-2">您可以尝试：</p>
                <ul className="list-disc list-inside space-y-1">
                  <li>点击&ldquo;重新加载&rdquo;按钮重试</li>
                  <li>返回首页重新开始</li>
                  <li>清除浏览器缓存后刷新页面</li>
                  <li>如果问题持续存在，请联系技术支持</li>
                </ul>
              </div>
            </CardContent>

            <CardFooter className="flex gap-3">
              <Button onClick={this.handleReset} variant="default" className="flex-1">
                <RefreshCw className="mr-2 h-4 w-4" />
                重新加载
              </Button>
              <Button onClick={this.handleGoHome} variant="outline" className="flex-1">
                <Home className="mr-2 h-4 w-4" />
                返回首页
              </Button>
            </CardFooter>
          </Card>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary
