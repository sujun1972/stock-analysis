'use client'

import { useParams, useRouter } from 'next/navigation'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { ArrowLeft, Save, Eye, AlertCircle } from 'lucide-react'
import { useTemplateData, useTemplateEditor } from './hooks'
import { TemplateEditor, VersionHistory, PreviewPanel } from './components'

export default function PromptTemplateEditPage() {
  const router = useRouter()
  const params = useParams()
  const templateKey = params.key as string

  const {
    loading,
    saving,
    template,
    formData,
    setFormData,
    handleSave,
    newVarKey,
    setNewVarKey,
    newVarDesc,
    setNewVarDesc,
    isOptional,
    setIsOptional,
    addVariable,
    removeVariable,
    addTag,
    removeTag,
  } = useTemplateData(templateKey)

  const {
    previewLoading,
    previewResult,
    handlePreview,
  } = useTemplateEditor(templateKey, formData)

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
            <p className="text-sm text-muted-foreground">Key: {templateKey}</p>
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
        <TemplateEditor
          formData={formData}
          setFormData={setFormData}
          newVarKey={newVarKey}
          setNewVarKey={setNewVarKey}
          newVarDesc={newVarDesc}
          setNewVarDesc={setNewVarDesc}
          isOptional={isOptional}
          setIsOptional={setIsOptional}
          addVariable={addVariable}
          removeVariable={removeVariable}
        />

        {/* 右侧：配置和预览 */}
        <div className="space-y-6">
          <PreviewPanel
            formData={formData}
            setFormData={setFormData}
            previewResult={previewResult}
            addTag={addTag}
            removeTag={removeTag}
          />

          {/* 统计信息 */}
          <VersionHistory template={template} />
        </div>
      </div>
    </div>
  )
}
