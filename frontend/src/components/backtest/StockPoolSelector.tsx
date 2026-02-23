/**
 * 股票池选择器组件
 *
 * 功能特性：
 * - 从股票列表选择（弹窗筛选）
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
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { X, List } from 'lucide-react'
import { StockSelectionDialog } from './StockSelectionDialog'

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
  maxStocks = 500
}: StockPoolSelectorProps) {
  const [dialogOpen, setDialogOpen] = useState(false)

  /**
   * 从股票池中移除指定股票
   */
  const removeStock = useCallback((stockCode: string) => {
    onChange(value.filter(code => code !== stockCode))
  }, [value, onChange])

  /**
   * 处理从弹窗确认选择
   */
  const handleDialogConfirm = useCallback((selectedCodes: string[]) => {
    // 合并已有股票和新选择的股票，去重
    const allCodes = [...value, ...selectedCodes]
    const uniqueCodes = Array.from(new Set(allCodes))

    // 限制在 maxStocks 范围内
    const finalCodes = uniqueCodes.slice(0, maxStocks)

    onChange(finalCodes)
  }, [value, maxStocks, onChange])

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">
          股票池 ({value.length}/{maxStocks})
        </Label>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => setDialogOpen(true)}
          className="gap-2"
        >
          <List className="h-4 w-4" />
          从股票列表选择
        </Button>
      </div>

      {/* 已选股票列表 */}
      {value.length > 0 ? (
        <div className="border rounded-lg p-3 max-h-64 overflow-y-auto">
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
      ) : (
        <div className="border rounded-lg p-6 text-center">
          <div className="text-gray-400 dark:text-gray-500 mb-2">
            <List className="h-12 w-12 mx-auto mb-2 opacity-50" />
            <p className="text-sm">还未选择股票</p>
            <p className="text-xs mt-1">点击上方按钮从股票列表中选择</p>
          </div>
        </div>
      )}

      {/* 股票筛选弹窗 */}
      <StockSelectionDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onConfirm={handleDialogConfirm}
        initialSelected={[]}
        maxSelection={maxStocks}
        existingCount={value.length}
      />
    </div>
  )
})

StockPoolSelector.displayName = 'StockPoolSelector'

export default StockPoolSelector
