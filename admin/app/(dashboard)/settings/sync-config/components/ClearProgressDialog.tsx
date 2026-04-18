'use client'

import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle
} from '@/components/ui/dialog'
import type { SyncOverviewItem } from '@/lib/api/sync-dashboard'

export function ClearProgressDialog({
  item,
  onClose,
  onConfirm,
}: {
  item: SyncOverviewItem | null
  onClose: () => void
  onConfirm: () => void
}) {
  return (
    <Dialog open={!!item} onOpenChange={() => onClose()}>
      <DialogContent className="sm:max-w-[400px]">
        <DialogHeader>
          <DialogTitle>清除全量同步进度</DialogTitle>
          <DialogDescription>
            确定要清除 <strong>{item?.display_name}</strong> 的 Redis 续继进度吗？
            清除后下次全量同步将从头开始。
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>取消</Button>
          <Button variant="destructive" onClick={onConfirm}>确认清除</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
