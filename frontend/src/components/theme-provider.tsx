"use client"

import * as React from "react"
import { ThemeProvider as NextThemesProvider } from "next-themes"

/**
 * 主题提供者组件
 * 封装 next-themes 的 ThemeProvider，为整个应用提供主题管理功能
 * 支持深色/浅色主题切换，并可跟随系统主题设置
 */
export function ThemeProvider({
  children,
  ...props
}: React.ComponentProps<typeof NextThemesProvider>) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>
}
