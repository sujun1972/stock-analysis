/**
 * 用户表格列定义
 */
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Crown, ShieldCheck, UserIcon } from 'lucide-react'
import type { User } from '@/hooks/queries/use-users'
import type { Column } from '@/components/common/DataTable'

/**
 * 渲染角色徽章
 * 根据不同角色显示不同颜色和图标
 */
export function getRoleBadge(role: string) {
  const config: Record<string, { label: string; variant: any; icon: any }> = {
    super_admin: { label: '超级管理员', variant: 'destructive', icon: Crown },
    admin: { label: '管理员', variant: 'default', icon: ShieldCheck },
    vip_user: { label: 'VIP用户', variant: 'secondary', icon: UserIcon },
    user: { label: '普通用户', variant: 'outline', icon: UserIcon },
    normal_user: { label: '普通用户', variant: 'outline', icon: UserIcon },
    trial_user: { label: '试用用户', variant: 'outline', icon: UserIcon },
  }

  const { label, variant, icon: Icon } = config[role] || config.user

  return (
    <Badge variant={variant} className="gap-1">
      <Icon className="h-3 w-3" />
      {label}
    </Badge>
  )
}

/**
 * 获取用户表格列定义
 */
export function getUserTableColumns(
  handleToggleStatus: (user: User) => void,
  isToggling: boolean
): Column<User>[] {
  return [
    {
      key: 'id',
      header: 'ID',
      cellClassName: 'font-mono text-sm',
      width: 80,
    },
    {
      key: 'username',
      header: '用户名',
      accessor: (user) => (
        <div className="font-medium">{user.username}</div>
      ),
    },
    {
      key: 'email',
      header: '邮箱',
      cellClassName: 'text-sm',
    },
    {
      key: 'role',
      header: '角色',
      accessor: (user) => getRoleBadge(user.role),
    },
    {
      key: 'is_active',
      header: '状态',
      accessor: (user) => (
        <Button
          variant="ghost"
          size="sm"
          onClick={(e) => {
            e.stopPropagation()
            handleToggleStatus(user)
          }}
          disabled={isToggling}
        >
          {user.is_active ? (
            <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
              活跃
            </Badge>
          ) : (
            <Badge variant="outline" className="bg-gray-50 text-gray-700 border-gray-200">
              禁用
            </Badge>
          )}
        </Button>
      ),
    },
    {
      key: 'is_email_verified',
      header: '邮箱验证',
      accessor: (user) => (
        user.is_email_verified ? (
          <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
            已验证
          </Badge>
        ) : (
          <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
            未验证
          </Badge>
        )
      ),
      hideOnMobile: true,
    },
  ]
}
