import { Plus, Sparkles } from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ProviderCard } from './ProviderCard'
import type { AIProvider } from '../hooks/useAiConfigData'

interface ProviderListProps {
  providers: AIProvider[]
  onEdit: (provider: AIProvider) => void
  onDelete: (providerKey: string) => void
  onCreate: () => void
}

export function ProviderList({ providers, onEdit, onDelete, onCreate }: ProviderListProps) {
  if (providers.length === 0) {
    return (
      <div className="grid gap-4">
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Sparkles className="w-12 h-12 text-gray-400 mb-4" />
            <p className="text-gray-500 mb-4">暂无AI提供商配置</p>
            <Button onClick={onCreate} className="gap-2">
              <Plus className="w-4 h-4" />
              添加第一个AI提供商
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="grid gap-4">
      {providers.map((provider) => (
        <ProviderCard
          key={provider.id}
          provider={provider}
          onEdit={onEdit}
          onDelete={onDelete}
        />
      ))}
    </div>
  )
}
