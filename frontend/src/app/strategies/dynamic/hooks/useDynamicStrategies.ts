'use client'

import { useState, useEffect, useMemo, useCallback } from 'react'
import { useToast } from '@/hooks/use-toast'
import { apiClient } from '@/lib/api-client'
import type { DynamicStrategy } from '@/types/strategy'

const DEFAULT_CODE_TEMPLATE = `from core.strategies.base_strategy import BaseStrategy
import pandas as pd
import numpy as np

class MyCustomStrategy(BaseStrategy):
    """
    自定义策略示例

    这是一个模板策略，你可以根据需求修改。
    """

    def __init__(self, **kwargs):
        """初始化策略"""
        super().__init__(**kwargs)
        # 在这里添加策略参数

    def generate_signals(self, prices, features=None, volumes=None, **kwargs):
        """
        生成交易信号

        参数:
            prices: 价格数据 (DataFrame)
            features: 特征数据 (DataFrame, 可选)
            volumes: 成交量数据 (DataFrame, 可选)

        返回:
            signals: 交易信号 (DataFrame)
                    index: 日期
                    columns: 股票代码
                    values: 1 (买入), 0 (持有), -1 (卖出)
        """
        # TODO: 实现你的策略逻辑

        # 示例: 简单的动量策略
        returns = prices.pct_change(periods=20)  # 20日收益率
        signals = pd.DataFrame(0, index=prices.index, columns=prices.columns)

        # 收益率大于10%时买入
        signals[returns > 0.10] = 1
        # 收益率小于-5%时卖出
        signals[returns < -0.05] = -1

        return signals
`

export interface StrategyFormData {
  strategy_name: string
  display_name: string
  class_name: string
  description: string
  generated_code: string
}

export interface ValidationResult {
  is_valid: boolean
  errors: string[]
  warnings: string[]
}

export interface ValidationStats {
  passed: number
  failed: number
  warning: number
  pending: number
}

const INITIAL_FORM_DATA: StrategyFormData = {
  strategy_name: '',
  display_name: '',
  class_name: '',
  description: '',
  generated_code: ''
}

