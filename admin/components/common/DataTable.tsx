/**
 * @file components/common/DataTable.tsx
 * @description 通用的数据表格组件，支持分页、排序、筛选、响应式布局
 * @author Claude
 * @created 2024-03-16
 * @updated 2024-03-16
 */

'use client'

import React, { ReactNode, useState } from 'react'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
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
  message?: string | ReactNode
}) {
  return (
    <TableRow>
      <TableCell colSpan={columns} className="h-24 text-center">
        <div className="flex flex-col items-center justify-center gap-2">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
          <div className="text-sm text-muted-foreground">{message}</div>
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
  message?: string | ReactNode
}) {
  return (
    <TableRow>
      <TableCell colSpan={columns} className="h-24 text-center">
        <div className="text-sm text-muted-foreground">{message}</div>
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
  message?: string | ReactNode
  onRetry?: () => void
}) {
  return (
    <TableRow>
      <TableCell colSpan={columns} className="h-24 text-center">
        <div className="flex flex-col items-center justify-center gap-2">
          <div className="text-sm text-destructive">{message}</div>
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
  const [jumpPage, setJumpPage] = useState('')

  // 智能调整分页选项，移除超过总数的选项
  const effectivePageSizeOptions = pageSizeOptions.filter(size => size <= total || size === pageSizeOptions[0])

  /**
   * 生成页码范围
   * 桌面端：显示当前页左右各1页
   * 移动端：页数<=7时显示所有页码，>7时仅显示首页、当前页、末页
   */
  const getPageNumbers = () => {
    const delta = 1 // 当前页码左右各显示几个页码
    const range: (number | string)[] = []
    const rangeWithDots: (number | string)[] = []
    let l: number | undefined

    // 在移动端显示更少的页码
    const isMobile = window.innerWidth < 640
    const actualDelta = isMobile ? 0 : delta

    // 移动端特殊处理：当页数很多时，采用紧凑显示
    if (isMobile && totalPages > 7) {
      // 紧凑模式：1 ... 当前页 ... 末页
      if (page === 1) {
        return [1, '...', totalPages]
      } else if (page === totalPages) {
        return [1, '...', totalPages]
      } else {
        return [1, '...', page, '...', totalPages]
      }
    }

    for (let i = 1; i <= totalPages; i++) {
      if (i === 1 || i === totalPages || (i >= page - actualDelta && i <= page + actualDelta)) {
        range.push(i)
      }
    }

    range.forEach((i) => {
      if (l) {
        if (i !== l + 1) {
          rangeWithDots.push('...')
        }
      }
      rangeWithDots.push(i)
      l = i as number
    })

    return rangeWithDots
  }

  const handleJump = () => {
    const pageNum = parseInt(jumpPage, 10)
    if (pageNum && pageNum >= 1 && pageNum <= totalPages) {
      onPageChange(pageNum)
      setJumpPage('')
    }
  }

  return (
    <div className="px-2 py-4 space-y-4">
      {/* 移动端布局（垂直排列） */}
      <div className="flex flex-col gap-3 sm:hidden">
        {/* 第一行：显示信息 */}
        <div className="flex items-center justify-between">
          <div className="text-xs text-muted-foreground">
            <span className="font-medium">{startIndex}-{endIndex}</span> / {total} 条
          </div>
          {onPageSizeChange && (
            <Select value={pageSize.toString()} onValueChange={(v) => onPageSizeChange(Number(v))}>
              <SelectTrigger className="h-7 w-20 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {effectivePageSizeOptions.map((size) => (
                  <SelectItem key={size} value={size.toString()} className="text-xs">
                    {size} 条/页
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        </div>

        {/* 第二行：简化的分页控制 */}
        <div className="flex items-center justify-between">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page === 1}
            className="h-8 w-8 p-0"
            aria-label="上一页"
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          {/* 页数很多时显示更紧凑的页码指示器 */}
          {totalPages > 7 ? (
            <div className="flex items-center gap-1 text-xs">
              <span className="text-muted-foreground">第</span>
              <span className="font-medium px-1">{page}</span>
              <span className="text-muted-foreground">/ {totalPages} 页</span>
            </div>
          ) : (
            <div className="flex items-center gap-1">
              {getPageNumbers().map((pageNum, index) => {
                if (pageNum === '...') {
                  return (
                    <span key={`dots-${index}`} className="px-1 text-xs text-muted-foreground">
                      {pageNum}
                    </span>
                  )
                }
                return (
                  <Button
                    key={pageNum}
                    variant={pageNum === page ? 'default' : 'ghost'}
                    size="sm"
                    onClick={() => onPageChange(pageNum as number)}
                    className={cn(
                      "h-8 min-w-[2rem] px-2 text-xs",
                      pageNum === page && "pointer-events-none"
                    )}
                  >
                    {pageNum}
                  </Button>
                )
              })}
            </div>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page === totalPages}
            className="h-8 w-8 p-0"
            aria-label="下一页"
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>

        {/* 第三行：快速跳转和快捷操作 */}
        {totalPages > 5 && (
          <div className="flex items-center gap-2 justify-center">
            {/* 快速跳转到首页和末页的按钮 */}
            {page > 2 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onPageChange(1)}
                className="h-7 px-2 text-xs"
              >
                首页
              </Button>
            )}

            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">跳至</span>
              <input
                type="number"
                value={jumpPage}
                onChange={(e) => setJumpPage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleJump()}
                className="h-7 w-12 text-xs rounded border bg-background px-2 text-center"
                min="1"
                max={totalPages}
                placeholder={page.toString()}
              />
              <Button
                variant="outline"
                size="sm"
                onClick={handleJump}
                className="h-7 px-2 text-xs"
              >
                确定
              </Button>
            </div>

            {page < totalPages - 1 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onPageChange(totalPages)}
                className="h-7 px-2 text-xs"
              >
                末页
              </Button>
            )}
          </div>
        )}
      </div>

      {/* 桌面端布局（水平排列） */}
      <div className="hidden sm:flex sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <span>显示</span>
            {onPageSizeChange ? (
              <Select value={pageSize.toString()} onValueChange={(v) => onPageSizeChange(Number(v))}>
                <SelectTrigger className="h-8 w-24">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {effectivePageSizeOptions.map((size) => (
                    <SelectItem key={size} value={size.toString()}>
                      {size} 条/页
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ) : (
              <span className="font-medium">{pageSize}</span>
            )}
            <span>条，共 {total} 条</span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(1)}
            disabled={page === 1}
            className="h-8"
          >
            <ChevronsLeft className="h-4 w-4 mr-1" />
            首页
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page - 1)}
            disabled={page === 1}
            className="h-8"
          >
            <ChevronLeft className="h-4 w-4 mr-1" />
            上一页
          </Button>

          <div className="flex items-center gap-1">
            {getPageNumbers().map((pageNum, index) => {
              if (pageNum === '...') {
                return (
                  <span key={`dots-${index}`} className="px-2 text-sm text-muted-foreground">
                    {pageNum}
                  </span>
                )
              }
              return (
                <Button
                  key={pageNum}
                  variant={pageNum === page ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => onPageChange(pageNum as number)}
                  className={cn(
                    "h-8 min-w-[2.5rem]",
                    pageNum === page && "pointer-events-none"
                  )}
                >
                  {pageNum}
                </Button>
              )
            })}
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(page + 1)}
            disabled={page === totalPages}
            className="h-8"
          >
            下一页
            <ChevronRight className="h-4 w-4 ml-1" />
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onPageChange(totalPages)}
            disabled={page === totalPages}
            className="h-8"
          >
            末页
            <ChevronsRight className="h-4 w-4 ml-1" />
          </Button>

          {/* 快速跳转 */}
          {totalPages > 10 && (
            <div className="flex items-center gap-2 ml-4">
              <span className="text-sm text-muted-foreground">跳至</span>
              <input
                type="number"
                value={jumpPage}
                onChange={(e) => setJumpPage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleJump()}
                className="h-8 w-16 text-sm rounded border bg-background px-2 text-center"
                min="1"
                max={totalPages}
                placeholder={page.toString()}
              />
              <span className="text-sm text-muted-foreground">页</span>
            </div>
          )}
        </div>
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

            {error && <TableError columns={columnCount} message={errorMessage || String(error)} />}

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