/**
 * AI 策略生成专用页面
 *
 * 流程：
 * 1. 用户选择策略类型（入场/离场/选股）
 * 2. 用户描述策略需求
 * 3. 提交后台生成任务（异步）
 * 4. 生成完成后自动验证代码
 * 5. 验证通过后自动保存，跳转到策略列表
 */

'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter } from 'next/navigation'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import {
  ArrowLeft,
  Sparkles,
  Wand2,
  Loader2,
  TrendingUp,
  TrendingDown,
  Filter,
  CheckCircle,
  XCircle,
  AlertCircle,
  X,
  Save,
} from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { useAIGenerationTask } from '@/contexts/AIGenerationTaskContext'
import { apiClient } from '@/lib/api-client'
import { useAuthStore } from '@/stores/auth-store'

type StrategyType = 'entry' | 'exit' | 'stock_selection'

const STRATEGY_TYPE_OPTIONS = [
  {
    value: 'entry' as StrategyType,
    label: '入场策略',
    desc: '决定何时买入股票的信号策略',
    icon: <TrendingUp className="h-5 w-5" />,
    hint: '例如：均线金叉、MACD上穿零轴、放量突破等买入信号',
  },
  {
    value: 'exit' as StrategyType,
    label: '离场策略',
    desc: '决定何时卖出持仓的止盈止损策略',
    icon: <TrendingDown className="h-5 w-5" />,
    hint: '例如：均线死叉、跌破支撑位、固定止损比例等卖出信号',
  },
  {
    value: 'stock_selection' as StrategyType,
    label: '选股策略',
    desc: '从全市场筛选出目标股票池',
    icon: <Filter className="h-5 w-5" />,
    hint: '例如：量价选股、财务指标筛选、动量因子排名等选股方法',
  },
]

const DEFAULT_REQUIREMENTS: Record<StrategyType, string> = {
  entry: `**策略类别**: trend_following

**核心逻辑**:
- 使用MA(5, 20)判断趋势方向
- 买入条件：MA5上穿MA20（金叉），收盘价站上MA20
- 买入确认：成交量大于20日均量的80%

**技术指标**: MA（移动平均线），成交量

**参数配置**:
- ma_fast: 5 (快速均线周期)
- ma_slow: 20 (慢速均线周期)
- volume_ratio: 0.8 (成交量比率阈值)

**风险控制**:
- 每期选择评分最高的前10只股票
- 单股仓位不超过10%`,

  exit: `**策略类别**: trend_following

**核心逻辑**:
- 止损条件：持仓价格跌破买入价的 -8%，立即清仓
- 止盈条件：持仓涨幅超过 +20% 后回落 5%，触发移动止盈
- 技术止损：MA5下穿MA20死叉，且价格跌破MA20，卖出

**技术指标**: MA（移动平均线），持仓成本计算

**参数配置**:
- stop_loss: 0.08 (止损比例)
- take_profit: 0.20 (止盈触发比例)
- trailing_stop: 0.05 (移动止盈回撤比例)
- ma_fast: 5
- ma_slow: 20

**信号语义**: 返回 -1 表示清仓信号，0 表示继续持有`,

  stock_selection: `**策略类别**: factor

**核心逻辑**:
- 动量因子：过去20日涨幅排名前30%
- 量价因子：成交量放大且价格突破近20日最高价
- 综合打分：两个因子等权加总，取前50只股票

**技术指标**: 动量、量价突破

**参数配置**:
- lookback: 20 (回看周期，单位：日)
- momentum_pct: 0.30 (动量因子选股比例)
- top_n: 50 (最终入选股票数)
- min_price: 5.0 (最低价格过滤，单位：元)
- min_volume_ratio: 1.2 (成交量放大倍数)

**信号语义**: 返回 1 表示入选股票池，0 表示不入选`,
}

