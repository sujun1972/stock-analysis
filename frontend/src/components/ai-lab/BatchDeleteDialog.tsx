/**
 * 批量删除确认对话框组件
 */

'use client';

import { memo } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { AlertCircle } from 'lucide-react';

interface BatchDeleteDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  selectedCount: number;
  onConfirm: () => void;
}

const BatchDeleteDialog = memo(function BatchDeleteDialog({
  open,
  onOpenChange,
  selectedCount,
  onConfirm
}: BatchDeleteDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <AlertCircle className="h-5 w-5 text-red-500" />
            确认批量删除
          </DialogTitle>
          <DialogDescription>
            您确定要删除选中的 {selectedCount} 个模型吗？此操作无法撤销。
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button variant="destructive" onClick={onConfirm}>
            确认删除
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
});

export default BatchDeleteDialog;
