/**
 * 策略编辑页面 (V2.0)
 * 用于编辑现有策略的代码、元信息和配置
 */

'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import dynamic from 'next/dynamic'
import { useTheme } from 'next-themes'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  ArrowLeft,
  Save,
  CheckCircle,
  XCircle,
  Loader2,
  AlertTriangle
} from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { apiClient } from '@/lib/api-client'
import type { Strategy } from '@/types/strategy'
import { STRATEGY_CATEGORIES } from '@/types/strategy'

// 动态导入 Monaco Editor (客户端组件)
const Editor = dynamic(() => import('@monaco-editor/react'), {
  ssr: false,
  loading: () => (
    <div className="h-[600px] flex items-center justify-center border rounded-lg bg-muted">
      <Loader2 className="h-8 w-8 animate-spin" />
    </div>
  )
})

function EditStrategyContent() {
  const params = useParams()
  const router = useRouter()
  const { toast } = useToast()
  const { theme } = useTheme()
  const strategyId = parseInt(params.id as string)

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [validating, setValidating] = useState(false)
  const [validationResult, setValidationResult] = useState<any>(null)
  const [strategy, setStrategy] = useState<Strategy | null>(null)

  // 表单字段
  const [name, setName] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [className, setClassName] = useState('')
  const [description, setDescription] = useState('')
  const [code, setCode] = useState('')
  const [category, setCategory] = useState('')
  const [tags, setTags] = useState('')

  useEffect(() => {
    loadStrategy()
  }, [strategyId])

  const loadStrategy = async () => {
    try {
      setLoading(true)
      const response = await apiClient.getStrategy(strategyId)
      if (response.data) {
        const s = response.data
        setStrategy(s)
        setName(s.name)
        setDisplayName(s.display_name)
        setClassName(s.class_name)
        setDescription(s.description || '')
        setCode(s.code)
        setCategory(s.category || '')
        setTags(s.tags?.join(', ') || '')
      }
    } catch (error) {
      console.error('Failed to load strategy:', error)
      toast({
        title: '加载失败',
        description: '无法加载策略详情',
        variant: 'destructive'
      })
      router.push('/strategies')
    } finally {
      setLoading(false)
    }
  }

  // 验证代码
  const handleValidate = async () => {
    if (!code.trim()) {
      toast({
        title: '验证失败',
        description: '请输入策略代码',
        variant: 'destructive'
      })
      return
    }

    try {
      setValidating(true)
      const response = await apiClient.validateStrategy(code)
      if (response.data) {
        setValidationResult(response.data)
        if (response.data.is_valid) {
          toast({
            title: '验证成功',
            description: '代码验证通过'
          })
        } else {
          toast({
            title: '验证失败',
            description: '代码存在错误',
            variant: 'destructive'
          })
        }
      }
    } catch (error) {
      console.error('Validation failed:', error)
      toast({
        title: '验证失败',
        description: '无法验证代码',
        variant: 'destructive'
      })
    } finally {
      setValidating(false)
    }
  }

  // 提交更新
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!strategy) return

    // 内置策略不允许编辑
    if (strategy.source_type === 'builtin') {
      toast({
        title: '编辑失败',
        description: '内置策略不允许编辑',
        variant: 'destructive'
      })
      return
    }

    if (!name || !displayName || !className || !code) {
      toast({
        title: '提交失败',
        description: '请填写所有必填字段',
        variant: 'destructive'
      })
      return
    }

    try {
      setSaving(true)
      const response = await apiClient.updateStrategy(strategyId, {
        name,
        display_name: displayName,
        class_name: className,
        code,
        description,
        category: category || undefined,
        tags: tags ? tags.split(',').map(t => t.trim()).filter(Boolean) : undefined
      })

      if (response.data) {
        toast({
          title: '保存成功',
          description: '策略已成功更新'
        })
        router.push(`/strategies/${strategyId}/code`)
      }
    } catch (error: any) {
      console.error('Failed to update strategy:', error)
      toast({
        title: '保存失败',
        description: error.response?.data?.message || '无法更新策略',
        variant: 'destructive'
      })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="container mx-auto py-6 px-4 max-w-5xl">
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <Loader2 className="inline-block h-8 w-8 animate-spin" />
            <p className="mt-4 text-muted-foreground">加载中...</p>
          </div>
        </div>
      </div>
    )
  }

  if (!strategy) {
    return (
      <div className="container mx-auto py-6 px-4 max-w-5xl">
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <AlertTriangle className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">策略不存在</h3>
              <p className="text-muted-foreground mb-6">
                找不到该策略,可能已被删除
              </p>
              <Button onClick={() => router.push('/strategies')}>
                <ArrowLeft className="mr-2 h-4 w-4" />
                返回策略列表
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // 内置策略不允许编辑
  if (strategy.source_type === 'builtin') {
    return (
      <div className="container mx-auto py-6 px-4 max-w-5xl">
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <AlertTriangle className="mx-auto h-12 w-12 text-yellow-500 mb-4" />
              <h3 className="text-lg font-semibold mb-2">无法编辑内置策略</h3>
              <p className="text-muted-foreground mb-6">
                内置策略不允许直接编辑。您可以克隆此策略创建一个可编辑的副本。
              </p>
              <div className="flex gap-4 justify-center">
                <Button
                  variant="outline"
                  onClick={() => router.push('/strategies')}
                >
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  返回列表
                </Button>
                <Button
                  onClick={() => router.push(`/strategies/create?clone=${strategyId}`)}
                >
                  克隆策略
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  // 已发布或待审核的策略不允许编辑
  if (strategy.publish_status === 'pending_review' || strategy.publish_status === 'approved') {
    const statusText = strategy.publish_status === 'pending_review' ? '待审核' : '已发布'
    return (
      <div className="container mx-auto py-6 px-4 max-w-5xl">
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <AlertTriangle className="mx-auto h-12 w-12 text-yellow-500 mb-4" />
              <h3 className="text-lg font-semibold mb-2">无法编辑{statusText}的策略</h3>
              <p className="text-muted-foreground mb-6">
                {strategy.publish_status === 'pending_review'
                  ? '策略正在审核中，如需修改请先撤回发布申请。'
                  : '已发布的策略不允许直接编辑，以确保稳定性。您可以克隆此策略创建一个可编辑的副本。'
                }
              </p>
              <div className="flex gap-4 justify-center">
                <Button
                  variant="outline"
                  onClick={() => router.push(`/strategies/${strategyId}/code`)}
                >
                  <ArrowLeft className="mr-2 h-4 w-4" />
                  返回策略详情
                </Button>
                <Button
                  onClick={() => router.push(`/strategies/create?clone=${strategyId}`)}
                >
                  克隆策略
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-6 px-4 max-w-5xl">
      {/* 返回按钮 */}
      <Button
        variant="ghost"
        className="mb-4"
        onClick={() => router.push(`/strategies/${strategyId}/code`)}
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        返回策略详情
      </Button>

      {/* 页面标题 */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold">编辑策略</h1>
        <p className="text-muted-foreground mt-1">
          修改策略代码和元信息
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* 基本信息 */}
        <Card>
          <CardHeader>
            <CardTitle>基本信息</CardTitle>
            <CardDescription>
              修改策略的基本信息和标识
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="name">策略标识 *</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="例如: my_momentum_strategy"
                  required
                />
                <p className="text-xs text-muted-foreground">
                  唯一标识符,只能包含字母、数字和下划线
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="displayName">显示名称 *</Label>
                <Input
                  id="displayName"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="例如: 我的动量策略"
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="className">Python 类名 *</Label>
                <Input
                  id="className"
                  value={className}
                  onChange={(e) => setClassName(e.target.value)}
                  placeholder="例如: MyMomentumStrategy"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="category">策略类别</Label>
                <Select value={category} onValueChange={setCategory}>
                  <SelectTrigger id="category">
                    <SelectValue placeholder="请选择策略类别" />
                  </SelectTrigger>
                  <SelectContent>
                    {STRATEGY_CATEGORIES.map((cat) => (
                      <SelectItem key={cat.value} value={cat.value}>
                        <div className="flex flex-col">
                          <span>{cat.label}</span>
                          <span className="text-xs text-muted-foreground">{cat.description}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">策略描述</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="简要描述策略的核心逻辑和特点..."
                rows={3}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="tags">标签</Label>
              <Input
                id="tags"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="用逗号分隔,例如: 动量, 短期, 高频"
              />
            </div>
          </CardContent>
        </Card>

        {/* 策略代码 */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>策略代码 *</CardTitle>
                <CardDescription>
                  编辑 Python 策略类代码
                </CardDescription>
              </div>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleValidate}
                disabled={validating || !code.trim()}
              >
                {validating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    验证中...
                  </>
                ) : (
                  <>
                    <CheckCircle className="mr-2 h-4 w-4" />
                    验证代码
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Monaco 代码编辑器 */}
            <div className="border rounded-lg overflow-hidden">
              <Editor
                height="600px"
                defaultLanguage="python"
                value={code}
                onChange={(value) => setCode(value || '')}
                theme={theme === 'dark' ? 'vs-dark' : 'light'}
                options={{
                  minimap: { enabled: true },
                  fontSize: 14,
                  lineNumbers: 'on',
                  rulers: [80, 120],
                  wordWrap: 'on',
                  formatOnPaste: true,
                  formatOnType: true,
                  autoIndent: 'full',
                  tabSize: 4,
                  scrollBeyondLastLine: false,
                  folding: true,
                  renderWhitespace: 'selection',
                  bracketPairColorization: {
                    enabled: true
                  }
                }}
              />
            </div>

            {/* 验证结果 */}
            {validationResult && (
              <div>
                {validationResult.is_valid ? (
                  <div className="bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800 rounded-lg p-4">
                    <div className="flex items-start gap-2">
                      <CheckCircle className="h-5 w-5 text-green-600 mt-0.5" />
                      <div className="flex-1">
                        <p className="font-medium text-green-900 dark:text-green-100">
                          验证通过
                        </p>
                        <p className="text-sm text-green-700 dark:text-green-300 mt-1">
                          代码结构正确,风险等级: <Badge>{validationResult.risk_level}</Badge>
                        </p>
                        {validationResult.warnings && validationResult.warnings.length > 0 && (
                          <div className="mt-2">
                            <p className="text-sm font-medium">警告:</p>
                            <ul className="list-disc list-inside text-sm text-green-700 dark:text-green-300">
                              {validationResult.warnings.map((warning: string, index: number) => (
                                <li key={index}>{warning}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-lg p-4">
                    <div className="flex items-start gap-2">
                      <XCircle className="h-5 w-5 text-red-600 mt-0.5" />
                      <div className="flex-1">
                        <p className="font-medium text-red-900 dark:text-red-100">
                          验证失败
                        </p>
                        {validationResult.errors && validationResult.errors.length > 0 && (
                          <div className="mt-2">
                            <p className="text-sm font-medium">错误:</p>
                            <ul className="list-disc list-inside text-sm text-red-700 dark:text-red-300">
                              {validationResult.errors.map((error: string, index: number) => (
                                <li key={index}>{error}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* 提交按钮 */}
        <div className="flex gap-4">
          <Button
            type="button"
            variant="outline"
            onClick={() => router.push(`/strategies/${strategyId}/code`)}
            className="flex-1"
          >
            取消
          </Button>
          <Button
            type="submit"
            disabled={saving}
            className="flex-1"
          >
            {saving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                保存中...
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                保存修改
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}

export default function EditStrategyPage() {
  return (
    <ProtectedRoute requireAuth={true}>
      <EditStrategyContent />
    </ProtectedRoute>
  )
}
