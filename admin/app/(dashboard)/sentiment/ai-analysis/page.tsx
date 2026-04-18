"use client"

import { Card, CardContent } from "@/components/ui/card"
import { PageHeader } from "@/components/common/PageHeader"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertTriangleIcon, RefreshCwIcon } from "lucide-react"

// Hooks
import { useAiAnalysisData, formatDateStr } from './hooks/useAiAnalysisData'
import { useAiAnalysisActions } from './hooks/useAiAnalysisActions'

// Components
import { ControlPanel } from './components/ControlPanel'
import { AnalysisTabs } from './components/AnalysisTabs'
import { PromptPreviewDialog } from './components/PromptPreviewDialog'

export default function SentimentAIAnalysisPage() {
  const {
    date,
    aiProvider,
    setAiProvider,
    aiProviders,
    analysisData,
    isLoading,
    isLoadingProviders,
    loadAnalysis,
    handleDateChange,
  } = useAiAnalysisData()

  const {
    isGenerating,
    taskId,
    promptDialogOpen,
    setPromptDialogOpen,
    promptText,
    promptDate,
    isLoadingPrompt,
    handlePreviewPrompt,
    handleGenerate,
  } = useAiAnalysisActions({
    date,
    aiProvider,
    aiProviders,
    loadAnalysis,
  })

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <PageHeader
        title="市场情绪AI分析"
        description="基于LLM的四维度盘后情绪深度分析（看空间、看情绪、看暗流、明日战术）"
      />

      {/* 控制面板 */}
      <ControlPanel
        date={date}
        aiProvider={aiProvider}
        setAiProvider={setAiProvider}
        aiProviders={aiProviders}
        analysisData={analysisData}
        isLoading={isLoading}
        isLoadingProviders={isLoadingProviders}
        isGenerating={isGenerating}
        taskId={taskId}
        isLoadingPrompt={isLoadingPrompt}
        onDateChange={handleDateChange}
        onGenerate={handleGenerate}
        onRefresh={() => loadAnalysis()}
        onPreviewPrompt={handlePreviewPrompt}
      />

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
            {formatDateStr(date)} 暂无AI分析数据，请点击&ldquo;生成分析&rdquo;按钮创建分析报告。
          </AlertDescription>
        </Alert>
      ) : (
        <AnalysisTabs analysisData={analysisData} />
      )}

      {/* 提示词预览弹窗 */}
      <PromptPreviewDialog
        open={promptDialogOpen}
        onOpenChange={setPromptDialogOpen}
        promptText={promptText}
        promptDate={promptDate}
        isLoading={isLoadingPrompt}
      />
    </div>
  )
}
