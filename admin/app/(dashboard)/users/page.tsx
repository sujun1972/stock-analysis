/**
 * 用户管理页面
 *
 * 功能：
 * - 用户列表展示（分页、搜索、筛选）
 * - 创建新用户（含表单验证）
 * - 编辑用户信息（邮箱、角色、邮箱验证状态等）
 * - 删除用户（含二次确认）
 * - 查看用户详细信息（配额使用情况、登录统计等）
 *
 * 响应式设计：
 * - 使用 DataTable 组件自动处理桌面/移动端切换
 * - 桌面端（≥768px）：表格视图
 * - 移动端（<768px）：卡片视图
 *
 * 架构：Hooks + Components 模式
 * - hooks/: 数据管理和业务逻辑
 * - components/: UI 组件
 */
'use client'

import { useMemo, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader } from '@/components/common/PageHeader'
import { DataTable } from '@/components/common/DataTable'
import { Plus } from 'lucide-react'
import { toast } from 'sonner'
import { useUserList, type User } from '@/hooks/queries/use-users'

// Hooks
import {
  useUserFilters,
  useUserDialogs,
  useUserForm,
  useUserActions,
} from './hooks'

// Components
import {
  UserFilters,
  getUserTableColumns,
  UserMobileCard,
  UserActions,
  CreateUserDialog,
  EditUserDialog,
  DeleteUserDialog,
  UserDetailDialog,
} from './components'

export default function UsersPage() {
  // 筛选和分页
  const {
    search,
    setSearch,
    roleFilter,
    setRoleFilter,
    page,
    setPage,
    pageSize,
    queryParams,
    handleSearch,
  } = useUserFilters()

  // 对话框管理
  const {
    isCreateDialogOpen,
    setIsCreateDialogOpen,
    isEditDialogOpen,
    setIsEditDialogOpen,
    isDeleteDialogOpen,
    setIsDeleteDialogOpen,
    isDetailDialogOpen,
    setIsDetailDialogOpen,
    selectedUser,
    openDetailDialog,
    openEditDialog,
    openDeleteDialog,
    closeDialogs,
  } = useUserDialogs()

  // 表单管理
  const {
    formData,
    setFormData,
    resetForm,
    validateCreateForm,
    validateEditForm,
  } = useUserForm()

  // 数据查询
  const { data, isLoading, error, refetch } = useUserList(queryParams)
  const users = data?.items || []
  const total = data?.total || 0

  // 用户操作
  const {
    createUserMutation,
    updateUserMutation,
    deleteUserMutation,
    toggleStatusMutation,
    handleCreate,
    handleEdit,
    handleDelete,
    handleToggleStatus,
  } = useUserActions({
    formData,
    selectedUser,
    validateCreateForm,
    validateEditForm,
    resetForm,
    closeDialogs,
  })

  // 打开编辑对话框（需要填充表单数据）
  const handleOpenEditDialog = useCallback((user: User) => {
    setFormData({
      email: user.email,
      username: user.username,
      password: '', // 密码保持为空，只在需要修改时填写
      full_name: '',
      phone: '',
      role: user.role as any,
      is_email_verified: user.is_email_verified,
    })
    openEditDialog(user)
  }, [setFormData, openEditDialog])

  // 表格列定义
  const columns = useMemo(() =>
    getUserTableColumns(handleToggleStatus, toggleStatusMutation.isPending),
    [handleToggleStatus, toggleStatusMutation.isPending]
  )

  // 移动端卡片渲染
  const mobileCard = useCallback((user: User) => (
    <UserMobileCard
      user={user}
      onEdit={handleOpenEditDialog}
      onDelete={openDeleteDialog}
    />
  ), [handleOpenEditDialog, openDeleteDialog])

  // 操作列渲染
  const actions = useCallback((user: User) => (
    <UserActions
      user={user}
      onDetail={openDetailDialog}
      onEdit={handleOpenEditDialog}
      onDelete={openDeleteDialog}
    />
  ), [openDetailDialog, handleOpenEditDialog, openDeleteDialog])

  // 关闭创建对话框
  const handleCloseCreateDialog = useCallback(() => {
    setIsCreateDialogOpen(false)
    resetForm()
  }, [setIsCreateDialogOpen, resetForm])

  // 关闭编辑对话框
  const handleCloseEditDialog = useCallback(() => {
    setIsEditDialogOpen(false)
    resetForm()
  }, [setIsEditDialogOpen, resetForm])

  // 关闭删除对话框
  const handleCloseDeleteDialog = useCallback(() => {
    setIsDeleteDialogOpen(false)
  }, [setIsDeleteDialogOpen])

  // 从详情对话框跳转到编辑对话框
  const handleEditFromDetail = useCallback(() => {
    setIsDetailDialogOpen(false)
    if (selectedUser) {
      handleOpenEditDialog(selectedUser)
    }
  }, [setIsDetailDialogOpen, selectedUser, handleOpenEditDialog])

  // 处理错误
  if (error) {
    toast.error('加载用户列表失败: ' + error.message)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="用户管理"
        description={`管理系统用户和权限 (${total} 个用户)`}
        actions={
          <Button onClick={() => setIsCreateDialogOpen(true)} className="w-full sm:w-auto">
            <Plus className="mr-2 h-4 w-4" />
            创建用户
          </Button>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle>用户列表</CardTitle>
        </CardHeader>

        <CardContent>
          {/* 搜索和筛选 */}
          <div className="mb-6">
            <UserFilters
              search={search}
              setSearch={setSearch}
              roleFilter={roleFilter}
              setRoleFilter={setRoleFilter}
              onSearch={handleSearch}
              onRefresh={refetch}
              isLoading={isLoading}
            />
          </div>

          {/* 用户列表 */}
          <DataTable
            data={users}
            columns={columns}
            loading={isLoading}
            emptyMessage="暂无用户数据"
            loadingMessage="加载中..."
            pagination={{
              page,
              pageSize,
              total,
              onPageChange: setPage,
            }}
            actions={actions}
            mobileCard={mobileCard}
            rowKey={(user) => user.id}
          />
        </CardContent>
      </Card>

      {/* 创建用户对话框 */}
      <CreateUserDialog
        open={isCreateDialogOpen}
        onOpenChange={setIsCreateDialogOpen}
        formData={formData}
        setFormData={setFormData}
        onCreate={handleCreate}
        onCancel={handleCloseCreateDialog}
        isCreating={createUserMutation.isPending}
      />

      {/* 编辑用户对话框 */}
      <EditUserDialog
        open={isEditDialogOpen}
        onOpenChange={setIsEditDialogOpen}
        formData={formData}
        setFormData={setFormData}
        onEdit={handleEdit}
        onCancel={handleCloseEditDialog}
        isEditing={updateUserMutation.isPending}
      />

      {/* 删除用户确认对话框 */}
      <DeleteUserDialog
        open={isDeleteDialogOpen}
        onOpenChange={setIsDeleteDialogOpen}
        user={selectedUser}
        onDelete={handleDelete}
        onCancel={handleCloseDeleteDialog}
        isDeleting={deleteUserMutation.isPending}
      />

      {/* 用户详情对话框 */}
      <UserDetailDialog
        open={isDetailDialogOpen}
        onOpenChange={setIsDetailDialogOpen}
        user={selectedUser}
        onEdit={handleEditFromDetail}
        onClose={closeDialogs}
      />
    </div>
  )
}
