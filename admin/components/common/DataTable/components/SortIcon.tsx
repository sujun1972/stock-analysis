/**
 * @file components/common/DataTable/components/SortIcon.tsx
 * @description 排序图标组件
 * @created 2026-03-20
 */

'use client'

import { ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'

interface SortIconProps {
  sorted: boolean
  direction: 'asc' | 'desc' | null
}

export function SortIcon({ sorted, direction }: SortIconProps) {
  if (!sorted || !direction) {
    return <ArrowUpDown className="ml-2 h-4 w-4" />
  }
  return direction === 'asc'
    ? <ArrowUp className="ml-2 h-4 w-4" />
    : <ArrowDown className="ml-2 h-4 w-4" />
}
