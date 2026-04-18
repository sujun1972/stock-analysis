import axios, { AxiosInstance, AxiosRequestConfig } from 'axios'
import { isTokenExpiringSoon } from '@/lib/jwt-utils'
import type { ApiResponse } from '@/types'

/**
 * API基础URL配置
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * 创建axios实例
 */
const axiosInstance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 600000,
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * Token刷新状态管理
 */
let isRefreshing = false
let failedQueue: Array<{
  resolve: (value: string | null) => void
  reject: (reason?: Error) => void
}> = []

const processQueue = (error: Error | null = null, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })
  failedQueue = []
}

/**
 * 请求拦截器
 */
axiosInstance.interceptors.request.use(
  async (config) => {
    if (typeof window === 'undefined') {
      return config
    }

    const isAuthRequest =
      config.url?.includes('/api/auth/login') ||
      config.url?.includes('/api/auth/register') ||
      config.url?.includes('/api/auth/refresh') ||
      config.url?.includes('/api/auth/logout')

    const authStorage = localStorage.getItem('auth-storage')
    if (authStorage) {
      try {
        const { state } = JSON.parse(authStorage)
        const accessToken = state?.accessToken

        if (accessToken) {
          if (!isAuthRequest && isTokenExpiringSoon(accessToken, 5)) {
            if (isRefreshing) {
              return new Promise((resolve, reject) => {
                failedQueue.push({ resolve, reject })
              })
                .then((token) => {
                  config.headers.Authorization = `Bearer ${token}`
                  return config
                })
                .catch((err) => {
                  return Promise.reject(err)
                })
            }

            isRefreshing = true

            try {
              const { useAuthStore } = await import('@/stores/auth-store')
              await useAuthStore.getState().refreshAccessToken()

              const newAuthStorage = localStorage.getItem('auth-storage')
              if (newAuthStorage) {
                const { state: newState } = JSON.parse(newAuthStorage)
                const newAccessToken = newState?.accessToken
                if (newAccessToken) {
                  config.headers.Authorization = `Bearer ${newAccessToken}`
                  processQueue(null, newAccessToken)
                }
              }
            } catch (refreshError) {
              processQueue(refreshError as Error, null)
              return Promise.reject(refreshError)
            } finally {
              isRefreshing = false
            }
          } else {
            config.headers.Authorization = `Bearer ${accessToken}`
          }
        }
      } catch (error) {
        console.error('Failed to parse auth storage:', error)
      }
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

/**
 * 响应拦截器
 */
axiosInstance.interceptors.response.use(
  (response) => {
    return response
  },
  async (error) => {
    const originalRequest = error.config

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/api/auth/refresh') &&
      !originalRequest.url?.includes('/api/auth/login')
    ) {
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then((token) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            return axiosInstance(originalRequest)
          })
          .catch((err) => {
            return Promise.reject(err)
          })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const { useAuthStore } = await import('@/stores/auth-store')
        await useAuthStore.getState().refreshAccessToken()

        const authStorage = localStorage.getItem('auth-storage')
        if (authStorage) {
          const { state } = JSON.parse(authStorage)
          const accessToken = state?.accessToken
          if (accessToken) {
            originalRequest.headers.Authorization = `Bearer ${accessToken}`
            processQueue(null, accessToken)
            return axiosInstance(originalRequest)
          }
        }

        throw new Error('Failed to get new access token')
      } catch (refreshError) {
        console.error('Token refresh failed, redirecting to login...')

        processQueue(refreshError as Error, null)

        const { useAuthStore } = await import('@/stores/auth-store')
        useAuthStore.getState().logout()

        if (typeof window !== 'undefined') {
          const currentPath = window.location.pathname
          const redirectPath = currentPath !== '/login' ? `?redirect=${encodeURIComponent(currentPath)}` : ''
          window.location.href = `/login${redirectPath}`
        }

        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    if (error.response) {
      console.error('API Error:', error.response.data)
    } else if (error.request) {
      console.error('Network Error:', error.request)
    } else {
      console.error('Error:', error.message)
    }
    return Promise.reject(error)
  }
)

/**
 * 基础HTTP方法（供领域模块使用）
 */
export async function apiGet<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  const response = await axiosInstance.get(url, config)
  return response.data
}

export async function apiPost<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  const response = await axiosInstance.post(url, data, config)
  return response.data
}

export async function apiPut<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  const response = await axiosInstance.put(url, data, config)
  return response.data
}

export async function apiPatch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  const response = await axiosInstance.patch(url, data, config)
  return response.data
}

export async function apiDelete<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
  const response = await axiosInstance.delete(url, config)
  return response.data
}

export { axiosInstance }
export default axiosInstance
