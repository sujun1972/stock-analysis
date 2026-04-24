'use client'

import { useEffect, useState } from 'react'
import { useStockListStore } from '@/stores/stock-list-store'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from '@/components/ui/dialog'

interface AddToListDialogProps {
  open: boolean
  onClose: () => void
  selectedCodes: string[]
  onSuccess: () => void
}

export function AddToListDialog({ open, onClose, selectedCodes, onSuccess }: AddToListDialogProps) {
  const { lists, createList, addStocks } = useStockListStore()
  const [mode, setMode] = useState<'new' | 'existing'>('existing')
  const [newName, setNewName] = useState('')
  const [selectedListId, setSelectedListId] = useState<number | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [localError, setLocalError] = useState('')

  useEffect(() => {
    if (open) {
      setMode(lists.length === 0 ? 'new' : 'existing')
      setSelectedListId(lists.length > 0 ? lists[0].id : null)
      setNewName('')
      setLocalError('')
    }
  }, [open, lists])

  const handleConfirm = async () => {
    if (selectedCodes.length === 0) return
    setLocalError('')
    setSubmitting(true)
    try {
      let targetListId = selectedListId
      if (mode === 'new') {
        if (!newName.trim()) { setLocalError('请输入列表名称'); setSubmitting(false); return }
        const created = await createList(newName.trim())
        targetListId = created.id
      }
      if (!targetListId) { setLocalError('请选择目标列表'); setSubmitting(false); return }
      await addStocks(targetListId, selectedCodes)
      onSuccess()
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
      <DialogContent className="sm:max-w-[420px]">
        <DialogHeader>
          <DialogTitle>添加 {selectedCodes.length} 只股票到列表</DialogTitle>
          <DialogDescription>选择目标列表，或创建一个新列表</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="flex gap-3">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                checked={mode === 'existing'}
                onChange={() => setMode('existing')}
                disabled={lists.length === 0}
                className="accent-blue-600"
              />
              <span className={lists.length === 0 ? 'text-gray-400 dark:text-gray-600' : ''}>追加到已有列表</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                checked={mode === 'new'}
                onChange={() => setMode('new')}
                className="accent-blue-600"
              />
              <span>新建列表</span>
            </label>
          </div>

          {mode === 'existing' ? (
            <Select
              value={selectedListId?.toString() ?? ''}
              onValueChange={(v) => setSelectedListId(Number(v))}
            >
              <SelectTrigger>
                <SelectValue placeholder="选择列表..." />
              </SelectTrigger>
              <SelectContent>
                {lists.map((l) => (
                  <SelectItem key={l.id} value={l.id.toString()}>
                    {l.name}（{l.stock_count} 只）
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <Input
              placeholder="新列表名称（最多50个字符）"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              maxLength={50}
              autoFocus
            />
          )}

          {localError && (
            <p className="text-sm text-red-500">{localError}</p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={submitting}>取消</Button>
          <Button onClick={handleConfirm} disabled={submitting}>
            {submitting ? '处理中...' : '确认添加'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