function AICreateStrategyContent() {
  const router = useRouter()
  const { toast } = useToast()
  const { user } = useAuthStore()
  const { activeTasks, addTask, cancelTask, getTaskResult, clearCachedResult, hasActiveTasks } =
    useAIGenerationTask()

  const [strategyType, setStrategyType] = useState<StrategyType>('entry')
  const [requirement, setRequirement] = useState(DEFAULT_REQUIREMENTS.entry)

  // 阶段：selecting → generating → validating → saving → done
  const [phase, setPhase] = useState<'selecting' | 'generating' | 'validating' | 'saving'>('selecting')
  const [validationResult, setValidationResult] = useState<any>(null)
  const [generatedCode, setGeneratedCode] = useState('')
  const [generatedMetadata, setGeneratedMetadata] = useState<any>(null)

  const currentTask = activeTasks.size > 0 ? Array.from(activeTasks.values())[0] : null
  const isGenerating = currentTask && ['PENDING', 'PROGRESS'].includes(currentTask.status)

  // 监听生成完成 → 自动验证
  useEffect(() => {
    if (currentTask?.status === 'SUCCESS' && currentTask.taskId && phase === 'generating') {
      const result = getTaskResult(currentTask.taskId)
      if (result) {
        clearCachedResult(currentTask.taskId)
        setGeneratedCode(result.strategy_code)
        setGeneratedMetadata(result.strategy_metadata)
        autoValidate(result.strategy_code, result.strategy_metadata)
      }
    }
  }, [currentTask?.status, currentTask?.taskId, phase])

  // 监听生成失败
  useEffect(() => {
    if (currentTask?.status === 'FAILURE' && phase === 'generating') {
      setPhase('selecting')
      toast({
        title: 'AI 生成失败',
        description: currentTask.message || '请稍后重试',
        variant: 'destructive',
      })
    }
  }, [currentTask?.status, phase])

  const autoValidate = async (code: string, metadata: any) => {
    setPhase('validating')
    try {
      const response = await apiClient.validateStrategy(code)
      if (response.data) {
        setValidationResult(response.data)
        if (response.data.is_valid) {
          await autoSave(code, metadata)
        } else {
          toast({
            title: '代码验证未通过',
            description: '生成的代码存在问题，请查看详情或重新生成',
            variant: 'destructive',
          })
          setPhase('selecting')
        }
      }
    } catch (error) {
      console.error('Validation failed:', error)
      toast({
        title: '验证失败',
        description: '无法验证代码，请稍后重试',
        variant: 'destructive',
      })
      setPhase('selecting')
    }
  }

  const autoSave = async (code: string, metadata: any) => {
    setPhase('saving')
    const meta = metadata || {}
    try {
      const response = await apiClient.createStrategy({
        name: meta.strategy_id || `ai_${strategyType}_${Date.now()}`,
        display_name: meta.display_name || `AI ${STRATEGY_TYPE_OPTIONS.find(o => o.value === strategyType)?.label}`,
        class_name: meta.class_name || 'AIGeneratedStrategy',
        code,
        source_type: 'ai',
        strategy_type: strategyType,
        description: meta.description || '',
        category: meta.category || undefined,
        tags: Array.isArray(meta.tags) ? meta.tags : undefined,
      })

      if (response.data) {
        toast({
          title: '策略已创建',
          description: 'AI 策略已自动命名、分类并保存',
        })
        router.push(`/strategies?type=${strategyType}`)
      }
    } catch (error: any) {
      console.error('Save failed:', error)
      toast({
        title: '保存失败',
        description: error.response?.data?.message || '无法保存策略',
        variant: 'destructive',
      })
      setPhase('selecting')
    }
  }

  const handleGenerate = async () => {
    if (!requirement.trim()) {
      toast({ title: '请填写策略需求', variant: 'destructive' })
      return
    }
    if (hasActiveTasks()) {
      toast({
        title: '已有生成任务进行中',
        description: '请等待当前任务完成',
        variant: 'destructive',
      })
      return
    }

    try {
      const response = await apiClient.generateStrategyAsync({
        strategy_requirement: requirement,
        strategy_type: strategyType,
        use_custom_prompt: false,
      })
      addTask(response.task_id, response.provider_used)
      setPhase('generating')
      toast({
        title: 'AI 生成任务已提交',
        description: `使用 ${response.provider_used}，生成完成后将自动验证并保存`,
      })
    } catch (error) {
      console.error('Submit failed:', error)
      toast({ title: '提交失败', variant: 'destructive' })
    }
  }

  const handleCancel = () => {
    if (currentTask) {
      cancelTask(currentTask.taskId)
    }
    setPhase('selecting')
    setValidationResult(null)
    setGeneratedCode('')
    setGeneratedMetadata(null)
  }

  const isProcessing = phase !== 'selecting'

  return (
    <div className="container mx-auto py-6 px-4 max-w-3xl">
      <Button variant="ghost" className="mb-4" onClick={() => router.push('/strategies')}>
        <ArrowLeft className="mr-2 h-4 w-4" />
        返回策略列表
      </Button>

      {/* 页面标题 */}
      <div className="flex items-center gap-3 mb-6">
        <Sparkles className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-3xl font-bold">AI 生成策略</h1>
          <p className="text-muted-foreground mt-1">
            描述你的策略需求，AI 将自动生成、验证并保存
          </p>
        </div>
      </div>

      <div className="space-y-6">
        {/* 步骤指示器 */}
        <div className="flex items-center gap-2 text-sm">
          {[
            { key: 'selecting', label: '① 配置需求' },
            { key: 'generating', label: '② AI 生成' },
            { key: 'validating', label: '③ 验证代码' },
            { key: 'saving', label: '④ 自动保存' },
          ].map((step, idx) => {
            const phases = ['selecting', 'generating', 'validating', 'saving']
            const current = phases.indexOf(phase)
            const stepIdx = phases.indexOf(step.key)
            const isDone = stepIdx < current
            const isActive = stepIdx === current
            return (
              <span
                key={step.key}
                className={`flex items-center gap-1 ${
                  isDone
                    ? 'text-green-600 dark:text-green-400'
                    : isActive
                    ? 'text-primary font-medium'
                    : 'text-muted-foreground'
                }`}
              >
                {isDone && <CheckCircle className="h-3.5 w-3.5" />}
                {isActive && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                {step.label}
                {idx < 3 && <span className="ml-2 text-muted-foreground">→</span>}
              </span>
            )
          })}
        </div>

        {/* 策略类型选择 */}
        <Card>
          <CardHeader>
            <CardTitle>选择策略类型</CardTitle>
            <CardDescription>AI 将根据策略类型生成符合接口规范的代码</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-3">
              {STRATEGY_TYPE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  disabled={isProcessing}
                  onClick={() => {
                    setStrategyType(opt.value)
                    // 如果当前内容是某个默认模板，自动替换为新类型的默认模板
                    const isDefaultContent = Object.values(DEFAULT_REQUIREMENTS).some(
                      (tmpl) => tmpl === requirement
                    )
                    if (isDefaultContent) {
                      setRequirement(DEFAULT_REQUIREMENTS[opt.value])
                    }
                  }}
                  className={`flex flex-col items-center gap-2 rounded-lg border-2 p-4 text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                    strategyType === opt.value
                      ? 'border-primary bg-primary/5 text-primary'
                      : 'border-muted hover:border-muted-foreground/50'
                  }`}
                >
                  {opt.icon}
                  <span className="font-medium">{opt.label}</span>
                  <span className="text-xs text-center text-muted-foreground">{opt.desc}</span>
                </button>
              ))}
            </div>
            <p className="mt-3 text-xs text-muted-foreground">
              💡 {STRATEGY_TYPE_OPTIONS.find((o) => o.value === strategyType)?.hint}
            </p>
          </CardContent>
        </Card>

        {/* 策略需求输入 */}
        <Card>
          <CardHeader>
            <CardTitle>策略需求描述</CardTitle>
            <CardDescription>
              描述越详细，AI 生成质量越高。<strong>必须包含策略类别</strong>（momentum, trend_following, factor 等）
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Textarea
              value={requirement}
              onChange={(e) => setRequirement(e.target.value)}
              placeholder="详细描述你的策略需求..."
              className="min-h-[260px] font-mono text-sm"
              disabled={isProcessing}
            />

            {/* 生成进度 */}
            {phase === 'generating' && currentTask && (
              <Alert className="border-primary/50 bg-primary/5">
                <Loader2 className="h-4 w-4 animate-spin text-primary" />
                <AlertTitle className="text-primary">AI 正在生成策略代码...</AlertTitle>
                <AlertDescription className="mt-2 space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="flex gap-1">
                      {[0, 150, 300].map((d) => (
                        <span
                          key={d}
                          className="w-1.5 h-1.5 bg-primary rounded-full animate-bounce"
                          style={{ animationDelay: `${d}ms` }}
                        />
                      ))}
                    </div>
                    <p className="text-sm">{currentTask.message}</p>
                  </div>
                  {currentTask.providerUsed && (
                    <p className="text-xs text-muted-foreground">
                      AI 提供商：<span className="font-medium text-primary">{currentTask.providerUsed}</span>
                    </p>
                  )}
                  <p className="text-xs text-muted-foreground">
                    生成完成后将自动验证代码并保存策略，通常需要 10–60 秒
                  </p>
                </AlertDescription>
              </Alert>
            )}

            {/* 验证中 */}
            {phase === 'validating' && (
              <Alert className="border-blue-500/50 bg-blue-500/5">
                <Loader2 className="h-4 w-4 animate-spin text-blue-500" />
                <AlertTitle className="text-blue-700 dark:text-blue-400">正在验证代码...</AlertTitle>
                <AlertDescription className="text-sm mt-1">
                  检查代码结构和风险等级
                </AlertDescription>
              </Alert>
            )}

            {/* 保存中 */}
            {phase === 'saving' && (
              <Alert className="border-green-500/50 bg-green-500/5">
                <Loader2 className="h-4 w-4 animate-spin text-green-500" />
                <AlertTitle className="text-green-700 dark:text-green-400">正在保存策略...</AlertTitle>
                <AlertDescription className="text-sm mt-1">
                  自动命名、归类并写入数据库
                </AlertDescription>
              </Alert>
            )}

            {/* 验证结果（仅失败时展示） */}
            {validationResult && !validationResult.is_valid && (
              <Alert className="border-red-500/50 bg-red-500/5">
                <XCircle className="h-4 w-4 text-red-500" />
                <AlertTitle className="text-red-700 dark:text-red-400">代码验证失败</AlertTitle>
                <AlertDescription className="mt-2">
                  <ul className="list-disc list-inside text-sm space-y-1">
                    {validationResult.errors?.map((err: string, i: number) => (
                      <li key={i} className="text-red-600 dark:text-red-400">{err}</li>
                    ))}
                  </ul>
                </AlertDescription>
              </Alert>
            )}

            {/* 操作按钮 */}
            <div className="flex gap-3 pt-1">
              {isProcessing ? (
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleCancel}
                  className="gap-2"
                >
                  <X className="h-4 w-4" />
                  取消
                </Button>
              ) : (
                <>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => router.push('/strategies')}
                  >
                    取消
                  </Button>
                  <Button
                    type="button"
                    onClick={handleGenerate}
                    disabled={!requirement.trim()}
                    className="gap-2 flex-1"
                  >
                    <Wand2 className="h-4 w-4" />
                    AI 生成并自动保存
                  </Button>
                </>
              )}
            </div>
          </CardContent>
        </Card>

        {/* 使用说明 */}
        <Alert>
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>自动化流程说明</AlertTitle>
          <AlertDescription className="text-sm mt-2 space-y-1">
            <p>提交后，系统将自动完成：</p>
            <ol className="list-decimal list-inside space-y-1 mt-1">
              <li>调用 AI（DeepSeek / Gemini）生成策略 Python 代码</li>
              <li>自动提取策略名称、类别、描述、标签等元数据</li>
              <li>自动验证代码结构和风险等级</li>
              <li>验证通过后自动保存，无需手动填写任何表单</li>
            </ol>
            <p className="mt-2 text-muted-foreground">
              如需精细控制代码细节，请使用
              <button
                type="button"
                className="mx-1 underline text-primary"
                onClick={() => router.push('/strategies/create')}
              >
                手动创建
              </button>
              模式。
            </p>
          </AlertDescription>
        </Alert>
      </div>
    </div>
  )
}

export default function AICreateStrategyPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      }
    >
      <ProtectedRoute requireAuth={true}>
        <AICreateStrategyContent />
      </ProtectedRoute>
    </Suspense>
  )
}
