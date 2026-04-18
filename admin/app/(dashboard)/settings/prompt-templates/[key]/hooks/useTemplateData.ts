import { useEffect, useState, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import logger from '@/lib/logger'
import { promptTemplateApi } from '@/lib/prompt-template-api'
import { PromptTemplate } from '@/types/prompt-template'
import { useToast } from '@/hooks/use-toast'

export interface TemplateFormData {
  template_name: string
  business_type: string
  template_key: string
  system_prompt: string
  user_prompt_template: string
  output_format: string
  required_variables: Record<string, string>
  optional_variables: Record<string, string>
  version: string
  is_active: boolean
  is_default: boolean
  recommended_provider: string
  recommended_model: string
  recommended_temperature: number
  recommended_max_tokens: number
  description: string
  changelog: string
  tags: string[]
}

const initialFormData: TemplateFormData = {
  template_name: '',
  business_type: '',
  template_key: '',
  system_prompt: '',
  user_prompt_template: '',
  output_format: '',
  required_variables: {},
  optional_variables: {},
  version: '1.0.0',
  is_active: true,
  is_default: false,
  recommended_provider: 'deepseek',
  recommended_model: 'deepseek-chat',
  recommended_temperature: 0.7,
  recommended_max_tokens: 4000,
  description: '',
  changelog: '',
  tags: []
}

export function useTemplateData(templateKey: string) {
  const router = useRouter()
  const { toast } = useToast()

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [template, setTemplate] = useState<PromptTemplate | null>(null)
  const [formData, setFormData] = useState<TemplateFormData>(initialFormData)

  // 变量编辑状态
  const [newVarKey, setNewVarKey] = useState('')
  const [newVarDesc, setNewVarDesc] = useState('')
  const [isOptional, setIsOptional] = useState(false)

  const loadTemplate = useCallback(async () => {
    try {
      setLoading(true)
      const data = await promptTemplateApi.getByKey(templateKey)
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
  }, [templateKey, toast])

  useEffect(() => {
    loadTemplate()
  }, [loadTemplate])

  const handleSave = async () => {
    try {
      setSaving(true)
      await promptTemplateApi.updateByKey(templateKey, formData)
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

  return {
    loading,
    saving,
    template,
    formData,
    setFormData,
    handleSave,
    // 变量管理
    newVarKey,
    setNewVarKey,
    newVarDesc,
    setNewVarDesc,
    isOptional,
    setIsOptional,
    addVariable,
    removeVariable,
    // 标签管理
    addTag,
    removeTag,
  }
}
