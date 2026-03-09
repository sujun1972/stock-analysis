/**
 * 策略创建页面 (V2.0)
 * 支持三种创建方式：基于内置模板、AI生成、自定义代码
 */

'use client'

import { useState, useEffect, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import dynamic from 'next/dynamic'
import { useTheme } from 'next-themes'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  ArrowLeft,
  Building2,
  Sparkles,
  Code,
  Save,
  CheckCircle,
  XCircle,
  Loader2
} from 'lucide-react'
import { useToast } from '@/hooks/use-toast'
import { apiClient } from '@/lib/api-client'
import { STRATEGY_CATEGORIES } from '@/types/strategy'
import AIStrategyPromptHelperV2 from '@/components/strategies/AIStrategyPromptHelperV2'
import { useAuthStore } from '@/stores/auth-store'

// 动态导入 Monaco Editor (客户端组件)
const Editor = dynamic(() => import('@monaco-editor/react'), {
  ssr: false,
  loading: () => (
    <div className="h-[600px] flex items-center justify-center border rounded-lg bg-muted">
      <Loader2 className="h-8 w-8 animate-spin" />
    </div>
  )
})

function CreateStrategyContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { toast } = useToast()
  const { theme } = useTheme()
  const { user } = useAuthStore()

  const source = searchParams.get('source') || 'custom'
  const cloneId = searchParams.get('clone')

  const [loading, setLoading] = useState(false)
  const [validating, setValidating] = useState(false)
  const [validationResult, setValidationResult] = useState<any>(null)

  // 表单字段
  const [name, setName] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [className, setClassName] = useState('')
  const [description, setDescription] = useState('')
  const [code, setCode] = useState('')
  const [category, setCategory] = useState('')
  const [tags, setTags] = useState('')

  // 处理AI生成的策略
  const handleAIGenerated = (strategyCode: string, metadata: any) => {
    setCode(strategyCode)

    if (metadata) {
      if (metadata.strategy_id) setName(metadata.strategy_id)
      if (metadata.display_name) setDisplayName(metadata.display_name)
      if (metadata.class_name) setClassName(metadata.class_name)
      if (metadata.description) setDescription(metadata.description)
      if (metadata.category) setCategory(metadata.category)
      if (metadata.tags && Array.isArray(metadata.tags)) {
        setTags(metadata.tags.join(', '))
      }
    }

    toast({
      title: '已填充表单',
      description: '策略代码和元信息已自动填充，请检查并调整'
    })

    // 自动验证代码
    setTimeout(() => {
      handleValidate()
    }, 500)
  }

  useEffect(() => {
    // 如果是克隆模式,加载原策略
    if (cloneId) {
      loadStrategyForClone(parseInt(cloneId))
    }
  }, [cloneId])

  const loadStrategyForClone = async (id: number) => {
    try {
      const response = await apiClient.getStrategy(id)
      if (response.data) {
        const original = response.data
        setName(`${original.name}_copy`)
        setDisplayName(`${original.display_name} (副本)`)
        setClassName(original.class_name)
        setDescription(original.description || '')
        setCode(original.code)
        setCategory(original.category || '')
        setTags(original.tags?.join(', ') || '')
      }
    } catch (error) {
      console.error('Failed to load strategy:', error)
      toast({
        title: '加载失败',
        description: '无法加载原始策略',
        variant: 'destructive'
      })
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

  // 提交创建
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!name || !displayName || !className || !code) {
      toast({
        title: '提交失败',
        description: '请填写所有必填字段',
        variant: 'destructive'
      })
      return
    }

    try {
      setLoading(true)
      const response = await apiClient.createStrategy({
        name,
        display_name: displayName,
        class_name: className,
        code,
        source_type: source as any,
        strategy_type: 'entry', // 默认为入场策略
        description,
        category: category || undefined,
        tags: tags ? tags.split(',').map(t => t.trim()).filter(Boolean) : undefined,
        user_id: user?.id  // 传递当前用户ID
      })

      if (response.data) {
        toast({
          title: '创建成功',
          description: '策略已成功创建'
        })
        router.push('/strategies')
      }
    } catch (error: any) {
      console.error('Failed to create strategy:', error)
      toast({
        title: '创建失败',
        description: error.response?.data?.message || '无法创建策略',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  // 获取来源图标
  const getSourceIcon = () => {
    switch (source) {
      case 'builtin':
        return <Building2 className="h-5 w-5" />
      case 'ai':
        return <Sparkles className="h-5 w-5" />
      default:
        return <Code className="h-5 w-5" />
    }
  }

  // 获取来源标题
  const getSourceTitle = () => {
    switch (source) {
      case 'builtin':
        return '基于内置模板创建'
      case 'ai':
        return 'AI 生成策略'
      default:
        return '自定义代码策略'
    }
  }

  return (
    <div className="container mx-auto py-6 px-4 max-w-5xl">
      {/* 返回按钮 */}
      <Button
        variant="ghost"
        className="mb-4"
        onClick={() => router.push('/strategies')}
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        返回策略列表
      </Button>

      {/* 页面标题 */}
      <div className="flex items-center gap-3 mb-6">
        {getSourceIcon()}
        <div>
          <h1 className="text-3xl font-bold">{getSourceTitle()}</h1>
          {cloneId && (
            <p className="text-muted-foreground mt-1">
              正在克隆现有策略
            </p>
          )}
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* AI策略生成助手 - 仅在自定义策略模式下显示 */}
        {source === 'custom' && (
          <AIStrategyPromptHelperV2 onStrategyGenerated={handleAIGenerated} />
        )}

        {/* 基本信息 */}
        <Card>
          <CardHeader>
            <CardTitle>基本信息</CardTitle>
            <CardDescription>
              填写策略的基本信息和标识
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
                  编写完整的 Python 策略类代码
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

            {/* 代码模板提示 */}
            {!code && (
              <div className="bg-muted/50 border border-dashed rounded-lg p-4 text-sm text-muted-foreground">
                <p className="font-medium mb-2">💡 代码模板提示：</p>
                <pre className="text-xs overflow-x-auto">{`"""
策略名称: 我的策略
策略说明: 简要说明
"""

from typing import Optional, Dict, Any
import pandas as pd
import numpy as np
from core.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    def __init__(self, name: str = "my_strategy", config: Dict[str, Any] = None):
        super().__init__(name, config)
        # 初始化参数

    def calculate_scores(self, prices: pd.DataFrame,
                        features: Optional[pd.DataFrame] = None,
                        date: Optional[pd.Timestamp] = None) -> pd.Series:
        # 计算股票评分
        pass

    def generate_signals(self, prices: pd.DataFrame,
                        features: Optional[pd.DataFrame] = None,
                        **kwargs) -> pd.DataFrame:
        # 生成交易信号
        pass
`}</pre>
              </div>
            )}

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
            onClick={() => router.push('/strategies')}
            className="flex-1"
          >
            取消
          </Button>
          <Button
            type="submit"
            disabled={loading}
            className="flex-1"
          >
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                创建中...
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                创建策略
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}

export default function CreateStrategyPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    }>
      <ProtectedRoute requireAuth={true}>
        <CreateStrategyContent />
      </ProtectedRoute>
    </Suspense>
  )
}
