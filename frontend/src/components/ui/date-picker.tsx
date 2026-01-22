"use client"

import * as React from "react"
import { format } from "date-fns"
import { zhCN } from "date-fns/locale"
import { Calendar as CalendarIcon } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"

interface DatePickerProps {
  /** 当前选中的日期 */
  date?: Date
  /** 日期变化时的回调函数 */
  onDateChange?: (date: Date | undefined) => void
  /** 未选中日期时的占位文本 */
  placeholder?: string
  /** 是否禁用选择器 */
  disabled?: boolean
  /** 自定义样式类名 */
  className?: string
}

/**
 * 日期选择器组件
 * 基于 react-day-picker 和 Shadcn/ui 构建，支持中文日历
 * 点击按钮后弹出日历面板进行日期选择
 */
export function DatePicker({
  date,
  onDateChange,
  placeholder = "选择日期",
  disabled = false,
  className,
}: DatePickerProps) {
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          variant={"outline"}
          disabled={disabled}
          className={cn(
            "w-full justify-start text-left font-normal",
            !date && "text-muted-foreground",
            className
          )}
        >
          <CalendarIcon className="mr-2 h-4 w-4" />
          {date ? format(date, "yyyy-MM-dd", { locale: zhCN }) : <span>{placeholder}</span>}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0">
        <Calendar
          mode="single"
          selected={date}
          onSelect={onDateChange}
          defaultMonth={date} // 日历默认打开到选中日期所在月份
          initialFocus
          locale={zhCN} // 使用中文本地化
        />
      </PopoverContent>
    </Popover>
  )
}
