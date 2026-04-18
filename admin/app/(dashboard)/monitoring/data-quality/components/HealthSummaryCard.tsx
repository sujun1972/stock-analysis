"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend
} from 'recharts'
import type { HealthSummary } from "@/app/(dashboard)/monitoring/data-quality/types"

interface HealthSummaryCardProps {
  healthSummary: HealthSummary
  pieData: Array<{ name: string; value: number; color: string }>
}

function getStatusBadge(status: string) {
  switch (status) {
    case "healthy":
      return <Badge className="bg-green-500">健康</Badge>
    case "warning":
      return <Badge className="bg-yellow-500">警告</Badge>
    case "critical":
      return <Badge className="bg-red-500">严重</Badge>
    default:
      return <Badge>未知</Badge>
  }
}

export function HealthSummaryCard({ healthSummary, pieData }: HealthSummaryCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>系统健康状态</span>
          {getStatusBadge(healthSummary.overall_status)}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-6 lg:grid-cols-2">
          <div>
            <div className="grid grid-cols-3 gap-2 sm:gap-4 mb-4">
              <div className="text-center">
                <div className="text-xl sm:text-2xl font-bold text-green-500">
                  {healthSummary.healthy_sources}
                </div>
                <div className="text-xs text-muted-foreground">健康</div>
              </div>
              <div className="text-center">
                <div className="text-xl sm:text-2xl font-bold text-yellow-500">
                  {healthSummary.warning_sources}
                </div>
                <div className="text-xs text-muted-foreground">警告</div>
              </div>
              <div className="text-center">
                <div className="text-xl sm:text-2xl font-bold text-red-500">
                  {healthSummary.critical_sources}
                </div>
                <div className="text-xs text-muted-foreground">严重</div>
              </div>
            </div>

            {healthSummary.recommendations.length > 0 && (
              <div className="space-y-2">
                <div className="text-sm font-medium">建议：</div>
                <ul className="text-sm text-muted-foreground space-y-1">
                  {healthSummary.recommendations.map((rec, idx) => (
                    <li key={idx} className="flex items-start">
                      <span className="mr-2">•</span>
                      <span>{rec}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* 饼图在小屏幕上隐藏，或者移到下方 */}
          <div className="h-48 sm:h-64 mt-4 lg:mt-0">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="value"
                  nameKey="name"
                  cx="50%"
                  cy="50%"
                  outerRadius={60}
                  label
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
