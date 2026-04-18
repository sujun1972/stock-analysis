'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'
import { CheckCircle2 } from 'lucide-react'
import type { TemplateFormData } from '../hooks'

interface PreviewPanelProps {
  formData: TemplateFormData
  setFormData: React.Dispatch<React.SetStateAction<TemplateFormData>>
  previewResult: any
  addTag: (tag: string) => void
  removeTag: (tag: string) => void
}

export function PreviewPanel({
  formData,
  setFormData,
  previewResult,
  addTag,
  removeTag,
}: PreviewPanelProps) {
  return (
    <>
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
    </>
  )
}
