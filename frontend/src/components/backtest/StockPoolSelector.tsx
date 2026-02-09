/**
 * 股票池选择器组件
 * 支持手动输入股票代码，搜索添加，批量导入
 */

'use client'

import { useState, useEffect, memo } from 'react'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { X, Plus, Search } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'

interface StockPoolSelectorProps {
  value: string[]
  onChange: (stockCodes: string[]) => void
  maxStocks?: number
}

const StockPoolSelector = memo(function StockPoolSelector({
  value,
  onChange,
  maxStocks = 100
}: StockPoolSelectorProps) {
  const [inputValue, setInputValue] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [open, setOpen] = useState(false)

  // 搜索股票
  useEffect(() => {
    if (searchQuery.length < 2) {
      setSearchResults([])
      return
    }

    const timer = setTimeout(async () => {
      setIsSearching(true)
      try {
        const result = await apiClient.getStockList({
          search: searchQuery,
          limit: 20
        })
        setSearchResults(result.items || [])
      } catch (error) {
        console.error('搜索股票失败:', error)
      } finally {
        setIsSearching(false)
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [searchQuery])

  const addStock = (stockCode: string) => {
    const code = stockCode.trim().toUpperCase()
    if (!code) return

    // 检查是否已存在
    if (value.includes(code)) {
      return
    }

    // 检查数量限制
    if (value.length >= maxStocks) {
      alert(`最多添加 ${maxStocks} 只股票`)
      return
    }

    onChange([...value, code])
    setInputValue('')
    setSearchQuery('')
  }

  const removeStock = (stockCode: string) => {
    onChange(value.filter(code => code !== stockCode))
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addStock(inputValue)
    }
  }

  const handleBatchAdd = () => {
    const codes = inputValue
      .split(/[\s,，;；\n]+/)
      .map(code => code.trim().toUpperCase())
      .filter(code => code.length > 0)
      .filter(code => !value.includes(code))
      .slice(0, maxStocks - value.length)

    if (codes.length > 0) {
      onChange([...value, ...codes])
      setInputValue('')
    }
  }

  return (
    <div className="space-y-3">
      <Label className="text-sm font-medium">
        股票池 ({value.length}/{maxStocks})
      </Label>

      {/* 输入区域 */}
      <div className="flex gap-2">
        <div className="flex-1 flex gap-2">
          <Popover open={open} onOpenChange={setOpen}>
            <PopoverTrigger asChild>
              <Input
                type="text"
                value={inputValue}
                onChange={(e) => {
                  setInputValue(e.target.value)
                  setSearchQuery(e.target.value)
                  setOpen(true)
                }}
                onKeyPress={handleKeyPress}
                placeholder="输入股票代码或名称，支持批量（逗号或换行分隔）"
                className="flex-1"
              />
            </PopoverTrigger>
            {searchQuery.length >= 2 && (
              <PopoverContent className="p-0 w-80" align="start">
                <Command>
                  <CommandInput placeholder="搜索股票..." value={searchQuery} />
                  <CommandEmpty>
                    {isSearching ? '搜索中...' : '未找到相关股票'}
                  </CommandEmpty>
                  <CommandGroup>
                    {searchResults.map((stock) => (
                      <CommandItem
                        key={stock.stock_code}
                        onSelect={() => {
                          addStock(stock.stock_code)
                          setOpen(false)
                        }}
                      >
                        <div className="flex items-center justify-between w-full">
                          <span className="font-medium">{stock.stock_code}</span>
                          <span className="text-sm text-muted-foreground">{stock.name}</span>
                        </div>
                      </CommandItem>
                    ))}
                  </CommandGroup>
                </Command>
              </PopoverContent>
            )}
          </Popover>
        </div>
        <Button
          type="button"
          size="sm"
          onClick={() => addStock(inputValue)}
          disabled={!inputValue.trim()}
        >
          <Plus className="h-4 w-4" />
        </Button>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={handleBatchAdd}
          disabled={!inputValue.includes(',') && !inputValue.includes('\n') && !inputValue.includes('，')}
        >
          批量添加
        </Button>
      </div>

      {/* 已选股票列表 */}
      {value.length > 0 && (
        <div className="border rounded-lg p-3 max-h-48 overflow-y-auto">
          <div className="flex flex-wrap gap-2">
            {value.map((stockCode) => (
              <Badge
                key={stockCode}
                variant="secondary"
                className="pl-2 pr-1 py-1"
              >
                <span>{stockCode}</span>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="h-4 w-4 p-0 ml-1 hover:bg-transparent"
                  onClick={() => removeStock(stockCode)}
                >
                  <X className="h-3 w-3" />
                </Button>
              </Badge>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs text-muted-foreground">
        提示: 输入代码后按回车或点击+添加；支持批量粘贴（用逗号或换行分隔）
      </p>
    </div>
  )
})

StockPoolSelector.displayName = 'StockPoolSelector'

export default StockPoolSelector
