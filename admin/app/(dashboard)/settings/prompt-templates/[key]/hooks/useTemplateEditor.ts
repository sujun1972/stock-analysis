import { useState } from 'react'
import logger from '@/lib/logger'
import { promptTemplateApi } from '@/lib/prompt-template-api'
import { useToast } from '@/hooks/use-toast'
import type { TemplateFormData } from './useTemplateData'

export function useTemplateEditor(templateKey: string, formData: TemplateFormData) {
  const { toast } = useToast()

  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewResult, setPreviewResult] = useState<any>(null)

  const handlePreview = async () => {
    try {
      setPreviewLoading(true)
      const testVariables: Record<string, any> = {}
      Object.keys(formData.required_variables).forEach(key => {
        testVariables[key] = `<${key}_示例值>`
      })

      const result = await promptTemplateApi.previewByKey(templateKey, testVariables)
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

  return {
    previewLoading,
    previewResult,
    handlePreview,
  }
}
