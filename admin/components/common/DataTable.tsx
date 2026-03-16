/**
 * @file components/common/DataTable.tsx
 * @description 通用的数据表格组件，支持分页、排序、筛选、响应式布局
 * @author Claude
 * @created 2024-03-16
 * @updated 2024-03-16
 */

'use client'

import React, { ReactNode } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { TABLE_CONFIG } from '@/lib/constants'

// ============== 类型定义 ==============

export interface Column<T> {
  key: string
  header: string | ReactNode
  accessor?: (item: T) => ReactNode
  sortable?: boolean
  className?: string
  headerClassName?: string
  cellClassName?: string
  width?: string | number
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
}

// ============== 子组件 ==============

/**
 * 表格加载状态
 */
function TableLoading({
  columns,
  message = TABLE_CONFIG.DEFAULT_LOADING_MESSAGE
}: {
  columns: number
  message?: string
}) {
  return (
    <TableRow>
      <TableCell colSpan={columns} className="h-24 text-center">
        <div className="flex flex-col items-center justify-center gap-2">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          <span className="text-sm text-muted-foreground">{message}</span>
        </div>
      </TableCell>
    </TableRow>
  )
}

/**
 * 表格空状态
 */
function TableEmpty({
  columns,
  message = TABLE_CONFIG.DEFAULT_EMPTY_MESSAGE
}: {
  columns: number
  message?: string
}) {
  return (
    <TableRow>
      <TableCell colSpan={columns} className="h-24 text-center">
        <span className="text-sm text-muted-foreground">{message}</span>
      </TableCell>
    </TableRow>
  )
}

/**
 * 表格错误状态
 */
function TableError({
  columns,
  message = TABLE_CONFIG.DEFAULT_ERROR_MESSAGE,
  onRetry
}: {
  columns: number
  message?: string
  onRetry?: () => void
}) {
  return (
    <TableRow>
      <TableCell colSpan={columns} className="h-24 text-center">
        <div className="flex flex-col items-center justify-center gap-2">
          <span className="text-sm text-destructive">{message}</span>
          {onRetry && (
            <Button size="sm" variant="outline" onClick={onRetry}>
              重试
            </Button>
          )}
        </div>
      </TableCell>
    </TableRow>
  )
}

/**
 * 排序图标
 */
function SortIcon({
  sorted,
  direction
}: {
  sorted: boolean
  direction: 'asc' | 'desc' | null
}) {
  if (!sorted || !direction) {
    return <ArrowUpDown className="ml-2 h-4 w-4" />
  }
  return direction === 'asc'
    ? <ArrowUp className="ml-2 h-4 w-4" />
    : <ArrowDown className="ml-2 h-4 w-4" />
}

/**
 * 分页组件
 */
