/**
 * 用户移动端卡片组件
 */
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Pencil, Trash2 } from 'lucide-react'
import type { User } from '@/hooks/queries/use-users'
import { getRoleBadge } from './UserTableColumns'

interface UserMobileCardProps {
  user: User
  onEdit: (user: User) => void
  onDelete: (user: User) => void
}

/**
 * 格式化日期为本地时间字符串
 */
function formatDate(dateString: string) {
  return new Date(dateString).toLocaleString('zh-CN')
}

export function UserMobileCard({ user, onEdit, onDelete }: UserMobileCardProps) {
  return (
    <div className="border rounded-lg p-4 bg-white space-y-3">
      {/* 顶部：用户名和操作按钮 */}
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-base truncate">{user.username}</div>
        </div>
        <div className="flex gap-1 ml-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onEdit(user)}
            className="h-8 w-8 shrink-0"
          >
            <Pencil className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => onDelete(user)}
            className="h-8 w-8 text-red-600 hover:text-red-700 hover:bg-red-50 shrink-0"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* 邮箱 */}
      <div className="text-sm text-gray-600 break-all">{user.email}</div>

      {/* 徽章：角色、状态、邮箱验证 */}
      <div className="flex flex-wrap gap-2">
        {getRoleBadge(user.role)}
        {user.is_active ? (
          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
            活跃
          </Badge>
        ) : (
          <Badge variant="outline" className="bg-gray-50 text-gray-700 border-gray-200">
            禁用
          </Badge>
        )}
        {user.is_email_verified ? (
          <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
            已验证
          </Badge>
        ) : (
          <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200">
            未验证
          </Badge>
        )}
      </div>

      {/* 配额信息 */}
      {user.quota && (
        <div className="text-sm space-y-1 bg-gray-50 rounded p-2">
          <div className="font-medium text-gray-700">配额使用情况</div>
          <div className="text-xs text-gray-600">
            配额: {user.quota.backtest_quota_used}/{user.quota.backtest_quota_total}
          </div>
        </div>
      )}

      {/* 底部信息：ID、创建时间 */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-gray-500 pt-2 border-t">
        <div>ID: <span className="font-mono">{user.id}</span></div>
        <div className="w-full sm:w-auto">创建于: {formatDate(user.created_at)}</div>
      </div>
    </div>
  )
}
