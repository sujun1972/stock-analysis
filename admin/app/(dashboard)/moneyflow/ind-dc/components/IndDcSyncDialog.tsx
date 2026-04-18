'use client'

import { Button } from '@/components/ui/button'
import { DatePicker } from '@/components/ui/date-picker'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { RefreshCw } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface IndDcSyncDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  syncDate: Date | undefined
  onSyncDateChange: (date: Date | undefined) => void
  syncContentType: string
  onSyncContentTypeChange: (value: string) => void
  onConfirm: () => void
  syncing: boolean
}

export function IndDcSyncDialog({
  open,
  onOpenChange,
  syncDate,
  onSyncDateChange,
  syncContentType,
  onSyncContentTypeChange,
  onConfirm,
  syncing,
}: IndDcSyncDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle>同步板块资金流向数据</DialogTitle>
          <DialogDescription>
            选择同步日期和板块类型（日期留空则同步最新交易日；&ldquo;全部&rdquo;将依次提交行业/概念/地域三个任务，共消耗约 18000 积分）。
          </DialogDescription>
        </DialogHeader>
        <div className="py-4 space-y-4">
          <div>
            <label className="text-sm font-medium mb-2 block">交易日期（可选）</label>
            <DatePicker
              date={syncDate}
              onDateChange={onSyncDateChange}
              placeholder="留空同步最新交易日"
            />
          </div>
          <div>
            <label className="text-sm font-medium mb-2 block">板块类型</label>
            <Select value={syncContentType} onValueChange={onSyncContentTypeChange}>
              <SelectTrigger>
                <SelectValue placeholder="选择类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部（行业+概念+地域）</SelectItem>
                <SelectItem value="行业">行业</SelectItem>
                <SelectItem value="概念">概念</SelectItem>
                <SelectItem value="地域">地域</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={onConfirm} disabled={syncing}>
            {syncing ? (
              <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
            ) : '确认同步'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