function Pagination({ config }: { config: PaginationConfig }) {
  const { page, pageSize, total, onPageChange, onPageSizeChange, pageSizeOptions = [10, 20, 50, 100] } = config
  const totalPages = Math.ceil(total / pageSize)
  const startIndex = (page - 1) * pageSize + 1
  const endIndex = Math.min(page * pageSize, total)

  return (
    <div className="flex items-center justify-between px-2 py-4">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span>
          显示 {startIndex} - {endIndex} / {total} 条
        </span>
        {onPageSizeChange && (
          <select
            value={pageSize}
            onChange={(e) => onPageSizeChange(Number(e.target.value))}
            className="h-8 rounded border bg-background px-2"
          >
            {pageSizeOptions.map((size) => (
              <option key={size} value={size}>
                {size} 条/页
              </option>
            ))}
          </select>
        )}
      </div>

      <div className="flex items-center gap-1">
        <Button
          variant="outline"
          size="icon"
          onClick={() => onPageChange(1)}
          disabled={page === 1}
        >
          <ChevronsLeft className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          onClick={() => onPageChange(page - 1)}
          disabled={page === 1}
        >
          <ChevronLeft className="h-4 w-4" />
        </Button>
        <span className="mx-2 text-sm">
          第 {page} / {totalPages} 页
        </span>
        <Button
          variant="outline"
          size="icon"
          onClick={() => onPageChange(page + 1)}
          disabled={page === totalPages}
        >
          <ChevronRight className="h-4 w-4" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          onClick={() => onPageChange(totalPages)}
          disabled={page === totalPages}
        >
          <ChevronsRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}

// ============== 主组件 ==============

export function DataTable<T>({
  data,
  columns,
  loading = false,
  error = null,
  emptyMessage,
  loadingMessage,
  errorMessage,
  pagination,
  sort,
  className,
  tableClassName,
  rowKey,
  onRowClick,
  rowClassName,
  selectable = false,
  selectedRows = new Set(),
  onSelectionChange,
  actions,
  mobileCard,
  headerActions,
  footerActions,
}: DataTableProps<T>) {
  // 计算实际的列数
  const columnCount = columns.length + (selectable ? 1 : 0) + (actions ? 1 : 0)

  // 处理排序
  const handleSort = (column: Column<T>) => {
    if (!column.sortable || !sort) return

    const { key, direction, onSort } = sort
    let newDirection: 'asc' | 'desc' | null = 'asc'

    if (key === column.key) {
      if (direction === 'asc') {
        newDirection = 'desc'
      } else if (direction === 'desc') {
        newDirection = null
      }
    }

    onSort(column.key, newDirection)
  }

  // 处理全选
  const handleSelectAll = () => {
    if (!onSelectionChange) return

    const allKeys = data.map((item, index) =>
      rowKey ? rowKey(item, index) : index
    )

    if (selectedRows.size === data.length) {
      onSelectionChange(new Set())
    } else {
      onSelectionChange(new Set(allKeys))
    }
  }

  // 处理单行选择
  const handleSelectRow = (item: T, index: number) => {
    if (!onSelectionChange) return

    const key = rowKey ? rowKey(item, index) : index
    const newSelection = new Set(selectedRows)

    if (newSelection.has(key)) {
      newSelection.delete(key)
    } else {
      newSelection.add(key)
    }

    onSelectionChange(newSelection)
  }

  // 响应式：移动端使用卡片布局
  const [isMobile, setIsMobile] = React.useState(false)

  React.useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < TABLE_CONFIG.MOBILE_BREAKPOINT)
    }

    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  // 移动端卡片视图
  if (isMobile && mobileCard) {
    return (
      <div className={cn('space-y-4', className)}>
        {headerActions && <div className="mb-4">{headerActions}</div>}

        {loading && (
          <Card className="p-8 text-center">
            <div className="flex flex-col items-center justify-center gap-2">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
              <span className="text-sm text-muted-foreground">
                {loadingMessage || TABLE_CONFIG.DEFAULT_LOADING_MESSAGE}
              </span>
            </div>
          </Card>
        )}

        {error && (
          <Card className="p-8 text-center">
            <span className="text-sm text-destructive">
              {errorMessage || error || TABLE_CONFIG.DEFAULT_ERROR_MESSAGE}
            </span>
          </Card>
        )}

        {!loading && !error && data.length === 0 && (
          <Card className="p-8 text-center">
            <span className="text-sm text-muted-foreground">
              {emptyMessage || TABLE_CONFIG.DEFAULT_EMPTY_MESSAGE}
            </span>
          </Card>
        )}

        {!loading && !error && data.map((item, index) => (
          <div key={rowKey ? rowKey(item, index) : index}>
            {mobileCard(item, index)}
          </div>
        ))}

        {pagination && <Pagination config={pagination} />}
        {footerActions && <div className="mt-4">{footerActions}</div>}
      </div>
    )
  }

  // 桌面端表格视图
  return (
    <div className={cn('w-full', className)}>
      {headerActions && <div className="mb-4">{headerActions}</div>}

      <div className="rounded-md border">
        <Table className={tableClassName}>
          <TableHeader>
            <TableRow>
              {selectable && (
                <TableHead className="w-12">
                  <input
                    type="checkbox"
                    checked={selectedRows.size === data.length && data.length > 0}
                    onChange={handleSelectAll}
                    className="rounded border-gray-300"
                  />
                </TableHead>
              )}
              {columns.map((column) => (
                <TableHead
                  key={column.key}
                  className={cn(
                    column.headerClassName,
                    column.sortable && 'cursor-pointer select-none',
                    column.align === 'center' && 'text-center',
                    column.align === 'right' && 'text-right',
                    column.sticky && 'sticky left-0 z-10 bg-background',
                    column.hideOnMobile && 'hidden md:table-cell'
                  )}
                  style={{ width: column.width }}
                  onClick={() => column.sortable && handleSort(column)}
                >
                  <div className="flex items-center">
                    {column.header}
                    {column.sortable && (
                      <SortIcon
                        sorted={sort?.key === column.key}
                        direction={sort?.key === column.key ? sort.direction : null}
                      />
                    )}
                  </div>
                </TableHead>
              ))}
              {actions && <TableHead className="text-right">操作</TableHead>}
            </TableRow>
          </TableHeader>

          <TableBody>
            {loading && <TableLoading columns={columnCount} message={loadingMessage} />}

            {error && <TableError columns={columnCount} message={errorMessage || error} />}

            {!loading && !error && data.length === 0 && (
              <TableEmpty columns={columnCount} message={emptyMessage} />
            )}

            {!loading && !error && data.map((item, index) => {
              const key = rowKey ? rowKey(item, index) : index
              const isSelected = selectedRows.has(key)

              return (
                <TableRow
                  key={key}
                  className={cn(
                    onRowClick && 'cursor-pointer hover:bg-muted/50',
                    isSelected && 'bg-muted/50',
                    rowClassName?.(item, index)
                  )}
                  onClick={() => onRowClick?.(item, index)}
                >
                  {selectable && (
                    <TableCell className="w-12">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => handleSelectRow(item, index)}
                        onClick={(e) => e.stopPropagation()}
                        className="rounded border-gray-300"
                      />
                    </TableCell>
                  )}
                  {columns.map((column) => (
                    <TableCell
                      key={column.key}
                      className={cn(
                        column.cellClassName,
                        column.align === 'center' && 'text-center',
                        column.align === 'right' && 'text-right',
                        column.sticky && 'sticky left-0 z-10 bg-background',
                        column.hideOnMobile && 'hidden md:table-cell'
                      )}
                    >
                      {column.accessor ? column.accessor(item) : (item as any)[column.key]}
                    </TableCell>
                  ))}
                  {actions && (
                    <TableCell className="text-right">
                      {actions(item, index)}
                    </TableCell>
                  )}
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>

      {pagination && <Pagination config={pagination} />}
      {footerActions && <div className="mt-4">{footerActions}</div>}
    </div>
  )
}

export default DataTable