/**
 * 顶部导航栏组件
 *
 * 功能：
 * - 侧边栏切换按钮（大屏折叠，小屏滑入）
 * - 用户信息展示（头像、姓名、角色）
 * - 用户菜单（个人资料、修改密码、登出）
 *
 * @author Admin Team
 * @since 2026-03-03
 */

'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/stores/auth-store'
import { useSidebarStore } from '@/stores/sidebar-store'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { LogOut, User, Menu, KeyRound } from 'lucide-react'
import { ChangePasswordDialog } from '@/components/auth/ChangePasswordDialog'
import { TaskStatusIcon } from '@/components/TaskStatusIcon'
import { useTaskPolling } from '@/hooks/useTaskPolling'
import { useTaskSync } from '@/hooks/useTaskSync'

export function Header() {
  const router = useRouter()
  const { user, logout } = useAuthStore()
  const { toggleSidebar } = useSidebarStore()
  const [passwordDialogOpen, setPasswordDialogOpen] = useState(false)

  // 启用全局任务轮询（每5秒检查一次已有任务的状态）
  useTaskPolling(true, 5000)

  // 启用任务同步（每30秒从后端同步正在运行的任务）
  useTaskSync(true, 30000)

  const handleLogout = async () => {
    await logout()
    router.push('/login')
  }

  if (!user) {
    return null
  }

  // 获取用户名首字母
  const initials = user.full_name
    ? user.full_name.slice(0, 2).toUpperCase()
    : user.username.slice(0, 2).toUpperCase()

  // 角色徽章颜色
  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'super_admin':
        return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300'
      case 'admin':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300'
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300'
    }
  }

  const getRoleLabel = (role: string) => {
    switch (role) {
      case 'super_admin':
        return '超级管理员'
      case 'admin':
        return '管理员'
      default:
        return role
    }
  }

  return (
    <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-16 items-center justify-between px-4">
        <div className="flex items-center gap-4">
          {/* 菜单切换按钮 */}
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleSidebar}
            className="hover:bg-accent"
          >
            <Menu className="h-5 w-5" />
            <span className="sr-only">切换菜单</span>
          </Button>

          <h1 className="text-xl font-bold">管理后台</h1>
        </div>

        <div className="flex items-center gap-4">
          {/* 任务状态图标 */}
          <TaskStatusIcon />

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="relative h-10 gap-2">
                <Avatar className="h-8 w-8">
                  <AvatarImage src={user.avatar_url || '/assets/default-avatar.svg'} alt={user.username} />
                  <AvatarFallback>{initials}</AvatarFallback>
                </Avatar>
                <div className="flex flex-col items-start text-left">
                  <span className="text-sm font-medium">{user.full_name || user.username}</span>
                  <span className={`text-xs px-1.5 py-0.5 rounded ${getRoleBadgeColor(user.role)}`}>
                    {getRoleLabel(user.role)}
                  </span>
                </div>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="w-56" align="end" forceMount>
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">{user.full_name || user.username}</p>
                  <p className="text-xs leading-none text-muted-foreground">{user.email}</p>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={() => router.push('/profile')}>
                <User className="mr-2 h-4 w-4" />
                <span>个人资料</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => setPasswordDialogOpen(true)}>
                <KeyRound className="mr-2 h-4 w-4" />
                <span>修改密码</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout} className="text-red-600 dark:text-red-400">
                <LogOut className="mr-2 h-4 w-4" />
                <span>登出</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* 修改密码对话框 */}
      <ChangePasswordDialog open={passwordDialogOpen} onOpenChange={setPasswordDialogOpen} />
    </header>
  )
}
