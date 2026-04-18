"use client"

import { useCallback } from "react"

export function useDataQualityActions(fetchAlerts: () => Promise<void>) {
  // 确认告警
  const acknowledgeAlert = useCallback(async (alertId: number) => {
    try {
      const response = await fetch(`/api/data-quality/alerts/acknowledge/${alertId}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`
        }
      })
      if (response.ok) {
        fetchAlerts()
      }
    } catch (error) {
      // 静默处理
    }
  }, [fetchAlerts])

  // 导出报告
  const exportReport = useCallback(async (format: "json" | "html") => {
    try {
      const response = await fetch(`/api/data-quality/daily-report?format=${format}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("access_token")}`
        }
      })
      if (response.ok) {
        const blob = await response.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement("a")
        a.href = url
        a.download = `quality-report-${new Date().toISOString().split("T")[0]}.${format}`
        a.click()
      }
    } catch (error) {
      // 静默处理
    }
  }, [])

  return {
    acknowledgeAlert,
    exportReport,
  }
}
