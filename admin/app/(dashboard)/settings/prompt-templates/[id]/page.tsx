/**
 * 提示词模板编辑页面
 *
 * 功能:
 * - 编辑模板基本信息（名称、类型、版本等）
 * - 编辑提示词内容（System Prompt、User Prompt Template）
 * - 管理变量（添加/删除必填和可选变量）
 * - 配置AI参数（提供商、模型、Temperature等）
 * - 实时预览渲染结果
 * - 查看统计信息
 *
 * 路由: /settings/prompt-templates/[id]
 *
 * @author Admin Team
 * @since 2026-03-11
 */

'use client'

import { useEffect, useState, useCallback } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import logger from '@/lib/logger'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { ArrowLeft, Save, Eye, FileText, AlertCircle, CheckCircle2 } from 'lucide-react'
import { promptTemplateApi } from '@/lib/prompt-template-api'
import { PromptTemplate, BUSINESS_TYPES, BUSINESS_TYPE_LABELS } from '@/types/prompt-template'
import { useToast } from '@/hooks/use-toast'

export default function PromptTemplateEditPage() {
  const router = useRouter()
  const params = useParams()
  const { toast } = useToast()
  const templateId = parseInt(params.id as string)

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [template, setTemplate] = useState<PromptTemplate | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewResult, setPreviewResult] = useState<any>(null)

  // 表单字段
  const [formData, setFormData] = useState({
    template_name: '',
    business_type: '',
    template_key: '',
    system_prompt: '',
    user_prompt_template: '',
    output_format: '',
    required_variables: {} as Record<string, string>,
    optional_variables: {} as Record<string, string>,
    version: '1.0.0',
    is_active: true,
    is_default: false,
    recommended_provider: 'deepseek',
    recommended_model: 'deepseek-chat',
    recommended_temperature: 0.7,
    recommended_max_tokens: 4000,
    description: '',
    changelog: '',
    tags: [] as string[]
  })

  // 变量编辑状态
  const [newVarKey, setNewVarKey] = useState('')
  const [newVarDesc, setNewVarDesc] = useState('')
  const [isOptional, setIsOptional] = useState(false)

  const loadTemplate = useCallback(async () => {
    try {
      setLoading(true)
      const data = await promptTemplateApi.get(templateId)
      setTemplate(data)
      setFormData({
        template_name: data.template_name,
        business_type: data.business_type,
        template_key: data.template_key,
        system_prompt: data.system_prompt || '',
        user_prompt_template: data.user_prompt_template,
        output_format: data.output_format || '',
        required_variables: data.required_variables || {},
        optional_variables: data.optional_variables || {},
        version: data.version,
        is_active: data.is_active,
        is_default: data.is_default,
        recommended_provider: data.recommended_provider || 'deepseek',
        recommended_model: data.recommended_model || 'deepseek-chat',
        recommended_temperature: data.recommended_temperature || 0.7,
        recommended_max_tokens: data.recommended_max_tokens || 4000,
        description: data.description || '',
        changelog: data.changelog || '',
        tags: data.tags || []
      })
    } catch (error) {
      logger.error('Failed to load template', error)
      toast({
        title: '加载失败',
        description: '无法加载模板数据',
        variant: 'destructive'
      })
    } finally {
      setLoading(false)
    }
  }, [templateId, toast])

  useEffect(() => {
    loadTemplate()
  }, [loadTemplate])

  const handleSave = async () => {
    try {
      setSaving(true)
      await promptTemplateApi.update(templateId, formData)
      toast({
        title: '保存成功',
        description: '提示词模板已更新'
      })
      router.push('/settings/prompt-templates')
    } catch (error) {
      logger.error('Failed to save template', error)
      toast({
        title: '保存失败',
        description: '无法保存模板',
        variant: 'destructive'
      })
    } finally {
      setSaving(false)
    }
  }

  const handlePreview = async () => {
    try {
      setPreviewLoading(true)
      // 构造测试变量
      const testVariables: Record<string, any> = {}
      Object.keys(formData.required_variables).forEach(key => {
        testVariables[key] = `<${key}_示例值>`
      })

      const result = await promptTemplateApi.preview(templateId, testVariables)
      setPreviewResult(result)
      toast({
        title: '预览成功',
        description: '模板渲染结果已生成'
      })
    } catch (error) {
      logger.error('Failed to preview template', error)
      toast({
        title: '预览失败',
        description: '模板渲染出错，请检查语法',
        variant: 'destructive'
      })
    } finally {
      setPreviewLoading(false)
    }
  }

  const addVariable = () => {
    if (!newVarKey.trim() || !newVarDesc.trim()) {
      toast({
        title: '输入不完整',
        description: '请填写变量名称和描述',
        variant: 'destructive'
      })
      return
    }

    setFormData(prev => ({
      ...prev,
      [isOptional ? 'optional_variables' : 'required_variables']: {
        ...(isOptional ? prev.optional_variables : prev.required_variables),
        [newVarKey]: newVarDesc
      }
    }))

    setNewVarKey('')
    setNewVarDesc('')
  }

  const removeVariable = (key: string, optional: boolean) => {
    setFormData(prev => {
      const variables = { ...(optional ? prev.optional_variables : prev.required_variables) }
      delete variables[key]
      return {
        ...prev,
        [optional ? 'optional_variables' : 'required_variables']: variables
      }
    })
  }

  const addTag = (tag: string) => {
    if (tag.trim() && !formData.tags.includes(tag.trim())) {
      setFormData(prev => ({
        ...prev,
        tags: [...prev.tags, tag.trim()]
      }))
    }
  }

  const removeTag = (tag: string) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags.filter(t => t !== tag)
    }))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">加载中...</div>
      </div>
    )
  }

  if (!template) {
    return (
      <div className="flex items-center justify-center h-64">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>模板不存在</AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            返回
          </Button>
          <div>
            <h1 className="text-2xl font-bold">编辑提示词模板</h1>
            <p className="text-sm text-muted-foreground">ID: {templateId}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={handlePreview} disabled={previewLoading}>
            <Eye className="h-4 w-4 mr-2" />
            {previewLoading ? '渲染中...' : '预览'}
          </Button>
          <Button onClick={handleSave} disabled={saving}>
            <Save className="h-4 w-4 mr-2" />
            {saving ? '保存中...' : '保存'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧：基本信息和配置 */}
        <div className="lg:col-span-2 space-y-6">
          {/* 基本信息 */}
          <Card>
            <CardHeader>
              <CardTitle>基本信息</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>模板名称 *</Label>
                  <Input
                    value={formData.template_name}
                    onChange={(e) => setFormData({ ...formData, template_name: e.target.value })}
                    placeholder="市场情绪四维度灵魂拷问"
                  />
                </div>
                <div>
                  <Label>业务类型 *</Label>
                  <Select
                    value={formData.business_type}
                    onValueChange={(value) => setFormData({ ...formData, business_type: value })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {Object.entries(BUSINESS_TYPE_LABELS).map(([value, label]) => (
                        <SelectItem key={value} value={value}>{label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>模板Key *</Label>
                  <Input
                    value={formData.template_key}
                    onChange={(e) => setFormData({ ...formData, template_key: e.target.value })}
                    placeholder="soul_questioning_v1"
                    disabled
                  />
                  <p className="text-xs text-muted-foreground mt-1">模板Key创建后不可修改</p>
                </div>
                <div>
                  <Label>版本号</Label>
                  <Input
                    value={formData.version}
                    onChange={(e) => setFormData({ ...formData, version: e.target.value })}
                    placeholder="1.0.0"
                  />
                </div>
              </div>

              <div>
                <Label>描述</Label>
                <Textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="简要描述此模板的用途..."
                  rows={2}
                />
              </div>
            </CardContent>
          </Card>

          {/* 提示词内容 */}
          <Card>
            <CardHeader>
              <CardTitle>提示词内容</CardTitle>
              <CardDescription>使用Jinja2语法，变量用 {`{{ variable_name }}`} 表示</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>System Prompt</Label>
                <Textarea
                  value={formData.system_prompt}
                  onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
                  placeholder="你是一位..."
                  rows={4}
                  className="font-mono text-sm"
                />
              </div>

              <div>
                <Label>User Prompt Template *</Label>
                <Textarea
                  value={formData.user_prompt_template}
                  onChange={(e) => setFormData({ ...formData, user_prompt_template: e.target.value })}
                  placeholder="# 分析任务\n\n{{ variable_name }}\n\n..."
                  rows={15}
                  className="font-mono text-sm"
                />
              </div>

              <div>
                <Label>期望输出格式</Label>
                <Textarea
                  value={formData.output_format}
                  onChange={(e) => setFormData({ ...formData, output_format: e.target.value })}
                  placeholder="JSON格式，包含字段..."
                  rows={2}
                />
              </div>
            </CardContent>
          </Card>

          {/* 变量管理 */}
          <Card>
            <CardHeader>
              <CardTitle>变量管理</CardTitle>
              <CardDescription>定义模板中使用的变量</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* 添加变量 */}
              <div className="flex gap-2">
                <Input
                  placeholder="变量名 (如: trade_date)"
                  value={newVarKey}
                  onChange={(e) => setNewVarKey(e.target.value)}
                  className="flex-1"
                />
                <Input
                  placeholder="变量描述"
                  value={newVarDesc}
                  onChange={(e) => setNewVarDesc(e.target.value)}
                  className="flex-1"
                />
                <Select value={isOptional ? 'optional' : 'required'} onValueChange={(v) => setIsOptional(v === 'optional')}>
                  <SelectTrigger className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="required">必填</SelectItem>
                    <SelectItem value="optional">可选</SelectItem>
                  </SelectContent>
                </Select>
                <Button onClick={addVariable}>添加</Button>
              </div>

              {/* 必填变量列表 */}
              <div>
                <Label className="text-sm font-semibold">必填变量</Label>
                <div className="mt-2 space-y-2">
                  {Object.entries(formData.required_variables).map(([key, desc]) => (
                    <div key={key} className="flex items-center justify-between p-2 bg-muted rounded">
                      <div className="flex-1">
                        <code className="text-sm font-mono">{key}</code>
                        <span className="text-sm text-muted-foreground ml-2">- {desc}</span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeVariable(key, false)}
                      >
                        删除
                      </Button>
                    </div>
                  ))}
                  {Object.keys(formData.required_variables).length === 0 && (
                    <p className="text-sm text-muted-foreground">暂无必填变量</p>
                  )}
                </div>
              </div>

              {/* 可选变量列表 */}
              <div>
                <Label className="text-sm font-semibold">可选变量</Label>
                <div className="mt-2 space-y-2">
                  {Object.entries(formData.optional_variables).map(([key, desc]) => (
                    <div key={key} className="flex items-center justify-between p-2 bg-muted rounded">
                      <div className="flex-1">
                        <code className="text-sm font-mono">{key}</code>
                        <span className="text-sm text-muted-foreground ml-2">- {desc}</span>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeVariable(key, true)}
                      >
                        删除
                      </Button>
                    </div>
                  ))}
                  {Object.keys(formData.optional_variables).length === 0 && (
                    <p className="text-sm text-muted-foreground">暂无可选变量</p>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 右侧：配置和预览 */}
        <div className="space-y-6">
          {/* AI配置 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">AI配置</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label className="text-sm">推荐提供商</Label>
                <Select
                  value={formData.recommended_provider}
                  onValueChange={(value) => setFormData({ ...formData, recommended_provider: value })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="deepseek">DeepSeek</SelectItem>
                    <SelectItem value="anthropic">Anthropic (Claude)</SelectItem>
                    <SelectItem value="openai">OpenAI</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label className="text-sm">推荐模型</Label>
                <Input
                  value={formData.recommended_model}
                  onChange={(e) => setFormData({ ...formData, recommended_model: e.target.value })}
                  placeholder="deepseek-chat"
                />
              </div>

              <div>
                <Label className="text-sm">Temperature</Label>
                <Input
                  type="number"
                  step="0.1"
                  min="0"
                  max="2"
                  value={formData.recommended_temperature}
                  onChange={(e) => setFormData({ ...formData, recommended_temperature: parseFloat(e.target.value) })}
                />
              </div>

              <div>
                <Label className="text-sm">Max Tokens</Label>
                <Input
                  type="number"
                  value={formData.recommended_max_tokens}
                  onChange={(e) => setFormData({ ...formData, recommended_max_tokens: parseInt(e.target.value) })}
                />
              </div>
            </CardContent>
          </Card>

          {/* 状态和标签 */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">状态和标签</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <Label>启用状态</Label>
                <Button
                  variant={formData.is_active ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setFormData({ ...formData, is_active: !formData.is_active })}
                >
                  {formData.is_active ? '已启用' : '已停用'}
                </Button>
              </div>

              <div className="flex items-center justify-between">
                <Label>默认模板</Label>
                <Button
                  variant={formData.is_default ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setFormData({ ...formData, is_default: !formData.is_default })}
                >
                  {formData.is_default ? '是' : '否'}
                </Button>
              </div>

              <div>
                <Label className="text-sm">标签</Label>
                <div className="flex flex-wrap gap-2 mt-2">
                  {formData.tags.map(tag => (
                    <Badge key={tag} variant="secondary" className="cursor-pointer" onClick={() => removeTag(tag)}>
                      {tag} ×
                    </Badge>
                  ))}
                </div>
                <Input
                  placeholder="输入标签后按Enter"
                  className="mt-2"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      addTag(e.currentTarget.value)
                      e.currentTarget.value = ''
                    }
                  }}
                />
              </div>
            </CardContent>
          </Card>

          {/* 预览结果 */}
          {previewResult && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                  预览结果
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div>
                    <Label className="text-xs">System Prompt</Label>
                    <pre className="text-xs bg-muted p-2 rounded mt-1 overflow-auto max-h-32">
                      {previewResult.system_prompt}
                    </pre>
                  </div>
                  <div>
                    <Label className="text-xs">User Prompt</Label>
                    <pre className="text-xs bg-muted p-2 rounded mt-1 overflow-auto max-h-48">
                      {previewResult.user_prompt}
                    </pre>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          {/* 统计信息 */}
          {template && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">统计信息</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">使用次数</span>
                  <span className="font-semibold">{template.usage_count || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">成功率</span>
                  <span className="font-semibold">
                    {template.success_rate ? `${(template.success_rate * 100).toFixed(1)}%` : '-'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">平均Token</span>
                  <span className="font-semibold">{template.avg_tokens_used || '-'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">创建时间</span>
                  <span className="text-xs">{new Date(template.created_at).toLocaleString('zh-CN')}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">更新时间</span>
                  <span className="text-xs">{new Date(template.updated_at).toLocaleString('zh-CN')}</span>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
