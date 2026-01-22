"use client"

import * as React from "react"
import { Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"

import { Button } from "@/components/ui/button"

/**
 * 主题切换按钮组件
 * 提供深色/浅色主题切换功能，图标会根据当前主题动态变化
 */
export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = React.useState(false)

  // 避免服务端渲染和客户端渲染不一致，等待组件挂载后再显示实际主题
  React.useEffect(() => {
    setMounted(true)
  }, [])

  // 组件未挂载时显示占位按钮，避免闪烁
  if (!mounted) {
    return (
      <Button variant="ghost" size="icon" className="w-9 h-9">
        <Sun className="h-4 w-4" />
      </Button>
    )
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      className="w-9 h-9"
    >
      {/* 深色模式显示太阳图标，浅色模式显示月亮图标 */}
      {theme === "dark" ? (
        <Sun className="h-4 w-4 text-yellow-400 transition-all" />
      ) : (
        <Moon className="h-4 w-4 transition-all" />
      )}
      <span className="sr-only">切换主题</span>
    </Button>
  )
}
