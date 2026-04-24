'use client'

import { SlidersHorizontal, RotateCcw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  COLUMN_CONFIGS,
  COLUMN_GROUP_LABELS,
  COLUMN_GROUP_ORDER,
  type StockColumnConfig,
  type StockColumnGroup,
  type StockColumnId,
} from '../hooks/useStockTableColumns'

interface Props {
  isVisible: (id: StockColumnId) => boolean
  onToggle: (id: StockColumnId) => void
  onReset: () => void
  visibleCount: number
}

// 模块级常量：按 COLUMN_GROUP_ORDER 聚合，组内保留 COLUMN_CONFIGS 原顺序（便于用户预期列位置）
const GROUPED_COLUMNS: ReadonlyArray<readonly [StockColumnGroup, StockColumnConfig[]]> = (() => {
  const groups = new Map<StockColumnGroup, StockColumnConfig[]>()
  for (const g of COLUMN_GROUP_ORDER) groups.set(g, [])
  for (const col of COLUMN_CONFIGS) groups.get(col.group)!.push(col)
  return Array.from(groups.entries()).filter(([, cols]) => cols.length > 0)
})()

const TOTAL_COLUMNS = COLUMN_CONFIGS.length

export function ColumnVisibilityMenu({ isVisible, onToggle, onReset, visibleCount }: Props) {
  // 仅当有列被隐藏时显示计数徽章，避免默认态的视觉噪音
  const showBadge = visibleCount < TOTAL_COLUMNS

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
          title="显示列"
          aria-label={showBadge ? `显示列（${visibleCount}/${TOTAL_COLUMNS}）` : '显示列'}
        >
          <SlidersHorizontal className="h-3.5 w-3.5" />
          {/* <lg 断点只显示图标，避免筛选器头在窄屏被挤压；≥lg 恢复图标+文字 */}
          <span className="hidden lg:inline">显示列</span>
          {showBadge && (
            <span className="inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full text-[10px] font-semibold bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-200 tabular-nums">
              {visibleCount}/{TOTAL_COLUMNS}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="flex items-center justify-between">
          <span>显示列</span>
          <button
            type="button"
            onClick={onReset}
            className="inline-flex items-center gap-1 text-[11px] font-normal text-gray-500 hover:text-blue-600 dark:text-gray-400 dark:hover:text-blue-400 focus-ring rounded-sm px-1"
            title="恢复默认显示"
          >
            <RotateCcw className="h-3 w-3" />
            恢复默认
          </button>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {GROUPED_COLUMNS.map(([group, cols], idx) => (
          <div key={group}>
            {idx > 0 && <DropdownMenuSeparator />}
            <DropdownMenuLabel className="text-[10px] uppercase tracking-wider text-gray-400 dark:text-gray-500 font-medium py-1">
              {COLUMN_GROUP_LABELS[group]}
            </DropdownMenuLabel>
            {cols.map(col => (
              <DropdownMenuCheckboxItem
                key={col.id}
                checked={isVisible(col.id)}
                onCheckedChange={() => onToggle(col.id)}
                // 阻止选中后关闭菜单，便于连续切换多列
                onSelect={(e) => e.preventDefault()}
              >
                {col.label}
              </DropdownMenuCheckboxItem>
            ))}
          </div>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
