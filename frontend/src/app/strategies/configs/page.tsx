'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { useToast } from '@/hooks/use-toast'
import { apiClient } from '@/lib/api-client'
import type { StrategyTypeMeta, StrategyConfig } from '@/types/strategy'
import StrategyConfigEditor from '@/components/strategies/StrategyConfigEditor'
import StrategyCard from '@/components/strategies/StrategyCard'
import { Loader2, Plus, Search, Filter, ArrowLeft } from 'lucide-react'
import Link from 'next/link'

export default function StrategyConfigsPage() {
  // 状态管理
  const [configs, setConfigs] = useState<StrategyConfig[]>([])
  const [strategyTypes, setStrategyTypes] = useState<StrategyTypeMeta[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterType, setFilterType] = useState<string>('all')
  const [filterStatus, setFilterStatus] = useState<string>('all')

  // 对话框状态
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [selectedConfig, setSelectedConfig] = useState<StrategyConfig | null>(null)

  // 表单状态
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    strategy_type: '',
    config: {} as Record<string, any>
  })

  const { toast } = useToast()

  // 加载数据
  useEffect(() => {
    loadStrategyTypes()
    loadConfigs()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadStrategyTypes = async () => {
    try {
      const response = await apiClient.getStrategyTypes()
      if (response.success && response.data) {
        setStrategyTypes(response.data)
        if (response.data.length > 0 && !formData.strategy_type) {
          const firstType = response.data[0]
          setFormData(prev => ({
            ...prev,
            strategy_type: firstType.type,
            config: firstType.default_params
          }))
        }
      }
    } catch (error: any) {
      console.error('加载策略类型失败:', error)
    }
  }

  const loadConfigs = async () => {
    setIsLoading(true)
    try {
      const response = await apiClient.getStrategyConfigs()
      if (response.success && response.data) {
        setConfigs(response.data.items || [])
      }
    } catch (error: any) {
      toast({
        title: '加载失败',
        description: error.message || '无法加载策略配置列表',
        variant: 'destructive'
      })
    } finally {
      setIsLoading(false)
    }
  }

  // 筛选配置
  const filteredConfigs = (configs || []).filter(config => {
    // 搜索过滤
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      const matchName = config.name.toLowerCase().includes(query)
      const matchType = config.strategy_type.toLowerCase().includes(query)
      const matchDesc = config.description?.toLowerCase().includes(query)
      if (!matchName && !matchType && !matchDesc) return false
    }

    // 类型过滤
    if (filterType !== 'all' && config.strategy_type !== filterType) {
      return false
    }

    // 状态过滤
    if (filterStatus === 'active' && !config.is_active) return false
    if (filterStatus === 'inactive' && config.is_active) return false

    return true
  })

  // 打开创建对话框
  const handleOpenCreateDialog = () => {
    if (strategyTypes.length > 0) {
      setFormData({
        name: '',
        description: '',
        strategy_type: strategyTypes[0].type,
        config: strategyTypes[0].default_params
      })
    }
    setIsCreateDialogOpen(true)
  }

  // 打开编辑对话框
  const handleOpenEditDialog = (config: StrategyConfig) => {
    setSelectedConfig(config)
    setFormData({
      name: config.name,
      description: config.description || '',
      strategy_type: config.strategy_type,
      config: config.config
    })
    setIsEditDialogOpen(true)
  }

  // 打开删除确认对话框
  const handleOpenDeleteDialog = (config: StrategyConfig) => {
    setSelectedConfig(config)
    setIsDeleteDialogOpen(true)
  }

  // 创建配置
  const handleCreateConfig = async () => {
    if (!formData.name.trim()) {
      toast({
        title: '参数错误',
        description: '请输入配置名称',
        variant: 'destructive'
      })
      return
    }

    setIsLoading(true)
    try {
      const response = await apiClient.createStrategyConfig({
        strategy_type: formData.strategy_type,
        name: formData.name,
        config: formData.config,
        description: formData.description
      })

      if (response.success) {
        toast({
          title: '创建成功',
          description: '策略配置已创建'
        })
        setIsCreateDialogOpen(false)
        loadConfigs()
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

  // 更新配置
  const handleUpdateConfig = async () => {
    if (!selectedConfig) return

    if (!formData.name.trim()) {
      toast({
        title: '参数错误',
        description: '请输入配置名称',
        variant: 'destructive'
      })
      return
    }

    setIsLoading(true)
    try {
      const response = await apiClient.updateStrategyConfig(selectedConfig.id, {
        name: formData.name,
        config: formData.config,
        description: formData.description
      })

      if (response.success) {
        toast({
          title: '更新成功',
          description: '策略配置已更新'
        })
        setIsEditDialogOpen(false)
        loadConfigs()
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

  // 删除配置
  const handleDeleteConfig = async () => {
    if (!selectedConfig) return

    setIsLoading(true)
    try {
      const response = await apiClient.deleteStrategyConfig(selectedConfig.id)

      if (response.success) {
        toast({
          title: '删除成功',
          description: '策略配置已删除'
        })
        setIsDeleteDialogOpen(false)
        loadConfigs()
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

  // 测试配置
  const handleTestConfig = async (configId: number) => {
    setIsLoading(true)
    try {
      const response = await apiClient.testStrategyConfig(configId)

      if (response.success && response.data?.success) {
        toast({
          title: '测试成功',
          description: response.data.message || '策略配置测试通过'
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

  // 切换激活状态
  const handleToggleActive = async (config: StrategyConfig) => {
    setIsLoading(true)
    try {
      const response = await apiClient.updateStrategyConfig(config.id, {
        is_active: !config.is_active
      })

      if (response.success) {
        toast({
          title: '更新成功',
          description: `已${config.is_active ? '禁用' : '启用'}配置`
        })
        loadConfigs()
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

  const currentStrategyType = strategyTypes.find(t => t.type === formData.strategy_type)
  const uniqueTypes = Array.from(new Set((configs || []).map(c => c.strategy_type)))

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
            <h1 className="text-3xl font-bold tracking-tight">策略配置管理</h1>
            <p className="text-muted-foreground mt-2">
              创建、编辑和管理策略配置
            </p>
          </div>
          <Button onClick={handleOpenCreateDialog} size="lg">
            <Plus className="h-4 w-4 mr-2" />
            新建配置
          </Button>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                总配置数
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{(configs || []).length}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                启用配置
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-green-600">
                {(configs || []).filter(c => c.is_active).length}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                策略类型
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{uniqueTypes.length}</div>
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                可用策略
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold text-blue-600">
                {strategyTypes.length}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* 搜索和筛选 */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">筛选配置</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col md:flex-row gap-4">
              <div className="flex-1">
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="搜索配置名称、类型或描述..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="pl-9"
                  />
                </div>
              </div>
              <Select value={filterType} onValueChange={setFilterType}>
                <SelectTrigger className="w-full md:w-48">
                  <Filter className="h-4 w-4 mr-2" />
                  <SelectValue placeholder="策略类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">所有类型</SelectItem>
                  {uniqueTypes.map(type => (
                    <SelectItem key={type} value={type}>
                      {type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger className="w-full md:w-32">
                  <SelectValue placeholder="状态" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部</SelectItem>
                  <SelectItem value="active">启用</SelectItem>
                  <SelectItem value="inactive">禁用</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* 配置列表 */}
        {isLoading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : filteredConfigs.length === 0 ? (
          <Card className="p-12 text-center">
            <div className="flex flex-col items-center justify-center">
              <div className="rounded-full bg-muted p-6 mb-4">
                <Plus className="h-12 w-12 text-muted-foreground" />
              </div>
              <CardTitle className="mb-2">暂无策略配置</CardTitle>
              <CardDescription className="mb-4">
                {searchQuery || filterType !== 'all' || filterStatus !== 'all'
                  ? '没有符合筛选条件的配置'
                  : '点击"新建配置"按钮创建第一个策略配置'}
              </CardDescription>
              {!searchQuery && filterType === 'all' && filterStatus === 'all' && (
                <Button onClick={handleOpenCreateDialog}>
                  <Plus className="h-4 w-4 mr-2" />
                  新建配置
                </Button>
              )}
            </div>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredConfigs.map(config => (
              <StrategyCard
                key={config.id}
                type="config"
                data={config}
                onEdit={() => handleOpenEditDialog(config)}
                onDelete={() => handleOpenDeleteDialog(config)}
                onTest={() => handleTestConfig(config.id)}
              />
            ))}
          </div>
        )}
      </div>

      {/* 创建配置对话框 */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>新建策略配置</DialogTitle>
            <DialogDescription>
              选择策略类型并配置参数
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="create-name">配置名称 *</Label>
              <Input
                id="create-name"
                placeholder="例如: 我的动量策略"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="create-type">策略类型 *</Label>
              <Select
                value={formData.strategy_type}
                onValueChange={(value) => {
                  const type = strategyTypes.find(t => t.type === value)
                  setFormData({
                    ...formData,
                    strategy_type: value,
                    config: type?.default_params || {}
                  })
                }}
              >
                <SelectTrigger id="create-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {strategyTypes.map(type => (
                    <SelectItem key={type.type} value={type.type}>
                      {type.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {currentStrategyType && (
                <p className="text-sm text-muted-foreground">
                  {currentStrategyType.description}
                </p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="create-description">描述</Label>
              <Textarea
                id="create-description"
                placeholder="简要描述此配置的用途..."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={3}
              />
            </div>

            {currentStrategyType && (
              <div className="space-y-2">
                <Label className="text-base font-semibold">策略参数</Label>
                <div className="border rounded-lg p-4 bg-muted/30">
                  <StrategyConfigEditor
                    strategyType={formData.strategy_type}
                    config={formData.config}
                    schema={currentStrategyType.param_schema}
                    onChange={(config) => setFormData({ ...formData, config })}
                  />
                </div>
              </div>
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
            <Button onClick={handleCreateConfig} disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              创建配置
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 编辑配置对话框 */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>编辑策略配置</DialogTitle>
            <DialogDescription>
              修改配置名称、描述和参数
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">配置名称 *</Label>
              <Input
                id="edit-name"
                placeholder="例如: 我的动量策略"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>

            <div className="space-y-2">
              <Label>策略类型</Label>
              <div className="flex items-center gap-2">
                <Badge variant="secondary">{formData.strategy_type}</Badge>
                <span className="text-sm text-muted-foreground">
                  (策略类型不可修改)
                </span>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="edit-description">描述</Label>
              <Textarea
                id="edit-description"
                placeholder="简要描述此配置的用途..."
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={3}
              />
            </div>

            {currentStrategyType && (
              <div className="space-y-2">
                <Label className="text-base font-semibold">策略参数</Label>
                <div className="border rounded-lg p-4 bg-muted/30">
                  <StrategyConfigEditor
                    strategyType={formData.strategy_type}
                    config={formData.config}
                    schema={currentStrategyType.param_schema}
                    onChange={(config) => setFormData({ ...formData, config })}
                  />
                </div>
              </div>
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
            <Button onClick={handleUpdateConfig} disabled={isLoading}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              保存更改
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
              确定要删除配置 &ldquo;{selectedConfig?.name}&rdquo; 吗？此操作无法撤销。
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
              onClick={handleDeleteConfig}
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
