/**
 * 系统配置 Context
 *
 * 功能：
 * - 在应用启动时加载系统配置
 * - 提供全局访问系统配置的能力
 * - 支持配置更新和刷新
 */
'use client'

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { apiClient } from '@/lib/api-client'
import logger from '@/lib/logger'

interface SystemConfig {
  stock_analysis_url: string
}

interface SystemConfigContextType {
  config: SystemConfig | null
  loading: boolean
  error: string | null
  refreshConfig: () => Promise<void>
}

const SystemConfigContext = createContext<SystemConfigContextType | undefined>(undefined)

const DEFAULT_CONFIG: SystemConfig = {
  stock_analysis_url: 'http://localhost:3000/analysis?code={code}'
}

export function SystemConfigProvider({ children }: { children: React.ReactNode }) {
  const [config, setConfig] = useState<SystemConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadConfig = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await apiClient.getSystemSettings()

      if (response.data) {
        setConfig(response.data)
        logger.info('System config loaded:', response.data)
      } else {
        // 使用默认配置
        setConfig(DEFAULT_CONFIG)
        logger.warn('No system config found, using defaults')
      }
    } catch (err: any) {
      const errorMsg = err.message || '加载系统配置失败'
      setError(errorMsg)
      // 出错时使用默认配置
      setConfig(DEFAULT_CONFIG)
      logger.error('Failed to load system config:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  const refreshConfig = useCallback(async () => {
    await loadConfig()
  }, [loadConfig])

  useEffect(() => {
    loadConfig()
  }, [loadConfig])

  return (
    <SystemConfigContext.Provider value={{ config, loading, error, refreshConfig }}>
      {children}
    </SystemConfigContext.Provider>
  )
}

export function useSystemConfig() {
  const context = useContext(SystemConfigContext)
  if (context === undefined) {
    throw new Error('useSystemConfig must be used within a SystemConfigProvider')
  }
  return context
}
