'use client'

/**
 * 概念选择器组件（支持懒加载和后端搜索）
 *
 * 特性：
 * - 懒加载：打开下拉框时才加载数据
 * - 后端搜索：搜索时从后端API获取结果
 * - 分页加载：支持滚动加载更多
 * - 防抖搜索：避免频繁请求
 * - 使用 React Portal 渲染下拉框，避免被父容器遮挡
 */

import * as React from 'react'
import { createPortal } from 'react-dom'
import { Check, ChevronsUpDown, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { axiosInstance } from '@/lib/api'
import logger from '@/lib/logger'
import type { Concept } from '@/types/stock'

interface LazyConceptSelectProps {
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

export function LazyConceptSelect({
  value,
  onSelect,
  placeholder = '选择概念...',
  disabled = false,
  includeAllOption = false,
  valueType = 'id',
}: LazyConceptSelectProps) {
  const [open, setOpen] = React.useState(false)
  const [search, setSearch] = React.useState('')
  const [concepts, setConcepts] = React.useState<Concept[]>([])
  const [loading, setLoading] = React.useState(false)
  const [selectedConcept, setSelectedConcept] = React.useState<Concept | null>(null)
  const [page, setPage] = React.useState(1)
  const [hasMore, setHasMore] = React.useState(true)
  const [dropdownPosition, setDropdownPosition] = React.useState({ top: 0, left: 0, width: 0 })

  const buttonRef = React.useRef<HTMLButtonElement>(null)
  const dropdownRef = React.useRef<HTMLDivElement>(null)
  const scrollRef = React.useRef<HTMLDivElement>(null)
  const [mounted, setMounted] = React.useState(false)
  const searchTimeoutRef = React.useRef<NodeJS.Timeout>()

  React.useEffect(() => {
    setMounted(true)
  }, [])

  // 加载已选中的概念信息
  React.useEffect(() => {
    if (value && value !== 'all' && !selectedConcept) {
      loadSelectedConcept()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, selectedConcept])

  const loadSelectedConcept = async () => {
    if (value === 'all') return

    try {
      // 如果是code类型，从concepts中查找
      if (valueType === 'code') {
        const response = await axiosInstance.get('/api/concepts/list', {
          params: { page: 1, page_size: 1000 },
        }) as any
        const data = response.data || { items: [] }
        const concept = data.items.find((c: Concept) => c.code === value)
        if (concept) {
          setSelectedConcept(concept)
        }
      } else {
        // 如果是id类型，直接调用API获取
        const response = await axiosInstance.get(`/api/concepts/${parseInt(value)}`) as any
        setSelectedConcept(response.data)
      }
    } catch (error) {
      logger.error('加载选中概念失败', error)
    }
  }

  // 加载概念列表
  const loadConcepts = async (searchQuery: string = '', pageNum: number = 1, append: boolean = false) => {
    setLoading(true)
    try {
      const apiResponse = await axiosInstance.get('/api/concepts/list', {
        params: { page: pageNum, page_size: 50, search: searchQuery || undefined },
      }) as any
      const responseData = apiResponse.data || { items: [], total_pages: 0 }

      if (append) {
        setConcepts(prev => [...prev, ...responseData.items])
      } else {
        setConcepts(responseData.items)
      }

      setHasMore(pageNum < responseData.total_pages)
      setPage(pageNum)
    } catch (error) {
      logger.error('加载概念列表失败', error)
    } finally {
      setLoading(false)
    }
  }

  // 打开下拉框时加载初始数据
  React.useEffect(() => {
    if (open && concepts.length === 0) {
      loadConcepts()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, concepts.length])

  // 搜索防抖
  React.useEffect(() => {
    if (!open) return

    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current)
    }

    searchTimeoutRef.current = setTimeout(() => {
      loadConcepts(search, 1, false)
    }, 300)

    return () => {
      if (searchTimeoutRef.current) {
        clearTimeout(searchTimeoutRef.current)
      }
    }
  }, [search, open])

  // 滚动加载更多
  const handleScroll = React.useCallback(() => {
    if (!scrollRef.current || loading || !hasMore) return

    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current
    if (scrollHeight - scrollTop <= clientHeight * 1.5) {
      loadConcepts(search, page + 1, true)
    }
  }, [loading, hasMore, search, page])

  // 更新下拉框位置
  React.useEffect(() => {
    if (open && buttonRef.current) {
      const rect = buttonRef.current.getBoundingClientRect()
      const viewportHeight = window.innerHeight
      const dropdownMaxHeight = 400

      const spaceBelow = viewportHeight - rect.bottom
      const spaceAbove = rect.top

      let top: number
      if (spaceBelow < dropdownMaxHeight && spaceAbove > spaceBelow) {
        top = rect.top + window.scrollY - dropdownMaxHeight - 4
      } else {
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
    if (selectedValue === 'all') {
      setSelectedConcept(null)
    } else {
      const concept = concepts.find(c =>
        valueType === 'id' ? c.id.toString() === selectedValue : c.code === selectedValue
      )
      if (concept) {
        setSelectedConcept(concept)
      }
    }
    onSelect(selectedValue)
    setOpen(false)
    setSearch('')
  }

  const getPortalContainer = React.useCallback(() => {
    const radixPortal = document.querySelector('[data-radix-portal]')
    if (radixPortal) return radixPortal as HTMLElement
    return document.body
  }, [])

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

      <div
        ref={scrollRef}
        className="max-h-[min(400px,60vh)] overflow-y-auto overflow-x-hidden p-1"
        onScroll={handleScroll}
      >
        {includeAllOption && (
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

        {concepts.length === 0 && !loading ? (
          <div className="py-6 text-center text-sm text-muted-foreground">
            {search ? '没有找到匹配的概念' : '暂无概念数据'}
          </div>
        ) : (
          concepts.map((concept) => {
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
                      {concept.stock_count}
                    </span>
                  )}
                </div>
              </div>
            )
          })
        )}

        {loading && (
          <div className="flex items-center justify-center py-4">
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">
              {concepts.length === 0 ? '加载中...' : '加载更多...'}
            </span>
          </div>
        )}
      </div>
    </div>
  )

  return (
    <>
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

      {mounted && createPortal(dropdownContent, getPortalContainer())}
    </>
  )
}
