/**
 * PageHeader 组件 - 统一的页面头部组件
 *
 * @description
 * 为所有管理后台页面提供统一的头部布局，确保视觉一致性和良好的用户体验。
 *
 * @features
 * - 响应式设计：自动适配桌面和移动端布局
 * - 灵活配置：支持标题、描述、操作按钮、返回按钮、面包屑等多种元素
 * - 可扩展性：通过 props 支持自定义内容和样式
 * - 无障碍支持：包含适当的 ARIA 标签
 *
 * @example
 * ```tsx
 * <PageHeader
 *   title="用户管理"
 *   description="管理系统用户账户"
 *   actions={<Button>新建用户</Button>}
 * />
 * ```
 */

import React, { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { ArrowLeft, Info } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'

interface PageHeaderProps {
  /**
   * 页面主标题
   */
  title: string

  /**
   * 页面副标题/描述 - 支持字符串或 React 节点
   */
  description?: string | ReactNode

  /**
   * 右侧操作按钮区域
   */
  actions?: ReactNode

  /**
   * 是否显示返回按钮
   */
  showBack?: boolean

  /**
   * 自定义返回按钮点击事件
   */
  onBack?: () => void

  /**
   * 额外的 CSS 类名
   */
  className?: string

  /**
   * 是否紧凑模式（用于嵌套页面或对话框）
   */
  compact?: boolean

  /**
   * 左侧额外内容（如状态标签、图标等）
   */
  prefix?: ReactNode

  /**
   * 底部额外内容（如标签页、筛选器等）
   */
  footer?: ReactNode

  /**
   * 详细信息内容（ReactNode），点击标题旁的 ⓘ 图标以 Popover 形式展示
   * 适合放接口名称、文档链接等补充信息
   */
  details?: ReactNode
}

export function PageHeader({
  title,
  description,
  actions,
  showBack = false,
  onBack,
  className,
  compact = false,
  prefix,
  footer,
  details
}: PageHeaderProps) {
  const router = useRouter()

  const handleBack = () => {
    if (onBack) {
      onBack()
    } else {
      router.back()
    }
  }

  return (
    <div className={cn('space-y-4', className)}>

      {/* 主要头部区域 */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-start gap-3">
          {/* 返回按钮 */}
          {showBack && (
            <Button
              variant="ghost"
              size="icon"
              onClick={handleBack}
              className="mt-0.5"
              aria-label="返回"
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
          )}

          {/* 标题区域 */}
          <div className="space-y-1 flex-1">
            <div className="flex items-center gap-2">
              {prefix}
              <h1
                className={cn(
                  'font-bold tracking-tight',
                  compact ? 'text-xl sm:text-2xl' : 'text-2xl sm:text-3xl'
                )}
              >
                {title}
              </h1>
              {details && (
                <Popover>
                  <PopoverTrigger asChild>
                    <button
                      type="button"
                      className="text-muted-foreground/40 hover:text-muted-foreground transition-colors mt-1"
                      aria-label="查看详情"
                    >
                      <Info className="h-4 w-4" />
                    </button>
                  </PopoverTrigger>
                  <PopoverContent
                    side="bottom"
                    align="start"
                    className="w-auto max-w-xs text-sm [&_a]:text-blue-500 [&_a]:underline [&_a:hover]:text-blue-600 space-y-1"
                  >
                    {details}
                  </PopoverContent>
                </Popover>
              )}
            </div>
            {description && (
              <p
                className={cn(
                  'text-muted-foreground',
                  compact ? 'text-sm' : 'text-sm sm:text-base'
                )}
              >
                {description}
              </p>
            )}
          </div>
        </div>

        {/* 操作按钮区域 */}
        {actions && (
          <div className="flex items-center gap-2 flex-wrap sm:flex-nowrap">
            {actions}
          </div>
        )}
      </div>

      {/* 底部内容（如标签页等） */}
      {footer && (
        <div className="border-t pt-4">
          {footer}
        </div>
      )}
    </div>
  )
}

/**
 * PageHeaderSkeleton - 页面头部骨架屏
 * 用于加载状态展示
 */
export function PageHeaderSkeleton({
  showBack = false,
  showActions = true
}: {
  showBack?: boolean
  showActions?: boolean
}) {
  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-start gap-3">
          {showBack && (
            <div className="w-10 h-10 bg-muted rounded animate-pulse" />
          )}
          <div className="space-y-2 flex-1">
            <div className="h-8 w-48 bg-muted rounded animate-pulse" />
            <div className="h-4 w-72 bg-muted rounded animate-pulse" />
          </div>
        </div>
        {showActions && (
          <div className="flex items-center gap-2">
            <div className="h-10 w-24 bg-muted rounded animate-pulse" />
            <div className="h-10 w-24 bg-muted rounded animate-pulse" />
          </div>
        )}
      </div>
    </div>
  )
}