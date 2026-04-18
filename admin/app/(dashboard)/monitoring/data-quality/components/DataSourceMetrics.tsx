"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { format } from "date-fns"
import type { QualityMetric } from "@/app/(dashboard)/monitoring/data-quality/types"

interface DataSourceMetricsProps {
  metrics: Record<string, QualityMetric>
}

export function DataSourceMetrics({ metrics }: DataSourceMetricsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>数据源质量指标</CardTitle>
      </CardHeader>
      <CardContent>
        {/* 移动端使用单列布局，平板使用2列，桌面使用3列 */}
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 xl:grid-cols-3">
          {Object.entries(metrics).map(([source, metric]) => (
            <Card key={source} className="overflow-hidden">
              <CardHeader className="pb-3 px-4 sm:px-6">
                <CardTitle className="text-sm font-medium break-all">
                  {source}
                </CardTitle>
                <CardDescription className="text-xs">
                  更新: {format(new Date(metric.last_updated), "MM-dd HH:mm")}
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2 px-4 sm:px-6">
                {/* 移动端使用更紧凑的布局 */}
                <div className="grid grid-cols-2 gap-2 text-xs sm:text-sm">
                  <div className="space-y-1">
                    <div className="text-muted-foreground">总记录</div>
                    <div className="font-medium">{metric.total_records.toLocaleString()}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-muted-foreground">有效</div>
                    <div className="font-medium text-green-600">
                      {metric.valid_records.toLocaleString()}
                    </div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-muted-foreground">错误</div>
                    <div className="font-medium text-red-600">{metric.error_count}</div>
                  </div>
                  <div className="space-y-1">
                    <div className="text-muted-foreground">警告</div>
                    <div className="font-medium text-yellow-600">{metric.warning_count}</div>
                  </div>
                </div>

                <div className="space-y-2 pt-2 border-t">
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span>完整性</span>
                      <span>{metric.completeness}%</span>
                    </div>
                    <Progress value={metric.completeness} className="h-1" />
                  </div>
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span>准确性</span>
                      <span>{metric.accuracy}%</span>
                    </div>
                    <Progress value={metric.accuracy} className="h-1" />
                  </div>
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span>及时性</span>
                      <span>{metric.timeliness}%</span>
                    </div>
                    <Progress value={metric.timeliness} className="h-1" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
