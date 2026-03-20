/**
 * 删除用户确认对话框
 */
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { User } from '@/hooks/queries/use-users'

interface DeleteUserDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  user: User | null
  onDelete: () => void
  onCancel: () => void
  isDeleting: boolean
}

export function DeleteUserDialog({
  open,
  onOpenChange,
  user,
  onDelete,
  onCancel,
  isDeleting,
}: DeleteUserDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>确认删除用户？</DialogTitle>
          <DialogDescription className="space-y-2">
            <span className="block">
              您即将删除用户 <span className="font-semibold">{user?.username}</span>
            </span>
            <span className="block text-sm break-all">({user?.email})</span>
            <span className="block text-red-600 font-medium mt-2">
              此操作无法撤销，请谨慎操作。
            </span>
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            onClick={onCancel}
            disabled={isDeleting}
            className="w-full sm:w-auto"
          >
            取消
          </Button>
          <Button
            onClick={onDelete}
            disabled={isDeleting}
            className="bg-red-600 hover:bg-red-700 w-full sm:w-auto"
          >
            {isDeleting ? '删除中...' : '确认删除'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
