"use client"

import { useState, useEffect, useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import {
  CalendarIcon,
  PlayIcon,
  RefreshCwIcon,
  TrendingUpIcon,
  TrendingDownIcon,
  AlertTriangleIcon,
  CheckCircle2Icon,
  Clock,
  Database,
  BrainCircuit,
  NewspaperIcon,
  BarChart3Icon
} from "lucide-react"
import { format } from "date-fns"
import { zhCN } from "date-fns/locale"
import { cn } from "@/lib/utils"
import { apiClient } from "@/lib/api-client"
import { toast } from "sonner"
import logger from "@/lib/logger"
import type {
  OvernightData,
  CollisionAnalysis,
  PremarketNews,
  AnalysisHistory,
  ApiResponse,
  SyncResult,
  NewsListResponse
} from "@/types/premarket"

interface AIProvider {
  id: number
  provider: string
  display_name: string
  is_active: boolean
  is_default: boolean
  model_name: string
}

export default function PremarketPage() {
  const [date, setDate] = useState<Date>(new Date())
  const [aiProvider, setAiProvider] = useState<string>("")
  const [aiProviders, setAiProviders] = useState<AIProvider[]>([])

  const [overnightData, setOvernightData] = useState<OvernightData | null>(null)
  const [collisionAnalysis, setCollisionAnalysis] = useState<CollisionAnalysis | null>(null)
  const [newsList, setNewsList] = useState<PremarketNews[]>([])
  const [history, setHistory] = useState<AnalysisHistory[]>([])

  const [isSyncing, setIsSyncing] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingProviders, setIsLoadingProviders] = useState(true)

  // 格式化日期为 YYYY-MM-DD
  const formatDate = (d: Date) => format(d, "yyyy-MM-dd")

  // 加载AI提供商列表
  const loadProviders = async () => {
    setIsLoadingProviders(true)
    try {
      const data = await apiClient.get('/api/ai-strategy/providers')

      if (!Array.isArray(data)) {
        logger.error('AI Providers data is not an array', data)
        toast.error("AI配置数据格式错误")
        setAiProviders([])
        return
      }

      const providers = data.filter((p: AIProvider) => p.is_active)
      setAiProviders(providers)

      const defaultProvider = providers.find((p: AIProvider) => p.is_default)
      if (defaultProvider) {
        setAiProvider(defaultProvider.provider)
      } else if (providers.length > 0) {
        setAiProvider(providers[0].provider)
      }
    } catch (error: any) {
      logger.error('Load AI Providers Error', error)
      toast.error("加载AI配置失败：" + (error.response?.data?.detail || error.message))
      setAiProviders([])
    } finally {
      setIsLoadingProviders(false)
    }
  }

  // 加载所有数据
  const loadAllData = useCallback(async (targetDate?: Date) => {
    const dateStr = formatDate(targetDate || date)
    setIsLoading(true)

    try {
      // 并行加载所有数据，使用 Promise.allSettled 确保单个请求失败不影响其他请求
      // 404 错误会被 axios 拦截器静默处理，不会在控制台显示
      const [overnightRes, analysisRes, newsRes] = await Promise.allSettled([
        apiClient.get(`/api/premarket/overnight-data/${dateStr}`),
        apiClient.get(`/api/premarket/collision-analysis/${dateStr}`),
        apiClient.get(`/api/premarket/news/${dateStr}`)
      ])

      // 处理外盘数据
      if (overnightRes.status === 'fulfilled' && (overnightRes.value as any)?.code === 200) {
        setOvernightData((overnightRes.value as any).data)
      } else {
        setOvernightData(null)
      }

      // 处理碰撞分析
      if (analysisRes.status === 'fulfilled' && (analysisRes.value as any)?.code === 200) {
        setCollisionAnalysis((analysisRes.value as any).data)
      } else {
        setCollisionAnalysis(null)
      }

      // 处理新闻列表
      if (newsRes.status === 'fulfilled' && (newsRes.value as any)?.code === 200) {
        setNewsList((newsRes.value as any).data?.news || [])
      } else {
        setNewsList([])
      }
    } catch (error: any) {
      logger.error('Load data error', error)
      toast.error("加载数据失败")
    } finally {
      setIsLoading(false)
    }
  }, [date])

  // 加载历史记录
  const loadHistory = async () => {
    try {
      const response = await apiClient.get<ApiResponse<AnalysisHistory[]>>('/api/premarket/history?limit=10') as any
      if (response.code === 200 && response.data) {
        setHistory(response.data)
      }
    } catch (error: any) {
      logger.error('Load history error', error)
    }
  }

  // 同步盘前数据
  const handleSync = async () => {
    const dateStr = formatDate(date)
    setIsSyncing(true)

    // 显示加载提示并保存 ID，用于后续关闭避免 toast 重叠
    const loadingToastId = toast.info("正在同步盘前数据...")

    try {
      const res = await apiClient.post<ApiResponse<SyncResult>>(
        `/api/premarket/sync?date=${dateStr}`
      ) as any

      // 先关闭加载提示，再显示结果，确保 toast 顺序展示不重叠
      toast.dismiss(loadingToastId)

      if (res.code === 200) {
        toast.success(res.message || "同步成功")
        // 重新加载数据
        await loadAllData()
      } else {
        toast.error(res.message || "同步失败")
      }
    } catch (error: any) {
      toast.dismiss(loadingToastId)
      toast.error("同步失败：" + (error.response?.data?.detail || error.message))
    } finally {
      setIsSyncing(false)
    }
  }

  // 生成碰撞分析
  const handleGenerate = async () => {
    const dateStr = formatDate(date)
    setIsGenerating(true)

    // 显示加载提示并保存 ID，用于后续关闭避免 toast 重叠
    const loadingToastId = toast.info("正在调用AI生成碰撞分析，请稍候...")

    try {
      const res = await apiClient.post<ApiResponse<any>>(
        `/api/premarket/collision-analysis/generate?date=${dateStr}&provider=${aiProvider}`
      ) as any

      // 先关闭加载提示，再显示结果，确保 toast 顺序展示不重叠
      toast.dismiss(loadingToastId)

      if (res.code === 200) {
        toast.success("碰撞分析生成成功")
        await loadAllData()
        await loadHistory()
      } else {
        toast.error(res.message || "生成失败")
      }
    } catch (error: any) {
      toast.dismiss(loadingToastId)
      toast.error("生成失败：" + (error.response?.data?.detail || error.message))
    } finally {
      setIsGenerating(false)
    }
  }

  // 初始加载
  useEffect(() => {
    loadProviders()
    loadAllData()
    loadHistory()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 日期变化时加载
  const handleDateChange = (newDate: Date | undefined) => {
    if (newDate) {
      setDate(newDate)
      loadAllData(newDate)
    }
  }

  // 获取变化率颜色
  const getChangeColor = (change: number) => {
    if (change > 0) return "text-red-500"
    if (change < 0) return "text-green-500"
    return "text-gray-500"
  }

  // 获取变化率前缀
  const getChangePrefix = (change: number) => {
    if (change > 0) return "+"
    return ""
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

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* 页面标题 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">盘前预期管理系统</h1>
          <p className="text-muted-foreground mt-1">
            每日早8:00自动执行：隔夜外盘数据 + 盘前新闻 + AI碰撞分析 = 早盘竞价行动指令
          </p>
        </div>
      </div>

      {/* 控制面板 */}
      <Card>
        <CardHeader>
          <CardTitle>控制面板</CardTitle>
          <CardDescription>选择日期，同步数据或生成AI碰撞分析</CardDescription>
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
                      暂无可用配置
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
            </div>

            {/* 操作按钮 */}
            <div className="flex gap-2 items-end">
              <Button
                onClick={handleSync}
                disabled={isSyncing}
                variant="outline"
                className="min-w-[140px]"
              >
                {isSyncing ? (
                  <>
                    <RefreshCwIcon className="mr-2 h-4 w-4 animate-spin" />
                    同步中...
                  </>
                ) : (
                  <>
                    <Database className="mr-2 h-4 w-4" />
                    同步盘前数据
                  </>
                )}
              </Button>

              <Button
                onClick={handleGenerate}
                disabled={isGenerating || aiProviders.length === 0}
                className="min-w-[140px]"
              >
                {isGenerating ? (
                  <>
                    <RefreshCwIcon className="mr-2 h-4 w-4 animate-spin" />
                    生成中...
                  </>
                ) : (
                  <>
                    <BrainCircuit className="mr-2 h-4 w-4" />
                    生成碰撞分析
                  </>
                )}
              </Button>

              <Button
                variant="outline"
                onClick={() => loadAllData()}
                disabled={isLoading}
              >
                <RefreshCwIcon className={cn("mr-2 h-4 w-4", isLoading && "animate-spin")} />
                刷新
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 主要内容区域 */}
      <Tabs defaultValue="analysis" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="analysis">📊 碰撞分析</TabsTrigger>
          <TabsTrigger value="overnight">🌏 外盘数据</TabsTrigger>
          <TabsTrigger value="news">📰 盘前新闻</TabsTrigger>
          <TabsTrigger value="history">📜 历史记录</TabsTrigger>
        </TabsList>

        {/* 碰撞分析标签页 */}
        <TabsContent value="analysis" className="space-y-4">
          {isLoading ? (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                <RefreshCwIcon className="h-8 w-8 animate-spin mx-auto mb-2" />
                加载中...
              </CardContent>
            </Card>
          ) : !collisionAnalysis ? (
            <Alert>
              <AlertTriangleIcon className="h-4 w-4" />
              <AlertTitle>暂无数据</AlertTitle>
              <AlertDescription>
                {formatDate(date)} 暂无碰撞分析数据，请先同步盘前数据，然后点击&ldquo;生成碰撞分析&rdquo;按钮。
              </AlertDescription>
            </Alert>
          ) : (
            <>
              {/* 行动指令卡片 */}
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
                      {collisionAnalysis.action_command}
                    </pre>
                  </div>
                  <div className="flex flex-wrap gap-4 text-sm text-muted-foreground mt-4 pt-4 border-t">
                    <div className="flex items-center gap-1">
                      <span className="font-medium">AI模型:</span>
                      <Badge variant="outline">{collisionAnalysis.ai_provider} / {collisionAnalysis.ai_model}</Badge>
                    </div>
                    <div className="flex items-center gap-1">
                      <span className="font-medium">Token消耗:</span>
                      <span>{collisionAnalysis.tokens_used}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      <span className="font-medium">生成耗时:</span>
                      <span>{collisionAnalysis.generation_time}s</span>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* 四维度分析 */}
              <div className="grid md:grid-cols-2 gap-4">
                {/* 宏观定调 */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">🎯 宏观定调</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {collisionAnalysis.macro_tone ? (
                      <>
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-muted-foreground">开盘预期:</span>
                          <Badge className="text-lg py-1 px-3">
                            {collisionAnalysis.macro_tone.direction}
                          </Badge>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-muted-foreground">置信度:</span>
                          <span className="font-bold">{collisionAnalysis.macro_tone.confidence}</span>
                        </div>
                        <div className="bg-blue-50 dark:bg-blue-900/10 p-3 rounded text-sm">
                          <div className="font-medium mb-1">A50影响:</div>
                          <p>{collisionAnalysis.macro_tone.a50_impact}</p>
                        </div>
                        <div className="bg-gray-50 dark:bg-gray-900/10 p-3 rounded text-sm">
                          <div className="font-medium mb-1">综合判断:</div>
                          <p>{collisionAnalysis.macro_tone.reasoning}</p>
                        </div>
                      </>
                    ) : (
                      <p className="text-sm text-muted-foreground">暂无数据</p>
                    )}
                  </CardContent>
                </Card>

                {/* 持仓排雷 */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">⚠️ 持仓排雷</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {collisionAnalysis.holdings_alert ? (
                      <>
                        <div className="flex items-center gap-2">
                          {collisionAnalysis.holdings_alert.has_risk ? (
                            <Badge variant="destructive">发现风险</Badge>
                          ) : (
                            <Badge className="bg-green-500">无风险</Badge>
                          )}
                        </div>
                        {collisionAnalysis.holdings_alert.affected_sectors.length > 0 && (
                          <div>
                            <div className="text-sm text-muted-foreground mb-2">受影响板块:</div>
                            <div className="flex flex-wrap gap-1">
                              {collisionAnalysis.holdings_alert.affected_sectors.map((sector, idx) => (
                                <Badge key={idx} variant="outline">{sector}</Badge>
                              ))}
                            </div>
                          </div>
                        )}
                        {collisionAnalysis.holdings_alert.affected_stocks.length > 0 && (
                          <div>
                            <div className="text-sm text-muted-foreground mb-2">受影响个股:</div>
                            <div className="space-y-2">
                              {collisionAnalysis.holdings_alert.affected_stocks.map((stock, idx) => (
                                <div key={idx} className="bg-red-50 dark:bg-red-900/10 p-2 rounded text-sm">
                                  <div className="font-medium">{stock.name} ({stock.code})</div>
                                  <div className="text-xs text-muted-foreground">{stock.reason}</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        {collisionAnalysis.holdings_alert.actions && (
                          <div className="bg-orange-50 dark:bg-orange-900/10 p-3 rounded text-sm">
                            <div className="font-medium mb-1">操作建议:</div>
                            <p>{collisionAnalysis.holdings_alert.actions}</p>
                          </div>
                        )}
                      </>
                    ) : (
                      <p className="text-sm text-muted-foreground">暂无数据</p>
                    )}
                  </CardContent>
                </Card>

                {/* 计划修正 */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">📝 计划修正</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {collisionAnalysis.plan_adjustment ? (
                      <>
                        {collisionAnalysis.plan_adjustment.cancel_buy.length > 0 && (
                          <div>
                            <div className="text-sm text-muted-foreground mb-2">❌ 取消买入:</div>
                            <div className="space-y-2">
                              {collisionAnalysis.plan_adjustment.cancel_buy.map((item, idx) => (
                                <div key={idx} className="bg-red-50 dark:bg-red-900/10 p-2 rounded text-sm">
                                  <div className="font-medium">{item.stock}</div>
                                  <div className="text-xs text-muted-foreground">{item.reason}</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        {collisionAnalysis.plan_adjustment.early_stop_loss.length > 0 && (
                          <div>
                            <div className="text-sm text-muted-foreground mb-2">🛑 提前止损:</div>
                            <div className="space-y-2">
                              {collisionAnalysis.plan_adjustment.early_stop_loss.map((item, idx) => (
                                <div key={idx} className="bg-orange-50 dark:bg-orange-900/10 p-2 rounded text-sm">
                                  <div className="font-medium">{item.stock}</div>
                                  <div className="text-xs text-muted-foreground">{item.reason}</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        {collisionAnalysis.plan_adjustment.keep_plan && (
                          <div className="bg-green-50 dark:bg-green-900/10 p-3 rounded text-sm">
                            <div className="font-medium mb-1">✅ 保持计划:</div>
                            <p>{collisionAnalysis.plan_adjustment.keep_plan}</p>
                          </div>
                        )}
                        <div className="bg-gray-50 dark:bg-gray-900/10 p-3 rounded text-sm">
                          <div className="font-medium mb-1">推理过程:</div>
                          <p>{collisionAnalysis.plan_adjustment.reasoning}</p>
                        </div>
                      </>
                    ) : (
                      <p className="text-sm text-muted-foreground">暂无数据</p>
                    )}
                  </CardContent>
                </Card>

                {/* 竞价盯盘 */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">👀 竞价盯盘 (9:15-9:25)</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {collisionAnalysis.auction_focus ? (
                      <>
                        {collisionAnalysis.auction_focus.stocks.length > 0 && (
                          <div>
                            <div className="text-sm text-muted-foreground mb-2">核心标的:</div>
                            <div className="space-y-2">
                              {collisionAnalysis.auction_focus.stocks.map((stock, idx) => (
                                <div key={idx} className="bg-blue-50 dark:bg-blue-900/10 p-2 rounded text-sm">
                                  <div className="font-medium">{stock.name} ({stock.code})</div>
                                  <div className="text-xs text-muted-foreground">{stock.reason}</div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                        {collisionAnalysis.auction_focus.conditions && (
                          <div className="space-y-2">
                            <div className="bg-green-50 dark:bg-green-900/10 p-3 rounded text-sm">
                              <div className="font-medium mb-1">✅ 参与条件:</div>
                              <p>{collisionAnalysis.auction_focus.conditions.participate_conditions}</p>
                            </div>
                            <div className="bg-red-50 dark:bg-red-900/10 p-3 rounded text-sm">
                              <div className="font-medium mb-1">❌ 禁止条件:</div>
                              <p>{collisionAnalysis.auction_focus.conditions.avoid_conditions}</p>
                            </div>
                          </div>
                        )}
                        {collisionAnalysis.auction_focus.actions && (
                          <div className="bg-purple-50 dark:bg-purple-900/10 p-3 rounded text-sm">
                            <div className="font-medium mb-1">操作步骤:</div>
                            <p>{collisionAnalysis.auction_focus.actions}</p>
                          </div>
                        )}
                      </>
                    ) : (
                      <p className="text-sm text-muted-foreground">暂无数据</p>
                    )}
                  </CardContent>
                </Card>
              </div>
            </>
          )}
        </TabsContent>

        {/* 外盘数据标签页 */}
        <TabsContent value="overnight" className="space-y-4">
          {!overnightData ? (
            <Alert>
              <AlertTriangleIcon className="h-4 w-4" />
              <AlertTitle>暂无数据</AlertTitle>
              <AlertDescription>
                请先点击&ldquo;同步盘前数据&rdquo;按钮获取隔夜外盘数据
              </AlertDescription>
            </Alert>
          ) : (
            <>
              {/* A50和中概股 */}
              <div className="grid md:grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">富时A50期指</CardTitle>
                    <CardDescription>直接影响A股大盘开盘</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-bold">{overnightData.a50.close.toFixed(2)}</span>
                      <span className={cn("text-xl font-semibold", getChangeColor(overnightData.a50.change))}>
                        {getChangePrefix(overnightData.a50.change)}{overnightData.a50.change.toFixed(2)}%
                      </span>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">中概股指数</CardTitle>
                    <CardDescription>外资对中国资产的态度</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-bold">{overnightData.china_concept.close.toFixed(2)}</span>
                      <span className={cn("text-xl font-semibold", getChangeColor(overnightData.china_concept.change))}>
                        {getChangePrefix(overnightData.china_concept.change)}{overnightData.china_concept.change.toFixed(2)}%
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* 大宗商品 */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">大宗商品</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <div className="text-sm text-muted-foreground mb-1">WTI原油</div>
                      <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-bold">{overnightData.wti_crude.close.toFixed(2)}</span>
                        <span className={cn("font-semibold", getChangeColor(overnightData.wti_crude.change))}>
                          {getChangePrefix(overnightData.wti_crude.change)}{overnightData.wti_crude.change.toFixed(2)}%
                        </span>
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground mb-1">COMEX黄金</div>
                      <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-bold">{overnightData.comex_gold.close.toFixed(2)}</span>
                        <span className={cn("font-semibold", getChangeColor(overnightData.comex_gold.change))}>
                          {getChangePrefix(overnightData.comex_gold.change)}{overnightData.comex_gold.change.toFixed(2)}%
                        </span>
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground mb-1">伦敦铜</div>
                      <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-bold">{overnightData.lme_copper.close.toFixed(2)}</span>
                        <span className={cn("font-semibold", getChangeColor(overnightData.lme_copper.change))}>
                          {getChangePrefix(overnightData.lme_copper.change)}{overnightData.lme_copper.change.toFixed(2)}%
                        </span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* 外汇和美股 */}
              <div className="grid md:grid-cols-2 gap-4">
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">美元兑离岸人民币</CardTitle>
                    <CardDescription>资金流向指标</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-baseline gap-2">
                      <span className="text-3xl font-bold">{overnightData.usdcnh.close.toFixed(4)}</span>
                      <span className={cn("text-xl font-semibold", getChangeColor(overnightData.usdcnh.change))}>
                        {getChangePrefix(overnightData.usdcnh.change)}{overnightData.usdcnh.change.toFixed(2)}%
                      </span>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">美股三大指数</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">标普500:</span>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold">{overnightData.sp500.close.toFixed(2)}</span>
                          <span className={cn("font-semibold", getChangeColor(overnightData.sp500.change))}>
                            {getChangePrefix(overnightData.sp500.change)}{overnightData.sp500.change.toFixed(2)}%
                          </span>
                        </div>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">纳斯达克:</span>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold">{overnightData.nasdaq.close.toFixed(2)}</span>
                          <span className={cn("font-semibold", getChangeColor(overnightData.nasdaq.change))}>
                            {getChangePrefix(overnightData.nasdaq.change)}{overnightData.nasdaq.change.toFixed(2)}%
                          </span>
                        </div>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-muted-foreground">道琼斯:</span>
                        <div className="flex items-center gap-2">
                          <span className="font-semibold">{overnightData.dow.close.toFixed(2)}</span>
                          <span className={cn("font-semibold", getChangeColor(overnightData.dow.change))}>
                            {getChangePrefix(overnightData.dow.change)}{overnightData.dow.change.toFixed(2)}%
                          </span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </>
          )}
        </TabsContent>

        {/* 盘前新闻标签页 */}
        <TabsContent value="news" className="space-y-4">
          {newsList.length === 0 ? (
            <Alert>
              <AlertTriangleIcon className="h-4 w-4" />
              <AlertTitle>暂无数据</AlertTitle>
              <AlertDescription>
                请先点击&ldquo;同步盘前数据&rdquo;按钮获取盘前核心新闻
              </AlertDescription>
            </Alert>
          ) : (
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
                      className="border rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <Badge className={getImportanceColor(news.importance_level)}>
                            {news.importance_level === 'critical' ? '核弹级' :
                             news.importance_level === 'high' ? '高' : '中'}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {new Date(news.news_time).toLocaleString('zh-CN')}
                          </span>
                          <Badge variant="outline">{news.source}</Badge>
                        </div>
                      </div>
                      <div className="font-medium mb-2">{news.title}</div>
                      <div className="text-sm text-muted-foreground mb-2">{news.content}</div>
                      <div className="flex flex-wrap gap-1">
                        {news.keywords.map((keyword, idx) => (
                          <Badge key={idx} variant="secondary" className="text-xs">
                            {keyword}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* 历史记录标签页 */}
        <TabsContent value="history" className="space-y-4">
          {history.length === 0 ? (
            <Alert>
              <AlertTriangleIcon className="h-4 w-4" />
              <AlertTitle>暂无数据</AlertTitle>
              <AlertDescription>
                暂无历史碰撞分析记录
              </AlertDescription>
            </Alert>
          ) : (
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
                      className="border rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-900 transition-colors cursor-pointer"
                      onClick={() => {
                        const selectedDate = new Date(record.trade_date)
                        setDate(selectedDate)
                        loadAllData(selectedDate)
                      }}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-bold">{record.trade_date}</span>
                          <Badge variant={record.status === 'success' ? 'default' : 'destructive'}>
                            {record.status === 'success' ? '成功' : '失败'}
                          </Badge>
                        </div>
                        <div className="text-xs text-muted-foreground">
                          {record.ai_provider} | {record.tokens_used} tokens | {record.generation_time}s
                        </div>
                      </div>
                      <div className="bg-gray-50 dark:bg-gray-900 p-3 rounded text-sm">
                        {record.action_command}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
