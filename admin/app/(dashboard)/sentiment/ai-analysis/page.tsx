"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { CalendarIcon, PlayIcon, RefreshCwIcon, TrendingUpIcon, TrendingDownIcon, AlertTriangleIcon, CheckCircle2Icon, Clock } from "lucide-react"
import { format } from "date-fns"
import { zhCN } from "date-fns/locale"
import { cn } from "@/lib/utils"
import { apiClient } from "@/lib/api-client"
import { toast } from "sonner"

interface AIProvider {
  id: number
  provider: string
  display_name: string
  is_active: boolean
  is_default: boolean
  model_name: string
}

interface AIAnalysisResult {
  trade_date: string
  space_analysis?: {
    max_continuous_stock?: {
      code: string
      name: string
      days: number
    }
    theme?: string
    space_level?: string
    analysis?: string
  }
  sentiment_analysis?: {
    money_making_effect?: string
    strategy?: string
    reasoning?: string
  }
  capital_flow_analysis?: {
    hot_money_direction?: {
      themes?: string[]
      stocks?: string[]
      concentration?: string
    }
    institution_direction?: {
      sectors?: string[]
      style?: string
    }
    capital_consensus?: string
    analysis?: string
  }
  tomorrow_tactics?: {
    call_auction_tactics?: {
      participate_conditions?: string
      avoid_conditions?: string
    }
    opening_half_hour_tactics?: {
      low_buy_opportunities?: string
      chase_opportunities?: string
      wait_signals?: string
    }
    buy_conditions?: string[]
    stop_loss_conditions?: string[]
  }
  full_report?: string
  ai_provider?: string
  ai_model?: string
  tokens_used?: number
  generation_time?: number
  status?: string
  created_at?: string
}

