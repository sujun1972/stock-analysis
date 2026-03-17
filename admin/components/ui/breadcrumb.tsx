/**
 * 面包屑导航组件
 *
 * @description
 * 提供统一的面包屑导航组件，支持自动生成和手动配置
 * 在 AdminLayout 中全局使用，自动根据路由生成导航路径
 *
 * @features
 * - 响应式设计：移动端自动折叠中间项
 * - 支持图标显示
 * - 支持下拉菜单展示折叠项
 * - 自动添加首页链接
 * - 当前页面项不可点击
 *
 * @example
 * ```tsx
 * <Breadcrumb
 *   items={[
 *     { label: '系统设置', href: '/settings', icon: Settings },
 *     { label: '数据源配置' }
 *   ]}
 * />
 * ```
 */

import * as React from "react"
import Link from "next/link"
import { ChevronRight, Home, MoreHorizontal } from "lucide-react"
import { cn } from "@/lib/utils"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Button } from "@/components/ui/button"

export interface BreadcrumbItem {
  label: string
  href?: string
  icon?: React.ComponentType<{ className?: string }>
}

interface BreadcrumbProps {
  items: BreadcrumbItem[]
  className?: string
  maxItems?: number // 最大显示项数（移动端）
  showHome?: boolean // 是否显示首页
}

export function Breadcrumb({
  items,
  className,
  maxItems = 3,
  showHome = true,
}: BreadcrumbProps) {
  // 添加首页到面包屑
  const allItems = React.useMemo(() => {
    const homeItem: BreadcrumbItem = {
      label: "首页",
      href: "/",
      icon: Home,
    }
    return showHome ? [homeItem, ...items] : items
  }, [items, showHome])

  // 计算需要折叠的项
  const { visibleItems, collapsedItems } = React.useMemo(() => {
    if (allItems.length <= maxItems) {
      return { visibleItems: allItems, collapsedItems: [] }
    }

    // 保留第一项和最后两项
    const firstItem = allItems[0]
    const lastItems = allItems.slice(-2)
    const middleItems = allItems.slice(1, -2)

    return {
      visibleItems: [firstItem, ...lastItems],
      collapsedItems: middleItems,
    }
  }, [allItems, maxItems])

  return (
    <nav
      aria-label="面包屑导航"
      className={cn("flex items-center space-x-1 text-sm", className)}
    >
      {visibleItems.map((item, index) => {
        const Icon = item.icon
        const isLast = index === visibleItems.length - 1
        const isFirst = index === 0
        const showCollapsedMenu = isFirst && collapsedItems.length > 0

        return (
          <React.Fragment key={`${item.label}-${index}`}>
            {/* 分隔符 */}
            {index > 0 && (
              <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/50 flex-shrink-0" />
            )}

            {/* 面包屑项 */}
            <div className="flex items-center">
              {isLast ? (
                // 当前页面（不可点击）
                <span
                  className={cn(
                    "font-medium text-foreground flex items-center gap-1.5",
                    "max-w-[200px] truncate"
                  )}
                  aria-current="page"
                >
                  {Icon && <Icon className="h-4 w-4" />}
                  {item.label}
                </span>
              ) : item.href ? (
                // 可点击的链接
                <Link
                  href={item.href}
                  className={cn(
                    "text-muted-foreground hover:text-foreground transition-colors",
                    "flex items-center gap-1.5 max-w-[200px] truncate",
                    "hover:underline underline-offset-4"
                  )}
                >
                  {Icon && <Icon className="h-4 w-4" />}
                  {item.label}
                </Link>
              ) : (
                // 不可点击的文本
                <span
                  className={cn(
                    "text-muted-foreground flex items-center gap-1.5",
                    "max-w-[200px] truncate"
                  )}
                >
                  {Icon && <Icon className="h-4 w-4" />}
                  {item.label}
                </span>
              )}

              {/* 折叠菜单 */}
              {showCollapsedMenu && (
                <>
                  <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/50 mx-1 flex-shrink-0" />
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-auto p-1 hover:bg-muted"
                        aria-label="显示更多面包屑"
                      >
                        <MoreHorizontal className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="start">
                      {collapsedItems.map((collapsedItem) => {
                        const CollapsedIcon = collapsedItem.icon
                        return (
                          <DropdownMenuItem key={collapsedItem.label} asChild>
                            {collapsedItem.href ? (
                              <Link
                                href={collapsedItem.href}
                                className="flex items-center gap-2"
                              >
                                {CollapsedIcon && (
                                  <CollapsedIcon className="h-4 w-4" />
                                )}
                                {collapsedItem.label}
                              </Link>
                            ) : (
                              <span className="flex items-center gap-2">
                                {CollapsedIcon && (
                                  <CollapsedIcon className="h-4 w-4" />
                                )}
                                {collapsedItem.label}
                              </span>
                            )}
                          </DropdownMenuItem>
                        )
                      })}
                    </DropdownMenuContent>
                  </DropdownMenu>
                </>
              )}
            </div>
          </React.Fragment>
        )
      })}
    </nav>
  )
}

/**
 * 面包屑骨架屏
 */
export function BreadcrumbSkeleton() {
  return (
    <div className="flex items-center space-x-1">
      <div className="h-4 w-12 bg-muted rounded animate-pulse" />
      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/50" />
      <div className="h-4 w-20 bg-muted rounded animate-pulse" />
      <ChevronRight className="h-3.5 w-3.5 text-muted-foreground/50" />
      <div className="h-4 w-24 bg-muted rounded animate-pulse" />
    </div>
  )
}