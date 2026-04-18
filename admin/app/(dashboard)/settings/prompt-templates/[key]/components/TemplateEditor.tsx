'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { BUSINESS_TYPE_LABELS } from '@/types/prompt-template'
import type { TemplateFormData } from '../hooks'

interface TemplateEditorProps {
  formData: TemplateFormData
  setFormData: React.Dispatch<React.SetStateAction<TemplateFormData>>
  newVarKey: string
  setNewVarKey: (value: string) => void
  newVarDesc: string
  setNewVarDesc: (value: string) => void
  isOptional: boolean
  setIsOptional: (value: boolean) => void
  addVariable: () => void
  removeVariable: (key: string, optional: boolean) => void
}

export function TemplateEditor({
  formData,
  setFormData,
  newVarKey,
  setNewVarKey,
  newVarDesc,
  setNewVarDesc,
  isOptional,
  setIsOptional,
  addVariable,
  removeVariable,
}: TemplateEditorProps) {
  return (
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
  )
}
