/**
 * AI策略生成助手组件 V2
 * 支持直接调用后端AI API生成策略
 */

'use client'

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  Sparkles,
  Wand2,
  Loader2,
  CheckCircle,
  AlertCircle
} from 'lucide-react'
import { useToast } from '@/hooks/use-toast'

interface AIStrategyPromptHelperProps {
  onStrategyGenerated?: (strategyCode: string, metadata: any) => void
}

export default function AIStrategyPromptHelperV2({ onStrategyGenerated }: AIStrategyPromptHelperProps) {
  const { toast } = useToast()
  const [generating, setGenerating] = useState(false)

  // 用户输入的策略需求
  const [strategyRequirement, setStrategyRequirement] = useState(`**策略类型**: 简单均线策略

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

  const generateWithAI = async () => {
    if (!strategyRequirement.trim()) {
      toast({
        title: '请填写策略需求',
        description: '请先描述你的策略需求',
        variant: 'destructive'
      })
      return
    }

    try {
      setGenerating(true)
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

      toast({
        title: 'AI生成中',
        description: '正在调用后端AI服务生成策略，请稍候...'
      })

      const response = await fetch(`${API_BASE_URL}/api/ai-strategy/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          strategy_requirement: strategyRequirement,
          use_custom_prompt: false
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'AI生成失败')
      }

      const result = await response.json()

      if (result.success && result.strategy_code && result.strategy_metadata) {
        toast({
          title: '生成成功',
          description: `使用 ${result.provider_used} 生成策略，耗时 ${result.generation_time}秒，使用 ${result.tokens_used} tokens`
        })

        // 回调传递生成的代码和元信息
        if (onStrategyGenerated) {
          onStrategyGenerated(result.strategy_code, result.strategy_metadata)
        }
      } else {
        throw new Error(result.error_message || 'AI生成失败')
      }
    } catch (error) {
      console.error('AI generation error:', error)
      toast({
        title: 'AI生成失败',
        description: error instanceof Error ? error.message : '未知错误',
        variant: 'destructive'
      })
    } finally {
      setGenerating(false)
    }
  }

  return (
    <Card className="border-2 border-primary/20 bg-gradient-to-br from-primary/5 to-primary/10">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            <CardTitle>AI 策略生成助手</CardTitle>
          </div>
          <Button
            onClick={generateWithAI}
            disabled={generating}
            className="gap-2"
          >
            {generating ? (
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
        <CardDescription>
          直接使用后端AI（DeepSeek、Gemini）生成完整的策略代码和元信息
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* 使用说明 */}
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>使用说明</AlertTitle>
          <AlertDescription className="text-sm space-y-2 mt-2">
            <ol className="list-decimal list-inside space-y-1">
              <li>填写详细的策略需求描述（包括策略类型、核心逻辑、技术指标等）</li>
              <li>点击"使用AI生成"按钮，系统将调用后端AI服务</li>
              <li>生成成功后，策略代码和元信息将自动填充到表单中</li>
              <li>检查生成的代码，点击"验证代码"确保正确性</li>
              <li>填写或调整策略标识、显示名称等基本信息</li>
              <li>点击"创建策略"保存</li>
            </ol>
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
            disabled={generating}
          />
          <p className="text-xs text-muted-foreground">
            💡 提示：描述越详细，AI生成的代码质量越高。包含<strong>策略类别</strong>（momentum, reversal, mean_reversion等）、核心逻辑、技术指标、参数配置、风险控制等信息。
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

**策略类别**: trend_following (必须使用: momentum, reversal, mean_reversion, factor, ml, arbitrage, hybrid, trend_following, breakout, statistical 之一)

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
            </AlertDescription>
          </Alert>
        </div>
      </CardContent>
    </Card>
  )
}
