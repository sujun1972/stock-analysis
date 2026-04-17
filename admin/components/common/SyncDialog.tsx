/**
 * SyncDialog — 数据同步确认弹窗（带可选日期范围选择）
 *
 * 从 70+ 数据页面中提取的公共同步弹窗组件。
 * 支持三种模式：
 * 1. 无参数同步（直接确认）
 * 2. 日期范围同步（startDate + endDate）
 * 3. 自定义内容（children）
 */

'use client'

import { Button } from '@/components/ui/button'
import { DatePicker } from '@/components/ui/date-picker'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { ReactNode } from 'react'

export interface SyncDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => void | Promise<void>
  title: string
  description?: string
  disabled?: boolean

  /** 是否显示日期范围选择器 */
  showDateRange?: boolean
  startDate?: Date | undefined
  onStartDateChange?: (d: Date | undefined) => void
  endDate?: Date | undefined
  onEndDateChange?: (d: Date | undefined) => void
  startDateLabel?: string
  endDateLabel?: string

  /** 自定义内容（替代日期选择器） */
  children?: ReactNode
}

export function SyncDialog({
  open,
  onOpenChange,
  onConfirm,
  title,
  description,
  disabled,
  showDateRange,
  startDate,
  onStartDateChange,
  endDate,
  onEndDateChange,
  startDateLabel = '开始日期',
  endDateLabel = '结束日期',
  children,
}: SyncDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          {description && <DialogDescription>{description}</DialogDescription>}
        </DialogHeader>

        {children}

        {showDateRange && !children && (
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>{startDateLabel}</Label>
              <DatePicker date={startDate} onDateChange={onStartDateChange} />
            </div>
            <div className="space-y-2">
              <Label>{endDateLabel}</Label>
              <DatePicker date={endDate} onDateChange={onEndDateChange} />
            </div>
            <p className="text-xs text-muted-foreground">
              不选择日期则使用默认范围（通常为增量同步最近数据）
            </p>
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={onConfirm} disabled={disabled}>
            确认同步
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
