'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore, type UserRole } from '@/stores/auth-store'

interface ProtectedRouteProps {
  children: React.ReactNode
  /**
   * 是否需要登录才能访问
   * @default true
   */
  requireAuth?: boolean
  /**
   * 允许访问的角色列表（如果提供，则只有这些角色可以访问）
   */
  allowedRoles?: UserRole[]
  /**
   * 未授权时的重定向路径
   * @default '/login'
   */
  redirectTo?: string
  /**
   * 未授权时显示的提示信息（可选）
   */
  unauthorizedMessage?: string
}

/**
 * 路由保护组件
 *
 * 用法示例：
 *
 * 1. 必须登录才能访问：
 * <ProtectedRoute>
 *   <ProfilePage />
 * </ProtectedRoute>
 *
 * 2. 可选登录（未登录也可访问，但会有不同体验）：
 * <ProtectedRoute requireAuth={false}>
 *   <StocksPage />
 * </ProtectedRoute>
 *
 * 3. 限制特定角色访问：
 * <ProtectedRoute allowedRoles={['vip_user', 'admin', 'super_admin']}>
 *   <PremiumFeature />
 * </ProtectedRoute>
 */
export function ProtectedRoute({
  children,
  requireAuth = true,
  allowedRoles,
  redirectTo = '/login',
  unauthorizedMessage,
}: ProtectedRouteProps) {
  const router = useRouter()
  const { isAuthenticated, user, isLoading, checkAuth } = useAuthStore()
  const [isInitializing, setIsInitializing] = useState(true)
  const [isAuthorized, setIsAuthorized] = useState(false)

  useEffect(() => {
    const initialize = async () => {
      // 等待 Zustand persist 中间件恢复状态
      await new Promise((resolve) => setTimeout(resolve, 50))

      // 如果没有认证状态且不在加载中，尝试检查认证
      if (!isAuthenticated && !isLoading) {
        await checkAuth()
      }

      setIsInitializing(false)
    }

    initialize()
  }, [isAuthenticated, isLoading, checkAuth])

  useEffect(() => {
    // 等待初始化完成
    if (isInitializing || isLoading) {
      return
    }

    // 如果不需要登录，直接授权
    if (!requireAuth) {
      setIsAuthorized(true)
      return
    }

    // 需要登录但未登录
    if (!isAuthenticated) {
      // 保存当前路径用于登录后重定向
      const currentPath = window.location.pathname + window.location.search
      const redirectPath = currentPath !== redirectTo
        ? `${redirectTo}?redirect=${encodeURIComponent(currentPath)}`
        : redirectTo

      router.push(redirectPath)
      return
    }

    // 已登录，检查角色权限
    if (allowedRoles && user) {
      if (!allowedRoles.includes(user.role)) {
        // 角色不匹配
        if (unauthorizedMessage) {
          alert(unauthorizedMessage)
        } else {
          alert('您没有访问此页面的权限')
        }
        router.push('/')
        return
      }
    }

    // 授权通过
    setIsAuthorized(true)
  }, [
    isAuthenticated,
    user,
    isLoading,
    isInitializing,
    requireAuth,
    allowedRoles,
    redirectTo,
    unauthorizedMessage,
    router,
  ])

  // 加载中显示加载状态
  if (isInitializing || isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent align-[-0.125em] motion-reduce:animate-[spin_1.5s_linear_infinite]"></div>
          <p className="mt-4 text-muted-foreground">加载中...</p>
        </div>
      </div>
    )
  }

  // 如果不需要登录或已授权，显示内容
  if (!requireAuth || isAuthorized) {
    return <>{children}</>
  }

  // 其他情况（正在重定向）显示空白
  return null
}

/**
 * 高阶组件版本的路由保护
 *
 * 用法示例：
 * export default withAuth(ProfilePage, { requireAuth: true })
 */
export function withAuth<P extends object>(
  Component: React.ComponentType<P>,
  options?: Omit<ProtectedRouteProps, 'children'>
) {
  return function ProtectedComponent(props: P) {
    return (
      <ProtectedRoute {...options}>
        <Component {...props} />
      </ProtectedRoute>
    )
  }
}
