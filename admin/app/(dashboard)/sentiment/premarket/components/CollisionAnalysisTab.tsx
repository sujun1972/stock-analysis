import { Card, CardContent } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { RefreshCwIcon, AlertTriangleIcon } from "lucide-react"
import { format } from "@/lib/date-utils"
import { ActionCommandCard } from "./ActionCommandCard"
import { AnalysisDimensions } from "./AnalysisDimensions"
import type { CollisionAnalysis } from "@/types/premarket"

interface CollisionAnalysisTabProps {
  isLoading: boolean
  collisionAnalysis: CollisionAnalysis | null
  date: Date
}

/**
 * 碰撞分析标签页组件
 * 显示行动指令和四维度分析
 */
export function CollisionAnalysisTab({
  isLoading,
  collisionAnalysis,
  date
}: CollisionAnalysisTabProps) {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          <RefreshCwIcon className="h-8 w-8 animate-spin mx-auto mb-2" />
          加载中...
        </CardContent>
      </Card>
    )
  }

  if (!collisionAnalysis) {
    return (
      <Alert>
        <AlertTriangleIcon className="h-4 w-4" />
        <AlertTitle>暂无数据</AlertTitle>
        <AlertDescription>
          {format(date, 'yyyy-MM-dd')} 暂无碰撞分析数据，请先同步盘前数据，然后点击「生成碰撞分析」按钮。
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <div className="space-y-4">
      {/* 行动指令卡片 */}
      <ActionCommandCard analysis={collisionAnalysis} />

      {/* 四维度分析 */}
      <AnalysisDimensions analysis={collisionAnalysis} />
    </div>
  )
}
