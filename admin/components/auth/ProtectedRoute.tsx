'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/stores/auth-store'
import { Loader2 } from 'lucide-react'

interface ProtectedRouteProps {
  children: React.ReactNode
  requireAdmin?: boolean
  requireSuperAdmin?: boolean
}

/**
 * 路由保护组件
 *
 * 功能:
 * 1. 验证用户登录状态
 * 2. 检查用户权限级别
 * 3. 自动重定向未授权用户
 *
 * 优化:
 * - 只在首次挂载时检查认证状态，避免重复API调用
 * - 使用localStorage缓存，无需每次都调用 /api/auth/me
 * - Token过期时自动刷新，对用户透明
 * - 修复页面切换时的闪烁问题：等待 Zustand persist 恢复完成
 */
export function ProtectedRoute({
  children,
  requireAdmin = true,
  requireSuperAdmin = false,
}: ProtectedRouteProps) {
  const router = useRouter()
  const { isAuthenticated, user, isLoading, checkAuth } = useAuthStore()
  const [isInitializing, setIsInitializing] = useState(true)

  // 只在首次挂载时检查一次认证状态
  // 等待 Zustand persist 中间件恢复状态
  useEffect(() => {
    const initialize = async () => {
      // Zustand persist 需要时间从 localStorage 恢复
      // 等待一个微任务周期确保状态已恢复
      await Promise.resolve()

      if (!isAuthenticated && !isLoading) {
        await checkAuth()
      }

      setIsInitializing(false)
    }

    initialize()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    // 在初始化完成之前,不进行任何路由跳转
    if (isInitializing || isLoading) {
      return
    }

    // 未登录，重定向到登录页
    if (!isAuthenticated) {
      router.push('/login')
      return
    }

    // 检查权限
    if (user) {
      // 要求超级管理员
      if (requireSuperAdmin && user.role !== 'super_admin') {
        alert('需要超级管理员权限')
        router.push('/')
        return
      }

      // 要求管理员
      if (requireAdmin && user.role !== 'super_admin' && user.role !== 'admin') {
        alert('您没有访问管理后台的权限')
        useAuthStore.getState().logout()
        router.push('/login')
        return
      }
    }
  }, [isAuthenticated, user, isLoading, isInitializing, router, requireAdmin, requireSuperAdmin])

  // 初始化中或加载中 - 显示加载状态
  if (isInitializing || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-primary" />
          <p className="text-sm text-gray-600 dark:text-gray-400">加载中...</p>
        </div>
      </div>
    )
  }

  // 未认证或无权限 - 不显示内容(等待路由跳转)
  if (!isAuthenticated || !user) {
    return null
  }

  if (requireSuperAdmin && user.role !== 'super_admin') {
    return null
  }

  if (requireAdmin && user.role !== 'super_admin' && user.role !== 'admin') {
    return null
  }

  return <>{children}</>
}
