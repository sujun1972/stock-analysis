'use client'

/**
 * 概念选择器组件
 *
 * 支持搜索、自适应定位、高 z-index 的下拉选择器，适用于在 Dialog 等层级较高的容器中使用
 *
 * 特性：
 * - 使用 React Portal 渲染下拉框，避免被父容器遮挡
 * - 智能定位：根据屏幕空间自动选择向上或向下展开
 * - 响应式高度：最大高度不超过视口 60%
 * - 支持按 ID 或 Code 选择
 * - 支持"全部"选项
 * - 实时搜索过滤
 */

import * as React from 'react'
import { createPortal } from 'react-dom'
import { Check, ChevronsUpDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import type { Concept } from '@/types/stock'

interface SimpleConceptSelectProps {
  /** 概念列表 */
  concepts: Concept[]
  /** 当前选中的值（ID 或 Code，取决于 valueType） */
  value: string
  /** 选择回调 */
  onSelect: (value: string) => void
  /** 占位符文本 */
  placeholder?: string
  /** 是否禁用 */
  disabled?: boolean
  /** 是否包含"全部"选项 */
  includeAllOption?: boolean
  /** 值类型：'id' 使用概念 ID，'code' 使用概念代码 */
  valueType?: 'id' | 'code'
}

export function SimpleConceptSelect({
  concepts,
  value,
  onSelect,
  placeholder = '选择概念...',
  disabled = false,
  includeAllOption = false,
  valueType = 'id',
}: SimpleConceptSelectProps) {
  const [open, setOpen] = React.useState(false)
  const [search, setSearch] = React.useState('')
  const [dropdownPosition, setDropdownPosition] = React.useState({ top: 0, left: 0, width: 0 })
  const buttonRef = React.useRef<HTMLButtonElement>(null)
  const dropdownRef = React.useRef<HTMLDivElement>(null)
  const [mounted, setMounted] = React.useState(false)

  // 根据 valueType 查找选中的概念
  const selectedConcept = includeAllOption && value === 'all'
    ? null
    : concepts.find((c) =>
        valueType === 'id'
          ? c.id.toString() === value
          : c.code === value
      )

  // 过滤概念列表
  const filteredConcepts = React.useMemo(() => {
    if (!search) return concepts
    const query = search.toLowerCase()
    return concepts.filter(
      (c) =>
        c.code.toLowerCase().includes(query) ||
        c.name.toLowerCase().includes(query)
    )
  }, [concepts, search])

  // 挂载状态和 Portal 容器
  React.useEffect(() => {
    setMounted(true)
  }, [])

  // 获取 Portal 容器（优先使用 Radix Portal 容器）
  const getPortalContainer = React.useCallback(() => {
    // 尝试找到 Radix Portal 容器
    const radixPortal = document.querySelector('[data-radix-portal]')
    if (radixPortal) {
      return radixPortal as HTMLElement
    }
    // 否则使用 body
    return document.body
  }, [])

  // 更新下拉框位置
  React.useEffect(() => {
    if (open && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect()
      const viewportHeight = window.innerHeight
      const dropdownMaxHeight = 300 // 下拉框的最大高度（与 CSS 中的 max-h-[300px] 对应）

      // 计算向下展开是否会超出屏幕
      const spaceBelow = viewportHeight - rect.bottom
      const spaceAbove = rect.top

      let top: number

      // 如果下方空间不足，且上方空间更多，则向上展开
      if (spaceBelow < dropdownMaxHeight && spaceAbove > spaceBelow) {
        // 向上展开
        top = rect.top + window.scrollY - dropdownMaxHeight - 4
      } else {
        // 向下展开
        top = rect.bottom + window.scrollY + 4
      }

      setDropdownPosition({
        top,
        left: rect.left + window.scrollX,
        width: rect.width,
      })
    }
  }, [open])

  // 点击外部关闭
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(event.target as Node)
      ) {
        setOpen(false)
      }
    }

    if (open) {
      document.addEventListener('mousedown', handleClickOutside)
      return () => document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [open])

  const handleSelect = (selectedValue: string) => {
    onSelect(selectedValue)
    setOpen(false)
    setSearch('')
  }

  const dropdownContent = open && mounted && (
    <div
      ref={dropdownRef}
      className="fixed rounded-md border bg-popover text-popover-foreground shadow-lg outline-none animate-in fade-in-80"
      style={{
        top: `${dropdownPosition.top}px`,
        left: `${dropdownPosition.left}px`,
        width: `${dropdownPosition.width}px`,
        zIndex: 99999,
        pointerEvents: 'auto',
      }}
      onMouseDown={(e) => e.stopPropagation()}
      onClick={(e) => e.stopPropagation()}
    >
      <div className="p-2" onMouseDown={(e) => e.stopPropagation()}>
        <input
          type="text"
          placeholder="搜索概念..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
          autoFocus
        />
      </div>
      <div className="max-h-[min(300px,60vh)] overflow-y-auto overflow-x-hidden p-1">
        {includeAllOption && (!search || '全部概念'.includes(search)) && (
          <div
            className="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground"
            onClick={() => handleSelect('all')}
          >
            <Check
              className={cn(
                'mr-2 h-4 w-4',
                value === 'all' ? 'opacity-100' : 'opacity-0'
              )}
            />
            <span className="font-medium">全部概念</span>
          </div>
        )}

        {filteredConcepts.length === 0 ? (
          <div className="py-6 text-center text-sm text-muted-foreground">
            没有找到匹配的概念
          </div>
        ) : (
          filteredConcepts.map((concept) => {
            const itemValue = valueType === 'id' ? concept.id.toString() : concept.code
            return (
              <div
                key={concept.id}
                className="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground"
                onClick={() => handleSelect(itemValue)}
              >
                <Check
                  className={cn(
                    'mr-2 h-4 w-4',
                    value === itemValue ? 'opacity-100' : 'opacity-0'
                  )}
                />
                <div className="flex items-center gap-2 flex-1">
                  <span className="font-mono text-xs text-muted-foreground">
                    {concept.code}
                  </span>
                  <span className="flex-1">{concept.name}</span>
                  {concept.stock_count !== undefined && (
                    <span className="text-xs text-muted-foreground">
                      {concept.stock_count} 只股票
                    </span>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )

  return (
    <>
      {/* 触发按钮 */}
      <Button
        ref={buttonRef}
        type="button"
        variant="outline"
        role="combobox"
        aria-expanded={open}
        className="w-full justify-between"
        disabled={disabled}
        onClick={() => setOpen(!open)}
      >
        {selectedConcept ? (
          <span className="flex items-center gap-2">
            <span className="font-mono text-xs text-muted-foreground">
              {selectedConcept.code}
            </span>
            <span>{selectedConcept.name}</span>
            {selectedConcept.stock_count !== undefined && (
              <span className="text-xs text-muted-foreground">
                ({selectedConcept.stock_count})
              </span>
            )}
          </span>
        ) : (
          <span className="text-muted-foreground">
            {includeAllOption && value === 'all' ? '全部概念' : placeholder}
          </span>
        )}
        <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
      </Button>

      {/* 下拉列表（通过 Portal 渲染） */}
      {mounted && createPortal(dropdownContent, getPortalContainer())}
    </>
  )
}
