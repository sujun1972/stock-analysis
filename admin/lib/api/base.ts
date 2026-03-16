/**
 * @file lib/api/base.ts
 * @description API 客户端基础配置和拦截器
 * @author Claude
 * @created 2024-03-16
 * @updated 2024-03-16
 */

import axios, { AxiosInstance, AxiosError } from 'axios'
import { isTokenExpiringSoon } from '../jwt-utils'
import logger from '@/lib/logger'

/**
 * API基础URL配置
 */
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * 创建axios实例
 */
export const axiosInstance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 600000, // 10分钟超时
  headers: {
    'Content-Type': 'application/json',
  },
})

// Token 刷新状态管理
let isRefreshing = false
let failedQueue: Array<{
  resolve: (value?: any) => void
  reject: (reason?: any) => void
}> = []

/**
 * 处理刷新队列
 */
const processQueue = (error: any = null, token: string | null = null) => {
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
 * 刷新Token
 */
async function refreshAccessToken(): Promise<string | null> {
  try {
    const authStorage = localStorage.getItem('auth-storage')
    if (!authStorage) return null

    const { state } = JSON.parse(authStorage)
    const refreshToken = state?.refreshToken

    if (!refreshToken) return null

    const response = await axios.post(`${API_BASE_URL}/api/auth/refresh`, {
      refresh_token: refreshToken,
    })

    if (response.data.code === 200 && response.data.data) {
      const { access_token, refresh_token } = response.data.data

      // 更新存储
      const newAuthState = {
        ...state,
        accessToken: access_token,
        refreshToken: refresh_token,
      }

      const newAuthStorage = {
        ...JSON.parse(authStorage),
        state: newAuthState,
      }

      localStorage.setItem('auth-storage', JSON.stringify(newAuthStorage))

      return access_token
    }

    return null
  } catch (error) {
    logger.error('Token refresh failed', error)
    return null
  }
}

/**
 * 请求拦截器
 */
axiosInstance.interceptors.request.use(
  async (config) => {
    if (typeof window === 'undefined') {
      return config
    }

    const authStorage = localStorage.getItem('auth-storage')
    if (authStorage) {
      try {
        const { state } = JSON.parse(authStorage)
        const accessToken = state?.accessToken

        if (accessToken) {
          // 检查 token 是否即将过期
          const isAuthRequest =
            config.url?.includes('/api/auth/refresh') ||
            config.url?.includes('/api/auth/login')

          if (!isAuthRequest && isTokenExpiringSoon(accessToken, 5)) {
            if (isRefreshing) {
              // 等待刷新完成
              return new Promise((resolve, reject) => {
                failedQueue.push({ resolve, reject })
              }).then(() => {
                const newAuthStorage = localStorage.getItem('auth-storage')
                if (newAuthStorage) {
                  const { state: newState } = JSON.parse(newAuthStorage)
                  if (newState?.accessToken) {
                    config.headers.Authorization = `Bearer ${newState.accessToken}`
                  }
                }
                return config
              }).catch((err) => Promise.reject(err))
            } else {
              isRefreshing = true
              const newToken = await refreshAccessToken()
              isRefreshing = false

              if (newToken) {
                processQueue(null, newToken)
                config.headers.Authorization = `Bearer ${newToken}`
              } else {
                processQueue(new Error('Token refresh failed'), null)
              }
            }
          } else if (accessToken) {
            config.headers.Authorization = `Bearer ${accessToken}`
          }
        }
      } catch (error) {
        logger.error('Request interceptor error:', error)
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
    return response.data
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as any

    // 处理401错误
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (originalRequest.url?.includes('/api/auth/refresh')) {
        // 刷新token也失败了，需要重新登录
        const authStorage = localStorage.getItem('auth-storage')
        if (authStorage) {
          const parsed = JSON.parse(authStorage)
          parsed.state.isAuthenticated = false
          parsed.state.user = null
          parsed.state.accessToken = null
          parsed.state.refreshToken = null
          localStorage.setItem('auth-storage', JSON.stringify(parsed))
        }

        if (typeof window !== 'undefined') {
          window.location.href = '/login'
        }

        return Promise.reject(error)
      }

      if (isRefreshing) {
        // 等待刷新完成
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        }).then(() => {
          const authStorage = localStorage.getItem('auth-storage')
          if (authStorage) {
            const { state } = JSON.parse(authStorage)
            if (state?.accessToken) {
              originalRequest.headers.Authorization = `Bearer ${state.accessToken}`
            }
          }
          return axiosInstance(originalRequest)
        }).catch((err) => Promise.reject(err))
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const newToken = await refreshAccessToken()
        isRefreshing = false

        if (newToken) {
          processQueue(null, newToken)
          originalRequest.headers.Authorization = `Bearer ${newToken}`
          return axiosInstance(originalRequest)
        } else {
          processQueue(new Error('Token refresh failed'), null)
          throw new Error('Token refresh failed')
        }
      } catch (refreshError) {
        isRefreshing = false
        processQueue(refreshError, null)

        // 清除认证信息并重定向
        const authStorage = localStorage.getItem('auth-storage')
        if (authStorage) {
          const parsed = JSON.parse(authStorage)
          parsed.state.isAuthenticated = false
          parsed.state.user = null
          parsed.state.accessToken = null
          parsed.state.refreshToken = null
          localStorage.setItem('auth-storage', JSON.stringify(parsed))
        }

        if (typeof window !== 'undefined') {
          window.location.href = '/login'
        }

        return Promise.reject(refreshError)
      }
    }

    // 处理网络错误
    if (!error.response) {
      const networkError = {
        code: 0,
        message: '网络连接失败，请检查网络设置',
        data: null,
        timestamp: new Date().toISOString(),
      }
      return Promise.reject(networkError)
    }

    // 处理其他错误
    const errorResponse = {
      code: error.response.status,
      message: (error.response.data as any)?.message || error.message || '请求失败',
      data: (error.response.data as any)?.data || null,
      timestamp: new Date().toISOString(),
    }

    return Promise.reject(errorResponse)
  }
)

/**
 * 基础API客户端类
 */
export class BaseApiClient {
  protected instance = axiosInstance

  async get<T = any>(url: string, config?: any) {
    return this.instance.get<any, T>(url, config)
  }

  async post<T = any>(url: string, data?: any, config?: any) {
    return this.instance.post<any, T>(url, data, config)
  }

  async put<T = any>(url: string, data?: any, config?: any) {
    return this.instance.put<any, T>(url, data, config)
  }

  async patch<T = any>(url: string, data?: any, config?: any) {
    return this.instance.patch<any, T>(url, data, config)
  }

  async delete<T = any>(url: string, config?: any) {
    return this.instance.delete<any, T>(url, config)
  }
}