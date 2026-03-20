/**
 * @file components/common/DataTable/components/DesktopView.tsx
 * @description 桌面端表格视图
 * @created 2026-03-20
 */

'use client'

import { ReactNode } from 'react'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { cn } from '@/lib/utils'
import { TableLoading, TableEmpty, TableError } from './TableStates'
import { SortIcon } from './SortIcon'
import { Pagination } from './Pagination'
import type { Column, PaginationConfig, SortConfig } from '../types'

interface DesktopViewProps<T> {
  data: T[]
  columns: Column<T>[]
  loading?: boolean
  error?: string | null
  emptyMessage?: string | ReactNode
  loadingMessage?: string | ReactNode
  errorMessage?: string | ReactNode
  pagination?: PaginationConfig
  sort?: SortConfig
  tableClassName?: string
  rowKey?: (item: T, index: number) => string | number
  onRowClick?: (item: T, index: number) => void
  rowClassName?: (item: T, index: number) => string
  selectable?: boolean
  selectedRows?: Set<string | number>
  onSelectionChange?: (selectedRows: Set<string | number>) => void
  actions?: (item: T, index: number) => ReactNode
  headerActions?: ReactNode
  footerActions?: ReactNode
  onSelectAll: () => void
  onSelectRow: (item: T, index: number) => void
  onSort: (column: Column<T>) => void
}

export function DesktopView<T>({
  data,
  columns,
  loading = false,
  error = null,
  emptyMessage,
  loadingMessage,
  errorMessage,
  pagination,
  sort,
  tableClassName,
  rowKey,
  onRowClick,
  rowClassName,
  selectable = false,
  selectedRows = new Set(),
  onSelectionChange,
  actions,
  headerActions,
  footerActions,
  onSelectAll,
  onSelectRow,
  onSort,
}: DesktopViewProps<T>) {
  // 计算实际的列数
  const columnCount = columns.length + (selectable ? 1 : 0) + (actions ? 1 : 0)

  return (
    <div className="w-full">
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
                    onChange={onSelectAll}
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
                  onClick={() => column.sortable && onSort(column)}
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
                        onChange={() => onSelectRow(item, index)}
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
                      {column.accessor
                        ? column.accessor(item)
                        : column.render
                        ? column.render((item as any)[column.key], item)
                        : (item as any)[column.key]}
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