export function useDynamicStrategies() {
  // 策略列表状态
  const [strategies, setStrategies] = useState<DynamicStrategy[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterStatus, setFilterStatus] = useState<string>('all')
  const [filterValidation, setFilterValidation] = useState<string>('all')

  // 对话框状态
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [isViewCodeDialogOpen, setIsViewCodeDialogOpen] = useState(false)
  const [selectedStrategy, setSelectedStrategy] = useState<DynamicStrategy | null>(null)

  // 表单状态
  const [formData, setFormData] = useState<StrategyFormData>(INITIAL_FORM_DATA)

  // 验证状态
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null)

  const { toast } = useToast()

  // 加载策略列表
  const loadStrategies = useCallback(async () => {
    setIsLoading(true)
    try {
      const response = await apiClient.getDynamicStrategies()
      if (response.success && response.data) {
        setStrategies(response.data.items || [])
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '无法加载动态策略列表'
      toast({
        title: '加载失败',
        description: message,
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }, [toast])

  useEffect(() => {
    loadStrategies()
  }, [loadStrategies])

  // 筛选策略
  const filteredStrategies = useMemo(() => (strategies || []).filter(strategy => {
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      const matchName = strategy.display_name.toLowerCase().includes(query)
      const matchStrategyName = strategy.strategy_name.toLowerCase().includes(query)
      const matchDesc = strategy.description?.toLowerCase().includes(query)
      if (!matchName && !matchStrategyName && !matchDesc) return false
    }

    if (filterStatus === 'enabled' && !strategy.is_enabled) return false
    if (filterStatus === 'disabled' && strategy.is_enabled) return false

    if (filterValidation !== 'all' && strategy.validation_status !== filterValidation) {
      return false
    }

    return true
  }), [strategies, searchQuery, filterStatus, filterValidation])

  // 验证状态统计
  const validationStats: ValidationStats = useMemo(() => ({
    passed: (strategies || []).filter(s => s.validation_status === 'passed').length,
    failed: (strategies || []).filter(s => s.validation_status === 'failed').length,
    warning: (strategies || []).filter(s => s.validation_status === 'warning').length,
    pending: (strategies || []).filter(s => s.validation_status === 'pending').length
  }), [strategies])

  // 打开创建对话框
  const handleOpenCreateDialog = useCallback(() => {
    setFormData({
      ...INITIAL_FORM_DATA,
      generated_code: DEFAULT_CODE_TEMPLATE
    })
    setValidationResult(null)
    setIsCreateDialogOpen(true)
  }, [])

  // 打开编辑对话框
  const handleOpenEditDialog = useCallback((strategy: DynamicStrategy) => {
    setSelectedStrategy(strategy)
    setFormData({
      strategy_name: strategy.strategy_name,
      display_name: strategy.display_name,
      class_name: strategy.class_name,
      description: strategy.description || '',
      generated_code: strategy.generated_code
    })
    setValidationResult(null)
    setIsEditDialogOpen(true)
  }, [])

  // 打开删除确认对话框
  const handleOpenDeleteDialog = useCallback((strategy: DynamicStrategy) => {
    setSelectedStrategy(strategy)
    setIsDeleteDialogOpen(true)
  }, [])

  // 打开查看代码对话框
  const handleOpenViewCodeDialog = useCallback(async (strategy: DynamicStrategy) => {
    setSelectedStrategy(strategy)
    setIsLoading(true)
    try {
      const response = await apiClient.getDynamicStrategyCode(strategy.id)
      if (response.success && response.data) {
        const codeData = response.data
        setFormData(prev => ({
          ...prev,
          generated_code: codeData.code
        }))
        setIsViewCodeDialogOpen(true)
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '无法加载策略代码'
      toast({
        title: '加载失败',
        description: message,
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }, [toast])

  // 验证代码
  const handleValidateCode = useCallback(async () => {
    if (!formData.generated_code.trim()) {
      toast({
        title: '参数错误',
        description: '请输入策略代码',
        variant: 'destructive'
      })
      return
    }

    setIsLoading(true)
    try {
      if (selectedStrategy && isEditDialogOpen) {
        const response = await apiClient.validateDynamicStrategy(selectedStrategy.id)
        if (response.success && response.data) {
          setValidationResult(response.data)
          if (response.data.is_valid) {
            toast({
              title: '验证通过',
              description: '策略代码验证通过'
            })
          } else {
            toast({
              title: '验证失败',
              description: `发现 ${response.data.errors.length} 个错误`,
              variant: 'destructive'
            })
          }
        }
      } else {
        toast({
          title: '提示',
          description: '请先创建策略，然后再进行验证',
          variant: 'default'
        })
      }
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } }; message?: string }
      toast({
        title: '验证失败',
        description: err.response?.data?.detail || err.message || '网络错误',
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }, [formData.generated_code, selectedStrategy, isEditDialogOpen, toast])

  // 创建策略
  const handleCreateStrategy = useCallback(async () => {
    if (!formData.strategy_name.trim()) {
      toast({ title: '参数错误', description: '请输入策略名称', variant: 'destructive' })
      return
    }
    if (!formData.display_name.trim()) {
      toast({ title: '参数错误', description: '请输入显示名称', variant: 'destructive' })
      return
    }
    if (!formData.class_name.trim()) {
      toast({ title: '参数错误', description: '请输入类名', variant: 'destructive' })
      return
    }
    if (!formData.generated_code.trim()) {
      toast({ title: '参数错误', description: '请输入策略代码', variant: 'destructive' })
      return
    }

    setIsLoading(true)
    try {
      const response = await apiClient.createDynamicStrategy({
        strategy_name: formData.strategy_name,
        display_name: formData.display_name,
        class_name: formData.class_name,
        generated_code: formData.generated_code,
        description: formData.description
      })

      if (response.success) {
        toast({ title: '创建成功', description: '动态策略已创建，请进行验证' })
        setIsCreateDialogOpen(false)
        loadStrategies()
      } else {
        toast({
          title: '创建失败',
          description: response.error || '未知错误',
          variant: 'destructive'
        })
      }
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } }; message?: string }
      toast({
        title: '创建失败',
        description: err.response?.data?.detail || err.message || '网络错误',
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }, [formData, toast, loadStrategies])

  // 更新策略
  const handleUpdateStrategy = useCallback(async () => {
    if (!selectedStrategy) return

    if (!formData.display_name.trim()) {
      toast({ title: '参数错误', description: '请输入显示名称', variant: 'destructive' })
      return
    }
    if (!formData.generated_code.trim()) {
      toast({ title: '参数错误', description: '请输入策略代码', variant: 'destructive' })
      return
    }

    setIsLoading(true)
    try {
      const response = await apiClient.updateDynamicStrategy(selectedStrategy.id, {
        display_name: formData.display_name,
        generated_code: formData.generated_code,
        description: formData.description
      })

      if (response.success) {
        toast({ title: '更新成功', description: '动态策略已更新，建议重新验证' })
        setIsEditDialogOpen(false)
        loadStrategies()
      } else {
        toast({
          title: '更新失败',
          description: response.error || '未知错误',
          variant: 'destructive'
        })
      }
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } }; message?: string }
      toast({
        title: '更新失败',
        description: err.response?.data?.detail || err.message || '网络错误',
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }, [selectedStrategy, formData, toast, loadStrategies])

  // 删除策略
  const handleDeleteStrategy = useCallback(async () => {
    if (!selectedStrategy) return

    setIsLoading(true)
    try {
      const response = await apiClient.deleteDynamicStrategy(selectedStrategy.id)

      if (response.success) {
        toast({ title: '删除成功', description: '动态策略已删除' })
        setIsDeleteDialogOpen(false)
        loadStrategies()
      } else {
        toast({
          title: '删除失败',
          description: response.error || '未知错误',
          variant: 'destructive'
        })
      }
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } }; message?: string }
      toast({
        title: '删除失败',
        description: err.response?.data?.detail || err.message || '网络错误',
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }, [selectedStrategy, toast, loadStrategies])

  // 测试策略
  const handleTestStrategy = useCallback(async (strategyId: number) => {
    setIsLoading(true)
    try {
      const response = await apiClient.testDynamicStrategy(strategyId)

      if (response.success && response.data?.success) {
        toast({
          title: '测试成功',
          description: response.data.message || '策略测试通过'
        })
      } else {
        toast({
          title: '测试失败',
          description: response.data?.message || response.error || '测试未通过',
          variant: 'destructive'
        })
      }
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } }; message?: string }
      toast({
        title: '测试失败',
        description: err.response?.data?.detail || err.message || '网络错误',
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }, [toast])

  // 切换启用状态
  const handleToggleEnabled = useCallback(async (strategy: DynamicStrategy) => {
    setIsLoading(true)
    try {
      const response = await apiClient.updateDynamicStrategy(strategy.id, {
        is_enabled: !strategy.is_enabled
      })

      if (response.success) {
        toast({
          title: '更新成功',
          description: `已${strategy.is_enabled ? '禁用' : '启用'}策略`
        })
        loadStrategies()
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : '网络错误'
      toast({
        title: '更新失败',
        description: message,
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }, [toast, loadStrategies])

  return {
    // 列表数据
    strategies,
    filteredStrategies,
    isLoading,
    validationStats,

    // 搜索和筛选
    searchQuery,
    setSearchQuery,
    filterStatus,
    setFilterStatus,
    filterValidation,
    setFilterValidation,

    // 对话框状态
    isCreateDialogOpen,
    setIsCreateDialogOpen,
    isEditDialogOpen,
    setIsEditDialogOpen,
    isDeleteDialogOpen,
    setIsDeleteDialogOpen,
    isViewCodeDialogOpen,
    setIsViewCodeDialogOpen,
    selectedStrategy,

    // 表单状态
    formData,
    setFormData,
    validationResult,

    // 操作
    handleOpenCreateDialog,
    handleOpenEditDialog,
    handleOpenDeleteDialog,
    handleOpenViewCodeDialog,
    handleValidateCode,
    handleCreateStrategy,
    handleUpdateStrategy,
    handleDeleteStrategy,
    handleTestStrategy,
    handleToggleEnabled,
  }
}
