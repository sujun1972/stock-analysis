'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { apiClient } from '@/lib/api-client'

interface MarketStatus {
  status: string
  description: string
  is_trading: boolean
  should_refresh: boolean
  next_session_time: string | null
  next_session_desc: string | null
}

interface DataFreshness {
  should_refresh: boolean
  reason: string
  market_status: string
  market_description: string
  last_update: string | null
}

/**
 * 市场状态Hook
 * 用于管理交易时段判断和实时数据刷新策略
 */
export function useMarketStatus() {
  const [marketStatus, setMarketStatus] = useState<MarketStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  // 获取市场状态
  const fetchMarketStatus = useCallback(async () => {
    try {
      const response = await apiClient.getMarketStatus()
      if (response.data) {
        setMarketStatus(response.data)
      }
    } catch (error) {
      console.error('Failed to fetch market status:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  // 检查数据新鲜度
  const checkFreshness = useCallback(async (codes?: string[], force: boolean = false): Promise<DataFreshness | null> => {
    try {
      const response = await apiClient.checkDataFreshness({ codes, force })
      return response.data || null
    } catch (error) {
      console.error('Failed to check data freshness:', error)
      return null
    }
  }, [])

  // 组件挂载时获取市场状态，并每分钟更新一次
  useEffect(() => {
    fetchMarketStatus()

    // 每60秒更新一次市场状态
    intervalRef.current = setInterval(() => {
      fetchMarketStatus()
    }, 60000)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [fetchMarketStatus])

  return {
    marketStatus,
    loading,
    isTrading: marketStatus?.is_trading || false,
    shouldRefresh: marketStatus?.should_refresh || false,
    fetchMarketStatus,
    checkFreshness
  }
}

/**
 * 智能刷新Hook
 * 根据市场状态自动控制数据刷新频率
 *
 * @param refreshCallback 刷新数据的回调函数
 * @param codes 要监控的股票代码列表（可选）
 * @param enableAutoRefresh 是否启用自动刷新
 */
export function useSmartRefresh(
  refreshCallback: () => Promise<void>,
  codes?: string[],
  enableAutoRefresh: boolean = true
) {
  const { marketStatus, checkFreshness } = useMarketStatus()
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  // 执行刷新
  const doRefresh = useCallback(async (force: boolean = false) => {
    if (isRefreshing) return

    try {
      setIsRefreshing(true)

      // 检查是否需要刷新
      if (!force) {
        const freshness = await checkFreshness(codes)
        if (freshness && !freshness.should_refresh) {
          console.log(`跳过刷新: ${freshness.reason}`)
          return
        }
      }

      // 执行刷新
      await refreshCallback()
      setLastRefresh(new Date())
    } catch (error) {
      console.error('刷新失败:', error)
    } finally {
      setIsRefreshing(false)
    }
  }, [isRefreshing, checkFreshness, codes, refreshCallback])

  // 首次加载时检查是否需要刷新（即使非交易时段）
  const [hasCheckedInitial, setHasCheckedInitial] = useState(false)

  useEffect(() => {
    // 等待 marketStatus 加载完成后再执行首次检查
    if (!enableAutoRefresh || !marketStatus || hasCheckedInitial) return

    // 首次检查数据新鲜度
    const checkInitialFreshness = async () => {
      const freshness = await checkFreshness(codes, false)
      if (freshness?.should_refresh) {
        console.log(`首次加载检查: ${freshness.reason}`)
        await doRefresh(true)
      }
      setHasCheckedInitial(true)
    }

    checkInitialFreshness()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [marketStatus]) // 当 marketStatus 加载完成时触发

  // 根据市场状态设置刷新间隔
  useEffect(() => {
    if (!enableAutoRefresh) return

    // 清除旧的定时器
    if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }

    if (!marketStatus) return

    // 根据市场状态设置不同的刷新间隔
    let refreshInterval = 0

    if (marketStatus.status === 'trading') {
      // 交易时段：每3秒刷新一次
      refreshInterval = 3000
    } else if (marketStatus.status === 'call_auction') {
      // 集合竞价：每30秒刷新一次
      refreshInterval = 30000
    } else {
      // 非交易时段：不自动刷新
      return
    }

    // 设置定时刷新
    intervalRef.current = setInterval(() => {
      doRefresh(false)
    }, refreshInterval)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [enableAutoRefresh, marketStatus, doRefresh])

  return {
    refresh: () => doRefresh(true), // 强制刷新
    lastRefresh,
    isRefreshing,
    marketStatus
  }
}
