"use client"

import { useState, useEffect } from "react"
import { PageHeader } from '@/components/common/PageHeader'
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import {
  TrendingUp,
  Globe,
  Newspaper,
  History
} from "lucide-react"
import { format } from "@/lib/date-utils"
import { cn } from "@/lib/utils"

// Hooks
import { usePremarketData } from './hooks/usePremarketData'
import { useAIProviders } from './hooks/useAIProviders'
import { usePremarketActions } from './hooks/usePremarketActions'

// Components
import { ControlPanel } from './components/ControlPanel'
import { CollisionAnalysisTab } from './components/CollisionAnalysisTab'
import { OvernightDataTab } from './components/OvernightDataTab'
import { NewsListTab } from './components/NewsListTab'
import { HistoryTab } from './components/HistoryTab'

/**
 * 盘前预期管理系统
 * 每日早8:00自动执行：隔夜外盘数据 + 盘前新闻 + AI碰撞分析 = 早盘竞价行动指令
 */
export default function PremarketPage() {
  const [date, setDate] = useState<Date>(new Date())
  const [activeTab, setActiveTab] = useState<string>("analysis")

  // 格式化日期为 YYYY-MM-DD
  const formatDate = (d: Date) => format(d, "yyyy-MM-dd")

  // 使用自定义 Hooks
  const {
    overnightData,
    collisionAnalysis,
    newsList,
    history,
    isLoading,
    loadAllData,
    loadHistory
  } = usePremarketData(formatDate)

  const {
    aiProvider,
    setAiProvider,
    aiProviders,
    isLoadingProviders
  } = useAIProviders()

  const {
    isSyncing,
    isGenerating,
    handleSync,
    handleGenerate
  } = usePremarketActions(formatDate, async () => {
    // 成功回调：重新加载所有数据和历史记录
    await loadAllData(date)
    await loadHistory()
  })

  // 初始加载
  useEffect(() => {
    loadAllData(date)
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

  // 历史记录点击
  const handleHistoryClick = (record: { trade_date: string }) => {
    const selectedDate = new Date(record.trade_date)
    setDate(selectedDate)
    loadAllData(selectedDate)
  }

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <PageHeader
        title="盘前预期管理系统"
        description="每日早8:00自动执行：隔夜外盘数据 + 盘前新闻 + AI碰撞分析 = 早盘竞价行动指令"
      />

      {/* 控制面板 */}
      <ControlPanel
        date={date}
        onDateChange={handleDateChange}
        aiProvider={aiProvider}
        onAiProviderChange={setAiProvider}
        aiProviders={aiProviders}
        isLoadingProviders={isLoadingProviders}
        isSyncing={isSyncing}
        isGenerating={isGenerating}
        isLoading={isLoading}
        onSync={() => handleSync(date)}
        onGenerate={() => handleGenerate(date, aiProvider)}
        onRefresh={() => loadAllData(date)}
      />

      {/* 主要内容区域 */}
      <Tabs defaultValue="analysis" value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        {/* 移动端卡片式导航 (小于640px显示) */}
        <div className="grid grid-cols-2 gap-3 sm:hidden">
          <button
            onClick={() => setActiveTab("analysis")}
            className={cn(
              "flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all",
              activeTab === "analysis"
                ? "border-primary bg-primary/5 text-primary shadow-sm"
                : "border-border bg-muted/30 hover:bg-muted/50"
            )}
          >
            <TrendingUp className="h-5 w-5" />
            <span className="text-xs font-medium">碰撞分析</span>
          </button>
          <button
            onClick={() => setActiveTab("overnight")}
            className={cn(
              "flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all",
              activeTab === "overnight"
                ? "border-primary bg-primary/5 text-primary shadow-sm"
                : "border-border bg-muted/30 hover:bg-muted/50"
            )}
          >
            <Globe className="h-5 w-5" />
            <span className="text-xs font-medium">外盘数据</span>
          </button>
          <button
            onClick={() => setActiveTab("news")}
            className={cn(
              "flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all relative",
              activeTab === "news"
                ? "border-primary bg-primary/5 text-primary shadow-sm"
                : "border-border bg-muted/30 hover:bg-muted/50"
            )}
          >
            <Newspaper className="h-5 w-5" />
            <span className="text-xs font-medium">盘前新闻</span>
            {newsList.length > 0 && (
              <Badge variant="secondary" className="absolute -top-1 -right-1 h-5 px-1.5 text-xs">
                {newsList.length}
              </Badge>
            )}
          </button>
          <button
            onClick={() => setActiveTab("history")}
            className={cn(
              "flex flex-col items-center gap-2 p-4 rounded-xl border-2 transition-all relative",
              activeTab === "history"
                ? "border-primary bg-primary/5 text-primary shadow-sm"
                : "border-border bg-muted/30 hover:bg-muted/50"
            )}
          >
            <History className="h-5 w-5" />
            <span className="text-xs font-medium">历史记录</span>
            {history.length > 0 && (
              <Badge variant="outline" className="absolute -top-1 -right-1 h-5 px-1.5 text-xs">
                {history.length}
              </Badge>
            )}
          </button>
        </div>

        {/* 桌面端标签式导航 (640px及以上显示) */}
        <div className="relative hidden sm:block">
          {/* 渐变遮罩效果 */}
          <div className="absolute left-0 top-0 bottom-0 w-8 bg-gradient-to-r from-background to-transparent pointer-events-none z-10 md:hidden" />
          <div className="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-l from-background to-transparent pointer-events-none z-10 md:hidden" />

          {/* 可滚动的 Tabs 容器 */}
          <div className="w-full overflow-x-auto scrollbar-hide">
            <TabsList className="inline-flex h-12 items-center justify-start rounded-xl bg-muted/40 backdrop-blur-sm p-1.5 text-muted-foreground w-full md:w-auto min-w-max border border-border/50">
              <TabsTrigger
                value="analysis"
                className="relative inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium whitespace-nowrap rounded-lg transition-all duration-200 hover:bg-muted/60 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm data-[state=active]:border data-[state=active]:border-border/50"
              >
                <TrendingUp className="h-4 w-4 transition-colors" />
                <span>碰撞分析</span>
              </TabsTrigger>
              <TabsTrigger
                value="overnight"
                className="relative inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium whitespace-nowrap rounded-lg transition-all duration-200 hover:bg-muted/60 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm data-[state=active]:border data-[state=active]:border-border/50"
              >
                <Globe className="h-4 w-4 transition-colors" />
                <span>外盘数据</span>
              </TabsTrigger>
              <TabsTrigger
                value="news"
                className="relative inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium whitespace-nowrap rounded-lg transition-all duration-200 hover:bg-muted/60 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm data-[state=active]:border data-[state=active]:border-border/50"
              >
                <Newspaper className="h-4 w-4 transition-colors" />
                <span>盘前新闻</span>
                {newsList.length > 0 && (
                  <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-xs">
                    {newsList.length}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger
                value="history"
                className="relative inline-flex items-center gap-2 px-4 py-2.5 text-sm font-medium whitespace-nowrap rounded-lg transition-all duration-200 hover:bg-muted/60 data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm data-[state=active]:border data-[state=active]:border-border/50"
              >
                <History className="h-4 w-4 transition-colors" />
                <span>历史记录</span>
                {history.length > 0 && (
                  <Badge variant="outline" className="ml-1 h-5 px-1.5 text-xs">
                    {history.length}
                  </Badge>
                )}
              </TabsTrigger>
            </TabsList>
          </div>
        </div>

        {/* 标签页内容 */}
        <TabsContent value="analysis">
          <CollisionAnalysisTab
            isLoading={isLoading}
            collisionAnalysis={collisionAnalysis}
            date={date}
          />
        </TabsContent>

        <TabsContent value="overnight">
          <OvernightDataTab overnightData={overnightData} />
        </TabsContent>

        <TabsContent value="news">
          <NewsListTab newsList={newsList} />
        </TabsContent>

        <TabsContent value="history">
          <HistoryTab
            history={history}
            onHistoryClick={handleHistoryClick}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}
