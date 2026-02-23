'use client'

/**
 * 概念选择器组件（不使用 Command 组件，避免点击问题）
 *
 * 特性：
 * - 懒加载：打开下拉框时才加载数据
 * - 后端搜索：搜索时从后端API获取结果
 * - 分页加载：支持滚动加载更多
 * - 防抖搜索：避免频繁请求
 * - 使用 Popover 提供下拉功能
 */

import * as React from 'react'
import { Check, ChevronsUpDown, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { apiClient } from '@/lib/api-client'
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

  const searchTimeoutRef = React.useRef<NodeJS.Timeout>()
  const scrollRef = React.useRef<HTMLDivElement>(null)

  // 加载已选中的概念信息
  React.useEffect(() => {
    if (value && value !== 'all' && !selectedConcept) {
      loadSelectedConcept()
    }
  }, [value])

  const loadSelectedConcept = async () => {
    if (value === 'all') return

    try {
      if (valueType === 'code') {
        const response = await apiClient.getConceptsList({ limit: 1000 })
        const concept = response.items.find(c => c.code === value)
        if (concept) {
          setSelectedConcept(concept)
        }
      } else {
        const concept = await apiClient.getConcept(parseInt(value))
        setSelectedConcept(concept)
      }
    } catch (error) {
      console.error('加载选中概念失败:', error)
    }
  }

  // 加载概念列表
  const loadConcepts = async (searchQuery: string = '', pageNum: number = 1, append: boolean = false) => {
    setLoading(true)
    try {
      const response = await apiClient.getConceptsList({
        skip: (pageNum - 1) * 50,
        limit: 50,
        search: searchQuery || undefined,
      })

      if (append) {
        // 去重：只添加不存在的概念
        setConcepts(prev => {
          const existingIds = new Set(prev.map(c => c.id))
          const newConcepts = response.items.filter(c => !existingIds.has(c.id))
          return [...prev, ...newConcepts]
        })
      } else {
        setConcepts(response.items)
      }

      const totalPages = Math.ceil(response.total / 50)
      setHasMore(pageNum < totalPages)
      setPage(pageNum)
    } catch (error) {
      console.error('加载概念列表失败:', error)
    } finally {
      setLoading(false)
    }
  }

  // 打开下拉框时加载初始数据
  React.useEffect(() => {
    if (open && concepts.length === 0) {
      loadConcepts()
    }
  }, [open])

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
  const handleScroll = React.useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget
    if (loading || !hasMore) return

    const { scrollTop, scrollHeight, clientHeight } = target
    if (scrollHeight - scrollTop <= clientHeight * 1.5) {
      loadConcepts(search, page + 1, true)
    }
  }, [loading, hasMore, search, page])

  // 处理选择
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

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between"
          disabled={disabled}
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
      </PopoverTrigger>
      <PopoverContent
        className="w-[--radix-popover-trigger-width] p-0"
        align="start"
        side="bottom"
      >
        {/* 搜索输入框 */}
        <div className="flex items-center border-b px-3 py-2">
          <Input
            placeholder="搜索概念..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-9 border-0 focus-visible:ring-0 focus-visible:ring-offset-0"
          />
        </div>

        {/* 选项列表 */}
        <div
          ref={scrollRef}
          className="max-h-[300px] overflow-y-auto overflow-x-hidden"
          onScroll={handleScroll}
        >
          {concepts.length === 0 && !loading ? (
            <div className="py-6 text-center text-sm text-muted-foreground">
              {search ? '没有找到匹配的概念' : '暂无概念数据'}
            </div>
          ) : (
            <div className="p-1">
              {/* 全部选项 */}
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

              {/* 概念列表 */}
              {concepts.map((concept) => {
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
              })}

              {/* 加载指示器 */}
              {loading && (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  <span className="ml-2 text-sm text-muted-foreground">
                    {concepts.length === 0 ? '加载中...' : '加载更多...'}
                  </span>
                </div>
              )}
            </div>
          )}
        </div>
      </PopoverContent>
    </Popover>
  )
}
