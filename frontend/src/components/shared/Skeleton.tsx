'use client'

/**
 * 骨架屏组件：大列表首次加载时替代整页 spinner，避免 CLS 并提升感知性能。
 * 轻量二次 loading（翻页 / 排序 / 筛选）仍使用小型 Loader2 图标。
 */

import { cn } from '@/lib/utils'

export function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('animate-pulse rounded-md bg-gray-200 dark:bg-gray-800', className)}
      {...props}
    />
  )
}

interface StockTableSkeletonProps {
  rows?: number
  showCheckbox?: boolean
}

/** 桌面端表格骨架：列结构与 StockTableRow 保持一致，避免真实数据到达时的布局偏移。 */
export function StockTableSkeleton({ rows = 10, showCheckbox = true }: StockTableSkeletonProps) {
  return (
    <div className="hidden md:block overflow-x-auto" aria-hidden="true">
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
          {Array.from({ length: rows }).map((_, i) => (
            <tr key={i}>
              {showCheckbox && (
                <td className="px-4 py-4 w-10">
                  <Skeleton className="h-4 w-4" />
                </td>
              )}
              <td className="px-6 py-4">
                <Skeleton className="h-4 w-32" />
              </td>
              <td className="px-6 py-4 text-right">
                <Skeleton className="h-4 w-14 ml-auto" />
              </td>
              <td className="px-6 py-4 text-right">
                <Skeleton className="h-4 w-14 ml-auto" />
              </td>
              {/* 4 个评分列 */}
              {Array.from({ length: 4 }).map((_, j) => (
                <td key={`s${j}`} className="px-4 py-4 text-right">
                  <Skeleton className="h-5 w-10 ml-auto" />
                </td>
              ))}
              {/* CIO 日期 */}
              <td className="px-4 py-4 text-right">
                <Skeleton className="h-3 w-16 ml-auto" />
              </td>
              {/* 价值度量 3 列（ROC / EY / 安全边际） */}
              {Array.from({ length: 3 }).map((_, j) => (
                <td key={`v${j}`} className="px-4 py-4 text-right">
                  <Skeleton className="h-3 w-12 ml-auto" />
                </td>
              ))}
              {/* 关注价格 / 关注时间 */}
              <td className="px-4 py-4">
                <Skeleton className="h-3 w-16" />
              </td>
              <td className="px-4 py-4">
                <Skeleton className="h-3 w-16" />
              </td>
              {/* 操作按钮 */}
              <td className="px-4 py-4">
                <Skeleton className="h-6 w-16" />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/** 移动端卡片骨架：结构与 StockCard 对齐（股票名/代码 + 价格涨跌 + 4 个评分 Badge）。 */
export function StockCardSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="md:hidden p-3 space-y-3" aria-hidden="true">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-start gap-2 min-w-0 flex-1">
              <Skeleton className="h-4 w-4 mt-0.5" />
              <div className="min-w-0 flex-1 space-y-1.5">
                <Skeleton className="h-4 w-24" />
                <Skeleton className="h-3 w-16" />
              </div>
            </div>
            <div className="flex flex-col items-end gap-1.5">
              <Skeleton className="h-4 w-14" />
              <Skeleton className="h-3 w-10" />
            </div>
          </div>
          <div className="mt-3 grid grid-cols-4 gap-1.5">
            {Array.from({ length: 4 }).map((_, j) => (
              <Skeleton key={j} className="h-8 w-full" />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

/** 分析历史首次拉取记录时的骨架屏（行 + 翻页器 + 内容块）。 */
export function AnalysisHistorySkeleton() {
  return (
    <div
      className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 space-y-3"
      aria-hidden="true"
    >
      <div className="flex items-center justify-between">
        <Skeleton className="h-3 w-40" />
        <div className="flex gap-2">
          <Skeleton className="h-5 w-12" />
          <Skeleton className="h-5 w-5" />
          <Skeleton className="h-5 w-5" />
        </div>
      </div>
      <div className="space-y-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-[95%]" />
        <Skeleton className="h-3 w-[88%]" />
        <Skeleton className="h-3 w-[92%]" />
        <Skeleton className="h-3 w-[70%]" />
      </div>
    </div>
  )
}
