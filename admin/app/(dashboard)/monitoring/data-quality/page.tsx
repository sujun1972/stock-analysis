"use client"

import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { PageHeader } from "@/components/common/PageHeader"
import { Download, RefreshCw } from "lucide-react"
import { useDataQualityData, useDataQualityActions } from "@/app/(dashboard)/monitoring/data-quality/hooks"
import {
  HealthSummaryCard,
  QualityTrendsChart,
  DataSourceMetrics,
  ActiveAlerts,
} from "@/app/(dashboard)/monitoring/data-quality/components"

export default function DataQualityPage() {
  const {
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
  } = useDataQualityData()

  const { acknowledgeAlert, exportReport } = useDataQualityActions(fetchAlerts)

  return (
    <div className="space-y-6">
      <PageHeader
        title="数据质量监控"
        description="实时监控数据质量指标，确保数据准确性和完整性"
        actions={
          <div className="flex flex-wrap gap-2">
            {/* 移动端：使用下拉菜单整合导出选项 */}
            <div className="sm:hidden">
              <Select onValueChange={(value) => exportReport(value as "json" | "html")}>
                <SelectTrigger className="w-[100px]">
                  <Download className="h-4 w-4 mr-1" />
                  <SelectValue placeholder="导出" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="json">JSON格式</SelectItem>
                  <SelectItem value="html">HTML格式</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {/* 桌面端：显示完整按钮 */}
            <div className="hidden sm:flex gap-2">
              <Button variant="outline" size="sm" onClick={() => exportReport("json")}>
                <Download className="h-4 w-4 mr-1" />
                导出JSON
              </Button>
              <Button variant="outline" size="sm" onClick={() => exportReport("html")}>
                <Download className="h-4 w-4 mr-1" />
                导出HTML
              </Button>
            </div>
            <Button size="sm" onClick={fetchMetrics} disabled={loading}>
              <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
              <span className="hidden sm:inline">刷新</span>
            </Button>
          </div>
        }
      />

      {/* 健康状态摘要 */}
      {healthSummary && (
        <HealthSummaryCard
          healthSummary={healthSummary}
          pieData={getPieData()}
        />
      )}

      {/* 质量趋势 */}
      <QualityTrendsChart
        trendData={getTrendData()}
        dataSources={Object.keys(metrics)}
        selectedDataSource={selectedDataSource}
        onDataSourceChange={setSelectedDataSource}
        selectedPeriod={selectedPeriod}
        onPeriodChange={setSelectedPeriod}
      />

      {/* 数据源指标 */}
      <DataSourceMetrics metrics={metrics} />

      {/* 活跃告警 */}
      <ActiveAlerts
        alerts={alerts}
        onAcknowledge={acknowledgeAlert}
      />
    </div>
  )
}
