'use client'

import React, { Component, ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { AlertCircle, RefreshCw } from 'lucide-react'

interface ErrorBoundaryProps {
  children: ReactNode
  fallback?: ReactNode
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
  errorInfo: React.ErrorInfo | null
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    }
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo)
    this.setState({ error, errorInfo })
  }

  handleReset = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    })
  }

  render() {
    if (this.state.hasError) {
      // 如果提供了自定义降级 UI，使用它
      if (this.props.fallback) {
        return this.props.fallback
      }

      // 默认错误 UI
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 p-4">
          <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <AlertCircle className="h-8 w-8 text-red-500" />
              <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                出错了
              </h2>
            </div>

            <p className="text-gray-600 dark:text-gray-300 mb-4">
              应用程序遇到了一个错误。请刷新页面重试，如果问题持续存在，请联系技术支持。
            </p>

            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="mb-4">
                <summary className="cursor-pointer text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200">
                  错误详情（开发模式）
                </summary>
                <div className="mt-2 p-3 bg-gray-100 dark:bg-gray-900 rounded text-xs overflow-auto max-h-48">
                  <p className="font-mono text-red-600 dark:text-red-400 mb-2">
                    {this.state.error.toString()}
                  </p>
                  {this.state.errorInfo && (
                    <pre className="text-gray-700 dark:text-gray-300 whitespace-pre-wrap">
                      {this.state.errorInfo.componentStack}
                    </pre>
                  )}
                </div>
              </details>
            )}

            <div className="flex gap-3">
              <Button
                onClick={() => window.location.reload()}
                className="flex-1"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                刷新页面
              </Button>
              <Button
                onClick={this.handleReset}
                variant="outline"
                className="flex-1"
              >
                重试
              </Button>
            </div>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
