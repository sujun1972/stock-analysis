/**
 * 系统配置 Context
 *
 * 功能：
 * - 在应用启动时加载系统配置
 * - 提供全局访问系统配置的能力
 * - 支持配置更新和刷新
 *
 * 优化：使用 React Query 管理配置状态
 */
'use client'

import React, { createContext, useContext } from 'react'
import { useSystemSettings } from '@/hooks/queries/use-system'
import logger from '@/lib/logger'
import { useQueryClient } from '@tanstack/react-query'
import { queryKeys } from '@/lib/query/keys'

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
  const queryClient = useQueryClient()

  // 使用 React Query hook 获取系统设置
  const { data: settings, isLoading, error } = useSystemSettings()

  // 构建配置对象
  const config: SystemConfig | null = settings
    ? {
        stock_analysis_url: settings.stock_analysis_url || DEFAULT_CONFIG.stock_analysis_url
      }
    : null

  // 如果加载失败，使用默认配置
  const finalConfig = config || DEFAULT_CONFIG

  // 刷新配置函数
  const refreshConfig = async () => {
    try {
      // 使配置查询失效，触发重新获取
      await queryClient.invalidateQueries({
        queryKey: queryKeys.system.settings()
      })
      logger.info('System config refreshed')
    } catch (err) {
      logger.error('Failed to refresh system config:', err)
    }
  }

  // 记录配置加载状态
  React.useEffect(() => {
    if (settings) {
      logger.info('System config loaded:', settings)
    }
    if (error) {
      logger.error('Failed to load system config:', error)
    }
  }, [settings, error])

  return (
    <SystemConfigContext.Provider
      value={{
        config: finalConfig,
        loading: isLoading,
        error: error?.message || null,
        refreshConfig
      }}
    >
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