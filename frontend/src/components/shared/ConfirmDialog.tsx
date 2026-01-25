/**
 * 确认对话框组件
 * 用于确认删除等危险操作的通用对话框
 */

'use client';

import { memo, ReactNode } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';

export type ConfirmDialogVariant = 'default' | 'destructive';

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onConfirm: () => void;
  title: string;
  description: string | ReactNode;
  confirmText?: string;
  cancelText?: string;
  variant?: ConfirmDialogVariant;
  showWarning?: boolean;
  warningTitle?: string;
  warningMessage?: string;
  isLoading?: boolean;
}

const ConfirmDialog = memo(function ConfirmDialog({
  open,
  onOpenChange,
  onConfirm,
  title,
  description,
  confirmText = '确认',
  cancelText = '取消',
  variant = 'default',
  showWarning = false,
  warningTitle = '警告',
  warningMessage,
  isLoading = false
}: ConfirmDialogProps) {
  const handleConfirm = () => {
    onConfirm();
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle className={variant === 'destructive' ? 'flex items-center gap-2' : ''}>
            {variant === 'destructive' && (
              <AlertCircle className="h-5 w-5 text-red-500" />
            )}
            {title}
          </DialogTitle>
          <DialogDescription>
            {description}
          </DialogDescription>
        </DialogHeader>

        {showWarning && warningMessage && (
          <div className="py-4">
            <Alert variant={variant}>
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>{warningTitle}</AlertTitle>
              <AlertDescription>
                {warningMessage}
              </AlertDescription>
            </Alert>
          </div>
        )}

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={isLoading}
          >
            {cancelText}
          </Button>
          <Button
            variant={variant}
            onClick={handleConfirm}
            disabled={isLoading}
          >
            {isLoading ? '处理中...' : confirmText}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
});

ConfirmDialog.displayName = 'ConfirmDialog';

export default ConfirmDialog;
