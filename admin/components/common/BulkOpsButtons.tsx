'use client'

/**
 * BulkOpsButtons
 *
 * 通用的"全量同步"和"清空数据"按钮组，配合 useDataBulkOps hook 使用。
 *
 * 用法：
 *   <BulkOpsButtons
 *     onFullSync={handleFullSync}
 *     onClearConfirm={handleClear}
 *     isClearDialogOpen={isClearDialogOpen}
 *     setIsClearDialogOpen={setIsClearDialogOpen}
 *     fullSyncing={fullSyncing}
 *     isClearing={isClearing}
 *     earliestHistoryDate={earliestHistoryDate}
 *     tableName="每日指标"
 *   />
 */

import { History, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

interface BulkOpsButtonsProps {
  onFullSync: () => void
  onClearConfirm: () => void
  isClearDialogOpen: boolean
  setIsClearDialogOpen: (open: boolean) => void
  fullSyncing?: boolean
  isClearing?: boolean
  earliestHistoryDate?: string
  /** 页面/表格的中文名称，用于弹窗提示文字 */
  tableName: string
}

export function BulkOpsButtons({
  onFullSync,
  onClearConfirm,
  isClearDialogOpen,
  setIsClearDialogOpen,
  fullSyncing = false,
  isClearing = false,
  earliestHistoryDate = '2021-01-04',
  tableName,
}: BulkOpsButtonsProps) {
  return (
    <>
      <Button
        onClick={onFullSync}
        disabled={fullSyncing}
        variant="outline"
        title={`从 ${earliestHistoryDate} 开始全量同步`}
      >
        <History className="h-4 w-4 mr-1" />
        {fullSyncing ? '全量同步中...' : '全量同步'}
      </Button>

      <Button
        onClick={() => setIsClearDialogOpen(true)}
        disabled={isClearing}
        variant="outline"
        className="text-red-600 border-red-300 hover:bg-red-50 hover:text-red-700 dark:text-red-400 dark:border-red-700 dark:hover:bg-red-950"
      >
        <Trash2 className="h-4 w-4 mr-1" />
        清空数据
      </Button>

      {/* 清空确认弹窗 */}
      <Dialog open={isClearDialogOpen} onOpenChange={setIsClearDialogOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>确认清空数据</DialogTitle>
            <DialogDescription>
              此操作将清空「{tableName}」表中的<strong>所有数据</strong>，且无法撤销。确定要继续吗？
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsClearDialogOpen(false)}>
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={onClearConfirm}
              disabled={isClearing}
            >
              {isClearing ? '清空中...' : '确认清空'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
