import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { AlertTriangleIcon } from "lucide-react"
import { cn } from "@/lib/utils"
import type { PremarketNews } from "@/types/premarket"

interface NewsListTabProps {
  newsList: PremarketNews[]
}

// 获取重要性级别颜色
const getImportanceColor = (level: string) => {
  switch (level) {
    case "critical": return "bg-red-500 text-white"
    case "high": return "bg-orange-500 text-white"
    case "medium": return "bg-yellow-500 text-white"
    default: return "bg-gray-300 text-gray-700"
  }
}

/**
 * 盘前新闻标签页组件
 * 显示盘前核心新闻列表
 */
export function NewsListTab({ newsList }: NewsListTabProps) {
  if (newsList.length === 0) {
    return (
      <Alert>
        <AlertTriangleIcon className="h-4 w-4" />
        <AlertTitle>暂无数据</AlertTitle>
        <AlertDescription>
          请先点击「同步盘前数据」按钮获取盘前核心新闻
        </AlertDescription>
      </Alert>
    )
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>盘前核心新闻 ({newsList.length}条)</CardTitle>
        <CardDescription>22:00-8:00的重要快讯，已通过关键词过滤</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {newsList.map((news) => (
            <div
              key={news.id}
              className="border rounded-lg p-3 sm:p-4 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
            >
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 mb-2">
                <div className="flex flex-wrap items-center gap-2">
                  <Badge className={cn(getImportanceColor(news.importance_level), "text-xs")}>
                    {news.importance_level === 'critical' ? '核弹级' :
                     news.importance_level === 'high' ? '高' : '中'}
                  </Badge>
                  <span className="text-xs text-muted-foreground">
                    {new Date(news.news_time).toLocaleString('zh-CN', {
                      month: '2-digit',
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit'
                    })}
                  </span>
                  <Badge variant="outline" className="text-xs">{news.source}</Badge>
                </div>
              </div>
              <div className="font-medium text-sm sm:text-base mb-2 line-clamp-2">{news.title}</div>
              <div className="text-xs sm:text-sm text-muted-foreground mb-2 line-clamp-3">{news.content}</div>
              <div className="flex flex-wrap gap-1">
                {news.keywords.slice(0, 5).map((keyword, idx) => (
                  <Badge key={idx} variant="secondary" className="text-xs py-0 px-1">
                    {keyword}
                  </Badge>
                ))}
                {news.keywords.length > 5 && (
                  <Badge variant="secondary" className="text-xs py-0 px-1">
                    +{news.keywords.length - 5}
                  </Badge>
                )}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
