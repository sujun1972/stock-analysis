'use client'

import { useState } from 'react'
import { Strategy } from '@/types/strategy'
import { strategyApi, axiosInstance } from '@/lib/api'
import logger from '@/lib/logger'
import { toast } from 'sonner'

export interface User {
  id: number
  username: string
  email: string
  full_name?: string
}

export function useStrategiesActions(fetchStrategies: () => Promise<void>) {
  // 用户编辑对话框状态
  const [editUserDialogOpen, setEditUserDialogOpen] = useState(false)
  const [editingStrategy, setEditingStrategy] = useState<Strategy | null>(null)
  const [selectedUserId, setSelectedUserId] = useState<string>('')
  const [users, setUsers] = useState<User[]>([])
  const [loadingUsers, setLoadingUsers] = useState(false)
  const [updatingUser, setUpdatingUser] = useState(false)
  const [userSearchTerm, setUserSearchTerm] = useState('')

  // 详情对话框状态
  const [isDetailDialogOpen, setIsDetailDialogOpen] = useState(false)
  const [selectedStrategy, setSelectedStrategy] = useState<Strategy | null>(null)

  // 删除确认对话框
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deletingStrategy, setDeletingStrategy] = useState<Strategy | null>(null)

  // 获取用户列表
  const fetchUsers = async (searchQuery: string = '') => {
    setLoadingUsers(true)
    try {
      const params = new URLSearchParams({
        page: '1',
        page_size: '50',
      })

      if (searchQuery) {
        params.append('search', searchQuery)
      }

      const response = await axiosInstance.get(`/api/users?${params}`) as any

      if (response?.code === 200 && response.data?.users) {
        setUsers(response.data.users)
      } else {
        setUsers([])
      }
    } catch (error) {
      logger.error('获取用户列表失败', error)
      setUsers([])
    } finally {
      setLoadingUsers(false)
    }
  }

  // 打开用户编辑对话框
  const openEditUserDialog = async (strategy: Strategy) => {
    setEditingStrategy(strategy)
    setSelectedUserId(strategy.user_id?.toString() || '')
    setUserSearchTerm('')
    setEditUserDialogOpen(true)
    await fetchUsers()
  }

  // 更新策略用户归属
  const handleUpdateStrategyUser = async () => {
    if (!editingStrategy) return

    setUpdatingUser(true)
    try {
      const userId = selectedUserId ? parseInt(selectedUserId) : null
      await axiosInstance.put(`/api/strategies/${editingStrategy.id}`, {
        user_id: userId
      })
      toast.success('用户归属更新成功')
      setEditUserDialogOpen(false)
      fetchStrategies()
    } catch (error) {
      logger.error('更新策略用户归属失败', error)
      toast.error('更新失败')
    } finally {
      setUpdatingUser(false)
    }
  }

  // 切换策略启用状态
  const toggleStrategyStatus = async (strategy: Strategy) => {
    try {
      await axiosInstance.put(`/api/strategies/${strategy.id}`, {
        is_enabled: !strategy.is_enabled
      })
      toast.success(strategy.is_enabled ? '策略已禁用' : '策略已启用')
      fetchStrategies()
    } catch (error) {
      logger.error('更新策略状态失败', error)
      toast.error('更新失败')
    }
  }

  // 删除策略
  const handleDeleteStrategy = async () => {
    if (!deletingStrategy) return

    try {
      await strategyApi.deleteStrategy(deletingStrategy.id)
      toast.success('策略删除成功')
      setDeleteDialogOpen(false)
      fetchStrategies()
    } catch (error) {
      logger.error('删除策略失败', error)
      toast.error('删除失败')
    }
  }

  // 取消发布策略
  const handleUnpublish = async (strategy: Strategy) => {
    try {
      await strategyApi.unpublishStrategy(strategy.id)
      toast.success('策略已取消发布')
      fetchStrategies()
    } catch (error) {
      logger.error('取消发布失败', error)
      toast.error('取消发布失败')
    }
  }

  // 打开详情对话框
  const openDetailDialog = (strategy: Strategy) => {
    setSelectedStrategy(strategy)
    setIsDetailDialogOpen(true)
  }

  // 打开删除确认对话框
  const openDeleteDialog = (strategy: Strategy) => {
    setDeletingStrategy(strategy)
    setDeleteDialogOpen(true)
  }

  return {
    // 用户编辑对话框
    editUserDialogOpen,
    setEditUserDialogOpen,
    editingStrategy,
    selectedUserId,
    setSelectedUserId,
    users,
    loadingUsers,
    updatingUser,
    userSearchTerm,
    setUserSearchTerm,
    openEditUserDialog,
    handleUpdateStrategyUser,

    // 详情对话框
    isDetailDialogOpen,
    setIsDetailDialogOpen,
    selectedStrategy,
    openDetailDialog,

    // 删除对话框
    deleteDialogOpen,
    setDeleteDialogOpen,
    deletingStrategy,
    handleDeleteStrategy,
    openDeleteDialog,

    // 策略操作
    toggleStrategyStatus,
    handleUnpublish,
  }
}
