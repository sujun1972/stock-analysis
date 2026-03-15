"use client"

import * as React from "react"
import { usePathname, useRouter } from "next/navigation"
import Link from "next/link"
import { Menu, User, LogOut, Crown, Bell, Settings } from "lucide-react"
import { useAuthStore, getRoleDisplayName } from "@/stores/auth-store"
import { NotificationBadge } from "@/components/notifications/NotificationBadge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"
import { cn } from "@/lib/utils"

/**
 * 移动端导航菜单组件
 * 使用汉堡图标触发侧边抽屉菜单,适配小屏幕设备
 */
export function MobileNav() {
  const [open, setOpen] = React.useState(false)
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
    setOpen(false)
    router.push('/login')
  }

  const getUserInitials = (username: string) => {
    return username.slice(0, 2).toUpperCase()
  }

  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon" className="md:hidden">
          <Menu className="h-5 w-5" />
          <span className="sr-only">打开菜单</span>
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-[280px] sm:w-[320px]">
        <SheetHeader>
          <SheetTitle>导航菜单</SheetTitle>
        </SheetHeader>

        {/* 用户信息区域 */}
        {isAuthenticated && user ? (
          <div className="mt-6 mb-4">
            <div className="flex items-center gap-3 px-4 py-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
              <Avatar className="h-10 w-10">
                <AvatarImage src={user.avatar_url || undefined} />
                <AvatarFallback>{getUserInitials(user.username)}</AvatarFallback>
              </Avatar>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{user.username}</p>
                <p className="text-xs text-muted-foreground">{getRoleDisplayName(user.role)}</p>
              </div>
              {(['vip_user', 'admin', 'super_admin'].includes(user.role)) && (
                <Crown className="h-4 w-4 text-purple-600 flex-shrink-0" />
              )}
            </div>
          </div>
        ) : (
          <div className="mt-6 mb-4 flex flex-col gap-2">
            <Button onClick={() => { setOpen(false); router.push('/login') }} className="w-full">
              登录
            </Button>
            <Button variant="outline" onClick={() => { setOpen(false); router.push('/register') }} className="w-full">
              注册
            </Button>
          </div>
        )}

        <Separator className="my-4" />

        {/* 导航菜单 */}
        <nav className="flex flex-col gap-2">
          {menuItems.map((item) => {
            // 如果需要登录但未登录，则不显示该菜单
            if (item.requireAuth && !isAuthenticated) {
              return null
            }
            return (
              <Link
                key={item.href}
                href={item.href}
                onClick={() => setOpen(false)}
                className={cn(
                  "flex items-center px-4 py-3 text-base font-medium rounded-lg transition-colors",
                  isActive(item.href)
                    ? "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
                    : "text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800"
                )}
              >
                {item.label}
              </Link>
            )
          })}
        </nav>

        {/* 登录后的额外选项 */}
        {isAuthenticated && user && (
          <>
            <Separator className="my-4" />
            <div className="flex flex-col gap-2">
              <Button
                variant="ghost"
                className="w-full justify-start relative"
                onClick={() => { setOpen(false); router.push('/notifications') }}
              >
                <Bell className="mr-2 h-4 w-4" />
                通知中心
                <NotificationBadge className="ml-2" enablePolling={true} />
              </Button>
              <Button
                variant="ghost"
                className="w-full justify-start"
                onClick={() => { setOpen(false); router.push('/settings/notifications') }}
              >
                <Settings className="mr-2 h-4 w-4" />
                通知设置
              </Button>
              <Button
                variant="ghost"
                className="w-full justify-start"
                onClick={() => { setOpen(false); router.push('/profile') }}
              >
                <User className="mr-2 h-4 w-4" />
                个人中心
              </Button>
              <Button
                variant="ghost"
                className="w-full justify-start text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
                onClick={handleLogout}
              >
                <LogOut className="mr-2 h-4 w-4" />
                退出登录
              </Button>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}
