"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import {
  AlertCircle,
  XCircle,
  AlertTriangle
} from "lucide-react"
import { format } from "date-fns"
import type { QualityAlert } from "@/app/(dashboard)/monitoring/data-quality/types"

interface ActiveAlertsProps {
  alerts: QualityAlert[]
  onAcknowledge: (alertId: number) => void
}

function getAlertIcon(severity: string) {
  switch (severity) {
    case "high":
      return <XCircle className="h-4 w-4 text-red-500" />
    case "medium":
      return <AlertTriangle className="h-4 w-4 text-yellow-500" />
    case "low":
      return <AlertCircle className="h-4 w-4 text-blue-500" />
    default:
      return <AlertCircle className="h-4 w-4" />
  }
}

export function ActiveAlerts({ alerts, onAcknowledge }: ActiveAlertsProps) {
  if (alerts.length === 0) return null

  return (
    <Card>
      <CardHeader>
        <CardTitle>活跃告警</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {alerts.map(alert => (
            <Alert key={alert.id} className="p-3 sm:p-4">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
                <div className="flex items-start sm:items-center gap-2">
                  {getAlertIcon(alert.severity)}
                  <div className="flex-1 min-w-0">
                    <AlertTitle className="text-sm break-all">
                      {alert.data_source}
                    </AlertTitle>
                    <AlertDescription className="text-xs mt-1">
                      <div className="break-all">{alert.message}</div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {format(new Date(alert.created_at), "MM-dd HH:mm")}
                      </div>
                    </AlertDescription>
                  </div>
                </div>
                {!alert.acknowledged && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onAcknowledge(alert.id)}
                    className="self-end sm:self-auto"
                  >
                    确认
                  </Button>
                )}
              </div>
            </Alert>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
