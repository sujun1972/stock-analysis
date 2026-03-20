/**
 * @file components/common/DataTable/components/MobileView.tsx
 * @description 移动端卡片视图
 * @created 2026-03-20
 */

'use client'

import { ReactNode } from 'react'
import { Card } from '@/components/ui/card'
import { TABLE_CONFIG } from '@/lib/constants'
import { Pagination } from './Pagination'
import type { PaginationConfig } from '../types'
import { cn } from '@/lib/utils'

interface MobileViewProps<T> {
  data: T[]
  loading?: boolean
  error?: string | null
  emptyMessage?: string | ReactNode
  loadingMessage?: string | ReactNode
  errorMessage?: string | ReactNode
  pagination?: PaginationConfig
  rowKey?: (item: T, index: number) => string | number
  mobileCard: (item: T, index: number) => ReactNode
  headerActions?: ReactNode
  footerActions?: ReactNode
  className?: string
}

export function MobileView<T>({
  data,
  loading = false,
  error = null,
  emptyMessage,
  loadingMessage,
  errorMessage,
  pagination,
  rowKey,
  mobileCard,
  headerActions,
  footerActions,
  className,
}: MobileViewProps<T>) {
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