export default function SentimentAIAnalysisPage() {
  const [date, setDate] = useState<Date>(new Date())
  const [aiProvider, setAiProvider] = useState<string>("")
  const [aiProviders, setAiProviders] = useState<AIProvider[]>([])
  const [analysisData, setAnalysisData] = useState<AIAnalysisResult | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingProviders, setIsLoadingProviders] = useState(true)

  // 格式化日期为 YYYY-MM-DD
  const formatDate = (d: Date) => format(d, "yyyy-MM-dd")

  // 加载分析数据
  const loadAnalysis = async (targetDate?: Date) => {
    const dateStr = formatDate(targetDate || date)
    setIsLoading(true)

    try {
      const response = await apiClient.get(`/api/sentiment/ai-analysis/${dateStr}`)

      if (response.code === 200 && response.data) {
        setAnalysisData(response.data)
      } else if (response.code === 404) {
        // 暂无数据是正常情况，静默处理，不显示错误提示
        setAnalysisData(null)
      } else {
        setAnalysisData(null)
        if (response.message) {
          console.info(`${dateStr}: ${response.message}`)
        }
      }
    } catch (error: any) {
      // 仅对网络错误或服务器异常显示错误提示，404则静默处理
      setAnalysisData(null)
      if (error.response?.status !== 404) {
        toast.error("加载失败：" + (error.response?.data?.detail || error.message))
      }
    } finally {
      setIsLoading(false)
    }
  }

  // 生成AI分析
  const handleGenerate = async () => {
    const dateStr = formatDate(date)
    setIsGenerating(true)

    // 显示加载提示并保存 ID，用于后续关闭避免 toast 重叠
    const loadingToastId = toast.info("正在调用AI生成分析，请稍候...")

    try {
      const response = await apiClient.post("/api/sentiment/ai-analysis/generate", null, {
        params: { date: dateStr, provider: aiProvider }
      })

      // 先关闭加载提示，再显示结果，确保 toast 顺序展示不重叠
      toast.dismiss(loadingToastId)

      if (response.code === 200) {
        toast.success("AI分析生成成功")
        loadAnalysis()
      } else {
        toast.error(response.message || "生成失败")
      }
    } catch (error: any) {
      toast.dismiss(loadingToastId)
      toast.error("生成失败：" + (error.response?.data?.detail || error.message))
    } finally {
      setIsGenerating(false)
    }
  }

  // 加载AI提供商列表
  const loadProviders = async () => {
    setIsLoadingProviders(true)
    try {
      // apiClient.get() 已经返回 response.data，所以这里直接得到的是数据
      const data = await apiClient.get('/api/ai-strategy/providers')

      // 确保是数组
      if (!Array.isArray(data)) {
        console.error('AI Providers data is not an array:', data)
        toast.error("AI配置数据格式错误")
        setAiProviders([])
        return
      }

      const providers = data.filter((p: AIProvider) => p.is_active)

      setAiProviders(providers)

      // 设置默认提供商
      const defaultProvider = providers.find((p: AIProvider) => p.is_default)
      if (defaultProvider) {
        setAiProvider(defaultProvider.provider)
      } else if (providers.length > 0) {
        setAiProvider(providers[0].provider)
      }
    } catch (error: any) {
      console.error('Load AI Providers Error:', error)
      toast.error("加载AI配置失败：" + (error.response?.data?.detail || error.message))
      setAiProviders([])
    } finally {
      setIsLoadingProviders(false)
    }
  }

  // 初始加载
  useEffect(() => {
    loadProviders()
    loadAnalysis()
  }, [])

  // 日期变化时加载
  const handleDateChange = (newDate: Date | undefined) => {
    if (newDate) {
      setDate(newDate)
      loadAnalysis(newDate)
    }
  }

  // 获取空间级别的颜色
  const getSpaceLevelColor = (level?: string) => {
    switch (level) {
      case "超高空间": return "bg-red-500 text-white"
      case "高空间": return "bg-orange-500 text-white"
      case "中等空间": return "bg-yellow-500 text-white"
      case "低空间": return "bg-gray-500 text-white"
      default: return "bg-gray-300 text-gray-700"
    }
  }

  // 获取策略的颜色
  const getStrategyColor = (strategy?: string) => {
    switch (strategy) {
      case "激进进攻": return "bg-red-500 text-white"
      case "稳健参与": return "bg-blue-500 text-white"
      case "防守为主": return "bg-yellow-500 text-white"
      case "空仓观望": return "bg-gray-500 text-white"
      default: return "bg-gray-300 text-gray-700"
    }
  }

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">市场情绪AI分析</h1>
          <p className="text-muted-foreground mt-1">
            基于LLM的四维度盘后情绪深度分析（看空间、看情绪、看暗流、明日战术）
          </p>
        </div>
      </div>

      {/* 控制面板 */}
      <Card>
        <CardHeader>
          <CardTitle>分析控制面板</CardTitle>
          <CardDescription>选择日期和AI提供商，生成或查看AI分析报告</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-4">
            {/* 日期选择 */}
            <div className="flex-1 min-w-[200px]">
              <label className="text-sm font-medium mb-2 block">分析日期</label>
              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    variant="outline"
                    className={cn(
                      "w-full justify-start text-left font-normal",
                      !date && "text-muted-foreground"
                    )}
                  >
                    <CalendarIcon className="mr-2 h-4 w-4" />
                    {date ? format(date, "PPP", { locale: zhCN }) : "选择日期"}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="start">
                  <Calendar
                    mode="single"
                    selected={date}
                    onSelect={handleDateChange}
                    initialFocus
                    locale={zhCN}
                  />
                </PopoverContent>
              </Popover>
            </div>

            {/* AI提供商选择 */}
            <div className="flex-1 min-w-[200px]">
              <label className="text-sm font-medium mb-2 block">AI提供商</label>
              <Select value={aiProvider} onValueChange={setAiProvider} disabled={isLoadingProviders}>
                <SelectTrigger>
                  <SelectValue placeholder={isLoadingProviders ? "加载中..." : "选择AI提供商"} />
                </SelectTrigger>
                <SelectContent>
                  {aiProviders.length === 0 ? (
                    <div className="p-2 text-sm text-muted-foreground text-center">
                      暂无可用配置，请先在设置中配置AI
                    </div>
                  ) : (
                    aiProviders.map((provider) => (
                      <SelectItem key={provider.id} value={provider.provider}>
                        {provider.display_name} {provider.is_default && "(默认)"}
                        <span className="text-xs text-muted-foreground ml-2">
                          {provider.model_name}
                        </span>
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
              {aiProviders.length === 0 && !isLoadingProviders && (
                <p className="text-xs text-amber-600 mt-1">
                  ⚠️ 请先在 <a href="/settings/ai-config" className="underline">系统设置 → AI配置</a> 中添加AI提供商
                </p>
              )}
            </div>

            {/* 操作按钮 */}
            <div className="flex gap-2 items-end">
              <Button
                onClick={handleGenerate}
                disabled={isGenerating || aiProviders.length === 0}
                className="min-w-[120px]"
              >
                {isGenerating ? (
                  <>
                    <RefreshCwIcon className="mr-2 h-4 w-4 animate-spin" />
                    生成中...
                  </>
                ) : (
                  <>
                    <PlayIcon className="mr-2 h-4 w-4" />
                    生成分析
                  </>
                )}
              </Button>

              <Button
                variant="outline"
                onClick={() => loadAnalysis()}
                disabled={isLoading}
              >
                <RefreshCwIcon className={cn("mr-2 h-4 w-4", isLoading && "animate-spin")} />
                刷新
              </Button>
            </div>
          </div>

          {/* 元信息 */}
          {analysisData && (
            <div className="flex flex-wrap gap-4 text-sm text-muted-foreground pt-4 border-t">
              <div className="flex items-center gap-1">
                <span className="font-medium">AI模型:</span>
                <Badge variant="outline">{analysisData.ai_provider} / {analysisData.ai_model}</Badge>
              </div>
              <div className="flex items-center gap-1">
                <span className="font-medium">Token消耗:</span>
                <span>{analysisData.tokens_used || 0}</span>
              </div>
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                <span className="font-medium">生成耗时:</span>
                <span>{analysisData.generation_time || 0}s</span>
              </div>
              <div className="flex items-center gap-1">
                <span className="font-medium">生成时间:</span>
                <span>{analysisData.created_at ? new Date(analysisData.created_at).toLocaleString('zh-CN') : '-'}</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 分析结果展示 */}
      {isLoading ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <RefreshCwIcon className="h-8 w-8 animate-spin mx-auto mb-2" />
            加载中...
          </CardContent>
        </Card>
      ) : !analysisData ? (
        <Alert>
          <AlertTriangleIcon className="h-4 w-4" />
          <AlertTitle>暂无数据</AlertTitle>
          <AlertDescription>
            {formatDate(date)} 暂无AI分析数据，请点击"生成分析"按钮创建分析报告。
          </AlertDescription>
        </Alert>
      ) : (
        <Tabs defaultValue="space" className="space-y-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="space">🚀 看空间</TabsTrigger>
            <TabsTrigger value="sentiment">🔥 看情绪</TabsTrigger>
            <TabsTrigger value="capital">💰 看暗流</TabsTrigger>
            <TabsTrigger value="tactics">📝 明日战术</TabsTrigger>
          </TabsList>

          {/* 看空间 */}
          <TabsContent value="space">
            <Card>
              <CardHeader>
                <CardTitle>【看空间】最高连板分析</CardTitle>
                <CardDescription>今日最高连板是谁？代表什么题材？空间是否被打开？</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {analysisData.space_analysis ? (
                  <>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="bg-muted p-4 rounded-lg">
                        <div className="text-sm text-muted-foreground mb-1">主线龙头</div>
                        <div className="font-bold">
                          {analysisData.space_analysis.max_continuous_stock?.name || '-'}
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {analysisData.space_analysis.max_continuous_stock?.code || '-'}
                        </div>
                      </div>

                      <div className="bg-muted p-4 rounded-lg">
                        <div className="text-sm text-muted-foreground mb-1">连板天数</div>
                        <div className="text-2xl font-bold text-red-500">
                          {analysisData.space_analysis.max_continuous_stock?.days || 0}
                          <span className="text-sm ml-1">天</span>
                        </div>
                      </div>

                      <div className="bg-muted p-4 rounded-lg">
                        <div className="text-sm text-muted-foreground mb-1">所属题材</div>
                        <Badge variant="secondary" className="mt-1">
                          {analysisData.space_analysis.theme || '-'}
                        </Badge>
                      </div>

                      <div className="bg-muted p-4 rounded-lg">
                        <div className="text-sm text-muted-foreground mb-1">空间判断</div>
                        <Badge className={cn("mt-1", getSpaceLevelColor(analysisData.space_analysis.space_level))}>
                          {analysisData.space_analysis.space_level || '-'}
                        </Badge>
                      </div>
                    </div>

                    <div className="bg-blue-50 dark:bg-blue-900/10 p-4 rounded-lg border border-blue-200 dark:border-blue-800">
                      <div className="font-medium mb-2 flex items-center gap-2">
                        <TrendingUpIcon className="h-4 w-4 text-blue-500" />
                        AI分析
                      </div>
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">
                        {analysisData.space_analysis.analysis || '暂无分析'}
                      </p>
                    </div>
                  </>
                ) : (
                  <Alert>
                    <AlertDescription>暂无空间分析数据</AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* 看情绪 */}
          <TabsContent value="sentiment">
            <Card>
              <CardHeader>
                <CardTitle>【看情绪】赚钱效应分析</CardTitle>
                <CardDescription>结合炸板率和跌停数，今日接力资金赚钱效应如何？是该进攻还是防守？</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {analysisData.sentiment_analysis ? (
                  <>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-muted p-6 rounded-lg text-center">
                        <div className="text-sm text-muted-foreground mb-2">赚钱效应</div>
                        <div className="text-3xl font-bold">
                          {analysisData.sentiment_analysis.money_making_effect || '-'}
                        </div>
                      </div>

                      <div className="bg-muted p-6 rounded-lg text-center">
                        <div className="text-sm text-muted-foreground mb-2">操作策略</div>
                        <Badge className={cn("text-lg py-2 px-4", getStrategyColor(analysisData.sentiment_analysis.strategy))}>
                          {analysisData.sentiment_analysis.strategy || '-'}
                        </Badge>
                      </div>
                    </div>

                    <div className="bg-orange-50 dark:bg-orange-900/10 p-4 rounded-lg border border-orange-200 dark:border-orange-800">
                      <div className="font-medium mb-2 flex items-center gap-2">
                        <TrendingDownIcon className="h-4 w-4 text-orange-500" />
                        推理分析
                      </div>
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">
                        {analysisData.sentiment_analysis.reasoning || '暂无推理'}
                      </p>
                    </div>
                  </>
                ) : (
                  <Alert>
                    <AlertDescription>暂无情绪分析数据</AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* 看暗流 */}
          <TabsContent value="capital">
            <Card>
              <CardHeader>
                <CardTitle>【看暗流】资金动向分析</CardTitle>
                <CardDescription>顶级游资今天主攻了哪个方向？机构在建仓什么？</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {analysisData.capital_flow_analysis ? (
                  <>
                    <div className="grid md:grid-cols-2 gap-4">
                      {/* 游资方向 */}
                      <div className="bg-red-50 dark:bg-red-900/10 p-4 rounded-lg border border-red-200 dark:border-red-800">
                        <div className="font-medium mb-3 text-red-700 dark:text-red-400">游资方向</div>
                        <div className="space-y-2 text-sm">
                          <div>
                            <span className="text-muted-foreground">主攻题材：</span>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {analysisData.capital_flow_analysis.hot_money_direction?.themes?.map((theme, idx) => (
                                <Badge key={idx} variant="destructive">{theme}</Badge>
                              ))}
                            </div>
                          </div>
                          <div>
                            <span className="text-muted-foreground">集中度：</span>
                            <Badge variant="outline" className="ml-2">
                              {analysisData.capital_flow_analysis.hot_money_direction?.concentration || '-'}
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
                              {analysisData.capital_flow_analysis.institution_direction?.sectors?.map((sector, idx) => (
                                <Badge key={idx} className="bg-green-500 hover:bg-green-600">{sector}</Badge>
                              ))}
                            </div>
                          </div>
                          <div>
                            <span className="text-muted-foreground">风格：</span>
                            <Badge variant="outline" className="ml-2">
                              {analysisData.capital_flow_analysis.institution_direction?.style || '-'}
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
                        {analysisData.capital_flow_analysis.capital_consensus || '-'}
                      </AlertDescription>
                    </Alert>

                    {/* 详细分析 */}
                    <div className="bg-purple-50 dark:bg-purple-900/10 p-4 rounded-lg border border-purple-200 dark:border-purple-800">
                      <div className="font-medium mb-2">详细分析</div>
                      <p className="text-sm leading-relaxed whitespace-pre-wrap">
                        {analysisData.capital_flow_analysis.analysis || '暂无分析'}
                      </p>
                    </div>
                  </>
                ) : (
                  <Alert>
                    <AlertDescription>暂无资金动向分析数据</AlertDescription>
                  </Alert>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* 明日战术 */}
          <TabsContent value="tactics">
            <div className="space-y-4">
              {analysisData.tomorrow_tactics ? (
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
                          {analysisData.tomorrow_tactics.call_auction_tactics?.participate_conditions || '暂无'}
                        </div>
                      </div>
                      <div>
                        <div className="font-medium text-sm mb-2 text-red-600">❌ 禁止条件</div>
                        <div className="bg-red-50 dark:bg-red-900/10 p-3 rounded text-sm">
                          {analysisData.tomorrow_tactics.call_auction_tactics?.avoid_conditions || '暂无'}
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
                          {analysisData.tomorrow_tactics.opening_half_hour_tactics?.low_buy_opportunities || '暂无'}
                        </div>
                      </div>
                      <div>
                        <div className="font-medium text-sm mb-2">📈 追涨机会</div>
                        <div className="bg-orange-50 dark:bg-orange-900/10 p-3 rounded text-sm">
                          {analysisData.tomorrow_tactics.opening_half_hour_tactics?.chase_opportunities || '暂无'}
                        </div>
                      </div>
                      <div>
                        <div className="font-medium text-sm mb-2">🔍 观望信号</div>
                        <div className="bg-gray-50 dark:bg-gray-900/10 p-3 rounded text-sm">
                          {analysisData.tomorrow_tactics.opening_half_hour_tactics?.wait_signals || '暂无'}
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
                          {analysisData.tomorrow_tactics.buy_conditions?.map((condition, idx) => (
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
                          {analysisData.tomorrow_tactics.stop_loss_conditions?.map((condition, idx) => (
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
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}
