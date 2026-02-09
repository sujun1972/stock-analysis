/**
 * 日期范围选择器组件
 * 支持快捷选择和自定义日期范围
 */

'use client'

import { memo } from 'react'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

interface DateRangeSelectorProps {
  value: { start: string; end: string }
  onChange: (range: { start: string; end: string }) => void
}

const DateRangeSelector = memo(function DateRangeSelector({
  value,
  onChange
}: DateRangeSelectorProps) {
  const today = new Date()
  const formatDate = (date: Date) => {
    return date.toISOString().split('T')[0]
  }

  const quickSelections = [
    {
      label: '近1年',
      getRange: () => {
        const start = new Date(today)
        start.setFullYear(start.getFullYear() - 1)
        return { start: formatDate(start), end: formatDate(today) }
      }
    },
    {
      label: '近3年',
      getRange: () => {
        const start = new Date(today)
        start.setFullYear(start.getFullYear() - 3)
        return { start: formatDate(start), end: formatDate(today) }
      }
    },
    {
      label: '近5年',
      getRange: () => {
        const start = new Date(today)
        start.setFullYear(start.getFullYear() - 5)
        return { start: formatDate(start), end: formatDate(today) }
      }
    },
    {
      label: '今年',
      getRange: () => {
        const start = new Date(today.getFullYear(), 0, 1)
        return { start: formatDate(start), end: formatDate(today) }
      }
    },
    {
      label: '去年',
      getRange: () => {
        const start = new Date(today.getFullYear() - 1, 0, 1)
        const end = new Date(today.getFullYear() - 1, 11, 31)
        return { start: formatDate(start), end: formatDate(end) }
      }
    }
  ]

  return (
    <div className="space-y-3">
      <Label className="text-sm font-medium">回测日期范围</Label>

      {/* 快捷选择 */}
      <div className="flex flex-wrap gap-2">
        {quickSelections.map((selection) => (
          <Button
            key={selection.label}
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onChange(selection.getRange())}
          >
            {selection.label}
          </Button>
        ))}
      </div>

      {/* 自定义日期 */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-2">
          <Label htmlFor="start-date" className="text-xs text-muted-foreground">
            开始日期
          </Label>
          <Input
            id="start-date"
            type="date"
            value={value.start}
            onChange={(e) => onChange({ ...value, start: e.target.value })}
            max={value.end || formatDate(today)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="end-date" className="text-xs text-muted-foreground">
            结束日期
          </Label>
          <Input
            id="end-date"
            type="date"
            value={value.end}
            onChange={(e) => onChange({ ...value, end: e.target.value })}
            min={value.start}
            max={formatDate(today)}
          />
        </div>
      </div>

      {value.start && value.end && (
        <p className="text-xs text-muted-foreground">
          回测周期: {value.start} 至 {value.end}
          {' '}({Math.ceil((new Date(value.end).getTime() - new Date(value.start).getTime()) / (1000 * 60 * 60 * 24))} 天)
        </p>
      )}
    </div>
  )
})

DateRangeSelector.displayName = 'DateRangeSelector'

export default DateRangeSelector
