'use client'

import { Plus, RefreshCw } from 'lucide-react'
import { PageHeader } from '@/components/common/PageHeader'
import { Button } from '@/components/ui/button'
import { useAiConfigData, useAiConfigActions } from './hooks'
import { ProviderList, ProviderFormDialog } from './components'

export default function AIConfigPage() {
  const { providers, loading, fetchProviders } = useAiConfigData()

  const {
    isDialogOpen,
    setIsDialogOpen,
    editingProvider,
    formData,
    setFormData,
    handleCreate,
    handleEdit,
    handleSave,
    handleDelete,
    handleProviderChange,
  } = useAiConfigActions({ fetchProviders })

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="AI配置管理"
        description="管理AI策略生成的提供商配置"
        actions={
          <Button onClick={handleCreate} className="gap-2 w-full sm:w-auto">
            <Plus className="w-4 h-4" />
            添加AI提供商
          </Button>
        }
      />

      <ProviderList
        providers={providers}
        onEdit={handleEdit}
        onDelete={handleDelete}
        onCreate={handleCreate}
      />

      <ProviderFormDialog
        open={isDialogOpen}
        onOpenChange={setIsDialogOpen}
        editingProvider={editingProvider}
        formData={formData}
        setFormData={setFormData}
        onSave={handleSave}
        onProviderChange={handleProviderChange}
      />
    </div>
  )
}
