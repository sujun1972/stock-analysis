/**
 * @file components/common/DatePicker.tsx
 * @description 统一的日期选择器组件，支持交易日历和格式转换
 */

'use client'

import React, { useState, useEffect } from 'react'
import { Calendar } from 'lucide-react'
import { cn } from '@/lib/utils'

interface DatePickerProps {
  value?: string
  onChange?: (value: string) => void
  onFormattedChange?: (formatted: string) => void  // YYYYMMDD格式
  placeholder?: string
  className?: string
  disabled?: boolean
  max?: string
  min?: string
  label?: string
  required?: boolean
}

export function DatePicker({
  value,
  onChange,
  onFormattedChange,
  placeholder = '选择日期',
  className,
  disabled = false,
  max,
  min,
  label,
  required = false
}: DatePickerProps) {
  const [localValue, setLocalValue] = useState(value || '')

  useEffect(() => {
    setLocalValue(value || '')
  }, [value])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value
    setLocalValue(newValue)

    // 触发原始格式回调（YYYY-MM-DD）
    if (onChange) {
      onChange(newValue)
    }

    // 触发格式化回调（YYYYMMDD）
    if (onFormattedChange && newValue) {
      const formatted = newValue.replace(/-/g, '')
      onFormattedChange(formatted)
    }
  }

  // 获取今天的日期作为默认的最大值
  const getToday = () => {
    const today = new Date()
    return today.toISOString().split('T')[0]
  }

  // 获取一个月前的日期作为默认的最小值
  const getOneMonthAgo = () => {
    const date = new Date()
    date.setMonth(date.getMonth() - 1)
    return date.toISOString().split('T')[0]
  }

  return (
    <div className={cn('flex flex-col gap-1', className)}>
      {label && (
        <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      <div className="relative">
        <input
          type="date"
          value={localValue}
          onChange={handleChange}
          disabled={disabled}
          max={max || getToday()}
          min={min || getOneMonthAgo()}
          placeholder={placeholder}
          className={cn(
            'w-full px-3 py-2 pl-9',
            'border rounded-md',
            'bg-white dark:bg-gray-800',
            'border-gray-300 dark:border-gray-700',
            'focus:outline-none focus:ring-2 focus:ring-blue-500',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'text-sm',
            className
          )}
        />
        <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 pointer-events-none" />
      </div>
    </div>
  )
}

interface DateRangePickerProps {
  startDate?: string
  endDate?: string
  onStartChange?: (value: string) => void
  onEndChange?: (value: string) => void
  onFormattedStartChange?: (formatted: string) => void
  onFormattedEndChange?: (formatted: string) => void
  className?: string
  disabled?: boolean
  startLabel?: string
  endLabel?: string
  required?: boolean
}

export function DateRangePicker({
  startDate,
  endDate,
  onStartChange,
  onEndChange,
  onFormattedStartChange,
  onFormattedEndChange,
  className,
  disabled = false,
  startLabel = '开始日期',
  endLabel = '结束日期',
  required = false
}: DateRangePickerProps) {
  const handleStartChange = (value: string) => {
    if (onStartChange) onStartChange(value)
  }

  const handleEndChange = (value: string) => {
    if (onEndChange) onEndChange(value)
  }

  const handleFormattedStartChange = (formatted: string) => {
    if (onFormattedStartChange) onFormattedStartChange(formatted)
  }

  const handleFormattedEndChange = (formatted: string) => {
    if (onFormattedEndChange) onFormattedEndChange(formatted)
  }

  return (
    <div className={cn('flex flex-col sm:flex-row gap-4', className)}>
      <DatePicker
        value={startDate}
        onChange={handleStartChange}
        onFormattedChange={handleFormattedStartChange}
        label={startLabel}
        disabled={disabled}
        required={required}
        max={endDate}
        className="flex-1"
      />
      <DatePicker
        value={endDate}
        onChange={handleEndChange}
        onFormattedChange={handleFormattedEndChange}
        label={endLabel}
        disabled={disabled}
        required={required}
        min={startDate}
        className="flex-1"
      />
    </div>
  )
}

// 工具函数：格式化日期
export const formatDateToAPI = (date: string): string => {
  // YYYY-MM-DD -> YYYYMMDD
  return date.replace(/-/g, '')
}

export const formatDateFromAPI = (date: string): string => {
  // YYYYMMDD -> YYYY-MM-DD
  if (!date || date.length !== 8) return date
  return `${date.slice(0, 4)}-${date.slice(4, 6)}-${date.slice(6, 8)}`
}

// 工具函数：获取最近交易日
export const getLatestTradingDate = (): string => {
  const today = new Date()
  const day = today.getDay()

  // 如果是周末，回退到周五
  if (day === 0) { // 周日
    today.setDate(today.getDate() - 2)
  } else if (day === 6) { // 周六
    today.setDate(today.getDate() - 1)
  }

  // 如果是工作日但时间早于15:30，使用前一个交易日
  const hours = today.getHours()
  const minutes = today.getMinutes()
  if (day >= 1 && day <= 5) {
    if (hours < 15 || (hours === 15 && minutes < 30)) {
      today.setDate(today.getDate() - 1)
      // 如果回退后是周末，继续回退
      const newDay = today.getDay()
      if (newDay === 0) {
        today.setDate(today.getDate() - 2)
      } else if (newDay === 6) {
        today.setDate(today.getDate() - 1)
      }
    }
  }

  return today.toISOString().split('T')[0]
}

export default DatePicker