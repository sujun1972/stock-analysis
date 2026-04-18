import { Edit, Trash2, Sparkles } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import type { AIProvider } from '../hooks/useAiConfigData'

interface ProviderCardProps {
  provider: AIProvider
  onEdit: (provider: AIProvider) => void
  onDelete: (providerKey: string) => void
}

export function ProviderCard({ provider, onEdit, onDelete }: ProviderCardProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div className="flex items-start gap-3 flex-1 min-w-0">
            <Sparkles className="w-5 h-5 text-blue-500 shrink-0 mt-0.5" />
            <div className="flex-1 min-w-0">
              <CardTitle className="flex flex-wrap items-center gap-2">
                <span className="truncate">{provider.display_name}</span>
                {provider.is_default && (
                  <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded shrink-0">默认</span>
                )}
                {!provider.is_active && (
                  <span className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded shrink-0">已禁用</span>
                )}
              </CardTitle>
              <CardDescription className="mt-1">
                {provider.description || provider.provider}
              </CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {/* 桌面端按钮 */}
            <div className="hidden sm:flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onEdit(provider)}
                className="gap-2"
              >
                <Edit className="w-4 h-4" />
                编辑
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => onDelete(provider.provider)}
                className="gap-2 text-red-600 hover:text-red-700"
              >
                <Trash2 className="w-4 h-4" />
                删除
              </Button>
            </div>
            {/* 移动端图标按钮 */}
            <div className="flex items-center gap-1 sm:hidden">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => onEdit(provider)}
                className="h-8 w-8 shrink-0"
              >
                <Edit className="w-4 h-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => onDelete(provider.provider)}
                className="h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50 shrink-0"
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 text-sm">
          <div>
            <p className="text-gray-500 text-xs sm:text-sm">提供商</p>
            <p className="font-medium truncate">{provider.provider}</p>
          </div>
          <div>
            <p className="text-gray-500 text-xs sm:text-sm">模型</p>
            <p className="font-medium truncate">{provider.model_name}</p>
          </div>
          <div className="col-span-2 sm:col-span-1">
            <p className="text-gray-500 text-xs sm:text-sm">API密钥</p>
            <p className="font-mono text-xs truncate">{provider.api_key}</p>
          </div>
          <div>
            <p className="text-gray-500 text-xs sm:text-sm">优先级</p>
            <p className="font-medium">{provider.priority}</p>
          </div>
          <div>
            <p className="text-gray-500 text-xs sm:text-sm">最大Tokens</p>
            <p className="font-medium">{provider.max_tokens}</p>
          </div>
          <div>
            <p className="text-gray-500 text-xs sm:text-sm">温度</p>
            <p className="font-medium">{provider.temperature}</p>
          </div>
          <div>
            <p className="text-gray-500 text-xs sm:text-sm">限流</p>
            <p className="font-medium">{provider.rate_limit}/分钟</p>
          </div>
          <div>
            <p className="text-gray-500 text-xs sm:text-sm">超时</p>
            <p className="font-medium">{provider.timeout}秒</p>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
