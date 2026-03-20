/**
 * @file components/common/DataTable/components/Pagination.tsx
 * @description 分页组件
 * @created 2026-03-20
 */

'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import type { PaginationConfig } from '../types'

interface PaginationProps {
  config: PaginationConfig
}

export function Pagination({ config }: PaginationProps) {
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
