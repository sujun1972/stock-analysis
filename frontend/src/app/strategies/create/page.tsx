/**
 * 策略创建页面 (V2.0)
 * 支持三种创建方式：基于内置模板、AI生成、自定义代码
 */

'use client'

import { useState, useEffect } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
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
import type { Strategy } from '@/types/strategy'

export default function CreateStrategyPage() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { toast } = useToast()

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
        description,
        category: category || undefined,
        tags: tags ? tags.split(',').map(t => t.trim()).filter(Boolean) : undefined
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
                <Input
                  id="category"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  placeholder="例如: momentum, reversal, factor"
                />
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
            <Textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder={`"""
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

    def calculate_scores(self, prices: pd.DataFrame, features: Optional[pd.DataFrame] = None, date: Optional[pd.Timestamp] = None) -> pd.Series:
        # 计算股票评分
        pass

    def generate_signals(self, prices: pd.DataFrame, features: Optional[pd.DataFrame] = None, **kwargs) -> pd.DataFrame:
        # 生成交易信号
        pass
`}
              rows={20}
              className="font-mono text-sm"
              required
            />

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
