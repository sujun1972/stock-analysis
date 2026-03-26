/**
 * @file components/common/DataTable/types.ts
 * @description DataTable 组件类型定义
 * @created 2026-03-20
 */

import { ReactNode } from 'react'

export interface Column<T> {
  key: string
  header: string | ReactNode
  accessor?: (item: T) => ReactNode
  render?: (value: any, item: T) => ReactNode  // 向后兼容旧 API
  sortable?: boolean
  className?: string
  headerClassName?: string
  cellClassName?: string
  width?: string | number
  minWidth?: string | number
  align?: 'left' | 'center' | 'right'
  sticky?: boolean
  hideOnMobile?: boolean
}

export interface PaginationConfig {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
  onPageSizeChange?: (pageSize: number) => void
  pageSizeOptions?: number[]
}

export interface SortConfig {
  key: string | null
  direction: 'asc' | 'desc' | null
  onSort: (key: string, direction: 'asc' | 'desc' | null) => void
}

export interface DataTableProps<T> {
  data: T[]
  columns: Column<T>[]
  loading?: boolean
  error?: string | null
  emptyMessage?: string | ReactNode
  loadingMessage?: string | ReactNode
  errorMessage?: string | ReactNode
  pagination?: PaginationConfig
  sort?: SortConfig
  className?: string
  tableClassName?: string
  rowKey?: (item: T, index: number) => string | number
  onRowClick?: (item: T, index: number) => void
  rowClassName?: (item: T, index: number) => string
  selectable?: boolean
  selectedRows?: Set<string | number>
  onSelectionChange?: (selectedRows: Set<string | number>) => void
  actions?: (item: T, index: number) => ReactNode
  mobileCard?: (item: T, index: number) => ReactNode
  headerActions?: ReactNode
  footerActions?: ReactNode
  // 向后兼容：扁平化的分页属性
  page?: number
  pageSize?: number
  total?: number
  onPageChange?: (page: number) => void
  onPageSizeChange?: (pageSize: number) => void
  pageSizeOptions?: number[]
}
