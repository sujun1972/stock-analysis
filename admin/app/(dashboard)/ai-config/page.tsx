/**
 * AI配置管理页面
 *
 * 功能：
 * - 管理AI提供商配置（DeepSeek、Gemini、OpenAI等）
 * - 配置API密钥、模型参数
 * - 设置默认提供商和优先级
 *
 * @author Admin Team
 * @since 2026-03-01
 */

'use client'

import { useState, useEffect } from 'react'
import { Plus, Edit, Trash2, Check, X, Key, Sparkles, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import { useToast } from '@/hooks/use-toast'

interface AIProvider {
  id: number
  provider: string
  display_name: string
  api_key: string
  api_base_url: string
  model_name: string
  max_tokens: number
  temperature: number
  is_active: boolean
  is_default: boolean
  priority: number
  rate_limit: number
  timeout: number
  description: string
  created_at: string
  updated_at: string
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export default function AIConfigPage() {
  const { toast } = useToast()
  const [providers, setProviders] = useState<AIProvider[]>([])
  const [loading, setLoading] = useState(true)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [editingProvider, setEditingProvider] = useState<AIProvider | null>(null)
  const [formData, setFormData] = useState({
    provider: '',
    display_name: '',
    api_key: '',
    api_base_url: '',
    model_name: '',
    max_tokens: 8000,
    temperature: 0.7,
    is_active: true,
    is_default: false,
    priority: 50,
    rate_limit: 10,
    timeout: 60,
    description: ''
  })

  useEffect(() => {
    fetchProviders()
  }, [])

  const fetchProviders = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/ai-strategy/providers`)
      if (!response.ok) throw new Error('获取AI提供商列表失败')
      const data = await response.json()
      setProviders(data)
    } catch (error) {
      toast({
        title: '加载失败',
        description: error instanceof Error ? error.message : '未知错误',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = () => {
    setEditingProvider(null)
    setFormData({
      provider: '',
      display_name: '',
      api_key: '',
      api_base_url: '',
      model_name: '',
      max_tokens: 8000,
      temperature: 0.7,
      is_active: true,
      is_default: false,
      priority: 50,
      rate_limit: 10,
      timeout: 60,
      description: ''
    })
    setIsDialogOpen(true)
  }

  const handleEdit = (provider: AIProvider) => {
    setEditingProvider(provider)
    setFormData({
      provider: provider.provider,
      display_name: provider.display_name,
      api_key: provider.api_key.includes('*') ? '' : provider.api_key, // 如果是脱敏的，清空让用户重新输入
      api_base_url: provider.api_base_url,
      model_name: provider.model_name,
      max_tokens: provider.max_tokens,
      temperature: provider.temperature,
      is_active: provider.is_active,
      is_default: provider.is_default,
      priority: provider.priority,
      rate_limit: provider.rate_limit,
      timeout: provider.timeout,
      description: provider.description
    })
    setIsDialogOpen(true)
  }

  const handleSave = async () => {
    try {
      if (editingProvider) {
        // 更新
        const updateData: any = {}
        if (formData.api_key) updateData.api_key = formData.api_key
        if (formData.display_name) updateData.display_name = formData.display_name
        if (formData.api_base_url) updateData.api_base_url = formData.api_base_url
        if (formData.model_name) updateData.model_name = formData.model_name
        updateData.max_tokens = formData.max_tokens
        updateData.temperature = formData.temperature
        updateData.is_active = formData.is_active
        updateData.is_default = formData.is_default
        updateData.priority = formData.priority
        updateData.rate_limit = formData.rate_limit
        updateData.timeout = formData.timeout
        if (formData.description) updateData.description = formData.description

        const response = await fetch(`${API_BASE_URL}/api/ai-strategy/providers/${editingProvider.provider}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updateData)
        })

        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.detail || '更新失败')
        }

        toast({
          title: '更新成功',
          description: `AI提供商 ${formData.display_name} 已更新`
        })
      } else {
        // 创建
        const response = await fetch(`${API_BASE_URL}/api/ai-strategy/providers`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        })

        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.detail || '创建失败')
        }

        toast({
          title: '创建成功',
          description: `AI提供商 ${formData.display_name} 已创建`
        })
      }

      setIsDialogOpen(false)
      fetchProviders()
    } catch (error) {
      toast({
        title: '操作失败',
        description: error instanceof Error ? error.message : '未知错误',
        variant: 'destructive'
      })
    }
  }

  const handleDelete = async (provider: string) => {
    if (!confirm(`确定要删除 ${provider} 吗？`)) return

    try {
      const response = await fetch(`${API_BASE_URL}/api/ai-strategy/providers/${provider}`, {
        method: 'DELETE'
      })

      if (!response.ok) throw new Error('删除失败')

      toast({
        title: '删除成功',
        description: `AI提供商 ${provider} 已删除`
      })

      fetchProviders()
    } catch (error) {
      toast({
        title: '删除失败',
        description: error instanceof Error ? error.message : '未知错误',
        variant: 'destructive'
      })
    }
  }

  const getProviderPreset = (provider: string) => {
    const presets: Record<string, any> = {
      deepseek: {
        display_name: 'DeepSeek',
        api_base_url: 'https://api.deepseek.com/v1',
        model_name: 'deepseek-chat',
        description: 'DeepSeek AI - 高性价比的中文AI模型'
      },
      gemini: {
        display_name: 'Google Gemini',
        api_base_url: 'https://generativelanguage.googleapis.com/v1beta',
        model_name: 'gemini-1.5-flash',
        description: 'Google Gemini - 支持免费额度'
      },
      openai: {
        display_name: 'OpenAI',
        api_base_url: 'https://api.openai.com/v1',
        model_name: 'gpt-4o',
        description: 'OpenAI GPT-4 - 性能优秀'
      }
    }
    return presets[provider] || {}
  }

  const handleProviderChange = (value: string) => {
    const preset = getProviderPreset(value)
    setFormData({
      ...formData,
      provider: value,
      ...preset
    })
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">AI配置管理</h1>
          <p className="text-gray-500 mt-1">管理AI策略生成的提供商配置</p>
        </div>
        <Button onClick={handleCreate} className="gap-2">
          <Plus className="w-4 h-4" />
          添加AI提供商
        </Button>
      </div>

      <div className="grid gap-4">
        {providers.map((provider) => (
          <Card key={provider.id}>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <Sparkles className="w-5 h-5 text-blue-500" />
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      {provider.display_name}
                      {provider.is_default && (
                        <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">默认</span>
                      )}
                      {!provider.is_active && (
                        <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">已禁用</span>
                      )}
                    </CardTitle>
                    <CardDescription className="mt-1">
                      {provider.description || provider.provider}
                    </CardDescription>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleEdit(provider)}
                    className="gap-2"
                  >
                    <Edit className="w-4 h-4" />
                    编辑
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(provider.provider)}
                    className="gap-2 text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="w-4 h-4" />
                    删除
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-gray-500">提供商</p>
                  <p className="font-medium">{provider.provider}</p>
                </div>
                <div>
                  <p className="text-gray-500">模型</p>
                  <p className="font-medium">{provider.model_name}</p>
                </div>
                <div>
                  <p className="text-gray-500">API密钥</p>
                  <p className="font-mono text-xs">{provider.api_key}</p>
                </div>
                <div>
                  <p className="text-gray-500">优先级</p>
                  <p className="font-medium">{provider.priority}</p>
                </div>
                <div>
                  <p className="text-gray-500">最大Tokens</p>
                  <p className="font-medium">{provider.max_tokens}</p>
                </div>
                <div>
                  <p className="text-gray-500">温度</p>
                  <p className="font-medium">{provider.temperature}</p>
                </div>
                <div>
                  <p className="text-gray-500">限流</p>
                  <p className="font-medium">{provider.rate_limit}/分钟</p>
                </div>
                <div>
                  <p className="text-gray-500">超时</p>
                  <p className="font-medium">{provider.timeout}秒</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}

        {providers.length === 0 && (
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-12">
              <Sparkles className="w-12 h-12 text-gray-400 mb-4" />
              <p className="text-gray-500 mb-4">暂无AI提供商配置</p>
              <Button onClick={handleCreate} className="gap-2">
                <Plus className="w-4 h-4" />
                添加第一个AI提供商
              </Button>
            </CardContent>
          </Card>
        )}
      </div>

      {/* 编辑/创建对话框 */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingProvider ? '编辑AI提供商' : '添加AI提供商'}</DialogTitle>
            <DialogDescription>
              配置AI服务提供商的API信息和参数
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            {!editingProvider && (
              <div className="grid gap-2">
                <Label htmlFor="provider">提供商类型 *</Label>
                <Select value={formData.provider} onValueChange={handleProviderChange}>
                  <SelectTrigger>
                    <SelectValue placeholder="选择AI提供商" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="deepseek">DeepSeek</SelectItem>
                    <SelectItem value="gemini">Google Gemini</SelectItem>
                    <SelectItem value="openai">OpenAI</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="grid gap-2">
              <Label htmlFor="display_name">显示名称 *</Label>
              <Input
                id="display_name"
                value={formData.display_name}
                onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                placeholder="例如: DeepSeek"
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="api_key">
                API密钥 * {editingProvider && <span className="text-xs text-gray-500">(留空则不修改)</span>}
              </Label>
              <Input
                id="api_key"
                type="password"
                value={formData.api_key}
                onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                placeholder="sk-xxxxxxxxxxxxxxxx"
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="api_base_url">API基础URL</Label>
              <Input
                id="api_base_url"
                value={formData.api_base_url}
                onChange={(e) => setFormData({ ...formData, api_base_url: e.target.value })}
                placeholder="https://api.deepseek.com/v1"
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="model_name">模型名称</Label>
              <Input
                id="model_name"
                value={formData.model_name}
                onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                placeholder="deepseek-chat"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="max_tokens">最大Tokens</Label>
                <Input
                  id="max_tokens"
                  type="number"
                  value={formData.max_tokens}
                  onChange={(e) => setFormData({ ...formData, max_tokens: parseInt(e.target.value) })}
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="temperature">温度 (0-1)</Label>
                <Input
                  id="temperature"
                  type="number"
                  step="0.1"
                  min="0"
                  max="1"
                  value={formData.temperature}
                  onChange={(e) => setFormData({ ...formData, temperature: parseFloat(e.target.value) })}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="priority">优先级</Label>
                <Input
                  id="priority"
                  type="number"
                  value={formData.priority}
                  onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) })}
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="rate_limit">限流 (次/分钟)</Label>
                <Input
                  id="rate_limit"
                  type="number"
                  value={formData.rate_limit}
                  onChange={(e) => setFormData({ ...formData, rate_limit: parseInt(e.target.value) })}
                />
              </div>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="timeout">超时时间 (秒)</Label>
              <Input
                id="timeout"
                type="number"
                value={formData.timeout}
                onChange={(e) => setFormData({ ...formData, timeout: parseInt(e.target.value) })}
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="description">描述</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="简短描述这个AI提供商..."
                rows={2}
              />
            </div>

            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="space-y-0.5">
                <Label>启用</Label>
                <p className="text-sm text-gray-500">启用后可用于策略生成</p>
              </div>
              <Switch
                checked={formData.is_active}
                onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
              />
            </div>

            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="space-y-0.5">
                <Label>设为默认</Label>
                <p className="text-sm text-gray-500">作为默认的AI提供商</p>
              </div>
              <Switch
                checked={formData.is_default}
                onCheckedChange={(checked) => setFormData({ ...formData, is_default: checked })}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              取消
            </Button>
            <Button onClick={handleSave}>
              {editingProvider ? '保存' : '创建'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
