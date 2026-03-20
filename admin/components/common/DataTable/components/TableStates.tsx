/**
 * @file components/common/DataTable/components/TableStates.tsx
 * @description 表格状态组件（Loading/Empty/Error）
 * @created 2026-03-20
 */

'use client'

import { ReactNode } from 'react'
import { TableRow, TableCell } from '@/components/ui/table'
import { Button } from '@/components/ui/button'
import { TABLE_CONFIG } from '@/lib/constants'

interface TableLoadingProps {
  columns: number
  message?: string | ReactNode
}

export function TableLoading({
  columns,
  message = TABLE_CONFIG.DEFAULT_LOADING_MESSAGE
}: TableLoadingProps) {
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

interface TableEmptyProps {
  columns: number
  message?: string | ReactNode
}

export function TableEmpty({
  columns,
  message = TABLE_CONFIG.DEFAULT_EMPTY_MESSAGE
}: TableEmptyProps) {
  return (
    <TableRow>
      <TableCell colSpan={columns} className="h-24 text-center">
        <div className="text-sm text-muted-foreground">{message}</div>
      </TableCell>
    </TableRow>
  )
}

interface TableErrorProps {
  columns: number
  message?: string | ReactNode
  onRetry?: () => void
}

export function TableError({
  columns,
  message = TABLE_CONFIG.DEFAULT_ERROR_MESSAGE,
  onRetry
}: TableErrorProps) {
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
