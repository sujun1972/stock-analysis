"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { TrendingUpIcon, TrendingDownIcon, CheckCircle2Icon } from "lucide-react"
import { cn } from "@/lib/utils"
import { MarkdownRenderer } from "@/components/common/MarkdownRenderer"
import type { AIAnalysisResult } from "../hooks/useAiAnalysisData"

/** 获取空间级别的颜色 */
const getSpaceLevelColor = (level?: string) => {
  switch (level) {
    case "超高空间": return "bg-red-500 text-white"
    case "高空间": return "bg-orange-500 text-white"
    case "中等空间": return "bg-yellow-500 text-white"
    case "低空间": return "bg-gray-500 text-white"
    default: return "bg-gray-300 text-gray-700"
  }
}

/** 获取策略的颜色 */
const getStrategyColor = (strategy?: string) => {
  switch (strategy) {
    case "激进进攻": return "bg-red-500 text-white"
    case "稳健参与": return "bg-blue-500 text-white"
    case "防守为主": return "bg-yellow-500 text-white"
    case "空仓观望": return "bg-gray-500 text-white"
    default: return "bg-gray-300 text-gray-700"
  }
}

interface AnalysisTabsProps {
  analysisData: AIAnalysisResult
}

export function AnalysisTabs({ analysisData }: AnalysisTabsProps) {
  return (
    <Tabs defaultValue="space" className="space-y-4">
      <TabsList className="grid w-full grid-cols-4">
        <TabsTrigger value="space">🚀 看空间</TabsTrigger>
        <TabsTrigger value="sentiment">🔥 看情绪</TabsTrigger>
        <TabsTrigger value="capital">💰 看暗流</TabsTrigger>
        <TabsTrigger value="tactics">📝 明日战术</TabsTrigger>
      </TabsList>

      {/* 看空间 */}
      <TabsContent value="space">
        <SpaceTab data={analysisData.space_analysis} />
      </TabsContent>

      {/* 看情绪 */}
      <TabsContent value="sentiment">
        <SentimentTab data={analysisData.sentiment_analysis} />
      </TabsContent>

      {/* 看暗流 */}
      <TabsContent value="capital">
        <CapitalTab data={analysisData.capital_flow_analysis} />
      </TabsContent>

      {/* 明日战术 */}
      <TabsContent value="tactics">
        <TacticsTab data={analysisData.tomorrow_tactics} />
      </TabsContent>
    </Tabs>
  )
}

