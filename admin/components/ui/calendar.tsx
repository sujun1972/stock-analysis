"use client"

import * as React from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { DayPicker } from "react-day-picker"

import { cn } from "@/lib/utils"
import { buttonVariants } from "@/components/ui/button"

export type CalendarProps = React.ComponentProps<typeof DayPicker>

/**
 * Calendar 日历组件
 *
 * 基于 react-day-picker v9 构建
 * 注意: v9 版本的 classNames API 与 v8 不同，使用新的命名约定
 *
 * @example
 * <Calendar
 *   mode="single"
 *   selected={date}
 *   onSelect={setDate}
 *   locale={zhCN}
 * />
 */
function Calendar({
  className,
  classNames,
  showOutsideDays = true,
  ...props
}: CalendarProps) {
  return (
    <DayPicker
      showOutsideDays={showOutsideDays}
      className={cn("p-3", className)}
      classNames={{
        // react-day-picker v9 API 变更
        // v8 -> v9 映射:
        // caption -> month_caption
        // nav_button -> button_previous/button_next
        // table -> month_grid
        // head_row -> weekdays
        // head_cell -> weekday
        // row -> week
        // day_selected -> selected
        // day_today -> today
        root: "rdp-root",
        // months 容器加 relative 让 nav 的 absolute 定位以它为锚（v9 中 nav 与 month_caption
        // 是兄弟节点，不再嵌套在 caption 内）
        months: "relative flex flex-col sm:flex-row space-y-4 sm:space-x-4 sm:space-y-0",
        month: "space-y-4",
        month_caption: "flex justify-center pt-1 items-center",
        caption_label: "text-sm font-medium",
        // nav 浮于 month_caption 同高度的左右两端；不再让单个按钮各自 absolute，
        // 否则按钮会被定位到整个 calendar 的边缘从而压住第一/最后一列日期格子
        nav: "absolute top-1 inset-x-1 flex items-center justify-between pointer-events-none z-10",
        button_previous: cn(
          buttonVariants({ variant: "outline" }),
          "h-7 w-7 bg-transparent p-0 opacity-50 hover:opacity-100 pointer-events-auto"
        ),
        button_next: cn(
          buttonVariants({ variant: "outline" }),
          "h-7 w-7 bg-transparent p-0 opacity-50 hover:opacity-100 pointer-events-auto"
        ),
        month_grid: "w-full border-collapse space-y-1",
        weekdays: "flex",
        weekday: "text-muted-foreground rounded-md w-9 font-normal text-[0.8rem]",
        week: "flex w-full mt-2",
        day: cn(
          buttonVariants({ variant: "ghost" }),
          "h-9 w-9 p-0 font-normal aria-selected:opacity-100"
        ),
        day_button: "h-9 w-9 p-0 font-normal",
        selected:
          "bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground focus:bg-primary focus:text-primary-foreground",
        today: "bg-accent text-accent-foreground",
        outside:
          "day-outside text-muted-foreground opacity-50 aria-selected:bg-accent/50 aria-selected:text-muted-foreground aria-selected:opacity-30",
        disabled: "text-muted-foreground opacity-50",
        range_middle:
          "aria-selected:bg-accent aria-selected:text-accent-foreground",
        hidden: "invisible",
        ...classNames,
      }}
      components={{
        Chevron: ({ orientation }) => {
          const Icon = orientation === 'left' ? ChevronLeft : ChevronRight
          return <Icon className="h-4 w-4" />
        },
      }}
      {...props}
    />
  )
}
Calendar.displayName = "Calendar"

export { Calendar }
