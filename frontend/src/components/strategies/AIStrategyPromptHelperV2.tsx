/**
 * AI策略生成助手组件 V2（增强版）
 * 支持异步调用后端AI API生成策略
 *
 * 新增功能：
 * - 异步生成，不阻塞页面
 * - 离开页面后继续生成
 * - 全局任务监控
 * - 单任务限制（同时只能一个生成任务）
 * - 自动缓存结果
 */

'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  Sparkles,
  Wand2,
  Loader2,
  AlertCircle,
  X,
  CheckCircle
} from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { useAIGenerationTask } from '@/contexts/AIGenerationTaskContext'
import { apiClient } from '@/lib/api-client'

interface AIStrategyPromptHelperProps {
  onStrategyGenerated?: (strategyCode: string, metadata: any) => void
}

export default function AIStrategyPromptHelperV2({ onStrategyGenerated }: AIStrategyPromptHelperProps) {
  const { toast } = useToast()
  const { activeTasks, addTask, cancelTask, getTaskResult, clearCachedResult, hasActiveTasks } = useAIGenerationTask()

  const [strategyRequirement, setStrategyRequirement] = useState(`**策略类型**: 简单均线策略

**策略类别**: trend_following

**核心逻辑**:
- 使用MA(5, 20)判断趋势
- 买入条件：MA5上穿MA20（金叉）
- 卖出条件：MA5下穿MA20（死叉）

**技术指标**: MA（移动平均线）

**参数配置**:
- ma_fast: 5 (快速均线周期)
- ma_slow: 20 (慢速均线周期)

**风险控制**:
- 每期选择前10只股票`)

  // 获取当前活跃任务
  const currentTask = activeTasks.size > 0 ? Array.from(activeTasks.values())[0] : null
  const isGenerating = currentTask && ['PENDING', 'PROGRESS'].includes(currentTask.status)

  // 检测到生成完成时，自动填充表单
  useEffect(() => {
    if (currentTask?.status === 'SUCCESS' && currentTask.taskId) {
      const result = getTaskResult(currentTask.taskId)
      if (result && onStrategyGenerated) {
        // 调用回调函数填充表单
        onStrategyGenerated(result.strategy_code, result.strategy_metadata)

        // 清除缓存结果（避免重复使用）
        clearCachedResult(currentTask.taskId)

        toast({
          title: '✅ 策略已自动填充',
          description: '请检查生成的代码和元信息'
        })
      }
    }
  }, [currentTask?.status, currentTask?.taskId, getTaskResult, onStrategyGenerated, clearCachedResult, toast])

  const generateWithAI = async () => {
    if (!strategyRequirement.trim()) {
      toast({
        title: '请填写策略需求',
        description: '请先描述你的策略需求',
        variant: 'destructive'
      })
      return
    }

    // 检查是否已有活跃任务（由Context自动限制）
    if (hasActiveTasks()) {
      toast({
        title: '⚠️ 已有AI生成任务在进行中',
        description: '请等待当前任务完成后再提交新任务',
        variant: 'destructive'
      })
      return
    }

    try {
      // 调用异步API
      const response = await apiClient.generateStrategyAsync({
        strategy_requirement: strategyRequirement,
        use_custom_prompt: false
      })

      toast({
        title: '🚀 AI生成任务已提交',
        description: `使用 ${response.provider_used} 生成，您可以离开此页面继续其他操作`
      })

      // 添加到全局任务监控
      addTask(response.task_id, response.provider_used)
    } catch (error) {
      console.error('提交AI生成任务失败:', error)
      toast({
        title: '❌ 提交失败',
        description: error instanceof Error ? error.message : '未知错误',
        variant: 'destructive'
      })
    }
  }

  const handleCancel = () => {
    if (currentTask) {
      cancelTask(currentTask.taskId)
    }
  }

  return (
    <Card className="border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-primary/10">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            <CardTitle>AI 策略生成助手（异步增强版）</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            {isGenerating && (
              <Button
                onClick={handleCancel}
                variant="outline"
                size="sm"
                className="gap-2"
              >
                <X className="h-4 w-4" />
                取消任务
              </Button>
            )}
            <Button
              onClick={generateWithAI}
              disabled={isGenerating}
              className="gap-2"
            >
              {isGenerating ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  生成中...
                </>
              ) : (
                <>
                  <Wand2 className="h-4 w-4" />
                  使用AI生成
                </>
              )}
            </Button>
          </div>
        </div>
        <CardDescription>
          异步调用后端AI（DeepSeek、Gemini）生成策略，可离开页面继续操作
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* 任务进度显示 */}
        {currentTask && isGenerating && (
          <Alert className="border-primary/50 bg-primary/5">
            <Loader2 className="h-4 w-4 animate-spin text-primary" />
            <AlertTitle className="text-primary">AI策略生成进行中</AlertTitle>
            <AlertDescription className="space-y-2 mt-2">
              {/* 状态文字（带动画效果） */}
              <div className="flex items-center gap-2">
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                  <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                  <span className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                </div>
                <p className="text-sm">{currentTask.message}</p>
              </div>

              {currentTask.providerUsed && (
                <div className="flex items-center gap-1 text-xs">
                  <span className="text-muted-foreground">使用AI提供商:</span>
                  <span className="text-primary font-medium">{currentTask.providerUsed}</span>
                </div>
              )}

              <p className="text-xs text-muted-foreground">
                💡 您可以离开此页面，任务将在后台继续执行，完成后会通知您
              </p>
            </AlertDescription>
          </Alert>
        )}

        {/* 成功缓存提示 */}
        {currentTask?.status === 'SUCCESS' && (
          <Alert className="border-green-500/50 bg-green-500/5">
            <CheckCircle className="h-4 w-4 text-green-500" />
            <AlertTitle className="text-green-700 dark:text-green-400">策略生成成功</AlertTitle>
            <AlertDescription className="text-sm mt-2 text-green-600 dark:text-green-300">
              策略代码和元信息已自动填充到下方表单，请检查并保存
            </AlertDescription>
          </Alert>
        )}

        {/* 使用说明 */}
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>使用说明</AlertTitle>
          <AlertDescription className="text-sm space-y-2 mt-2">
            <ol className="list-decimal list-inside space-y-1">
              <li>填写详细的策略需求描述（包括策略类型、核心逻辑、技术指标等）</li>
              <li>点击"使用AI生成"按钮，系统将调用后端AI服务</li>
              <li><strong>任务在后台异步执行</strong>，您可以离开此页面继续其他操作</li>
              <li>任务进度会在页面右上角实时显示</li>
              <li>生成成功后，策略代码和元信息将<strong>自动填充</strong>到表单中</li>
              <li>检查生成的代码，点击"验证代码"确保正确性</li>
              <li>点击"创建策略"保存</li>
            </ol>
            <div className="mt-3 p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded border border-yellow-200 dark:border-yellow-800">
              <p className="text-xs text-yellow-800 dark:text-yellow-200">
                <strong>⚠️ 重要提示：</strong>同一时间只能有一个AI生成任务进行，以节省资源和成本。
              </p>
            </div>
          </AlertDescription>
        </Alert>

        {/* 策略需求输入 */}
        <div className="space-y-2">
          <Label htmlFor="strategy-requirement" className="text-base font-semibold">
            策略需求描述 *
          </Label>
          <Textarea
            id="strategy-requirement"
            value={strategyRequirement}
            onChange={(e) => setStrategyRequirement(e.target.value)}
            placeholder="详细描述你的策略需求..."
            className="min-h-[300px] font-mono text-sm"
            disabled={isGenerating}
          />
          <p className="text-xs text-muted-foreground">
            💡 提示：描述越详细，AI生成的代码质量越高。<strong>必须包含策略类别</strong>（momentum, reversal, mean_reversion, factor, ml, arbitrage, hybrid, trend_following, breakout, statistical 之一）
          </p>
        </div>

        {/* 策略描述示例 */}
        <div className="pt-4 border-t space-y-3">
          <p className="text-sm font-medium">📝 策略描述示例:</p>
          <div className="bg-muted/50 rounded-lg p-4 space-y-3 text-xs">
            <div>
              <p className="font-medium text-green-600 dark:text-green-400 mb-1">✅ 好的描述（详细清晰）:</p>
              <pre className="text-muted-foreground whitespace-pre-wrap">
{`**策略类型**: 趋势跟踪策略

**策略类别**: trend_following (必须指定！)

**核心逻辑**:
- 使用EMA(20,60,120)定义趋势，MACD(12,26,9)捕捉动能
- 买入条件：股价>EMA120 且 EMA20>EMA60 且 MACD零轴上方金叉
- 卖出条件：MACD死叉 或 股价跌破EMA60

**技术指标**: EMA, MACD

**参数配置**: ema_short:20, ema_mid:60, ema_long:120

**风险控制**: 成交量>20日均量80%, 每期选20只股票`}
              </pre>
            </div>
            <div>
              <p className="font-medium text-red-600 dark:text-red-400 mb-1">❌ 不好的描述（过于简单）:</p>
              <pre className="text-muted-foreground">
{`使用MACD策略
均线策略
一个赚钱的策略`}
              </pre>
            </div>
          </div>
        </div>

        {/* AI提供商信息 */}
        <div className="pt-4 border-t">
          <Alert>
            <CheckCircle className="h-4 w-4" />
            <AlertTitle>AI提供商</AlertTitle>
            <AlertDescription className="text-sm mt-2">
              系统当前使用 <strong>DeepSeek</strong> 作为默认AI提供商。管理员可以在后台管理页面配置其他AI提供商（Gemini、OpenAI等）。
              <br />
              <span className="text-xs text-muted-foreground mt-1 block">
                生成任务会在后台Celery worker中异步执行，通常耗时10-60秒。
              </span>
            </AlertDescription>
          </Alert>
        </div>
      </CardContent>
    </Card>
  )
}