/* ── 看空间 Tab ── */
function SpaceTab({ data }: { data: AIAnalysisResult['space_analysis'] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>【看空间】最高连板分析</CardTitle>
        <CardDescription>今日最高连板是谁？代表什么题材？空间是否被打开？</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {data ? (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-muted p-4 rounded-lg">
                <div className="text-sm text-muted-foreground mb-1">主线龙头</div>
                <div className="font-bold">
                  {data.max_continuous_stock?.name || '-'}
                </div>
                <div className="text-xs text-muted-foreground">
                  {data.max_continuous_stock?.code || '-'}
                </div>
              </div>

              <div className="bg-muted p-4 rounded-lg">
                <div className="text-sm text-muted-foreground mb-1">连板天数</div>
                <div className="text-2xl font-bold text-red-500">
                  {data.max_continuous_stock?.days || 0}
                  <span className="text-sm ml-1">天</span>
                </div>
              </div>

              <div className="bg-muted p-4 rounded-lg">
                <div className="text-sm text-muted-foreground mb-1">所属题材</div>
                <Badge variant="secondary" className="mt-1">
                  {data.theme || '-'}
                </Badge>
              </div>

              <div className="bg-muted p-4 rounded-lg">
                <div className="text-sm text-muted-foreground mb-1">空间判断</div>
                <Badge className={cn("mt-1", getSpaceLevelColor(data.space_level))}>
                  {data.space_level || '-'}
                </Badge>
              </div>
            </div>

            <div className="bg-blue-50 dark:bg-blue-900/10 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
              <div className="font-medium mb-2 flex items-center gap-2">
                <TrendingUpIcon className="h-4 w-4 text-blue-500" />
                AI分析
              </div>
              <MarkdownRenderer content={data.analysis || '暂无分析'} />
            </div>
          </>
        ) : (
          <Alert>
            <AlertDescription>暂无空间分析数据</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  )
}

/* ── 看情绪 Tab ── */
function SentimentTab({ data }: { data: AIAnalysisResult['sentiment_analysis'] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>【看情绪】赚钱效应分析</CardTitle>
        <CardDescription>结合炸板率和跌停数，今日接力资金赚钱效应如何？是该进攻还是防守？</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {data ? (
          <>
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-muted p-6 rounded-lg text-center">
                <div className="text-sm text-muted-foreground mb-2">赚钱效应</div>
                <div className="text-3xl font-bold">
                  {data.money_making_effect || '-'}
                </div>
              </div>

              <div className="bg-muted p-6 rounded-lg text-center">
                <div className="text-sm text-muted-foreground mb-2">操作策略</div>
                <Badge className={cn("text-lg py-2 px-4", getStrategyColor(data.strategy))}>
                  {data.strategy || '-'}
                </Badge>
              </div>
            </div>

            <div className="bg-orange-50 dark:bg-orange-900/10 p-4 rounded-lg border border-orange-200 dark:border-orange-800">
              <div className="font-medium mb-2 flex items-center gap-2">
                <TrendingDownIcon className="h-4 w-4 text-orange-500" />
                推理分析
              </div>
              <MarkdownRenderer content={data.reasoning || '暂无推理'} />
            </div>
          </>
        ) : (
          <Alert>
            <AlertDescription>暂无情绪分析数据</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  )
}

/* ── 看暗流 Tab ── */
function CapitalTab({ data }: { data: AIAnalysisResult['capital_flow_analysis'] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>【看暗流】资金动向分析</CardTitle>
        <CardDescription>顶级游资今天主攻了哪个方向？机构在建仓什么？</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {data ? (
          <>
            <div className="grid md:grid-cols-2 gap-4">
              {/* 游资方向 */}
              <div className="bg-red-50 dark:bg-red-900/10 p-4 rounded-lg border border-red-200 dark:border-red-800">
                <div className="font-medium mb-3 text-red-700 dark:text-red-400">游资方向</div>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">主攻题材：</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {data.hot_money_direction?.themes?.map((theme, idx) => (
                        <Badge key={idx} variant="destructive">{theme}</Badge>
                      ))}
                    </div>
                  </div>
                  <div>
                    <span className="text-muted-foreground">集中度：</span>
                    <Badge variant="outline" className="ml-2">
                      {data.hot_money_direction?.concentration || '-'}
                    </Badge>
                  </div>
                </div>
              </div>

              {/* 机构方向 */}
              <div className="bg-green-50 dark:bg-green-900/10 p-4 rounded-lg border border-green-200 dark:border-green-800">
                <div className="font-medium mb-3 text-green-700 dark:text-green-400">机构方向</div>
                <div className="space-y-2 text-sm">
                  <div>
                    <span className="text-muted-foreground">关注板块：</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {data.institution_direction?.sectors?.map((sector, idx) => (
                        <Badge key={idx} className="bg-green-500 hover:bg-green-600">{sector}</Badge>
                      ))}
                    </div>
                  </div>
                  <div>
                    <span className="text-muted-foreground">风格：</span>
                    <Badge variant="outline" className="ml-2">
                      {data.institution_direction?.style || '-'}
                    </Badge>
                  </div>
                </div>
              </div>
            </div>

            {/* 资金共识 */}
            <Alert>
              <CheckCircle2Icon className="h-4 w-4" />
              <AlertTitle>资金共识</AlertTitle>
              <AlertDescription className="font-medium">
                {data.capital_consensus || '-'}
              </AlertDescription>
            </Alert>

            {/* 详细分析 */}
            <div className="bg-purple-50 dark:bg-purple-900/10 p-4 rounded-lg border border-purple-200 dark:border-purple-800">
              <div className="font-medium mb-2">详细分析</div>
              <MarkdownRenderer content={data.analysis || '暂无分析'} />
            </div>
          </>
        ) : (
          <Alert>
            <AlertDescription>暂无资金动向分析数据</AlertDescription>
          </Alert>
        )}
      </CardContent>
    </Card>
  )
}

/* ── 明日战术 Tab ── */
function TacticsTab({ data }: { data: AIAnalysisResult['tomorrow_tactics'] }) {
  return (
    <div className="space-y-4">
      {data ? (
        <>
          {/* 集合竞价 */}
          <Card>
            <CardHeader>
              <CardTitle>🔔 集合竞价策略（9:15-9:25）</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <div className="font-medium text-sm mb-2 text-green-600">✅ 参与条件</div>
                <div className="bg-green-50 dark:bg-green-900/10 p-3 rounded text-sm">
                  {data.call_auction_tactics?.participate_conditions || '暂无'}
                </div>
              </div>
              <div>
                <div className="font-medium text-sm mb-2 text-red-600">❌ 禁止条件</div>
                <div className="bg-red-50 dark:bg-red-900/10 p-3 rounded text-sm">
                  {data.call_auction_tactics?.avoid_conditions || '暂无'}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 开盘半小时 */}
          <Card>
            <CardHeader>
              <CardTitle>🕘 开盘半小时策略（9:30-10:00）</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div>
                <div className="font-medium text-sm mb-2">📉 低吸机会</div>
                <div className="bg-blue-50 dark:bg-blue-900/10 p-3 rounded text-sm">
                  {data.opening_half_hour_tactics?.low_buy_opportunities || '暂无'}
                </div>
              </div>
              <div>
                <div className="font-medium text-sm mb-2">📈 追涨机会</div>
                <div className="bg-orange-50 dark:bg-orange-900/10 p-3 rounded text-sm">
                  {data.opening_half_hour_tactics?.chase_opportunities || '暂无'}
                </div>
              </div>
              <div>
                <div className="font-medium text-sm mb-2">🔍 观望信号</div>
                <div className="bg-gray-50 dark:bg-gray-900/10 p-3 rounded text-sm">
                  {data.opening_half_hour_tactics?.wait_signals || '暂无'}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 买入和止损条件 */}
          <div className="grid md:grid-cols-2 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">✅ 买入条件</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm">
                  {data.buy_conditions?.map((condition, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-green-500 mt-0.5">•</span>
                      <span>{condition}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">🛑 止损条件</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2 text-sm">
                  {data.stop_loss_conditions?.map((condition, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-red-500 mt-0.5">•</span>
                      <span>{condition}</span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          </div>
        </>
      ) : (
        <Alert>
          <AlertDescription>暂无明日战术数据</AlertDescription>
        </Alert>
      )}
    </div>
  )
}
