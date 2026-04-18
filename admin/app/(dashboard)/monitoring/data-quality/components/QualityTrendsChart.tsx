"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Legend
} from 'recharts'
import { format } from "date-fns"
import { COLORS } from "@/app/(dashboard)/monitoring/data-quality/types"
import type { QualityTrend } from "@/app/(dashboard)/monitoring/data-quality/types"

interface QualityTrendsChartProps {
  trendData: QualityTrend[]
  dataSources: string[]
  selectedDataSource: string
  onDataSourceChange: (value: string) => void
  selectedPeriod: string
  onPeriodChange: (value: string) => void
}

export function QualityTrendsChart({
  trendData,
  dataSources,
  selectedDataSource,
  onDataSourceChange,
  selectedPeriod,
  onPeriodChange,
}: QualityTrendsChartProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <CardTitle>质量趋势</CardTitle>
          <div className="flex flex-col sm:flex-row gap-2 sm:gap-4">
            <Select value={selectedDataSource} onValueChange={onDataSourceChange}>
              <SelectTrigger className="w-full sm:w-48">
                <SelectValue placeholder="选择数据源" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">所有数据源</SelectItem>
                {dataSources.map(source => (
                  <SelectItem key={source} value={source}>
                    {source}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={selectedPeriod} onValueChange={onPeriodChange}>
              <SelectTrigger className="w-full sm:w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="7">7天</SelectItem>
                <SelectItem value="14">14天</SelectItem>
                <SelectItem value="30">30天</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>
      <CardContent className="px-2 sm:px-6">
        <div className="h-64 sm:h-80">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={trendData} margin={{ top: 5, right: 5, left: -20, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tickFormatter={(value) => format(new Date(value), "MM-dd")}
                tick={{ fontSize: 12 }}
              />
              <YAxis domain={[0, 100]} tick={{ fontSize: 12 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Line
                type="monotone"
                dataKey="completeness"
                stroke={COLORS.healthy}
                name="完整性"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="accuracy"
                stroke={COLORS.primary}
                name="准确性"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="timeliness"
                stroke={COLORS.warning}
                name="及时性"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  )
}
