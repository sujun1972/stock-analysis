'use client'

import React from 'react'
import { ChevronUp, ChevronDown } from 'lucide-react'

export type SortIndicatorOrder = 'asc' | 'desc'

interface SortIndicatorProps {
  order: SortIndicatorOrder
  className?: string
}

/**
 * 表头排序方向指示器。
 * 用 lucide 的 ChevronUp / ChevronDown，避免在业务文件里写裸 SVG。
 * 颜色跟随 `currentColor`，方便承父级（如激活态蓝色）；外层自行约束字号。
 */
export function SortIndicator({ order, className = 'h-3 w-3' }: SortIndicatorProps) {
  const Icon = order === 'desc' ? ChevronDown : ChevronUp
  return <Icon className={className} aria-hidden />
}
