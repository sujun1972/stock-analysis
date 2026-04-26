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
    <div className="min-h-screen flex flex-col bg-background">
      <AIGenerationTaskMonitor />
      {/* Header：金融终端工具栏式（去 bg-blue-600 大色块），数据让位为视觉焦点。
          仅一根 border-b 分隔，无 shadow——Bloomberg/Refinitiv 同款克制风格 */}
      <header className="bg-card border-b border-border">
        <div className="container-custom py-3.5">
          <div className="flex items-center justify-between gap-4">
            <MobileNav />
            <div className="flex-1 flex items-baseline gap-3 min-w-0">
              {/* 左侧 2px 主色短条作为微品牌锚点（替代品牌色块） */}
              <span aria-hidden className="hidden sm:block h-5 w-[3px] rounded-sm bg-primary shrink-0" />
              <div className="min-w-0">
                <h1 className="text-base sm:text-lg font-semibold text-foreground leading-tight truncate">A股AI量化交易系统</h1>
                <p className="text-muted-foreground text-[11px] sm:text-xs hidden sm:block leading-tight mt-0.5">Stock Analysis Platform</p>
              </div>
            </div>
            <div className="hidden md:block">
              <StockSearch />
            </div>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <DesktopNav />

      <main className="flex-1">
        <div className="container-custom py-8">{children}</div>
      </main>

      {/* Footer：低调灰条（不再用 #1F2937 高对比深色块抢视觉） */}
      <footer className="bg-card border-t border-border py-5">
        <div className="container-custom text-center">
          <p className="text-xs text-muted-foreground">A股AI量化交易系统 &copy; 2026</p>
          <p className="text-[11px] text-muted-foreground/70 mt-1.5">仅供学习和研究使用，不构成任何投资建议</p>
        </div>
      </footer>

      <Toaster position="top-right" richColors closeButton theme="system" />
    </div>
  )
}
