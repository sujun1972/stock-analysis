"use client"

import { usePathname, useRouter } from "next/navigation"
import Link from "next/link"
import { useAuthStore, getRoleDisplayName } from "@/stores/auth-store"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { User, LogOut, Settings, Crown } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

/**
 * 桌面端导航菜单组件
 * 支持当前页面高亮显示和用户登录状态
 */
export function DesktopNav() {
  const pathname = usePathname()
  const router = useRouter()
  const { isAuthenticated, user, logout } = useAuthStore()

  const menuItems = [
    { href: "/", label: "首页" },
    { href: "/strategies", label: "策略中心" },
    { href: "/my-strategies", label: "我的策略", requireAuth: true },
    { href: "/my-backtests", label: "我的回测", requireAuth: true },
    { href: "/ai-lab", label: "AI实验舱" },
    { href: "/stocks", label: "股票列表" },
  ]

  const isActive = (href: string) => {
    if (href === "/") {
      return pathname === "/"
    }
    return pathname.startsWith(href)
  }

  const handleLogout = async () => {
    await logout()
    router.push('/login')
  }

  const getUserInitials = (username: string) => {
    return username.slice(0, 2).toUpperCase()
  }

  return (
    <nav className="bg-white dark:bg-gray-800 shadow hidden md:block">
      <div className="container-custom">
        <div className="flex items-center justify-between py-4">
          <div className="flex space-x-8">
            {menuItems.map((item) => {
              // 如果需要登录但未登录，则不显示该菜单
              if (item.requireAuth && !isAuthenticated) {
                return null
              }
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "transition-colors font-medium",
                    isActive(item.href)
                      ? "text-blue-600 dark:text-blue-400"
                      : "text-gray-700 dark:text-gray-300 hover:text-blue-600 dark:hover:text-blue-400"
                  )}
                >
                  {item.label}
                </Link>
              )
            })}
          </div>

          {/* 用户状态区域 */}
          <div className="flex items-center gap-3">
            {isAuthenticated && user ? (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" className="flex items-center gap-2 px-3">
                    <Avatar className="h-8 w-8">
                      <AvatarImage src={user.avatar_url || undefined} />
                      <AvatarFallback>{getUserInitials(user.username)}</AvatarFallback>
                    </Avatar>
                    <div className="flex flex-col items-start">
                      <span className="text-sm font-medium">{user.username}</span>
                      <span className="text-xs text-muted-foreground">{getRoleDisplayName(user.role)}</span>
                    </div>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-56">
                  <DropdownMenuLabel>
                    <div className="flex flex-col space-y-1">
                      <p className="text-sm font-medium">{user.username}</p>
                      <p className="text-xs text-muted-foreground">{user.email}</p>
                    </div>
                  </DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={() => router.push('/profile')}>
                    <User className="mr-2 h-4 w-4" />
                    个人中心
                  </DropdownMenuItem>
                  {(['vip_user', 'admin', 'super_admin'].includes(user.role)) && (
                    <DropdownMenuItem>
                      <Crown className="mr-2 h-4 w-4 text-purple-600" />
                      VIP权益
                    </DropdownMenuItem>
                  )}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleLogout}>
                    <LogOut className="mr-2 h-4 w-4" />
                    退出登录
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            ) : (
              <div className="flex gap-2">
                <Button variant="ghost" onClick={() => router.push('/login')}>
                  登录
                </Button>
                <Button onClick={() => router.push('/register')}>
                  注册
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  )
}
