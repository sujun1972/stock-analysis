/**
 * 概念标签管理页面
 *
 * 功能：
 * - 概念列表展示（分页、搜索）
 * - 创建新概念（含表单验证）
 * - 编辑概念信息
 * - 删除概念（含二次确认）
 * - 同步概念数据
 *
 * 响应式设计：
 * - 使用 DataTable 组件自动处理桌面/移动端切换
 * - 桌面端（≥768px）：表格视图
 * - 移动端（<768px）：卡片视图
 */
'use client'

import { useState, useEffect, useRef, useCallback, useMemo } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable, type Column } from '@/components/common/DataTable'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Plus, Search, RefreshCw, Edit, Trash2 } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { toast } from 'sonner'
import type { Concept } from '@/types/stock'
import { useTaskStore } from '@/stores/task-store'

export default function ConceptsPage() {
  const [concepts, setConcepts] = useState<Concept[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const pageSize = 50

  // 获取任务 store
  const tasks = useTaskStore((state) => state.tasks)
  const currentSyncTaskRef = useRef<string | null>(null)

  // 对话框状态
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [selectedConcept, setSelectedConcept] = useState<Concept | null>(null)
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    description: ''
  })

  // 加载概念列表
  const loadConcepts = useCallback(async () => {
    setLoading(true)
    try {
      const response = await apiClient.getConceptsList({
        page: page,
        page_size: pageSize,
        search: search || undefined,
      })
      setConcepts(response.items || [])
      setTotal(response.total || 0)
    } catch (error: any) {
      toast.error('加载概念列表失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }, [page, search])

  useEffect(() => {
    loadConcepts()
  }, [loadConcepts])

  // 检查是否有正在进行的概念同步任务
  const hasSyncingTask = Array.from(tasks.values()).some(
    (task) =>
      task.taskName === 'sync.concept' &&
      (task.status === 'pending' || task.status === 'running' || task.status === 'progress')
  )

  // 监听任务完成，自动刷新列表
  useEffect(() => {
    // 如果有当前同步任务ID
    if (currentSyncTaskRef.current) {
      const task = tasks.get(currentSyncTaskRef.current)

      // 任务完成（成功或失败）
      if (task && (task.status === 'success' || task.status === 'failure')) {
        if (task.status === 'success') {
          toast.success('概念数据同步完成，正在刷新列表...')
          loadConcepts()
        } else if (task.status === 'failure') {
          toast.error('概念数据同步失败: ' + (task.error || '未知错误'))
        }
        // 清除任务ID引用
        currentSyncTaskRef.current = null
      }
    }
  }, [tasks, loadConcepts])

  // 搜索时重置到第一页
  const handleSearch = (value: string) => {
    setSearch(value)
    setPage(1)
  }

  // 同步概念数据（使用系统配置的数据源）
  const handleSync = async () => {
    try {
      // 不传source参数，让后端使用系统配置的数据源
      const response = await apiClient.syncConcepts()

      // 保存任务ID，用于后续监听（后端返回格式：response.data.task_id）
      const taskId = (response?.data as any)?.task_id || (response as any)?.task_id
      if (taskId) {
        currentSyncTaskRef.current = taskId
        toast.success('概念数据同步任务已提交，请在任务面板查看进度')
      } else {
        toast.success('概念数据同步任务已提交')
      }
    } catch (error: any) {
      toast.error('同步失败: ' + (error.message || '未知错误'))
    }
  }

  // 创建概念
  const handleCreate = async () => {
    if (!formData.code || !formData.name) {
      toast.error('请填写概念代码和名称')
      return
    }

    try {
      await apiClient.createConcept({
        code: formData.code,
        name: formData.name,
        description: formData.description || undefined,
      })
      toast.success('创建成功')
      setIsCreateDialogOpen(false)
      setFormData({ code: '', name: '', description: '' })
      loadConcepts()
    } catch (error: any) {
      toast.error('创建失败: ' + (error.message || '未知错误'))
    }
  }

  // 编辑概念
  const handleEdit = async () => {
    if (!selectedConcept || !formData.name) {
      toast.error('请填写概念名称')
      return
    }

    try {
      await apiClient.updateConcept(selectedConcept.id, {
        code: formData.code,
        name: formData.name,
        description: formData.description || undefined,
      })
      toast.success('更新成功')
      setIsEditDialogOpen(false)
      setSelectedConcept(null)
      setFormData({ code: '', name: '', description: '' })
      loadConcepts()
    } catch (error: any) {
      toast.error('更新失败: ' + (error.message || '未知错误'))
    }
  }

  // 删除概念
  const handleDelete = async () => {
    if (!selectedConcept) return

    try {
      await apiClient.deleteConcept(selectedConcept.id)
      toast.success('删除成功')
      setIsDeleteDialogOpen(false)
      setSelectedConcept(null)
      loadConcepts()
    } catch (error: any) {
      toast.error('删除失败: ' + (error.message || '未知错误'))
    }
  }

  // 打开编辑对话框
  const openEditDialog = (concept: Concept) => {
    setSelectedConcept(concept)
    setFormData({
      code: concept.code,
      name: concept.name,
      description: concept.description || '',
    })
    setIsEditDialogOpen(true)
  }

  // 打开删除确认对话框
  const openDeleteDialog = (concept: Concept) => {
    setSelectedConcept(concept)
    setIsDeleteDialogOpen(true)
  }

  // 定义表格列
  const columns: Column<Concept>[] = useMemo(() => [
    {
      key: 'id',
      header: 'ID',
      width: 80,
    },
    {
      key: 'code',
      header: '代码',
      cellClassName: 'font-mono',
    },
    {
      key: 'name',
      header: '名称',
      cellClassName: 'font-medium',
    },
    {
      key: 'description',
      header: '描述',
      accessor: (concept) => concept.description || '-',
      cellClassName: 'max-w-xs truncate',
      hideOnMobile: true,
    },
    {
      key: 'source',
      header: '数据源',
      hideOnMobile: true,
    },
    {
      key: 'stock_count',
      header: '股票数量',
      accessor: (concept) => (
        <Badge variant="secondary" className="bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
          {concept.stock_count} 只
        </Badge>
      ),
      align: 'center',
    },
    {
      key: 'created_at',
      header: '创建时间',
      accessor: (concept) =>
        concept.created_at
          ? new Date(concept.created_at).toLocaleDateString('zh-CN')
          : '-',
      hideOnMobile: true,
    },
  ], [])

  // 移动端卡片渲染
  const mobileCard = useCallback((concept: Concept) => (
    <div className="border rounded-lg p-4 bg-white space-y-3">
      {/* 顶部：概念名称和操作按钮 */}
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-base">{concept.name}</div>
          <div className="text-sm text-gray-500 font-mono">{concept.code}</div>
        </div>
        <div className="flex gap-1 ml-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => openEditDialog(concept)}
            className="h-8 w-8 shrink-0"
          >
            <Edit className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => openDeleteDialog(concept)}
            className="h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50 shrink-0"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* 描述 */}
      {concept.description && (
        <div className="text-sm text-gray-600">{concept.description}</div>
      )}

      {/* 信息标签 */}
      <div className="flex flex-wrap gap-2 items-center">
        <Badge variant="secondary" className="bg-blue-100 text-blue-800">
          {concept.stock_count} 只股票
        </Badge>
        <span className="text-xs text-gray-500">
          来源: {concept.source}
        </span>
      </div>

      {/* 底部信息：ID、创建时间 */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 pt-2 border-t">
        <div>ID: <span className="font-mono">{concept.id}</span></div>
        <div className="w-full sm:w-auto">
          创建于: {concept.created_at ? new Date(concept.created_at).toLocaleDateString('zh-CN') : '-'}
        </div>
      </div>
    </div>
  ), [])

  // 操作列渲染
  const actions = useCallback((concept: Concept) => (
    <div className="flex items-center justify-end gap-2">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => openEditDialog(concept)}
      >
        <Edit className="h-4 w-4" />
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => openDeleteDialog(concept)}
      >
        <Trash2 className="h-4 w-4 text-destructive" />
      </Button>
    </div>
  ), [])

  return (
    <div className="space-y-6">
      {/* 页面标题和操作栏 */}
      <PageHeader
        title="概念标签管理"
        description="管理股票概念标签，包括创建、编辑、删除和同步"
        actions={
          <>
            <Button
              onClick={handleSync}
              variant="outline"
              disabled={hasSyncingTask}
              className="flex-1 sm:flex-none"
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${hasSyncingTask ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">
                {hasSyncingTask ? '同步中...' : '同步概念数据'}
              </span>
              <span className="sm:hidden">
                {hasSyncingTask ? '同步中' : '同步'}
              </span>
            </Button>
            <Button onClick={() => setIsCreateDialogOpen(true)} className="flex-1 sm:flex-none">
              <Plus className="mr-2 h-4 w-4" />
              创建概念
            </Button>
          </>
        }
      />

      {/* 搜索和筛选 */}
      <Card>
        <CardHeader>
          <CardTitle>搜索筛选</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索概念代码或名称..."
                value={search}
                onChange={(e) => handleSearch(e.target.value)}
                className="pl-10"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 概念列表 - 使用 DataTable 组件 */}
      <Card>
        <CardHeader>
          <CardTitle>概念列表</CardTitle>
          <CardDescription>
            共 {total} 个概念标签
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DataTable
            data={concepts}
            columns={columns}
            loading={loading}
            emptyMessage="暂无概念数据"
            loadingMessage="加载中..."
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: setPage,
            }}
            actions={actions}
            mobileCard={mobileCard}
            rowKey={(concept) => concept.id}
          />
        </CardContent>
      </Card>

      {/* 创建概念对话框 */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent className="max-w-md max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>创建概念标签</DialogTitle>
            <DialogDescription>
              填写概念标签的基本信息
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4 px-2 overflow-y-auto flex-1">
            <div className="space-y-2">
              <Label htmlFor="code">概念代码 <span className="text-red-500">*</span></Label>
              <Input
                id="code"
                placeholder="例如: NEW_ENERGY"
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="name">概念名称 <span className="text-red-500">*</span></Label>
              <Input
                id="name"
                placeholder="例如: 新能源"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">描述</Label>
              <Textarea
                id="description"
                placeholder="概念描述（可选）"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={3}
              />
            </div>
          </div>
          <DialogFooter className="flex-row gap-2">
            <Button
              variant="outline"
              onClick={() => setIsCreateDialogOpen(false)}
              className="flex-1"
            >
              取消
            </Button>
            <Button onClick={handleCreate} className="flex-1">创建</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 编辑概念对话框 */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent className="max-w-md max-h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>编辑概念标签</DialogTitle>
            <DialogDescription>
              修改概念标签的信息
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4 px-2 overflow-y-auto flex-1">
            <div className="space-y-2">
              <Label htmlFor="edit-code">概念代码</Label>
              <Input
                id="edit-code"
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-name">概念名称 <span className="text-red-500">*</span></Label>
              <Input
                id="edit-name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-description">描述</Label>
              <Textarea
                id="edit-description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={3}
              />
            </div>
          </div>
          <DialogFooter className="flex-row gap-2">
            <Button
              variant="outline"
              onClick={() => setIsEditDialogOpen(false)}
              className="flex-1"
            >
              取消
            </Button>
            <Button onClick={handleEdit} className="flex-1">保存</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 删除确认对话框 */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>确认删除概念标签？</DialogTitle>
            <DialogDescription className="space-y-2">
              <span className="block">
                您即将删除概念标签 <span className="font-semibold">{selectedConcept?.name}</span>
              </span>
              <span className="block text-sm">代码: {selectedConcept?.code}</span>
              <span className="block text-red-600 font-medium mt-2">
                此操作无法撤销，请谨慎操作。
              </span>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex-row gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setIsDeleteDialogOpen(false)
                setSelectedConcept(null)
              }}
              className="flex-1"
            >
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              className="flex-1"
            >
              确认删除
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}