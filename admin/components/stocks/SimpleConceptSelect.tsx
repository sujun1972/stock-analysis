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
 * - 支持远程搜索（异步加载）
 * - 支持本地搜索（同步过滤）
 */

import * as React from 'react'
import { createPortal } from 'react-dom'
import { Check, ChevronsUpDown, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import type { Concept } from '@/types/stock'

interface SimpleConceptSelectProps {
  /** 概念列表（仅在本地模式使用） */
  concepts?: Concept[]
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
  /** 是否启用远程搜索模式 */
  remoteSearch?: boolean
  /** 远程搜索函数（返回 Promise<Concept[]>） */
  onSearch?: (query: string) => Promise<Concept[]>
  /** 远程获取选中项详情（用于显示已选中的项） */
  onFetchSelected?: (value: string) => Promise<Concept | null>
}

export function SimpleConceptSelect({
  concepts = [],
  value,
  onSelect,
  placeholder = '选择概念...',
  disabled = false,
  includeAllOption = false,
  valueType = 'id',
  remoteSearch = false,
  onSearch,
  onFetchSelected,
}: SimpleConceptSelectProps) {
  const [open, setOpen] = React.useState(false)
  const [search, setSearch] = React.useState('')
  const [loading, setLoading] = React.useState(false)
  const [remoteConcepts, setRemoteConcepts] = React.useState<Concept[]>([])
  const [selectedConcept, setSelectedConcept] = React.useState<Concept | null>(null)
  const [dropdownPosition, setDropdownPosition] = React.useState({ top: 0, left: 0, width: 0 })
  const buttonRef = React.useRef<HTMLButtonElement>(null)
  const dropdownRef = React.useRef<HTMLDivElement>(null)
  const searchInputRef = React.useRef<HTMLInputElement>(null)
  const [mounted, setMounted] = React.useState(false)
  const searchTimeoutRef = React.useRef<NodeJS.Timeout>()
  const lastFetchedValueRef = React.useRef<string>('') // 追踪上次获取的值，避免重复请求

  // 获取当前使用的概念列表
  const currentConcepts = remoteSearch ? remoteConcepts : concepts

  // 根据 valueType 查找选中的概念（仅在本地模式下）
  React.useEffect(() => {
    if (!remoteSearch && value && value !== 'all') {
      const found = concepts.find((c) =>
        valueType === 'id'
          ? c.id.toString() === value
          : c.code === value
      )
      setSelectedConcept(found || null)
      lastFetchedValueRef.current = value
    } else if (remoteSearch && value && value !== 'all' && onFetchSelected) {
      // 远程模式：异步获取选中项详情
      // 只有当值变化时才重新获取
      if (lastFetchedValueRef.current !== value) {
        lastFetchedValueRef.current = value
        onFetchSelected(value).then((concept) => {
          setSelectedConcept(concept)
        })
      }
    } else if (!value || value === 'all') {
      // 清空选中项
      setSelectedConcept(null)
      lastFetchedValueRef.current = ''
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, valueType, remoteSearch])

  // 过滤概念列表（本地模式）
  const filteredConcepts = React.useMemo(() => {
    if (remoteSearch) return currentConcepts // 远程模式直接返回远程结果
    if (!search) return currentConcepts
    const query = search.toLowerCase()
    return currentConcepts.filter(
      (c) =>
        c.code.toLowerCase().includes(query) ||
        c.name.toLowerCase().includes(query)
    )
  }, [currentConcepts, search, remoteSearch])

  // 远程搜索处理（带防抖）
  React.useEffect(() => {
    if (!remoteSearch || !onSearch || !open) return

    // 清除之前的定时器
    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }

    // 设置新的定时器（300ms 防抖）
    searchTimeoutRef.current = setTimeout(async () => {
      setLoading(true)
      try {
        const results = await onSearch(search)
        setRemoteConcepts(results)
      } catch (error) {
        console.error('远程搜索失败:', error)
        setRemoteConcepts([])
      } finally {
        setLoading(false)
      }
    }, 300)

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current)
      }
    }
  }, [search, remoteSearch, onSearch, open])

  // 挂载状态和 Portal 容器
  React.useEffect(() => {
    setMounted(true)
  }, [])

  // 获取 Portal 容器（必须使用 Radix Dialog 的 Portal 容器）
  const getPortalContainer = React.useCallback(() => {
    // 在 Dialog 中必须渲染到 Dialog 的 Portal 容器内
    // 查找所有 Radix Portal 容器，选择最后一个（通常是当前 Dialog）
    const portals = document.querySelectorAll('[data-radix-portal]')
    if (portals.length > 0) {
      return portals[portals.length - 1] as HTMLElement
    }
    // 否则使用 body
    return document.body
  }, [])

  // 更新下拉框位置
  const updateDropdownPosition = React.useCallback(() => {
    if (buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect()
      const viewportHeight = window.innerHeight
      const dropdownMaxHeight = 300 // 下拉框的最大高度（与 CSS 中的 max-h-[300px] 对应）

      // 计算向下展开是否会超出屏幕
      const spaceBelow = viewportHeight - rect.bottom
      const spaceAbove = rect.top

      let top: number

      // 如果下方空间不足，且上方空间更多，则向上展开
      if (spaceBelow < dropdownMaxHeight && spaceAbove > spaceBelow) {
        // 向上展开（使用绝对位置）
        top = rect.top - dropdownMaxHeight - 4
      } else {
        // 向下展开（使用绝对位置）
        top = rect.bottom + 4
      }

      setDropdownPosition({
        top,
        left: rect.left, // 使用绝对位置
        width: rect.width,
      })
    }
  }, [])

  React.useEffect(() => {
    if (open) {
      // 初始定位
      updateDropdownPosition()

      // 多次尝试聚焦，使用不同的时机以确保成功
      const attemptFocus = () => {
        if (searchInputRef.current) {
          searchInputRef.current.focus({ preventScroll: true })
        }
      }

      // 立即尝试
      requestAnimationFrame(attemptFocus)
      // 延迟尝试（确保 Dialog 的焦点陷阱已经设置完成）
      setTimeout(attemptFocus, 50)
      setTimeout(attemptFocus, 100)

      // 监听滚动和窗口大小变化，实时更新位置
      const handleScroll = () => updateDropdownPosition()
      const handleResize = () => updateDropdownPosition()

      window.addEventListener('scroll', handleScroll, true) // 使用捕获阶段监听所有滚动
      window.addEventListener('resize', handleResize)

      // 使用 ResizeObserver 监听按钮位置变化
      let resizeObserver: ResizeObserver | null = null
      if (buttonRef.current) {
        resizeObserver = new ResizeObserver(updateDropdownPosition)
        resizeObserver.observe(buttonRef.current)
      }

      return () => {
        window.removeEventListener('scroll', handleScroll, true)
        window.removeEventListener('resize', handleResize)
        if (resizeObserver) {
          resizeObserver.disconnect()
        }
      }
    }
  }, [open, updateDropdownPosition])

  // 点击外部关闭
  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      const target = event.target as Node

      // 检查点击是否在下拉框或触发按钮外部
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(target) &&
        buttonRef.current &&
        !buttonRef.current.contains(target)
      ) {
        setOpen(false)
      }
    }

    if (open) {
      // 使用 mousedown 而不是 click，因为 Dialog 可能会拦截 click 事件
      document.addEventListener('mousedown', handleClickOutside, { capture: false })
      return () => document.removeEventListener('mousedown', handleClickOutside, { capture: false })
    }
  }, [open])

  const handleSelect = (selectedValue: string, concept?: Concept) => {
    onSelect(selectedValue)

    // 如果选择时提供了概念对象，立即设置（避免闪烁）
    if (concept) {
      setSelectedConcept(concept)
      lastFetchedValueRef.current = selectedValue
    }

    setOpen(false)
    setSearch('')
  }

  // 打开下拉框时触发初始搜索
  const handleOpenChange = (newOpen: boolean) => {
    setOpen(newOpen)
    if (newOpen && remoteSearch) {
      setSearch('') // 重置搜索关键词，触发初始加载
    }
  }

  const dropdownContent = open && mounted && (
    <div
      ref={dropdownRef}
      data-concept-select-dropdown
      role="dialog"
      aria-modal="false"
      className="fixed rounded-md border bg-popover text-popover-foreground shadow-lg outline-none animate-in fade-in-80"
      style={{
        top: `${dropdownPosition.top}px`,
        left: `${dropdownPosition.left}px`,
        width: `${dropdownPosition.width}px`,
        zIndex: 100000, // 确保高于 Dialog (Dialog 通常是 50)
        pointerEvents: 'auto',
      }}
    >
      <div className="p-2">
        <input
          ref={searchInputRef}
          type="text"
          placeholder="搜索概念..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          autoFocus
          className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        />
      </div>
      <div className="max-h-[min(300px,60vh)] overflow-y-auto overflow-x-hidden p-1">
        {includeAllOption && (!search || '全部概念'.includes(search)) && (
          <div
            className="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground"
            onClick={() => handleSelect('all', undefined)}
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

        {loading ? (
          <div className="py-6 flex items-center justify-center text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            搜索中...
          </div>
        ) : filteredConcepts.length === 0 ? (
          <div className="py-6 text-center text-sm text-muted-foreground">
            {remoteSearch && !search ? '请输入关键词搜索概念' : '没有找到匹配的概念'}
          </div>
        ) : (
          filteredConcepts.map((concept) => {
            const itemValue = valueType === 'id' ? concept.id.toString() : concept.code
            return (
              <div
                key={concept.id}
                className="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground"
                onClick={() => handleSelect(itemValue, concept)}
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
      <div className="relative w-full">
        {/* 触发按钮 */}
        <Button
          ref={buttonRef}
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between"
          disabled={disabled}
          onClick={() => handleOpenChange(!open)}
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
      </div>

      {/* 下拉列表（使用 Portal 渲染到 Dialog Portal 容器，避免影响 Dialog 大小） */}
      {mounted && dropdownContent && createPortal(dropdownContent, getPortalContainer())}
    </>
  )
}
