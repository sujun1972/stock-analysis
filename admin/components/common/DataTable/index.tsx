/**
 * @file components/common/DataTable/index.tsx
 * @description 通用的数据表格组件（主组件）
 * @author Claude
 * @created 2024-03-16
 * @updated 2026-03-20 - 模块化重构
 */

'use client'

import React, { useState, useEffect } from 'react'
import { TABLE_CONFIG } from '@/lib/constants'
import { MobileView } from './components/MobileView'
import { DesktopView } from './components/DesktopView'
import { cn } from '@/lib/utils'
import type { DataTableProps, Column } from './types'

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
  // 扁平化分页属性（向后兼容）
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions,
}: DataTableProps<T>) {
  // 向后兼容：将扁平化的分页属性转换为 PaginationConfig
  const effectivePagination = pagination || (
    page !== undefined && pageSize !== undefined && total !== undefined && onPageChange
      ? {
          page,
          pageSize,
          total,
          onPageChange,
          onPageSizeChange,
          pageSizeOptions,
        }
      : undefined
  )

  // 响应式：检测移动端
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < TABLE_CONFIG.MOBILE_BREAKPOINT)
    }

    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

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

  // 移动端卡片视图
  if (isMobile && mobileCard) {
    return (
      <MobileView
        data={data}
        loading={loading}
        error={error}
        emptyMessage={emptyMessage}
        loadingMessage={loadingMessage}
        errorMessage={errorMessage}
        pagination={effectivePagination}
        rowKey={rowKey}
        mobileCard={mobileCard}
        headerActions={headerActions}
        footerActions={footerActions}
        className={className}
      />
    )
  }

  // 桌面端表格视图
  return (
    <div className={cn('w-full', className)}>
      <DesktopView
        data={data}
        columns={columns}
        loading={loading}
        error={error}
        emptyMessage={emptyMessage}
        loadingMessage={loadingMessage}
        errorMessage={errorMessage}
        pagination={effectivePagination}
        sort={sort}
        tableClassName={tableClassName}
        rowKey={rowKey}
        onRowClick={onRowClick}
        rowClassName={rowClassName}
        selectable={selectable}
        selectedRows={selectedRows}
        onSelectionChange={onSelectionChange}
        actions={actions}
        headerActions={headerActions}
        footerActions={footerActions}
        onSelectAll={handleSelectAll}
        onSelectRow={handleSelectRow}
        onSort={handleSort}
      />
    </div>
  )
}

// 导出类型
export type {
  Column,
  PaginationConfig,
  SortConfig,
  DataTableProps,
} from './types'

export default DataTable
