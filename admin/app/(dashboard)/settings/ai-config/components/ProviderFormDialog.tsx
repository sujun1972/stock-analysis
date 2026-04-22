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
import type { AIProvider } from '../hooks/useAiConfigData'
import type { AIProviderFormData } from '../hooks/useAiConfigActions'

interface ProviderFormDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  editingProvider: AIProvider | null
  formData: AIProviderFormData
  setFormData: (data: AIProviderFormData) => void
  onSave: () => void
  onProviderChange: (value: string) => void
}

export function ProviderFormDialog({
  open,
  onOpenChange,
  editingProvider,
  formData,
  setFormData,
  onSave,
  onProviderChange,
}: ProviderFormDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>{editingProvider ? '编辑AI提供商' : '添加AI提供商'}</DialogTitle>
          <DialogDescription>
            配置AI服务提供商的API信息和参数
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-4 py-4 px-2 overflow-y-auto flex-1">
          {!editingProvider && (
            <div className="grid gap-2">
              <Label htmlFor="provider">提供商类型 <span className="text-red-500">*</span></Label>
              <Select value={formData.provider} onValueChange={onProviderChange}>
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
            <Label htmlFor="display_name">显示名称 <span className="text-red-500">*</span></Label>
            <Input
              id="display_name"
              value={formData.display_name}
              onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
              placeholder="例如: DeepSeek"
            />
          </div>

          <div className="grid gap-2">
            <Label htmlFor="api_key">
              API密钥 <span className="text-red-500">*</span>
              {editingProvider && <span className="text-xs text-gray-500 ml-1">(留空则不修改)</span>}
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

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
            <Label htmlFor="max_concurrent">并发上限（进程级 Semaphore）</Label>
            <Input
              id="max_concurrent"
              type="number"
              min={1}
              max={256}
              placeholder="留空按默认：deepseek=32 / openai=16 / gemini=8"
              value={formData.max_concurrent ?? ''}
              onChange={(e) => {
                const v = e.target.value
                setFormData({ ...formData, max_concurrent: v === '' ? null : parseInt(v) })
              }}
            />
            <p className="text-xs text-gray-500">同一 provider 在进程内同时"在飞"的 LLM 请求数。改动需重启后端/Celery 生效。</p>
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

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 p-3 sm:p-4 border rounded-lg">
            <div className="space-y-0.5">
              <Label>启用</Label>
              <p className="text-xs sm:text-sm text-gray-500">启用后可用于策略生成</p>
            </div>
            <Switch
              checked={formData.is_active}
              onCheckedChange={(checked) => setFormData({ ...formData, is_active: checked })}
              className="self-start sm:self-auto"
            />
          </div>

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 p-3 sm:p-4 border rounded-lg">
            <div className="space-y-0.5">
              <Label>设为默认</Label>
              <p className="text-xs sm:text-sm text-gray-500">作为默认的AI提供商</p>
            </div>
            <Switch
              checked={formData.is_default}
              onCheckedChange={(checked) => setFormData({ ...formData, is_default: checked })}
              className="self-start sm:self-auto"
            />
          </div>
        </div>

        <DialogFooter className="flex-row gap-2">
          <Button variant="outline" onClick={() => onOpenChange(false)} className="flex-1">
            取消
          </Button>
          <Button onClick={onSave} className="flex-1">
            {editingProvider ? '保存' : '创建'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
