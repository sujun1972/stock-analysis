'use client'

import { useEffect, useState, useCallback } from 'react'
import { monitorApi } from '@/lib/api'
import logger from '@/lib/logger'

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy'
  checks: {
    database?: {
      status: 'healthy' | 'unhealthy'
      message?: string
      response_time_ms?: number
    }
    redis?: {
      status: 'healthy' | 'unhealthy'
      message?: string
      ping_time_ms?: number
    }
    core_service?: {
      status: 'healthy' | 'unhealthy'
      message?: string
    }
    circuit_breakers?: {
      status: string
      details?: any
    }
  }
  timestamp: string
}

export interface ServiceStatus {
  status: string
  message: string
  responseTime?: number
}

// Grafana 和 Prometheus 配置
const GRAFANA_URL = 'http://localhost:3001'
const GRAFANA_DASHBOARD_UID = 'stock-analysis-overview'

export const getServiceStatus = (serviceCheck: any): ServiceStatus => {
  if (!serviceCheck) return { status: 'unhealthy', message: '未知' }
  return {
    status: serviceCheck.status || 'unhealthy',
    message: serviceCheck.message || serviceCheck.status,
    responseTime: serviceCheck.response_time_ms || serviceCheck.ping_time_ms
  }
}

export const useMonitorData = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const loadMonitorData = useCallback(async () => {
    try {
      setIsLoading(true)
      setError(null)

      const healthResponse = await monitorApi.healthCheck()

      if (healthResponse) {
        setHealth(healthResponse as any)
      }

      setLastUpdate(new Date())
    } catch (err: any) {
      setError(err.message || '加载监控数据失败')
      logger.error('Failed to load monitor data', err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    loadMonitorData()

    // 自动刷新健康检查
    let interval: NodeJS.Timeout
    if (autoRefresh) {
      interval = setInterval(() => {
        loadMonitorData()
      }, 10000) // 每10秒刷新一次
    }

    return () => {
      if (interval) clearInterval(interval)
    }
  }, [autoRefresh, loadMonitorData])

  // 打开 Grafana 完整仪表板
  const openGrafana = useCallback(() => {
    window.open(`${GRAFANA_URL}/d/${GRAFANA_DASHBOARD_UID}`, '_blank')
  }, [])

  // 打开 Prometheus
  const openPrometheus = useCallback(() => {
    window.open('http://localhost:9090', '_blank')
  }, [])

  const overallStatus = health?.status || 'unhealthy'

  return {
    health,
    isLoading,
    error,
    lastUpdate,
    autoRefresh,
    setAutoRefresh,
    overallStatus,
    loadMonitorData,
    openGrafana,
    openPrometheus,
  }
}
