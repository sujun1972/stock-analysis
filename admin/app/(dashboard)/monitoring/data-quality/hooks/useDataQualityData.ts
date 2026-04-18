"use client"

import { useState, useEffect, useCallback } from "react"
import type { QualityMetric, HealthSummary, QualityTrend, QualityAlert } from "@/app/(dashboard)/monitoring/data-quality/types"

export function useDataQualityData() {
  const [loading, setLoading] = useState(false)
  const [metrics, setMetrics] = useState<Record<string, QualityMetric>>({})
  const [healthSummary, setHealthSummary] = useState<HealthSummary | null>(null)
  const [trends, setTrends] = useState<Record<string, QualityTrend[]>>({})
  const [alerts, setAlerts] = useState<QualityAlert[]>([])
  const [selectedDataSource, setSelectedDataSource] = useState("all")
  const [selectedPeriod, setSelectedPeriod] = useState("7")

  // 获取实时指标
  const fetchMetrics = useCallback(async () => {
    try {
      setLoading(true)
      const response = await fetch("/api/data-quality/real-time-metrics", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setMetrics(data)
      }
    } catch (error) {
      // 静默处理，避免干扰用户
    } finally {
      setLoading(false)
    }
  }, [])

  // 获取健康摘要
  const fetchHealthSummary = useCallback(async () => {
    try {
      const response = await fetch("/api/data-quality/health-summary", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setHealthSummary(data)
      }
    } catch (error) {
      // 静默处理
    }
  }, [])

  // 获取质量趋势
  const fetchTrends = useCallback(async () => {
    try {
      const response = await fetch(`/api/data-quality/quality-trends?days=${selectedPeriod}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setTrends(data.trends)
      }
    } catch (error) {
      // 静默处理
    }
  }, [selectedPeriod])

  // 获取活跃告警
  const fetchAlerts = useCallback(async () => {
    try {
      const response = await fetch("/api/data-quality/alerts/active", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`
        }
      })
      if (response.ok) {
        const data = await response.json()
        setAlerts(data)
      }
    } catch (error) {
      // 静默处理
    }
  }, [])

  useEffect(() => {
    fetchMetrics()
    fetchHealthSummary()
    fetchAlerts()
  }, [fetchMetrics, fetchHealthSummary, fetchAlerts])

  useEffect(() => {
    fetchTrends()
  }, [fetchTrends])

  // 准备饼图数据
  const getPieData = useCallback(() => {
    if (!healthSummary) return []
    return [
      { name: "健康", value: healthSummary.healthy_sources, color: "#10b981" },
      { name: "警告", value: healthSummary.warning_sources, color: "#f59e0b" },
      { name: "严重", value: healthSummary.critical_sources, color: "#ef4444" }
    ].filter(item => item.value > 0)
  }, [healthSummary])

  // 准备趋势图数据
  const getTrendData = useCallback(() => {
    if (!selectedDataSource || selectedDataSource === "all" || !trends[selectedDataSource]) {
      // 聚合所有数据源的趋势
      const aggregated: Record<string, QualityTrend> = {}
      Object.values(trends).forEach(sourceTrends => {
        sourceTrends.forEach(trend => {
          if (!aggregated[trend.date]) {
            aggregated[trend.date] = {
              date: trend.date,
              completeness: 0,
              accuracy: 0,
              timeliness: 0
            }
          }
          aggregated[trend.date].completeness += trend.completeness
          aggregated[trend.date].accuracy += trend.accuracy
          aggregated[trend.date].timeliness += trend.timeliness
        })
      })

      const sourceCount = Object.keys(trends).length
      return Object.values(aggregated).map(trend => ({
        ...trend,
        completeness: trend.completeness / sourceCount,
        accuracy: trend.accuracy / sourceCount,
        timeliness: trend.timeliness / sourceCount
      }))
    }
    return trends[selectedDataSource]
  }, [selectedDataSource, trends])

  return {
    loading,
    metrics,
    healthSummary,
    alerts,
    selectedDataSource,
    setSelectedDataSource,
    selectedPeriod,
    setSelectedPeriod,
    fetchMetrics,
    fetchAlerts,
    getPieData,
    getTrendData,
  }
}
