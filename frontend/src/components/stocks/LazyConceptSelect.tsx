'use client'

/**
 * 东方财富板块选择器
 * - 支持概念板块 / 行业板块 / 地域板块三种类型切换
 * - 懒加载：打开时才请求数据
 * - 后端搜索：防抖 300ms 后向后端发搜索请求
 * - 滚动加载更多
 * - 数据来自 dc_index + dc_member
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

interface ConceptItem {
  ts_code: string
  name: string
  member_count: number
}

interface LazyConceptSelectProps {
  value: string
  onSelect: (value: string) => void
  placeholder?: string
  disabled?: boolean
  includeAllOption?: boolean
  /** 保留兼容旧调用，无实际用途 */
  valueType?: 'id' | 'code'
}

type IdxType = '概念板块' | '行业板块' | '地域板块'

const TABS: { key: IdxType; label: string }[] = [
  { key: '概念板块', label: '概念' },
  { key: '行业板块', label: '行业' },
  { key: '地域板块', label: '地域' },
]

const PAGE_SIZE = 50

export function LazyConceptSelect({
  value,
  onSelect,
  placeholder = '选择板块...',
  disabled = false,
  includeAllOption = false,
}: LazyConceptSelectProps) {
  const [open, setOpen] = React.useState(false)
  const [activeTab, setActiveTab] = React.useState<IdxType>('概念板块')
  const [search, setSearch] = React.useState('')
  const [concepts, setConcepts] = React.useState<ConceptItem[]>([])
  const [loading, setLoading] = React.useState(false)
  const [total, setTotal] = React.useState(0)
  const [offset, setOffset] = React.useState(0)
  const [selectedName, setSelectedName] = React.useState<string>('')

  const searchRef = React.useRef(search)
  const searchTimerRef = React.useRef<NodeJS.Timeout>()
  const isComposing = React.useRef(false)

  // 当外部 value 切换回 'all' 或清空时，重置显示名称
  React.useEffect(() => {
    if (!value || value === 'all') setSelectedName('')
  }, [value])

  const load = React.useCallback(async (q: string, off: number, append: boolean, idxType: IdxType) => {
    setLoading(true)
    try {
      const res = await apiClient.getConceptBoards({
        search: q || undefined,
        idx_type: idxType,
        limit: PAGE_SIZE,
        offset: off,
      })
      if (append) {
        setConcepts(prev => {
          const existing = new Set(prev.map(c => c.ts_code))
          return [...prev, ...res.items.filter(c => !existing.has(c.ts_code))]
        })
      } else {
        setConcepts(res.items)
      }
      setTotal(res.total)
      setOffset(off)

      // 若当前选中值在结果中，更新显示名称
      if (value && value !== 'all') {
        const found = res.items.find(c => c.ts_code === value)
        if (found) setSelectedName(found.name)
      }
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [value])

  // 打开时首次加载
  React.useEffect(() => {
    if (open && concepts.length === 0) {
      load('', 0, false, activeTab)
    }
  }, [open, concepts.length, load, activeTab])

  // 切换 Tab 时重置并重新加载
  const handleTabChange = (tab: IdxType) => {
    setActiveTab(tab)
    setSearch('')
    setConcepts([])
    setTotal(0)
    setOffset(0)
    load('', 0, false, tab)
  }

  // 搜索防抖（处理中文输入法）
  React.useEffect(() => {
    searchRef.current = search
    if (!open) return
    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
    searchTimerRef.current = setTimeout(() => {
      if (!isComposing.current) {
        load(search, 0, false, activeTab)
      }
    }, 300)
    return () => { if (searchTimerRef.current) clearTimeout(searchTimerRef.current) }
  }, [search, open, load, activeTab])

  // 滚动加载更多
  const handleScroll = React.useCallback((e: React.UIEvent<HTMLDivElement>) => {
    if (loading || concepts.length >= total) return
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget
    if (scrollHeight - scrollTop <= clientHeight * 1.5) {
      load(searchRef.current, offset + PAGE_SIZE, true, activeTab)
    }
  }, [loading, concepts.length, total, offset, load, activeTab])

  const handleSelect = (val: string, name?: string) => {
    if (val === 'all') {
      setSelectedName('')
    } else if (name) {
      setSelectedName(name)
    }
    onSelect(val)
    setOpen(false)
    setSearch('')
  }

  const displayLabel = value === 'all' || !value
    ? (includeAllOption ? '全部板块' : placeholder)
    : (selectedName || value)

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className="w-full justify-between font-normal"
          disabled={disabled}
        >
          <span className={cn(value && value !== 'all' ? '' : 'text-muted-foreground')}>
            {displayLabel}
          </span>
          <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="w-[--radix-popover-trigger-width] p-0"
        align="start"
        side="bottom"
      >
        {/* Tab 切换 */}
        <div className="flex border-b">
          {TABS.map(tab => (
            <button
              key={tab.key}
              type="button"
              onClick={() => handleTabChange(tab.key)}
              className={cn(
                'flex-1 px-2 py-2 text-xs font-medium transition-colors',
                activeTab === tab.key
                  ? 'border-b-2 border-primary text-primary'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* 搜索框 */}
        <div className="flex items-center border-b px-3 py-2">
          <Input
            placeholder={`搜索${TABS.find(t => t.key === activeTab)?.label ?? '板块'}...`}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onCompositionStart={() => { isComposing.current = true }}
            onCompositionEnd={(e) => {
              isComposing.current = false
              const q = (e.target as HTMLInputElement).value
              if (searchTimerRef.current) clearTimeout(searchTimerRef.current)
              load(q, 0, false, activeTab)
            }}
            className="h-9 border-0 focus-visible:ring-0 focus-visible:ring-offset-0"
          />
        </div>

        {/* 列表 */}
        <div
          className="max-h-[300px] overflow-y-auto overflow-x-hidden"
          onScroll={handleScroll}
        >
          {concepts.length === 0 && !loading ? (
            <div className="py-6 text-center text-sm text-muted-foreground">
              {search ? `没有找到匹配的${TABS.find(t => t.key === activeTab)?.label}` : '暂无板块成分股数据，请先同步板块成分'}
            </div>
          ) : (
            <div className="p-1">
              {includeAllOption && (
                <div
                  className="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground"
                  onClick={() => handleSelect('all')}
                >
                  <Check className={cn('mr-2 h-4 w-4', value === 'all' ? 'opacity-100' : 'opacity-0')} />
                  <span className="font-medium">全部板块</span>
                </div>
              )}

              {concepts.map((concept) => (
                <div
                  key={concept.ts_code}
                  className="relative flex cursor-pointer select-none items-center rounded-sm px-2 py-1.5 text-sm outline-none hover:bg-accent hover:text-accent-foreground"
                  onClick={() => handleSelect(concept.ts_code, concept.name)}
                >
                  <Check className={cn('mr-2 h-4 w-4', value === concept.ts_code ? 'opacity-100' : 'opacity-0')} />
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <span className="flex-1 truncate">{concept.name}</span>
                    <span className="text-xs text-muted-foreground shrink-0">{concept.member_count} 只</span>
                  </div>
                </div>
              ))}

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

        {/* 底部统计 */}
        {total > 0 && (
          <div className="border-t px-3 py-2 text-xs text-muted-foreground">
            共 {total} 个{TABS.find(t => t.key === activeTab)?.label}，已加载 {concepts.length} 个
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
}
