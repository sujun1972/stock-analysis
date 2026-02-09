'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useToast } from '@/hooks/use-toast'
import { apiClient } from '@/lib/api-client'
import type { DynamicStrategy } from '@/types/strategy'
import DynamicStrategyCodeEditor from '@/components/strategies/DynamicStrategyCodeEditor'
import StrategyValidationResult from '@/components/strategies/StrategyValidationResult'
import StrategyCard from '@/components/strategies/StrategyCard'
import { Loader2, Plus, Search, Filter, ArrowLeft, AlertTriangle, CheckCircle, Code2 } from 'lucide-react'
import Link from 'next/link'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

export default function DynamicStrategiesPage() {
  // 状态管理
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
  const [formData, setFormData] = useState({
    strategy_name: '',
    display_name: '',
    class_name: '',
    description: '',
    generated_code: ''
  })

  // 验证状态
  const [validationResult, setValidationResult] = useState<{
    is_valid: boolean
    errors: string[]
    warnings: string[]
  } | null>(null)

  const { toast } = useToast()

  // 加载数据
  useEffect(() => {
    loadStrategies()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadStrategies = async () => {
    setIsLoading(true)
    try {
      const response = await apiClient.getDynamicStrategies()
      if (response.success && response.data) {
        setStrategies(response.data.items || [])
      }
    } catch (error: any) {
      toast({
        title: '加载失败',
        description: error.message || '无法加载动态策略列表',
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }

  // 筛选策略
  const filteredStrategies = (strategies || []).filter(strategy => {
    // 搜索过滤
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      const matchName = strategy.display_name.toLowerCase().includes(query)
      const matchStrategyName = strategy.strategy_name.toLowerCase().includes(query)
      const matchDesc = strategy.description?.toLowerCase().includes(query)
      if (!matchName && !matchStrategyName && !matchDesc) return false
    }

    // 状态过滤
    if (filterStatus === 'enabled' && !strategy.is_enabled) return false
    if (filterStatus === 'disabled' && strategy.is_enabled) return false

    // 验证状态过滤
    if (filterValidation !== 'all' && strategy.validation_status !== filterValidation) {
      return false
    }

    return true
  })

  // 打开创建对话框
  const handleOpenCreateDialog = () => {
    setFormData({
      strategy_name: '',
      display_name: '',
      class_name: '',
      description: '',
      generated_code: `from core.strategies.base_strategy import BaseStrategy
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
    })
    setValidationResult(null)
    setIsCreateDialogOpen(true)
  }

  // 打开编辑对话框
  const handleOpenEditDialog = (strategy: DynamicStrategy) => {
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
  }

  // 打开删除确认对话框
  const handleOpenDeleteDialog = (strategy: DynamicStrategy) => {
    setSelectedStrategy(strategy)
    setIsDeleteDialogOpen(true)
  }

  // 打开查看代码对话框
  const handleOpenViewCodeDialog = async (strategy: DynamicStrategy) => {
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
    } catch (error: any) {
      toast({
        title: '加载失败',
        description: error.message || '无法加载策略代码',
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }

  // 验证代码
  const handleValidateCode = async () => {
    if (!formData.generated_code.trim()) {
      toast({
        title: '参数错误',
        description: '请输入策略代码',
        variant: 'destructive'
      })
      return
    }

    // 临时创建策略用于验证
    setIsLoading(true)
    try {
      // 如果是编辑模式且有选中的策略，直接验证
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
        // 创建模式：提示用户先保存
        toast({
          title: '提示',
          description: '请先创建策略，然后再进行验证',
          variant: 'default'
        })
      }
    } catch (error: any) {
      toast({
        title: '验证失败',
        description: error.response?.data?.detail || error.message || '网络错误',
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }

  // 创建策略
  const handleCreateStrategy = async () => {
    if (!formData.strategy_name.trim()) {
      toast({
        title: '参数错误',
        description: '请输入策略名称',
        variant: 'destructive'
      })
      return
    }

    if (!formData.display_name.trim()) {
      toast({
        title: '参数错误',
        description: '请输入显示名称',
        variant: 'destructive'
      })
      return
    }

    if (!formData.class_name.trim()) {
      toast({
        title: '参数错误',
        description: '请输入类名',
        variant: 'destructive'
      })
      return
    }

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
      const response = await apiClient.createDynamicStrategy({
        strategy_name: formData.strategy_name,
        display_name: formData.display_name,
        class_name: formData.class_name,
        generated_code: formData.generated_code,
        description: formData.description
      })

      if (response.success) {
        toast({
          title: '创建成功',
          description: '动态策略已创建，请进行验证'
        })
        setIsCreateDialogOpen(false)
        loadStrategies()
      } else {
        toast({
          title: '创建失败',
          description: response.error || '未知错误',
          variant: 'destructive'
        })
      }
    } catch (error: any) {
      toast({
        title: '创建失败',
        description: error.response?.data?.detail || error.message || '网络错误',
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }

  // 更新策略
  const handleUpdateStrategy = async () => {
    if (!selectedStrategy) return

    if (!formData.display_name.trim()) {
      toast({
        title: '参数错误',
        description: '请输入显示名称',
        variant: 'destructive'
      })
      return
    }

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
      const response = await apiClient.updateDynamicStrategy(selectedStrategy.id, {
        display_name: formData.display_name,
        generated_code: formData.generated_code,
        description: formData.description
      })

      if (response.success) {
        toast({
          title: '更新成功',
          description: '动态策略已更新，建议重新验证'
        })
        setIsEditDialogOpen(false)
        loadStrategies()
      } else {
        toast({
          title: '更新失败',
          description: response.error || '未知错误',
          variant: 'destructive'
        })
      }
    } catch (error: any) {
      toast({
        title: '更新失败',
        description: error.response?.data?.detail || error.message || '网络错误',
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }

  // 删除策略
  const handleDeleteStrategy = async () => {
    if (!selectedStrategy) return

    setIsLoading(true)
    try {
      const response = await apiClient.deleteDynamicStrategy(selectedStrategy.id)

      if (response.success) {
        toast({
          title: '删除成功',
          description: '动态策略已删除'
        })
        setIsDeleteDialogOpen(false)
        loadStrategies()
      } else {
        toast({
          title: '删除失败',
          description: response.error || '未知错误',
          variant: 'destructive'
        })
      }
    } catch (error: any) {
      toast({
        title: '删除失败',
        description: error.response?.data?.detail || error.message || '网络错误',
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }

  // 测试策略
  const handleTestStrategy = async (strategyId: number) => {
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
    } catch (error: any) {
      toast({
        title: '测试失败',
        description: error.response?.data?.detail || error.message || '网络错误',
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }

  // 切换启用状态
  const handleToggleEnabled = async (strategy: DynamicStrategy) => {
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
    } catch (error: any) {
      toast({
        title: '更新失败',
        description: error.message || '网络错误',
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }

  // 验证状态统计
  const validationStats = {
    passed: (strategies || []).filter(s => s.validation_status === 'passed').length,
    failed: (strategies || []).filter(s => s.validation_status === 'failed').length,
    warning: (strategies || []).filter(s => s.validation_status === 'warning').length,
    pending: (strategies || []).filter(s => s.validation_status === 'pending').length
  }

  return (
    <div className="container mx-auto py-6 px-4 max-w-7xl">
      <div className="space-y-6">
        {/* 页面标题 */}
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Link href="/backtest">
                <Button variant="ghost" size="sm">
                  <ArrowLeft className="h-4 w-4 mr-1" />
                  返回回测
                </Button>
              </Link>
            </div>
            <h1 className="text-3xl font-bold tracking-tight">动态策略管理</h1>
            <p className="text-muted-foreground mt-2">
              创建、编辑和管理自定义代码策略
            </p>
          </div>
          <Button onClick={handleOpenCreateDialog} size="lg">
            <Plus className="h-4 w-4 mr-2" />
            新建策略
          </Button>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                总策略数
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{(strategies || []).length}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                已启用
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {(strategies || []).filter(s => s.is_enabled).length}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                <CheckCircle className="h-4 w-4" />
                验证通过
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {validationStats.passed}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                <AlertTriangle className="h-4 w-4" />
                有警告
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-yellow-600">
                {validationStats.warning}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                验证失败
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-red-600">
                {validationStats.failed}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 安全提示 */}
        <Alert variant="default" className="border-yellow-200 bg-yellow-50 dark:bg-yellow-900/10">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>安全提示</AlertTitle>
          <AlertDescription>
            动态代码策略会在服务器上执行。请确保代码来自可信来源，不要运行未经验证的代码。
            所有代码都会经过安全检查和沙箱测试。
          </AlertDescription>
        </Alert>

        {/* 搜索和筛选 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">筛选策略</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="搜索策略名称或描述..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9"
                  />
                </div>
              </div>
              <Select value={filterValidation} onValueChange={setFilterValidation}>
                <SelectTrigger className="w-full md:w-48">
                  <Filter className="h-4 w-4 mr-2" />
                  <SelectValue placeholder="验证状态" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">所有状态</SelectItem>
                  <SelectItem value="passed">验证通过</SelectItem>
                  <SelectItem value="warning">有警告</SelectItem>
                  <SelectItem value="failed">验证失败</SelectItem>
                  <SelectItem value="pending">待验证</SelectItem>
                </SelectContent>
              </Select>
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger className="w-full md:w-32">
                  <SelectValue placeholder="启用状态" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部</SelectItem>
                  <SelectItem value="enabled">已启用</SelectItem>
                  <SelectItem value="disabled">已禁用</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* 策略列表 */}
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : filteredStrategies.length === 0 ? (
          <Card className="p-12 text-center">
            <div className="flex flex-col items-center justify-center">
              <div className="rounded-full bg-muted p-6 mb-4">
                <Code2 className="h-12 w-12 text-muted-foreground" />
              </div>
              <CardTitle className="mb-2">暂无动态策略</CardTitle>
              <CardDescription className="mb-4">
                {searchQuery || filterStatus !== 'all' || filterValidation !== 'all'
                  ? '没有符合筛选条件的策略'
                  : '点击"新建策略"按钮创建第一个动态策略'}
              </CardDescription>
              {!searchQuery && filterStatus === 'all' && filterValidation === 'all' && (
                <Button onClick={handleOpenCreateDialog}>
                  <Plus className="h-4 w-4 mr-2" />
                  新建策略
                </Button>
              )}
            </div>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredStrategies.map(strategy => (
              <StrategyCard
                key={strategy.id}
                type="dynamic"
                data={strategy}
                onEdit={() => handleOpenEditDialog(strategy)}
                onDelete={() => handleOpenDeleteDialog(strategy)}
                onTest={() => handleTestStrategy(strategy.id)}
                onView={() => handleOpenViewCodeDialog(strategy)}
              />
            ))}
          </div>
        )}
      </div>

      {/* 创建策略对话框 */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>新建动态策略</DialogTitle>
            <DialogDescription>
              编写自定义策略代码，实现个性化的交易逻辑
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="create-strategy-name">策略名称 * (英文, 用于文件名)</Label>
                <Input
                  id="create-strategy-name"
                  placeholder="my_custom_strategy"
                  value={formData.strategy_name}
                  onChange={(e) => setFormData({ ...formData, strategy_name: e.target.value })}
                />
                <p className="text-xs text-muted-foreground">
                  小写字母、数字和下划线，如: my_momentum_strategy
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="create-display-name">显示名称 *</Label>
                <Input
                  id="create-display-name"
                  placeholder="我的自定义策略"
                  value={formData.display_name}
                  onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="create-class-name">类名 * (Python 类名)</Label>
              <Input
                id="create-class-name"
                placeholder="MyCustomStrategy"
                value={formData.class_name}
                onChange={(e) => setFormData({ ...formData, class_name: e.target.value })}
              />
              <p className="text-xs text-muted-foreground">
                大写驼峰命名，如: MyMomentumStrategy
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="create-description">描述</Label>
              <Textarea
                id="create-description"
                placeholder="简要描述此策略的逻辑和用途..."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={2}
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-base font-semibold">策略代码 *</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleValidateCode}
                  disabled={isLoading}
                >
                  {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  验证代码
                </Button>
              </div>
              <DynamicStrategyCodeEditor
                value={formData.generated_code}
                onChange={(code) => setFormData({ ...formData, generated_code: code })}
                minHeight="400px"
              />
            </div>

            {validationResult && (
              <StrategyValidationResult
                isValid={validationResult.is_valid}
                errors={validationResult.errors.map(e => ({ type: 'error', message: e }))}
                warnings={validationResult.warnings.map(w => ({ type: 'warning', message: w }))}
              />
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsCreateDialogOpen(false)}
              disabled={isLoading}
            >
              取消
            </Button>
            <Button onClick={handleCreateStrategy} disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              创建策略
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 编辑策略对话框 */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>编辑动态策略</DialogTitle>
            <DialogDescription>
              修改策略代码和配置信息
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>策略名称</Label>
              <div className="flex items-center gap-2">
                <Badge variant="secondary">{formData.strategy_name}</Badge>
                <span className="text-sm text-muted-foreground">
                  (策略名称不可修改)
                </span>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="edit-display-name">显示名称 *</Label>
                <Input
                  id="edit-display-name"
                  value={formData.display_name}
                  onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                />
              </div>

              <div className="space-y-2">
                <Label>类名</Label>
                <div className="flex items-center gap-2">
                  <Badge variant="secondary">{formData.class_name}</Badge>
                  <span className="text-sm text-muted-foreground">
                    (类名不可修改)
                  </span>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-description">描述</Label>
              <Textarea
                id="edit-description"
                placeholder="简要描述此策略的逻辑和用途..."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={2}
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label className="text-base font-semibold">策略代码 *</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={handleValidateCode}
                  disabled={isLoading}
                >
                  {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  验证代码
                </Button>
              </div>
              <DynamicStrategyCodeEditor
                value={formData.generated_code}
                onChange={(code) => setFormData({ ...formData, generated_code: code })}
                minHeight="400px"
              />
            </div>

            {validationResult && (
              <StrategyValidationResult
                isValid={validationResult.is_valid}
                errors={validationResult.errors.map(e => ({ type: 'error', message: e }))}
                warnings={validationResult.warnings.map(w => ({ type: 'warning', message: w }))}
              />
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsEditDialogOpen(false)}
              disabled={isLoading}
            >
              取消
            </Button>
            <Button onClick={handleUpdateStrategy} disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              保存更改
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 查看代码对话框 */}
      <Dialog open={isViewCodeDialogOpen} onOpenChange={setIsViewCodeDialogOpen}>
        <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>查看策略代码</DialogTitle>
            <DialogDescription>
              {selectedStrategy?.display_name} ({selectedStrategy?.strategy_name})
            </DialogDescription>
          </DialogHeader>

          <div className="py-4">
            <DynamicStrategyCodeEditor
              value={formData.generated_code}
              onChange={() => {}}
              readOnly={true}
              minHeight="500px"
            />
          </div>

          <DialogFooter>
            <Button onClick={() => setIsViewCodeDialogOpen(false)}>
              关闭
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 删除确认对话框 */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
            <DialogDescription>
              确定要删除策略 &ldquo;{selectedStrategy?.display_name}&rdquo; 吗？此操作无法撤销。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setIsDeleteDialogOpen(false)}
              disabled={isLoading}
            >
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteStrategy}
              disabled={isLoading}
            >
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              确认删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
