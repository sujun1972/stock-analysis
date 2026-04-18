'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { strategyApi } from '@/lib/api'
import logger from '@/lib/logger'
import type { NewStrategyFormData } from './useNewStrategyForm'

export function useNewStrategyActions(formData: NewStrategyFormData) {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [validating, setValidating] = useState(false)
  const [validationResult, setValidationResult] = useState<any>(null)
  const [error, setError] = useState<string | null>(null)

  // 验证策略代码
  const handleValidate = async () => {
    setValidating(true)
    setValidationResult(null)
    setError(null)

    try {
      const result = await strategyApi.validateStrategy(formData.code)
      if (result.success || result.data) {
        setValidationResult(result.data || result)
      } else {
        setError((result as any).message || '验证失败')
      }
    } catch (err: any) {
      logger.error('验证策略代码失败', err)
      setError(err.response?.data?.detail || err.message)
    } finally {
      setValidating(false)
    }
  }

  // 提交表单
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      // 解析JSON字段
      let defaultParams = null
      if (formData.default_params.trim()) {
        try {
          defaultParams = JSON.parse(formData.default_params)
        } catch {
          throw new Error('默认参数格式错误，请输入有效的JSON')
        }
      }

      // 解析标签
      const tags = formData.tags
        .split(',')
        .map((t) => t.trim())
        .filter((t) => t)

      const payload: any = {
        name: formData.name,
        display_name: formData.display_name,
        class_name: formData.class_name,
        code: formData.code,
        source_type: formData.source_type as any,
        strategy_type: formData.strategy_type as any,
        description: formData.description || undefined,
        category: formData.category || undefined,
        tags: tags.length > 0 ? tags : undefined,
        default_params: defaultParams,
        created_by: 'admin',
      }

      // 如果指定了user_id，添加到payload
      if (formData.user_id) {
        payload.user_id = parseInt(formData.user_id)
      }

      const result = await strategyApi.createStrategy(payload)

      if (result.success || result.data) {
        const strategyId = (result.data as any)?.strategy_id || (result as any).strategy_id
        // 成功跳转到策略详情页
        router.push(`/strategies/${strategyId}`)
      } else {
        throw new Error((result as any).message || '创建失败')
      }
    } catch (err: any) {
      logger.error('创建策略失败', err)
      setError(err.response?.data?.detail || err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleCancel = () => {
    router.push('/strategies')
  }

  return {
    loading,
    validating,
    validationResult,
    error,
    handleValidate,
    handleSubmit,
    handleCancel,
  }
}
