'use client'

import { useEffect, useState } from 'react'
import { useStockListStore } from '@/stores/stock-list-store'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import type { StockList } from '@/types'

interface RenameListDialogProps {
  open: boolean
  list: StockList | null
  onClose: () => void
}

export function RenameListDialog({ open, list, onClose }: RenameListDialogProps) {
  const { updateList } = useStockListStore()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [localError, setLocalError] = useState('')

  useEffect(() => {
    if (open && list) {
      setName(list.name)
      setDescription(list.description ?? '')
      setLocalError('')
    }
  }, [open, list])

  const handleConfirm = async () => {
    if (!list) return
    setLocalError('')
    setSubmitting(true)
    try {
      await updateList(list.id, name.trim(), description.trim() || undefined)
      onClose()
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string }
      setLocalError(e?.response?.data?.detail || e.message || '操作失败')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-[380px]">
        <DialogHeader>
          <DialogTitle>重命名列表</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 py-2">
          <div>
            <Label>列表名称</Label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={50}
              autoFocus
            />
          </div>
          <div>
            <Label>描述（可选）</Label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              maxLength={200}
              placeholder="为这个列表添加一段描述..."
            />
          </div>
          {localError && <p className="text-sm text-red-500">{localError}</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={submitting}>取消</Button>
          <Button onClick={handleConfirm} disabled={submitting || !name.trim()}>
            {submitting ? '保存中...' : '保存'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
