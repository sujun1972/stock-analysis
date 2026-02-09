/**
 * 股票快速搜索组件
 *
 * 功能特性：
 * - 实时搜索股票（支持代码和名称）
 * - 下拉框展示搜索结果（显示价格和涨跌幅）
 * - 键盘导航支持（上下箭头、Enter、Escape）
 * - 支持自定义选中行为或默认跳转到分析页面
 *
 * 使用场景：
 * - Header 导航栏（默认跳转）
 * - 回测页面股票池选择（自定义 onSelect）
 * - 其他需要股票搜索的场景
 */

'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Input } from '@/components/ui/input'
import { Search } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { cn } from '@/lib/utils'

interface Stock {
  code: string
  name: string
  latest_price?: number
  pct_change?: number
}

interface StockSearchProps {
  /** 自定义选中回调，如果提供则不会跳转到分析页面 */
  onSelect?: (stock: Stock) => void
  /** 占位符文字 */
  placeholder?: string
  /** 最多显示多少条搜索结果 */
  maxResults?: number
  /** 自定义样式类名 */
  className?: string
}

export function StockSearch({
  onSelect,
  placeholder = '搜索股票...',
  maxResults = 5,
  className
}: StockSearchProps = {}) {
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<Stock[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  const router = useRouter()
  const inputRef = useRef<HTMLInputElement>(null)
  const resultsRef = useRef<HTMLDivElement>(null)

  /**
   * 获取价格/涨跌幅的颜色样式
   * A股市场：涨红跌绿
   */
  const getPriceColorClass = useCallback((pctChange?: number | null) => {
    if (pctChange === null || pctChange === undefined) {
      return 'text-gray-600 dark:text-gray-400'
    }
    if (pctChange > 0) {
      return 'text-red-600 dark:text-red-400'
    }
    if (pctChange < 0) {
      return 'text-green-600 dark:text-green-400'
    }
    return 'text-gray-600 dark:text-gray-400'
  }, [])

  /**
   * 搜索股票（带防抖）
   * 当输入内容变化时，延迟 300ms 后调用 API 搜索
   */
  useEffect(() => {
    if (searchQuery.length < 1) {
      setSearchResults([])
      setShowResults(false)
      return
    }

    const timer = setTimeout(async () => {
      setIsSearching(true)
      try {
        const result = await apiClient.getStockList({
          search: searchQuery,
          limit: maxResults
        })
        setSearchResults(result.items || [])
        setShowResults(true)
        setSelectedIndex(-1)
      } catch (error) {
        console.error('搜索股票失败:', error)
        setSearchResults([])
      } finally {
        setIsSearching(false)
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [searchQuery, maxResults])

  /**
   * 点击外部区域时关闭下拉框
   */
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        resultsRef.current &&
        !resultsRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setShowResults(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  /**
   * 处理股票选择
   * 根据是否提供 onSelect 回调决定行为
   */
  const handleSelectStock = useCallback((stock: Stock) => {
    if (onSelect) {
      onSelect(stock)
    } else {
      router.push(`/analysis?code=${stock.code}`)
    }
    setSearchQuery('')
    setShowResults(false)
    inputRef.current?.blur()
  }, [onSelect, router])

  /**
   * 处理键盘导航
   * 支持上下箭头选择、Enter 确认、Escape 关闭
   */
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (!showResults || searchResults.length === 0) return

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault()
        setSelectedIndex(prev =>
          prev < searchResults.length - 1 ? prev + 1 : prev
        )
        break
      case 'ArrowUp':
        e.preventDefault()
        setSelectedIndex(prev => prev > 0 ? prev - 1 : -1)
        break
      case 'Enter':
        e.preventDefault()
        if (selectedIndex >= 0 && selectedIndex < searchResults.length) {
          handleSelectStock(searchResults[selectedIndex])
        } else if (searchResults.length > 0) {
          handleSelectStock(searchResults[0])
        }
        break
      case 'Escape':
        setShowResults(false)
        inputRef.current?.blur()
        break
    }
  }, [showResults, searchResults, selectedIndex, handleSelectStock])

  return (
    <div className={cn("relative w-full max-w-xs", className)}>
      {/* 搜索输入框 */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          ref={inputRef}
          type="text"
          placeholder={placeholder}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (searchResults.length > 0) {
              setShowResults(true)
            }
          }}
          className="pl-9 bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm border-white/20 focus:border-white/40 text-gray-900 dark:text-white placeholder:text-gray-500 dark:placeholder:text-gray-400"
        />
      </div>

      {/* 搜索结果下拉框 */}
      {showResults && (
        <div
          ref={resultsRef}
          className="absolute top-full mt-2 w-full bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50 overflow-hidden"
        >
          {isSearching ? (
            <div className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 text-center">
              搜索中...
            </div>
          ) : searchResults.length === 0 ? (
            <div className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 text-center">
              未找到相关股票
            </div>
          ) : (
            <ul className="max-h-80 overflow-y-auto">
              {searchResults.map((stock, index) => (
                <li key={stock.code}>
                  <button
                    onClick={() => handleSelectStock(stock)}
                    onMouseEnter={() => setSelectedIndex(index)}
                    className={cn(
                      'w-full px-4 py-3 text-left hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors border-b border-gray-100 dark:border-gray-700 last:border-b-0',
                      selectedIndex === index && 'bg-gray-100 dark:bg-gray-700'
                    )}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-gray-900 dark:text-white">
                            {stock.code}
                          </span>
                          <span className="text-sm text-gray-600 dark:text-gray-300 truncate">
                            {stock.name}
                          </span>
                        </div>
                      </div>
                      {stock.latest_price !== undefined && (
                        <div className="flex items-center gap-3 flex-shrink-0">
                          <span className={cn('text-sm font-medium', getPriceColorClass(stock.pct_change))}>
                            {stock.latest_price.toFixed(2)}
                          </span>
                          {stock.pct_change !== null && stock.pct_change !== undefined && (
                            <span className={cn(
                              'text-xs font-medium min-w-[60px] text-right',
                              getPriceColorClass(stock.pct_change)
                            )}>
                              {stock.pct_change > 0 ? '+' : ''}{stock.pct_change.toFixed(2)}%
                            </span>
                          )}
                        </div>
                      )}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
