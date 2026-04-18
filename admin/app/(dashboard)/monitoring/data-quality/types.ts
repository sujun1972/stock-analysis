export interface QualityMetric {
  data_source: string
  total_records: number
  valid_records: number
  error_count: number
  warning_count: number
  completeness: number
  accuracy: number
  timeliness: number
  last_updated: string
}

export interface HealthSummary {
  overall_status: "healthy" | "warning" | "critical"
  total_data_sources: number
  healthy_sources: number
  warning_sources: number
  critical_sources: number
  recommendations: string[]
}

export interface QualityTrend {
  date: string
  completeness: number
  accuracy: number
  timeliness: number
}

export interface QualityAlert {
  id: number
  severity: "low" | "medium" | "high"
  data_source: string
  message: string
  created_at: string
  acknowledged: boolean
}

export const COLORS = {
  healthy: "#10b981",
  warning: "#f59e0b",
  critical: "#ef4444",
  primary: "#3b82f6"
}
