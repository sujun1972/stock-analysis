/**
 * 用户详情对话框
 */
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Pencil } from 'lucide-react'
import type { User } from '@/hooks/queries/use-users'
import { getRoleBadge } from './UserTableColumns'

interface UserDetailDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  user: User | null
  onEdit: () => void
  onClose: () => void
}

/**
 * 格式化日期为本地时间字符串
 */
function formatDate(dateString: string) {
  return new Date(dateString).toLocaleString('zh-CN')
}

export function UserDetailDialog({
  open,
  onOpenChange,
  user,
  onEdit,
  onClose,
}: UserDetailDialogProps) {
  if (!user) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>用户详情</DialogTitle>
          <DialogDescription>
            查看用户的完整信息
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-6 py-4 overflow-y-auto flex-1">
          {/* 基本信息 */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-900 border-b pb-2">基本信息</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label className="text-xs text-gray-500">用户ID</Label>
                <div className="mt-1 font-mono text-sm">{user.id}</div>
              </div>
              <div>
                <Label className="text-xs text-gray-500">用户名</Label>
                <div className="mt-1 font-medium text-sm">{user.username}</div>
              </div>
              <div>
                <Label className="text-xs text-gray-500">邮箱</Label>
                <div className="mt-1 text-sm break-all">{user.email}</div>
              </div>
              <div>
                <Label className="text-xs text-gray-500">角色</Label>
                <div className="mt-1">{getRoleBadge(user.role)}</div>
              </div>
              <div>
                <Label className="text-xs text-gray-500">账号状态</Label>
                <div className="mt-1">
                  {user.is_active ? (
                    <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                      活跃
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="bg-gray-50 text-gray-700 border-gray-200">
                      禁用
                    </Badge>
                  )}
                </div>
              </div>
              <div>
                <Label className="text-xs text-gray-500">邮箱验证</Label>
                <div className="mt-1">
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
              </div>
            </div>
          </div>

          {/* 配额信息 */}
          {user.quota && (
            <div className="space-y-4">
              <h3 className="text-sm font-semibold text-gray-900 border-b pb-2">配额使用情况</h3>
              <div className="bg-gray-50 rounded-lg p-4">
                <Label className="text-xs text-gray-500">配额使用情况</Label>
                <div className="mt-2 space-y-3">
                  <div className="space-y-2">
                    <div className="flex justify-between items-baseline">
                      <span className="text-sm text-gray-600">回测配额</span>
                      <span className="text-sm font-semibold">
                        {user.quota.backtest_quota_used || 0}/{user.quota.backtest_quota_total || 0}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-blue-500 h-2 rounded-full"
                        style={{
                          width: `${Math.min(((user.quota.backtest_quota_used || 0) / (user.quota.backtest_quota_total || 1)) * 100, 100)}%`
                        }}
                      ></div>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between items-baseline">
                      <span className="text-sm text-gray-600">预测配额</span>
                      <span className="text-sm font-semibold">
                        {user.quota.ml_prediction_quota_used || 0}/{user.quota.ml_prediction_quota_total || 0}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-green-500 h-2 rounded-full"
                        style={{
                          width: `${Math.min(((user.quota.ml_prediction_quota_used || 0) / (user.quota.ml_prediction_quota_total || 1)) * 100, 100)}%`
                        }}
                      ></div>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between items-baseline">
                      <span className="text-sm text-gray-600">策略数量</span>
                      <span className="text-sm font-semibold">
                        {user.quota.current_strategies || 0}/{user.quota.max_strategies || 0}
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className="bg-purple-500 h-2 rounded-full"
                        style={{
                          width: `${Math.min(((user.quota.current_strategies || 0) / (user.quota.max_strategies || 1)) * 100, 100)}%`
                        }}
                      ></div>
                    </div>
                  </div>
                  <div className="text-xs text-gray-500 mt-2">
                    {user.quota.backtest_quota_reset_at && (
                      <div>回测配额重置: {new Date(user.quota.backtest_quota_reset_at).toLocaleString('zh-CN')}</div>
                    )}
                    {user.quota.ml_prediction_quota_reset_at && (
                      <div>预测配额重置: {new Date(user.quota.ml_prediction_quota_reset_at).toLocaleString('zh-CN')}</div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 时间信息 */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-900 border-b pb-2">时间信息</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <Label className="text-xs text-gray-500">创建时间</Label>
                <div className="mt-1 text-sm">{formatDate(user.created_at)}</div>
              </div>
              <div>
                <Label className="text-xs text-gray-500">更��时间</Label>
                <div className="mt-1 text-sm">{formatDate(user.updated_at)}</div>
              </div>
              {user.last_login_at && (
                <div>
                  <Label className="text-xs text-gray-500">最后登录</Label>
                  <div className="mt-1 text-sm">{formatDate(user.last_login_at)}</div>
                </div>
              )}
            </div>
          </div>
        </div>
        <DialogFooter className="gap-2">
          <Button
            variant="outline"
            onClick={onClose}
            className="w-full sm:w-auto"
          >
            关闭
          </Button>
          <Button
            onClick={onEdit}
            className="w-full sm:w-auto"
          >
            <Pencil className="mr-2 h-4 w-4" />
            编辑用户
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
