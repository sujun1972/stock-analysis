'use client'

import { ReactNode, useState, useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { Header } from '@/components/layout/Header'
import { useSidebarStore } from '@/stores/sidebar-store'
import { cn } from '@/lib/utils'
import { Breadcrumb } from '@/components/ui/breadcrumb'
import { useBreadcrumbs } from '@/hooks/useBreadcrumbs'
import { navItems } from './navigation-config'
import type { NavItem } from './navigation-config'
import { SidebarMenuItem } from './SidebarMenuItem'

interface AdminLayoutProps {
  children: ReactNode
}

export default function AdminLayout({ children }: AdminLayoutProps) {
  const pathname = usePathname()
  const router = useRouter()
  const { isCollapsed, setCollapsed } = useSidebarStore()
  const breadcrumbs = useBreadcrumbs()

  const getInitialOpenMenus = (): string[] => {
    const openMenus: string[] = []
    navItems.forEach(item => {
      if (item.children) {
        const hasActiveChild = item.children.some(
          child => child.href && (pathname === child.href || pathname.startsWith(child.href + '/'))
        )
        if (hasActiveChild) {
          openMenus.push(item.name)
        }
      }
    })
    return openMenus
  }

  const [openMenus, setOpenMenus] = useState<string[]>(() => getInitialOpenMenus())

  useEffect(() => {
    const criticalPages = ['/strategies', '/settings/sync-config', '/users']
    const timer = setTimeout(() => {
      criticalPages.forEach(page => router.prefetch(page))
    }, 1000)
    return () => clearTimeout(timer)
  }, [router])

  // 路径变化时自动展开对应菜单
  useEffect(() => {
    const activeMenus = getInitialOpenMenus()
    setOpenMenus(activeMenus)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname])

  // 精确路径匹配，避免 /data/margin 匹配到 /data/margin-detail
  const isActive = (item: NavItem) => {
    if (item.children) {
      // parent 自身 href 精确匹配（如 /boardgame 页面本身）
      if (item.href && pathname === item.href) {
        return true
      }
      // 检查子菜单是否有激活项
      return item.children.some(child => {
        if (!child.href) return false
        if (child.href === '/') return pathname === '/'
        return pathname === child.href || pathname.startsWith(child.href + '/')
      })
    }
    if (item.href) {
      if (item.href === '/') {
        return pathname === '/'
      }
      return pathname === item.href || pathname.startsWith(item.href + '/')
    }
    return false
  }

  const toggleMenu = (menuName: string) => {
    setOpenMenus(prev =>
      prev.includes(menuName)
        ? prev.filter(name => name !== menuName)
        : [...prev, menuName]
    )
  }

  const handleMenuClick = () => {
    if (window.innerWidth < 768) {
      setCollapsed(true)
    }
  }

  return (
    <div className="flex h-screen bg-gray-100 dark:bg-gray-900 overflow-hidden">
      {/* 侧边栏 - 大屏幕折叠，小屏幕滑出 */}
      <aside
        className={cn(
          "bg-gray-900 text-white flex flex-col transition-all duration-300",
          // 大屏幕 (md+): 相对定位，收起时显示图标，展开时显示全部
          "md:relative md:flex",
          isCollapsed ? "md:w-20 md:overflow-visible" : "md:w-64",
          // 小屏幕: 固定定位，从左侧滑入/滑出
          "fixed left-0 top-0 h-full z-40 w-64",
          isCollapsed ? "md:translate-x-0 -translate-x-full" : "translate-x-0"
        )}
      >
        {/* Logo */}
        <div className={cn(
          "p-6 border-b border-gray-800 transition-all",
          isCollapsed && "md:p-4"
        )}>
          {/* 大屏幕收起时显示简化 Logo，小屏幕始终显示完整 Logo */}
          <div className={cn(
            isCollapsed && "hidden md:flex items-center justify-center"
          )}>
            {isCollapsed && (
              <div className="w-10 h-10 rounded-lg bg-gradient-to-r from-blue-400 to-purple-500 flex items-center justify-center">
                <span className="text-white font-bold text-lg">SA</span>
              </div>
            )}
          </div>

          <div className={cn(
            isCollapsed && "md:hidden"
          )}>
            <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              管理后台
            </h1>
            <p className="text-xs text-gray-400 mt-1">Stock Analysis Admin</p>
          </div>
        </div>

        {/* 导航菜单 */}
        <nav className={cn(
          "flex-1 p-4 space-y-1 overflow-y-auto scrollbar-hide",
          isCollapsed && "md:p-2 md:overflow-visible"
        )}>
          {navItems.map((item) => (
            <SidebarMenuItem
              key={item.name}
              item={item}
              pathname={pathname}
              isCollapsed={isCollapsed}
              isOpen={openMenus.includes(item.name)}
              isActive={isActive(item)}
              onToggleMenu={toggleMenu}
              onMenuClick={handleMenuClick}
            />
          ))}
        </nav>

        {/* 底部信息 */}
        {!isCollapsed && (
          <div className="p-4 border-t border-gray-800">
            <div className="text-xs text-gray-400 space-y-1">
              <p>版本: v1.0.0</p>
              <p>© 2026 Stock Analysis</p>
            </div>
          </div>
        )}
      </aside>

      {/* 遮罩层 - 仅小屏幕且侧边栏展开时显示 */}
      {!isCollapsed && (
        <div
          className="md:hidden fixed inset-0 bg-black/50 z-30"
          onClick={() => useSidebarStore.getState().setCollapsed(true)}
        />
      )}

      {/* 主内容区 */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* 顶部 Header */}
        <Header />

        {/* 面包屑导航 - 在Header下方，内容区上方 */}
        {breadcrumbs.length > 0 && (
          <div className="px-8 py-3 border-b bg-white dark:bg-gray-900">
            <Breadcrumb items={breadcrumbs} />
          </div>
        )}

        {/* 页面内容 */}
        <div className="flex-1 overflow-auto p-8">
          {children}
        </div>
      </main>
    </div>
  )
}
