'use client'

import { useRouter } from 'next/navigation'
import { Plus } from 'lucide-react'
import { PageHeader } from '@/components/common/PageHeader'
import { Button } from '@/components/ui/button'

import { useStrategiesData, useStrategiesActions } from './hooks'
import {
  StrategyFilters,
  StrategyTable,
  StrategyDetailDialog,
  UserAssignDialog,
  DeleteConfirmDialog,
} from './components'

export default function StrategiesPage() {
  const router = useRouter()

  const data = useStrategiesData()

  const actions = useStrategiesActions(data.fetchStrategies)

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <PageHeader
        title="策略管理"
        description="管理和监控所有交易策略"
        actions={
          <Button onClick={() => router.push('/strategies/create')}>
            <Plus className="mr-2 h-4 w-4" />
            创建策略
          </Button>
        }
      />

      {/* 筛选器 */}
      <StrategyFilters
        searchTerm={data.searchTerm}
        onSearchTermChange={data.setSearchTerm}
        filterStrategyType={data.filterStrategyType}
        onFilterStrategyTypeChange={data.setFilterStrategyType}
        filterSourceType={data.filterSourceType}
        onFilterSourceTypeChange={data.setFilterSourceType}
        filterPublishStatus={data.filterPublishStatus}
        onFilterPublishStatusChange={data.setFilterPublishStatus}
        filterUserId={data.filterUserId}
        onFilterUserIdChange={data.setFilterUserId}
        onResetFilters={data.handleResetFilters}
      />

      {/* 策略列表 */}
      <StrategyTable
        strategies={data.strategies}
        loading={data.loading}
        currentPage={data.currentPage}
        pageSize={data.pageSize}
        totalCount={data.totalCount}
        onPageChange={data.setCurrentPage}
        onToggleStatus={actions.toggleStrategyStatus}
        onOpenDetail={actions.openDetailDialog}
        onOpenEditUser={actions.openEditUserDialog}
        onOpenDelete={actions.openDeleteDialog}
        onUnpublish={actions.handleUnpublish}
      />

      {/* 用户编辑对话框 */}
      <UserAssignDialog
        open={actions.editUserDialogOpen}
        onOpenChange={actions.setEditUserDialogOpen}
        editingStrategy={actions.editingStrategy}
        selectedUserId={actions.selectedUserId}
        onSelectedUserIdChange={actions.setSelectedUserId}
        users={actions.users}
        loadingUsers={actions.loadingUsers}
        updatingUser={actions.updatingUser}
        userSearchTerm={actions.userSearchTerm}
        onUserSearchTermChange={actions.setUserSearchTerm}
        onConfirm={actions.handleUpdateStrategyUser}
      />

      {/* 策略详情对话框 */}
      <StrategyDetailDialog
        open={actions.isDetailDialogOpen}
        onOpenChange={actions.setIsDetailDialogOpen}
        strategy={actions.selectedStrategy}
      />

      {/* 删除确认对话框 */}
      <DeleteConfirmDialog
        open={actions.deleteDialogOpen}
        onOpenChange={actions.setDeleteDialogOpen}
        strategy={actions.deletingStrategy}
        onConfirm={actions.handleDeleteStrategy}
      />
    </div>
  )
}
