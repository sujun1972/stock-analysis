'use client'

import { usePathname } from 'next/navigation'
import { Toaster } from 'sonner'
import { ThemeToggle } from '@/components/theme-toggle'
import { MobileNav } from '@/components/mobile-nav'
import { DesktopNav } from '@/components/desktop-nav'
import { StockSearch } from '@/components/stock-search'
import { AIGenerationTaskMonitor } from '@/components/AIGenerationTaskMonitor'

// 认证路由跳过全站顶栏/导航/页脚，拥有独立的沉浸式布局（详见 components/auth/AuthLayout）
const AUTH_ROUTE_PREFIXES = ['/login', '/register', '/forgot-password', '/reset-password']

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const isAuthRoute =
    !!pathname && AUTH_ROUTE_PREFIXES.some((p) => pathname === p || pathname.startsWith(`${p}/`))

  if (isAuthRoute) {
    return (
      <>
        {children}
        <Toaster position="top-right" richColors closeButton theme="system" />
      </>
    )
  }

  return (
    <div className="min-h-screen flex flex-col">
      <AIGenerationTaskMonitor />
      <header className="bg-blue-600 text-white shadow-lg">
        <div className="container-custom py-4">
          <div className="flex items-center justify-between gap-4">
            <MobileNav />
            <div className="flex-1">
              <h1 className="text-xl sm:text-2xl font-bold">A股AI量化交易系统</h1>
              <p className="text-blue-100 text-xs sm:text-sm hidden sm:block">Stock Analysis Platform</p>
            </div>
            <div className="hidden md:block">
              <StockSearch />
            </div>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <DesktopNav />

      <main className="flex-1 bg-gray-50 dark:bg-gray-900">
        <div className="container-custom py-8">{children}</div>
      </main>

      <footer className="bg-gray-800 text-white py-6">
        <div className="container-custom text-center">
          <p className="text-sm">A股AI量化交易系统 &copy; 2026</p>
          <p className="text-xs text-gray-400 mt-2">仅供学习和研究使用，不构成任何投资建议</p>
        </div>
      </footer>

      <Toaster position="top-right" richColors closeButton theme="system" />
    </div>
  )
}
