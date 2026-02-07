"use client"

import { usePathname } from "next/navigation"
import Link from "next/link"
import { cn } from "@/lib/utils"

/**
 * 桌面端导航菜单组件
 * 支持当前页面高亮显示
 */
export function DesktopNav() {
  const pathname = usePathname()

  const menuItems = [
    { href: "/", label: "首页" },
    { href: "/strategies", label: "策略中心" },
    { href: "/backtest/three-layer", label: "三层回测" },
    { href: "/backtest", label: "传统回测" },
    { href: "/my-backtests", label: "我的回测" },
    { href: "/ai-lab", label: "AI实验舱" },
    { href: "/sync", label: "数据同步" },
    { href: "/stocks", label: "股票列表" },
    { href: "/settings", label: "系统设置" },
  ]

  const isActive = (href: string) => {
    if (href === "/") {
      return pathname === "/"
    }
    return pathname.startsWith(href)
  }

  return (
    <nav className="bg-white dark:bg-gray-800 shadow hidden md:block">
      <div className="container-custom">
        <div className="flex space-x-8 py-4">
          {menuItems.map((item) => (
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
          ))}
        </div>
      </div>
    </nav>
  )
}
