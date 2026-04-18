'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import DynamicStrategyCodeEditor from '@/components/strategies/DynamicStrategyCodeEditor'
import StrategyCard from '@/components/strategies/StrategyCard'
import StrategyFormDialog from './components/StrategyFormDialog'
import { useDynamicStrategies } from './hooks/useDynamicStrategies'
import { Loader2, Plus, Search, Filter, ArrowLeft, AlertTriangle, CheckCircle, Code2 } from 'lucide-react'
import Link from 'next/link'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

export default function DynamicStrategiesPage() {
  const {
    strategies,
    filteredStrategies,
    isLoading,
    validationStats,
    searchQuery,
    setSearchQuery,
    filterStatus,
    setFilterStatus,
    filterValidation,
    setFilterValidation,
    isCreateDialogOpen,
    setIsCreateDialogOpen,
    isEditDialogOpen,
    setIsEditDialogOpen,
    isDeleteDialogOpen,
    setIsDeleteDialogOpen,
    isViewCodeDialogOpen,
    setIsViewCodeDialogOpen,
    selectedStrategy,
    formData,
    setFormData,
    validationResult,
    handleOpenCreateDialog,
    handleOpenEditDialog,
    handleOpenDeleteDialog,
    handleValidateCode,
    handleCreateStrategy,
    handleUpdateStrategy,
    handleDeleteStrategy,
  } = useDynamicStrategies()

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
                strategy={strategy as any}
                onEdit={() => handleOpenEditDialog(strategy)}
                onDelete={() => handleOpenDeleteDialog(strategy)}
              />
            ))}
          </div>
        )}
      </div>

      {/* 创建策略对话框 */}
      <StrategyFormDialog
        mode="create"
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
        formData={formData}
        onFormDataChange={setFormData}
        validationResult={validationResult}
        isLoading={isLoading}
        onValidateCode={handleValidateCode}
        onSubmit={handleCreateStrategy}
      />

      {/* 编辑策略对话框 */}
      <StrategyFormDialog
        mode="edit"
        open={isEditDialogOpen}
        onOpenChange={setIsEditDialogOpen}
        formData={formData}
        onFormDataChange={setFormData}
        validationResult={validationResult}
        isLoading={isLoading}
        onValidateCode={handleValidateCode}
        onSubmit={handleUpdateStrategy}
      />

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
