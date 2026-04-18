"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { CalendarIcon, PlayIcon, RefreshCwIcon, FileTextIcon, Clock } from "lucide-react"
import { format, zhCN } from "@/lib/date-utils"
import { cn } from "@/lib/utils"
import type { AIProvider, AIAnalysisResult } from "../hooks/useAiAnalysisData"

interface ControlPanelProps {
  date: Date
  aiProvider: string
  setAiProvider: (v: string) => void
  aiProviders: AIProvider[]
  analysisData: AIAnalysisResult | null
  isLoading: boolean
  isLoadingProviders: boolean
  isGenerating: boolean
  taskId: string | null
  isLoadingPrompt: boolean
  onDateChange: (d: Date | undefined) => void
  onGenerate: () => void
  onRefresh: () => void
  onPreviewPrompt: () => void
}

export function ControlPanel({
  date,
  aiProvider,
  setAiProvider,
  aiProviders,
  analysisData,
  isLoading,
  isLoadingProviders,
  isGenerating,
  taskId,
  isLoadingPrompt,
  onDateChange,
  onGenerate,
  onRefresh,
  onPreviewPrompt,
}: ControlPanelProps) {
  return (
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
                  onSelect={onDateChange}
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
              variant="outline"
              onClick={onPreviewPrompt}
              disabled={isLoadingPrompt}
            >
              {isLoadingPrompt ? (
                <>
                  <RefreshCwIcon className="mr-2 h-4 w-4 animate-spin" />
                  加载中...
                </>
              ) : (
                <>
                  <FileTextIcon className="mr-2 h-4 w-4" />
                  生成提示词
                </>
              )}
            </Button>

            <Button
              onClick={onGenerate}
              disabled={isGenerating || taskId !== null || aiProviders.length === 0}
              className="min-w-[120px]"
            >
              {isGenerating || taskId !== null ? (
                <>
                  <RefreshCwIcon className="mr-2 h-4 w-4 animate-spin" />
                  {isGenerating ? '提交中...' : '生成中...'}
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
              onClick={onRefresh}
              disabled={isLoading}
            >
              <RefreshCwIcon className={cn("mr-2 h-4 w-4", isLoading && "animate-spin")} />
              刷新
            </Button>
          </div>
        </div>

        {/* 任务进行中提示 */}
        {taskId && (
          <Alert className="border-blue-200 bg-blue-50 dark:bg-blue-900/10">
            <RefreshCwIcon className="h-4 w-4 animate-spin text-blue-500" />
            <AlertTitle className="text-blue-700 dark:text-blue-400">正在生成AI分析</AlertTitle>
            <AlertDescription className="text-blue-600 dark:text-blue-300">
              任务正在后台执行，您可以离开此页面。生成完成时将自动通知您。
            </AlertDescription>
          </Alert>
        )}

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
  )
}
