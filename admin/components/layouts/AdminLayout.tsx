'use client'

import { ReactNode } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Settings,
  Database,
  FileText,
  Activity,
  LayoutDashboard,
  ChevronRight,
  Users,
  Tag
} from 'lucide-react'
import { Header } from '@/components/layout/Header'

interface AdminLayoutProps {
  children: ReactNode
}

const navItems = [
  {
    name: '控制台',
    href: '/',
    icon: LayoutDashboard
  },
  {
    name: '用户管理',
    href: '/users',
    icon: Users
  },
  {
    name: '概念管理',
    href: '/concepts',
    icon: Tag
  },
  {
    name: '系统设置',
    href: '/settings',
    icon: Settings
  },
  {
    name: '数据同步',
    href: '/sync',
    icon: Database
  },
  {
    name: '系统日志',
    href: '/logs',
    icon: FileText
  },
  {
    name: '性能监控',
    href: '/monitor',
    icon: Activity
  },
]

export default function AdminLayout({ children }: AdminLayoutProps) {
  const pathname = usePathname()

  const isActive = (href: string) => {
    if (href === '/') {
      return pathname === '/'
    }
    return pathname.startsWith(href)
  }

  return (
    <div className="flex h-screen bg-gray-100 dark:bg-gray-900">
      {/* 侧边栏 */}
      <aside className="w-64 bg-gray-900 text-white flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-gray-800">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            管理后台
          </h1>
          <p className="text-xs text-gray-400 mt-1">Stock Analysis Admin</p>
        </div>

        {/* 导航菜单 */}
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon
            const active = isActive(item.href)

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`
                  flex items-center gap-3 px-4 py-3 rounded-lg transition-all
                  ${active
                    ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/50'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                  }
                `}
              >
                <Icon className="w-5 h-5" />
                <span className="font-medium">{item.name}</span>
                {active && <ChevronRight className="w-4 h-4 ml-auto" />}
              </Link>
            )
          })}
        </nav>

        {/* 底部信息 */}
        <div className="p-4 border-t border-gray-800">
          <div className="text-xs text-gray-400 space-y-1">
            <p>版本: v1.0.0</p>
            <p>© 2026 Stock Analysis</p>
          </div>
        </div>
      </aside>

      {/* 主内容区 */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* 顶部 Header */}
        <Header />

        {/* 页面内容 */}
        <div className="flex-1 overflow-auto p-8">
          {children}
        </div>
      </main>
    </div>
  )
}
