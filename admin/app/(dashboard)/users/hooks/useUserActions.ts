/**
 * 用户操作逻辑 Hook
 */
import { useCallback } from 'react'
import {
  useCreateUser,
  useUpdateUser,
  useDeleteUser,
  useToggleUserStatus,
  type User,
  type CreateUserDto,
  type UpdateUserDto,
} from '@/hooks/queries/use-users'
import type { UserFormData } from './useUserForm'

interface UseUserActionsProps {
  formData: UserFormData
  selectedUser: User | null
  validateCreateForm: () => boolean
  validateEditForm: () => boolean
  resetForm: () => void
  closeDialogs: () => void
}

export function useUserActions({
  formData,
  selectedUser,
  validateCreateForm,
  validateEditForm,
  resetForm,
  closeDialogs,
}: UseUserActionsProps) {
  const createUserMutation = useCreateUser()
  const updateUserMutation = useUpdateUser()
  const deleteUserMutation = useDeleteUser()
  const toggleStatusMutation = useToggleUserStatus()

  // 创建用户
  const handleCreate = async () => {
    if (!validateCreateForm()) {
      return
    }

    const createData: CreateUserDto = {
      email: formData.email,
      username: formData.username,
      password: formData.password,
      role: formData.role as 'admin' | 'user',
      is_active: true,
    }

    createUserMutation.mutate(createData, {
      onSuccess: () => {
        closeDialogs()
        resetForm()
      }
    })
  }

  // 编辑用户
  const handleEdit = async () => {
    if (!selectedUser || !validateEditForm()) {
      return
    }

    // 构建更新数据（只发送变更的字段）
    const updateData: UpdateUserDto = {
      role: formData.role,
    }

    if (formData.email && formData.email !== selectedUser.email) {
      updateData.email = formData.email
    }
    if (formData.password) {
      updateData.password = formData.password
    }

    updateUserMutation.mutate(
      { id: selectedUser.id, data: updateData },
      {
        onSuccess: () => {
          closeDialogs()
          resetForm()
        }
      }
    )
  }

  // 删除用户
  const handleDelete = async () => {
    if (!selectedUser) return

    deleteUserMutation.mutate(selectedUser.id, {
      onSuccess: () => {
        closeDialogs()
      }
    })
  }

  // 切换用户状态
  const handleToggleStatus = useCallback((user: User) => {
    toggleStatusMutation.mutate({
      id: user.id,
      is_active: !user.is_active
    })
  }, [toggleStatusMutation])

  return {
    createUserMutation,
    updateUserMutation,
    deleteUserMutation,
    toggleStatusMutation,
    handleCreate,
    handleEdit,
    handleDelete,
    handleToggleStatus,
  }
}
