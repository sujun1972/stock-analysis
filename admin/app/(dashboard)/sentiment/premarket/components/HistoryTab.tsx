import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { AlertTriangleIcon } from "lucide-react"
import type { AnalysisHistory } from "@/types/premarket"

interface HistoryTabProps {
  history: AnalysisHistory[]
  onHistoryClick: (record: AnalysisHistory) => void
}

/**
 * 历史记录标签页组件
 * 显示最近10条碰撞分析历史记录
 */
export function HistoryTab({ history, onHistoryClick }: HistoryTabProps) {
  if (history.length === 0) {
    return (
      <Alert>
        <AlertTriangleIcon className="h-4 w-4" />
        <AlertTitle>暂无数据</AlertTitle>
        <AlertDescription>
          暂无历史碰撞分析记录
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>碰撞分析历史记录</CardTitle>
        <CardDescription>最近10条记录</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {history.map((record) => (
            <div
              key={record.trade_date}
              className="border rounded-lg p-3 sm:p-4 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors cursor-pointer"
              onClick={() => onHistoryClick(record)}
            >
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-sm sm:text-base">{record.trade_date}</span>
                  <Badge variant={record.status === 'success' ? 'default' : 'destructive'} className="text-xs">
                    {record.status === 'success' ? '成功' : '失败'}
                  </Badge>
                </div>
                <div className="text-xs text-muted-foreground">
                  <span className="block sm:inline">{record.ai_provider}</span>
                  <span className="hidden sm:inline"> | </span>
                  <span className="block sm:inline">{record.tokens_used} tokens</span>
                  <span className="hidden sm:inline"> | </span>
                  <span className="block sm:inline">{record.generation_time}s</span>
                </div>
              </div>
              <div className="bg-gray-50 dark:bg-gray-900 p-2 sm:p-3 rounded text-xs sm:text-sm line-clamp-3">
                {record.action_command}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
