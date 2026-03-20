import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { PlayIcon, Clock } from "lucide-react"
import type { CollisionAnalysis } from "@/types/premarket"

interface ActionCommandCardProps {
  analysis: CollisionAnalysis
}

/**
 * 行动指令卡片组件
 * 显示AI生成的早盘竞价行动指令和元数据
 */
export function ActionCommandCard({ analysis }: ActionCommandCardProps) {
  return (
    <Card className="border-2 border-blue-500">
      <CardHeader className="bg-blue-50 dark:bg-blue-900/20">
        <CardTitle className="flex items-center gap-2">
          <PlayIcon className="h-5 w-5 text-blue-500" />
          早盘竞价行动指令
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-6">
        <div className="bg-gray-50 dark:bg-gray-900 p-6 rounded-lg">
          <pre className="whitespace-pre-wrap text-lg leading-relaxed font-medium">
            {analysis.action_command}
          </pre>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-sm text-muted-foreground mt-4 pt-4 border-t">
          <div className="flex items-center gap-1">
            <span className="font-medium">AI模型:</span>
            <Badge variant="outline" className="text-xs">
              {analysis.ai_provider} / {analysis.ai_model}
            </Badge>
          </div>
          <div className="flex items-center gap-1">
            <span className="font-medium">Token消耗:</span>
            <span>{analysis.tokens_used}</span>
          </div>
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            <span className="font-medium">生成耗时:</span>
            <span>{analysis.generation_time}s</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
