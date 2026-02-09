/**
 * 股票池选择器组件
 *
 * 功能特性：
 * - 实时搜索添加股票（使用 StockSearch 组件）
 * - 批量输入股票代码（支持逗号、分号、换行分隔）
 * - 展示已选股票列表（支持删除）
 * - 数量限制和去重处理
 *
 * 使用场景：
 * - 回测页面配置股票池
 * - 其他需要选择多个股票的场景
 */

'use client'

import { useState, memo, useCallback } from 'react'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { X, Plus } from 'lucide-react'
import { StockSearch } from '@/components/stock-search'

interface StockPoolSelectorProps {
  /** 已选股票代码列表 */
  value: string[]
  /** 股票列表变化回调 */
  onChange: (stockCodes: string[]) => void
  /** 最大股票数量限制 */
  maxStocks?: number
}

const StockPoolSelector = memo(function StockPoolSelector({
  value,
  onChange,
  maxStocks = 100
}: StockPoolSelectorProps) {
  const [inputValue, setInputValue] = useState('')

  /**
   * 添加单个股票到股票池
   * 自动转大写、去重、检查数量限制
   */
  const addStock = useCallback((stockCode: string) => {
    const code = stockCode.trim().toUpperCase()
    if (!code) return

    if (value.includes(code)) {
      return
    }

    if (value.length >= maxStocks) {
      alert(`最多添加 ${maxStocks} 只股票`)
      return
    }

    onChange([...value, code])
    setInputValue('')
  }, [value, maxStocks, onChange])

  /**
   * 从股票池中移除指定股票
   */
  const removeStock = useCallback((stockCode: string) => {
    onChange(value.filter(code => code !== stockCode))
  }, [value, onChange])

  /**
   * 处理回车键添加股票
   */
  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault()
      addStock(inputValue)
    }
  }, [inputValue, addStock])

  /**
   * 批量添加股票
   * 支持逗号、分号、换行等分隔符
   */
  const handleBatchAdd = useCallback(() => {
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
  }, [inputValue, value, maxStocks, onChange])

  return (
    <div className="space-y-3">
      <Label className="text-sm font-medium">
        股票池 ({value.length}/{maxStocks})
      </Label>

      {/* 股票搜索 */}
      <StockSearch
        onSelect={(stock) => addStock(stock.code)}
        placeholder="搜索并添加股票..."
        maxResults={10}
        className="max-w-full"
      />

      {/* 批量输入区域 */}
      <div className="space-y-2">
        <Label className="text-xs text-muted-foreground">
          批量添加（支持逗号、分号或换行分隔）
        </Label>
        <div className="flex gap-2">
          <Input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="例如: 600000, 000001, 300750"
            className="flex-1"
          />
          <Button
            type="button"
            size="sm"
            onClick={() => addStock(inputValue)}
            disabled={!inputValue.trim() || inputValue.includes(',') || inputValue.includes('\n') || inputValue.includes('，')}
            title="单个添加"
          >
            <Plus className="h-4 w-4" />
          </Button>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={handleBatchAdd}
            disabled={!inputValue.includes(',') && !inputValue.includes('\n') && !inputValue.includes('，')}
            title="批量添加"
          >
            批量添加
          </Button>
        </div>
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
        提示: 可通过搜索框快速查找股票，或批量粘贴股票代码
      </p>
    </div>
  )
})

StockPoolSelector.displayName = 'StockPoolSelector'

export default StockPoolSelector
