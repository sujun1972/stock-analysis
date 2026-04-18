'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ChevronRight, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { NavItem } from './navigation-config'

interface SidebarMenuItemProps {
  item: NavItem
  pathname: string
  isCollapsed: boolean
  isOpen: boolean
  isActive: boolean
  onToggleMenu: (menuName: string) => void
  onMenuClick: () => void
}

export function SidebarMenuItem({
  item,
  pathname,
  isCollapsed,
  isOpen,
  isActive: active,
  onToggleMenu,
  onMenuClick,
}: SidebarMenuItemProps) {
  const router = useRouter()
  const Icon = item.icon

  // 有子菜单的项
  if (item.children) {
    return (
      <div className="relative menu-item-with-submenu">
        {/* 父菜单项 */}
        <div
          className={cn(
            "w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-all",
            active
              ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/50'
              : 'text-gray-300 hover:bg-gray-800 hover:text-white',
            isCollapsed && "md:px-2 md:justify-center"
          )}
          title={isCollapsed ? item.name : undefined}
        >
          {/* 图标+名称区域：有 href 则跳转，否则展开菜单 */}
          {item.href && !isCollapsed ? (
            <Link
              href={item.href}
              onClick={onMenuClick}
              className="flex items-center gap-3 flex-1 min-w-0"
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              <span className="font-medium flex-1 text-left truncate">{item.name}</span>
            </Link>
          ) : (
            <button
              onClick={() => item.href ? router.push(item.href) : onToggleMenu(item.name)}
              className="flex items-center gap-3 flex-1 min-w-0 text-left"
            >
              <Icon className={cn(
                "w-5 h-5 flex-shrink-0",
                isCollapsed && "md:w-6 md:h-6"
              )} />
              <span className={cn(
                "font-medium flex-1 text-left",
                isCollapsed && "md:hidden"
              )}>
                {item.name}
              </span>
            </button>
          )}
          {/* 展开/收起箭头 - 仅展开状态显示，独立点击区域 */}
          {!isCollapsed && (
            <button
              onClick={(e) => { e.stopPropagation(); onToggleMenu(item.name) }}
              className="p-1 rounded hover:bg-white/10 flex-shrink-0"
            >
              <ChevronDown className={cn(
                "w-4 h-4 transition-transform",
                isOpen && "rotate-180"
              )} />
            </button>
          )}
        </div>

        {/* 收起时的悬浮子菜单 - 仅大屏幕 */}
        {isCollapsed && item.children && (
          <div className="submenu-dropdown absolute left-full top-0 ml-2 bg-gray-800 rounded-lg z-[100] min-w-[200px] py-1 shadow-xl border border-gray-700 opacity-0 invisible transition-all duration-200">
            <div className={cn(
              "px-3 py-2 text-xs font-semibold border-b border-gray-700 flex items-center gap-2",
              active ? "text-blue-400" : "text-gray-400"
            )}>
              <Icon className="w-3 h-3" />
              {item.name}
            </div>
            <div className="py-1">
              {item.children.map((child) => {
                const ChildIcon = child.icon
                const childActive = child.href && (pathname === child.href || pathname.startsWith(child.href + '/'))
                return (
                  <Link
                    key={child.href}
                    href={child.href!}
                    onClick={onMenuClick}
                    className={cn(
                      "flex items-center gap-3 px-4 py-2.5 text-sm transition-colors",
                      childActive
                        ? 'bg-blue-600 text-white'
                        : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                    )}
                  >
                    <ChildIcon className="w-4 h-4" />
                    <span>{child.name}</span>
                  </Link>
                )
              })}
            </div>
          </div>
        )}

        {/* 子菜单项 - 仅展开状态显示 */}
        {!isCollapsed && isOpen && (
          <div className="mt-1 ml-4 space-y-1">
            {item.children.map((child) => {
              const ChildIcon = child.icon
              const childActive = child.href && (pathname === child.href || pathname.startsWith(child.href + '/'))
              return (
                <Link
                  key={child.href}
                  href={child.href!}
                  onClick={onMenuClick}
                  className={cn(
                    "flex items-center gap-3 px-4 py-2 rounded-lg transition-all text-sm",
                    childActive
                      ? 'text-blue-400 hover:bg-gray-800'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                  )}
                >
                  <ChildIcon className="w-4 h-4" />
                  <span className="font-medium">{child.name}</span>
                </Link>
              )
            })}
          </div>
        )}

        {/* 小屏幕展开显示子菜单 */}
        {isCollapsed && isOpen && (
          <div className="md:hidden mt-1 ml-4 space-y-1">
            {item.children.map((child) => {
              const ChildIcon = child.icon
              const childActive = child.href && (pathname === child.href || pathname.startsWith(child.href + '/'))
              return (
                <Link
                  key={child.href}
                  href={child.href!}
                  onClick={onMenuClick}
                  className={cn(
                    "flex items-center gap-3 px-4 py-2 rounded-lg transition-all text-sm",
                    childActive
                      ? 'text-blue-400 hover:bg-gray-800'
                      : 'text-gray-400 hover:bg-gray-800 hover:text-white'
                  )}
                >
                  <ChildIcon className="w-4 h-4" />
                  <span className="font-medium">{child.name}</span>
                </Link>
              )
            })}
          </div>
        )}
      </div>
    )
  }

  // 普通菜单项（无子菜单）
  return (
    <Link
      href={item.href!}
      onClick={onMenuClick}
      className={cn(
        "flex items-center gap-3 px-4 py-3 rounded-lg transition-all group relative",
        active
          ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/50'
          : 'text-gray-300 hover:bg-gray-800 hover:text-white',
        isCollapsed && "md:px-2 md:justify-center"
      )}
      title={isCollapsed ? item.name : undefined}
    >
      <Icon className={cn("w-5 h-5", isCollapsed && "md:w-6 md:h-6")} />
      <span className={cn(
        "font-medium",
        isCollapsed && "md:hidden"
      )}>
        {item.name}
      </span>
      {active && !isCollapsed && <ChevronRight className="w-4 h-4 ml-auto" />}

      {/* 收起时的悬浮提示 - 仅大屏幕 */}
      {isCollapsed && (
        <div className="hidden md:block absolute left-full ml-2 px-3 py-2 bg-gray-800 text-white text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
          {item.name}
        </div>
      )}
    </Link>
  )
}
