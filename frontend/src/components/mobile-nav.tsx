"use client"

import * as React from "react"
import { usePathname } from "next/navigation"
import Link from "next/link"
import { Menu } from "lucide-react"
import { Button } from "@/components/ui/button"
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
        <nav className="flex flex-col gap-2 mt-6">
          {menuItems.map((item) => (
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
          ))}
        </nav>
      </SheetContent>
    </Sheet>
  )
}
