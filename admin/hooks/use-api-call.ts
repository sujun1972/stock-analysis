/**
 * @file hooks/use-api-call.ts
 * @description 通用的 API 调用 Hook，处理加载状态、错误处理和 Toast 提示
 * @author Claude
 * @created 2024-03-16
 * @updated 2024-03-16
 */

import { useState, useCallback } from 'react'
import { toast } from 'sonner'
import { ApiResponse } from '@/types/api'
import { formatErrorMessage } from '@/lib/error-formatter'

interface UseApiCallOptions {
  showSuccessToast?: boolean
  showErrorToast?: boolean
  successMessage?: string
  onSuccess?: (data: any) => void
  onError?: (error: any) => void
}

/**
 * 通用的 API 调用 Hook
 * @param options - 配置选项
 * @returns API 调用状态和执行函数
 */
export function useApiCall<T = any>(options: UseApiCallOptions = {}) {
  const {
    showSuccessToast = false,
    showErrorToast = true,
    successMessage,
    onSuccess,
    onError
  } = options

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<T | null>(null)

  const execute = useCallback(async (
    apiCall: () => Promise<ApiResponse<T>>
  ): Promise<T | null> => {
    try {
      setLoading(true)
      setError(null)

      const response = await apiCall()

      // 检查响应状态
      if (response.code < 200 || response.code >= 300) {
        throw new Error(response.message || '请求失败')
      }

      const result = response.data as T
      setData(result)

      // 成功回调
      onSuccess?.(result)

      // 成功提示
      if (showSuccessToast) {
        toast.success(successMessage || response.message || '操作成功')
      }

      return result
    } catch (err: any) {
      const errorMsg = formatErrorMessage(err)
      setError(errorMsg)

      // 错误回调
      onError?.(err)

      // 错误提示
      if (showErrorToast) {
        toast.error(errorMsg)
      }

      return null
    } finally {
      setLoading(false)
    }
  }, [showSuccessToast, showErrorToast, successMessage, onSuccess, onError])

  const reset = useCallback(() => {
    setLoading(false)
    setError(null)
    setData(null)
  }, [])

  return {
    loading,
    error,
    data,
    execute,
    reset
  }
}

/**
 * 批量操作 Hook
 * @param options - 配置选项
 * @returns 批量操作状态和执行函数
 */
export function useBatchApiCall<T = any>(options: UseApiCallOptions = {}) {
  const [loading, setLoading] = useState(false)
  const [errors, setErrors] = useState<Map<string, string>>(new Map())
  const [results, setResults] = useState<Map<string, T>>(new Map())

  const executeBatch = useCallback(async (
    calls: Array<{
      key: string
      call: () => Promise<ApiResponse<T>>
    }>
  ): Promise<Map<string, T>> => {
    try {
      setLoading(true)
      setErrors(new Map())
      setResults(new Map())

      const promises = calls.map(async ({ key, call }) => {
        try {
          const response = await call()
          if (response.code >= 200 && response.code < 300 && response.data) {
            results.set(key, response.data)
          } else {
            throw new Error(response.message || '请求失败')
          }
        } catch (err) {
          const errorMsg = formatErrorMessage(err)
          errors.set(key, errorMsg)
          if (options.showErrorToast) {
            toast.error(`${key}: ${errorMsg}`)
          }
        }
      })

      await Promise.all(promises)

      setResults(new Map(results))
      setErrors(new Map(errors))

      if (options.showSuccessToast && results.size > 0) {
        toast.success(options.successMessage || `成功完成 ${results.size} 个操作`)
      }

      return results
    } finally {
      setLoading(false)
    }
  }, [options])

  return {
    loading,
    errors,
    results,
    executeBatch
  }
}

/**
 * 轮询 API Hook
 * @param apiCall - API 调用函数
 * @param interval - 轮询间隔（毫秒）
 * @param options - 配置选项
 */
export function usePollingApi<T = any>(
  apiCall: () => Promise<ApiResponse<T>>,
  interval: number = 5000,
  options: UseApiCallOptions = {}
) {
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [isPolling, setIsPolling] = useState(false)

  const startPolling = useCallback(() => {
    setIsPolling(true)

    const poll = async () => {
      if (!isPolling) return

      try {
        setLoading(true)
        const response = await apiCall()

        if (response.code >= 200 && response.code < 300 && response.data) {
          setData(response.data)
          setError(null)
          options.onSuccess?.(response.data)
        } else {
          throw new Error(response.message || '请求失败')
        }
      } catch (err) {
        const errorMsg = formatErrorMessage(err)
        setError(errorMsg)
        options.onError?.(err)
      } finally {
        setLoading(false)
      }
    }

    // 立即执行一次
    poll()

    // 设置定时器
    const timer = setInterval(poll, interval)

    // 返回清理函数
    return () => {
      clearInterval(timer)
      setIsPolling(false)
    }
  }, [apiCall, interval, options])

  const stopPolling = useCallback(() => {
    setIsPolling(false)
  }, [])

  return {
    data,
    loading,
    error,
    isPolling,
    startPolling,
    stopPolling
  }
}