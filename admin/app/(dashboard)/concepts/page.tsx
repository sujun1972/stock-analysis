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
 * - 桌面端（≥768px）：表格视图，紧凑操作按钮
 * - 移动端（<768px）：卡片视图，图标操作按钮
 * - 对话框：支持小屏幕滚动，自适应布局
 */
'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
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
import { Plus, Search, RefreshCw, Edit, Trash2, ChevronLeft, ChevronRight } from 'lucide-react'
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
  const [totalPages, setTotalPages] = useState(0)
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
      setTotalPages(response.total_pages || 0)
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

  return (
        <div className="space-y-6">
          {/* 页面标题和操作栏 */}
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">概念标签管理</h1>
              <p className="text-sm sm:text-base text-muted-foreground mt-1 sm:mt-2">
                管理股票概念标签，包括创建、编辑、删除和同步
              </p>
            </div>
            <div className="flex items-center gap-2">
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
            </div>
          </div>

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

          {/* 概念列表 */}
          <Card>
            <CardHeader>
              <CardTitle>概念列表</CardTitle>
              <CardDescription>
                共 {total} 个概念标签，第 {page}/{totalPages} 页
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* 加载和空状态 */}
              {loading ? (
                <div className="text-center py-12 text-gray-500">
                  <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-2" />
                  加载中...
                </div>
              ) : concepts.length === 0 ? (
                <div className="text-center py-12 text-gray-500">
                  暂无概念数据
                </div>
              ) : (
                <>
                  {/* 桌面端表格视图 - 隐藏在小屏幕 */}
                  <div className="hidden md:block border rounded-lg">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>ID</TableHead>
                          <TableHead>代码</TableHead>
                          <TableHead>名称</TableHead>
                          <TableHead>描述</TableHead>
                          <TableHead>数据源</TableHead>
                          <TableHead>股票数量</TableHead>
                          <TableHead>创建时间</TableHead>
                          <TableHead className="text-right">操作</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {concepts.map((concept) => (
                          <TableRow key={concept.id}>
                            <TableCell>{concept.id}</TableCell>
                            <TableCell className="font-mono">{concept.code}</TableCell>
                            <TableCell className="font-medium">{concept.name}</TableCell>
                            <TableCell className="max-w-xs truncate">
                              {concept.description || '-'}
                            </TableCell>
                            <TableCell>{concept.source}</TableCell>
                            <TableCell>
                              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                                {concept.stock_count} 只
                              </span>
                            </TableCell>
                            <TableCell>
                              {concept.created_at
                                ? new Date(concept.created_at).toLocaleDateString('zh-CN')
                                : '-'}
                            </TableCell>
                            <TableCell className="text-right">
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
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </div>

                  {/* 移动端卡片视图 - 仅在小屏幕显示 */}
                  <div className="md:hidden space-y-4">
                    {concepts.map((concept) => (
                      <div key={concept.id} className="border rounded-lg p-4 bg-white space-y-3">
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
                          <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                            {concept.stock_count} 只股票
                          </span>
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
                    ))}
                  </div>
                </>
              )}

              {/* 分页控件 */}
              {totalPages > 1 && (
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mt-4">
                  <div className="text-sm text-gray-600 order-2 sm:order-1">
                    显示 {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, total)} / {total}
                  </div>
                  <div className="flex items-center gap-2 w-full sm:w-auto order-1 sm:order-2">
                    {/* 移动端简化分页 */}
                    <div className="flex sm:hidden w-full gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage(p => Math.max(1, p - 1))}
                        disabled={page === 1 || loading}
                        className="flex-1"
                      >
                        <ChevronLeft className="h-4 w-4 mr-1" />
                        上一页
                      </Button>
                      <div className="flex items-center justify-center px-3 text-sm font-medium min-w-[60px]">
                        {page}/{totalPages}
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage(p => p + 1)}
                        disabled={page === totalPages || loading}
                        className="flex-1"
                      >
                        下一页
                        <ChevronRight className="h-4 w-4 ml-1" />
                      </Button>
                    </div>

                    {/* 桌面端完整分页 */}
                    <div className="hidden sm:flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage(1)}
                        disabled={page === 1 || loading}
                      >
                        首页
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage(page - 1)}
                        disabled={page === 1 || loading}
                      >
                        <ChevronLeft className="h-4 w-4 mr-1" />
                        上一页
                      </Button>
                      <div className="flex items-center gap-1">
                        {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                          let pageNum: number
                          if (totalPages <= 5) {
                            pageNum = i + 1
                          } else if (page <= 3) {
                            pageNum = i + 1
                          } else if (page >= totalPages - 2) {
                            pageNum = totalPages - 4 + i
                          } else {
                            pageNum = page - 2 + i
                          }
                          return (
                            <Button
                              key={pageNum}
                              variant={page === pageNum ? 'default' : 'outline'}
                              size="sm"
                              onClick={() => setPage(pageNum)}
                              disabled={loading}
                              className="w-10"
                            >
                              {pageNum}
                            </Button>
                          )
                        })}
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage(page + 1)}
                        disabled={page === totalPages || loading}
                      >
                        下一页
                        <ChevronRight className="h-4 w-4 ml-1" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setPage(totalPages)}
                        disabled={page === totalPages || loading}
                      >
                        末页
                      </Button>
                    </div>
                  </div>
                </div>
              )}
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
