/**
 * 编辑用户对话框
 */
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { UserFormData } from '../hooks/useUserForm'

interface EditUserDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  formData: UserFormData
  setFormData: (data: UserFormData) => void
  onEdit: () => void
  onCancel: () => void
  isEditing: boolean
}

export function EditUserDialog({
  open,
  onOpenChange,
  formData,
  setFormData,
  onEdit,
  onCancel,
  isEditing,
}: EditUserDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>编辑用户</DialogTitle>
          <DialogDescription>
            修改用户信息。用户名不可修改。
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4 px-2 overflow-y-auto flex-1">
          <div className="space-y-2">
            <Label htmlFor="edit-username">用户名</Label>
            <Input
              id="edit-username"
              value={formData.username}
              disabled
              className="bg-gray-50"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="edit-email">邮箱</Label>
            <Input
              id="edit-email"
              type="email"
              placeholder="user@example.com"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="edit-password">新密码（留空表示不修改）</Label>
            <Input
              id="edit-password"
              type="password"
              placeholder="至少8位，含大小写字母和数字"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="edit-role">角色</Label>
            <Select
              value={formData.role}
              onValueChange={(value: any) => setFormData({ ...formData, role: value })}
            >
              <SelectTrigger id="edit-role">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="admin">管理员</SelectItem>
                <SelectItem value="user">普通用户</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter className="flex-row gap-2">
          <Button
            variant="outline"
            onClick={onCancel}
            disabled={isEditing}
            className="flex-1"
          >
            取消
          </Button>
          <Button
            onClick={onEdit}
            disabled={isEditing}
            className="flex-1"
          >
            {isEditing ? '保存中...' : '保存'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
