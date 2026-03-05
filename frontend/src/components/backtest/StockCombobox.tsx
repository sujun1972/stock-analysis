/**
 * 可搜索的股票选择下拉框组件
 *
 * 功能:
 * - 支持按股票代码和名称搜索
 * - 使用 Popover + 自定义列表实现 Combobox 模式
 * - 适用于大量股票数据的场景（如500只股票的股票池）
 *
 * 技术说明:
 * - 原本尝试使用 cmdk (Command) 组件，但遇到点击事件被阻止的问题
 * - 改用普通 HTML 元素 + onClick 事件，完全避开 cmdk 的事件处理问题
 * - 手动实现客户端搜索过滤，性能良好
 */

'use client'

import * as React from 'react'
import { Check, ChevronsUpDown, Search } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'

interface StockOption {
  value: string        // 股票代码
  label: string        // 显示文本（股票名称(代码)或仅代码）
  searchText: string   // 用于搜索的文本（包含代码和名称）
}

interface StockComboboxProps {
  value: string
  onValueChange: (value: string) => void
  options: StockOption[]
  placeholder?: string
  className?: string
  width?: string
}

export function StockCombobox({
  value,
  onValueChange,
  options,
  placeholder = '选择股票...',
  className,
  width = 'w-[200px]'
}: StockComboboxProps) {
  const [open, setOpen] = React.useState(false)
  const [search, setSearch] = React.useState('')

  // 找到当前选中项的显示文本
  const selectedOption = options.find((option) => option.value === value)
  const displayText = selectedOption?.label || placeholder

  // 手动过滤选项
  const filteredOptions = React.useMemo(() => {
    if (!search.trim()) return options
    const searchLower = search.toLowerCase()
    return options.filter((option) =>
      option.searchText.toLowerCase().includes(searchLower)
    )
  }, [options, search])

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={cn('justify-between h-9', width, className)}
        >
          <span className="truncate">{displayText}</span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent className={cn('p-0', width)} align="start">
        <div className="flex h-full w-full flex-col overflow-hidden rounded-md bg-popover text-popover-foreground">
          {/* 搜索输入框 */}
          <div className="flex items-center border-b px-3">
            <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
            <input
              className="flex h-10 w-full rounded-md bg-transparent py-3 text-sm outline-none placeholder:text-muted-foreground disabled:cursor-not-allowed disabled:opacity-50"
              placeholder="搜索股票代码或名称..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {/* 选项列表 */}
          <div className="max-h-[300px] overflow-y-auto overflow-x-hidden p-1">
            {filteredOptions.length === 0 ? (
              <div className="py-6 text-center text-sm">未找到相关股票</div>
            ) : (
              filteredOptions.map((option) => (
                <div
                  key={option.value}
                  className={cn(
                    'relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground',
                    value === option.value && 'bg-accent text-accent-foreground'
                  )}
                  onClick={() => {
                    onValueChange(option.value)
                    setOpen(false)
                    setSearch('')
                  }}
                >
                  <Check
                    className={cn(
                      'mr-2 h-4 w-4',
                      value === option.value ? 'opacity-100' : 'opacity-0'
                    )}
                  />
                  {option.label}
                </div>
              ))
            )}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}
