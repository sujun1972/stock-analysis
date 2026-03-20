/**
 * 创建用户对话框
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

interface CreateUserDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  formData: UserFormData
  setFormData: (data: UserFormData) => void
  onCreate: () => void
  onCancel: () => void
  isCreating: boolean
}

export function CreateUserDialog({
  open,
  onOpenChange,
  formData,
  setFormData,
  onCreate,
  onCancel,
  isCreating,
}: CreateUserDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>创建新用户</DialogTitle>
          <DialogDescription>
            填写用户的基本信息。密码需要至少8位，包含大小写字母和数字。
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4 px-2 overflow-y-auto flex-1">
          <div className="space-y-2">
            <Label htmlFor="create-email">
              邮箱 <span className="text-red-500">*</span>
            </Label>
            <Input
              id="create-email"
              type="email"
              placeholder="user@example.com"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="create-username">
              用户名 <span className="text-red-500">*</span>
            </Label>
            <Input
              id="create-username"
              placeholder="输入用户名"
              value={formData.username}
              onChange={(e) => setFormData({ ...formData, username: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="create-password">
              密码 <span className="text-red-500">*</span>
            </Label>
            <Input
              id="create-password"
              type="password"
              placeholder="至少8位，含大小写字母和数字"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="create-role">角色</Label>
            <Select
              value={formData.role}
              onValueChange={(value: any) => setFormData({ ...formData, role: value })}
            >
              <SelectTrigger id="create-role">
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
            disabled={isCreating}
            className="flex-1"
          >
            取消
          </Button>
          <Button
            onClick={onCreate}
            disabled={isCreating}
            className="flex-1"
          >
            {isCreating ? '创建中...' : '创建'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
