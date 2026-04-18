'use client'

import { Check } from 'lucide-react'
import { Strategy } from '@/types/strategy'
import type { User } from '@/app/(dashboard)/strategies/hooks/useStrategiesActions'
import { Button } from '@/components/ui/button'
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
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'

interface UserAssignDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  editingStrategy: Strategy | null
  selectedUserId: string
  onSelectedUserIdChange: (value: string) => void
  users: User[]
  loadingUsers: boolean
  updatingUser: boolean
  userSearchTerm: string
  onUserSearchTermChange: (value: string) => void
  onConfirm: () => void
}

export function UserAssignDialog({
  open,
  onOpenChange,
  editingStrategy,
  selectedUserId,
  onSelectedUserIdChange,
  users,
  loadingUsers,
  updatingUser,
  userSearchTerm,
  onUserSearchTermChange,
  onConfirm,
}: UserAssignDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>分配用户</DialogTitle>
          <DialogDescription>
            为策略「{editingStrategy?.display_name || editingStrategy?.name}」分配用户归属
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label>选择用户</Label>
            <Command className="rounded-lg border shadow-md">
              <CommandInput
                placeholder="搜索用户..."
                value={userSearchTerm}
                onValueChange={onUserSearchTermChange}
              />
              <CommandList>
                {loadingUsers ? (
                  <CommandEmpty>加载中...</CommandEmpty>
                ) : (
                  <>
                    <CommandEmpty>没有找到用户</CommandEmpty>
                    <CommandGroup>
                      <CommandItem
                        value=""
                        onSelect={() => onSelectedUserIdChange('')}
                        className="cursor-pointer"
                      >
                        <Check className={`mr-2 h-4 w-4 ${selectedUserId === '' ? 'opacity-100' : 'opacity-0'}`} />
                        系统策略（无用户归属）
                      </CommandItem>
                      {users.map((user) => (
                        <CommandItem
                          key={user.id}
                          value={user.id.toString()}
                          onSelect={() => onSelectedUserIdChange(user.id.toString())}
                          className="cursor-pointer"
                        >
                          <Check
                            className={`mr-2 h-4 w-4 ${
                              selectedUserId === user.id.toString() ? 'opacity-100' : 'opacity-0'
                            }`}
                          />
                          <div className="flex flex-col">
                            <span>{user.username}</span>
                            <span className="text-sm text-muted-foreground">{user.email}</span>
                          </div>
                        </CommandItem>
                      ))}
                    </CommandGroup>
                  </>
                )}
              </CommandList>
            </Command>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            取消
          </Button>
          <Button onClick={onConfirm} disabled={updatingUser}>
            {updatingUser ? '更新中...' : '确认'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
