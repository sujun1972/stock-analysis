'use client'

import { useState, useEffect } from 'react'
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
import { Plus, Search, RefreshCw, Edit, Trash2, Tag } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { toast } from 'sonner'
import type { Concept } from '@/types/stock'

export default function ConceptsPage() {
  const [concepts, setConcepts] = useState<Concept[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const pageSize = 50

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
  const loadConcepts = async () => {
    setLoading(true)
    try {
      const response = await apiClient.getConceptsList({
        limit: pageSize,
        search: search || undefined,
      })
      setConcepts(response.items || [])
      setTotal(response.total || 0)
    } catch (error: any) {
      toast.error('加载概念列表失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadConcepts()
  }, [search])

  // 同步概念数据
  const handleSync = async () => {
    setLoading(true)
    try {
      await apiClient.syncConcepts('ths')
      toast.success('概念数据同步成功')
      loadConcepts()
    } catch (error: any) {
      toast.error('同步失败: ' + (error.message || '未知错误'))
    } finally {
      setLoading(false)
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
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">概念标签管理</h1>
              <p className="text-muted-foreground mt-2">
                管理股票概念标签，包括创建、编辑、删除和同步
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button onClick={handleSync} variant="outline" disabled={loading}>
                <RefreshCw className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                同步概念数据
              </Button>
              <Button onClick={() => setIsCreateDialogOpen(true)}>
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
                    onChange={(e) => setSearch(e.target.value)}
                    className="pl-10"
                  />
                </div>
                <Button onClick={loadConcepts} variant="outline">
                  <Search className="mr-2 h-4 w-4" />
                  搜索
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* 概念列表 */}
          <Card>
            <CardHeader>
              <CardTitle>概念列表</CardTitle>
              <CardDescription>
                共 {total} 个概念标签
              </CardDescription>
            </CardHeader>
            <CardContent>
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
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-8">
                        <div className="flex items-center justify-center">
                          <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
                          加载中...
                        </div>
                      </TableCell>
                    </TableRow>
                  ) : concepts.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center py-8 text-muted-foreground">
                        暂无概念数据
                      </TableCell>
                    </TableRow>
                  ) : (
                    concepts.map((concept) => (
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
                    ))
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {/* 创建概念对话框 */}
          <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>创建概念标签</DialogTitle>
                <DialogDescription>
                  填写概念标签的基本信息
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="code">概念代码 *</Label>
                  <Input
                    id="code"
                    placeholder="例如: NEW_ENERGY"
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="name">概念名称 *</Label>
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
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsCreateDialogOpen(false)}>
                  取消
                </Button>
                <Button onClick={handleCreate}>创建</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          {/* 编辑概念对话框 */}
          <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>编辑概念标签</DialogTitle>
                <DialogDescription>
                  修改概念标签的信息
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="edit-code">概念代码</Label>
                  <Input
                    id="edit-code"
                    value={formData.code}
                    onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="edit-name">概念名称 *</Label>
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
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
                  取消
                </Button>
                <Button onClick={handleEdit}>保存</Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>

          {/* 删除确认对话框 */}
          <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>确认删除</DialogTitle>
                <DialogDescription>
                  确定要删除概念标签 "{selectedConcept?.name}" 吗？此操作不可恢复。
                </DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)}>
                  取消
                </Button>
                <Button variant="destructive" onClick={handleDelete}>
                  删除
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
  )
}
