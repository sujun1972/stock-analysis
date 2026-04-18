'use client'

import { useMemo, useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { Edit, Trash2, AlertCircle, Users, ClipboardList, Ban, MoreVertical, Info } from 'lucide-react'
import { Strategy } from '@/types/strategy'
import { DataTable, type Column } from '@/components/common/DataTable'
import PublishStatusBadge from '@/components/strategies/PublishStatusBadge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Switch } from '@/components/ui/switch'

// 策略类型标签颜色
const strategyTypeColors = {
  stock_selection: 'bg-blue-100 text-blue-800',
  entry: 'bg-green-100 text-green-800',
  exit: 'bg-red-100 text-red-800',
}

// 策略类型显示名称
const strategyTypeNames = {
  stock_selection: '选股策略',
  entry: '入场策略',
  exit: '离场策略',
}

// 来源类型标签颜色
const sourceTypeColors = {
  builtin: 'bg-gray-100 text-gray-800',
  ai: 'bg-purple-100 text-purple-800',
  custom: 'bg-yellow-100 text-yellow-800',
}

// 来源类型显示名称
const sourceTypeNames = {
  builtin: '系统内置',
  ai: 'AI生成',
  custom: '用户自定义',
}

// 验证状态标签颜色
const validationStatusColors = {
  pending: 'bg-gray-100 text-gray-800',
  passed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  validating: 'bg-yellow-100 text-yellow-800',
}

// 风险等级标签颜色
const riskLevelColors = {
  safe: 'bg-green-100 text-green-800',
  low: 'bg-blue-100 text-blue-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-red-100 text-red-800',
}

interface StrategyTableProps {
  strategies: Strategy[]
  loading: boolean
  currentPage: number
  pageSize: number
  totalCount: number
  onPageChange: (page: number) => void
  onToggleStatus: (strategy: Strategy) => void
  onOpenDetail: (strategy: Strategy) => void
  onOpenEditUser: (strategy: Strategy) => void
  onOpenDelete: (strategy: Strategy) => void
  onUnpublish: (strategy: Strategy) => void
}

export function StrategyTable({
  strategies,
  loading,
  currentPage,
  pageSize,
  totalCount,
  onPageChange,
  onToggleStatus,
  onOpenDetail,
  onOpenEditUser,
  onOpenDelete,
  onUnpublish,
}: StrategyTableProps) {
  const router = useRouter()

  // 定义表格列
  const columns: Column<Strategy>[] = useMemo(() => [
    {
      key: 'name',
      header: '策略名称',
      accessor: (strategy) => (
        <div className="space-y-1">
          <div className="font-medium">{strategy.display_name || strategy.name}</div>
          {strategy.description && (
            <div className="text-xs text-muted-foreground truncate max-w-xs">
              {strategy.description}
            </div>
          )}
        </div>
      ),
    },
    {
      key: 'type',
      header: '类型',
      accessor: (strategy) => (
        <div className="flex flex-col gap-1">
          <Badge className={strategyTypeColors[strategy.strategy_type as keyof typeof strategyTypeColors] || 'bg-gray-100 text-gray-800'}>
            {strategyTypeNames[strategy.strategy_type as keyof typeof strategyTypeNames] || strategy.strategy_type}
          </Badge>
          <Badge className={sourceTypeColors[strategy.source_type as keyof typeof sourceTypeColors] || 'bg-gray-100 text-gray-800'}>
            {sourceTypeNames[strategy.source_type as keyof typeof sourceTypeNames] || strategy.source_type}
          </Badge>
        </div>
      ),
      hideOnMobile: true,
    },
    {
      key: 'user',
      header: '用户',
      accessor: (strategy) => (
        <div className="text-sm">
          {strategy.username || (strategy.user_id ? `用户#${strategy.user_id}` : '系统')}
        </div>
      ),
      hideOnMobile: true,
    },
    {
      key: 'validation',
      header: '验证状态',
      accessor: (strategy) => (
        <Badge className={validationStatusColors[strategy.validation_status as keyof typeof validationStatusColors] || 'bg-gray-100 text-gray-800'}>
          {strategy.validation_status === 'pending' && '待验证'}
          {strategy.validation_status === 'passed' && '已通过'}
          {strategy.validation_status === 'failed' && '未通过'}
          {strategy.validation_status === 'validating' && '验证中'}
        </Badge>
      ),
    },
    {
      key: 'risk',
      header: '风险等级',
      accessor: (strategy) => (
        <Badge className={riskLevelColors[strategy.risk_level as keyof typeof riskLevelColors] || 'bg-gray-100 text-gray-800'}>
          {strategy.risk_level || '未知'}
        </Badge>
      ),
      hideOnMobile: true,
    },
    {
      key: 'publish',
      header: '发布状态',
      accessor: (strategy) => <PublishStatusBadge status={strategy.publish_status || 'draft'} />,
    },
    {
      key: 'enabled',
      header: '启用状态',
      accessor: (strategy) => (
        <Switch
          checked={strategy.is_enabled}
          onCheckedChange={() => onToggleStatus(strategy)}
          className="data-[state=checked]:bg-green-600"
        />
      ),
    },
  ], [onToggleStatus])

  // 操作列
  const actions = useCallback((strategy: Strategy) => (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <MoreVertical className="h-4 w-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => onOpenDetail(strategy)}>
          <Info className="mr-2 h-4 w-4" />
          查看详情
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push(`/strategies/edit/${strategy.id}`)}>
          <Edit className="mr-2 h-4 w-4" />
          编辑
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => router.push(`/strategies/validate/${strategy.id}`)}>
          <AlertCircle className="mr-2 h-4 w-4" />
          验证
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => onOpenEditUser(strategy)}>
          <Users className="mr-2 h-4 w-4" />
          分配用户
        </DropdownMenuItem>
        {strategy.publish_status !== 'approved' && (
          <DropdownMenuItem onClick={() => router.push(`/strategies/publish/${strategy.id}`)}>
            <ClipboardList className="mr-2 h-4 w-4" />
            发布管理
          </DropdownMenuItem>
        )}
        {strategy.publish_status === 'approved' && (
          <DropdownMenuItem onClick={() => onUnpublish(strategy)}>
            <Ban className="mr-2 h-4 w-4" />
            取消发布
          </DropdownMenuItem>
        )}
        <DropdownMenuItem
          onClick={() => onOpenDelete(strategy)}
          className="text-red-600"
        >
          <Trash2 className="mr-2 h-4 w-4" />
          删除
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  ), [router, onOpenDetail, onOpenEditUser, onOpenDelete, onUnpublish])

  return (
    <Card>
      <CardHeader>
        <CardTitle>策略列表</CardTitle>
        <CardDescription>
          共 {totalCount} 个策略
        </CardDescription>
      </CardHeader>
      <CardContent>
        <DataTable
          data={strategies}
          columns={columns}
          loading={loading}
          emptyMessage="暂无策略数据"
          loadingMessage="加载中..."
          pagination={{
            page: currentPage,
            pageSize,
            total: totalCount,
            onPageChange,
          }}
          actions={actions}
          mobileCard={(strategy) => (
            <StrategyMobileCard
              strategy={strategy}
              onToggleStatus={onToggleStatus}
              onOpenDetail={onOpenDetail}
              onOpenEditUser={onOpenEditUser}
              onOpenDelete={onOpenDelete}
              onUnpublish={onUnpublish}
            />
          )}
          rowKey={(strategy) => strategy.id}
        />
      </CardContent>
    </Card>
  )
}

// 移动端卡片内联组件
function StrategyMobileCard({
  strategy,
  onToggleStatus,
  onOpenDetail,
  onOpenEditUser,
  onOpenDelete,
  onUnpublish,
}: {
  strategy: Strategy
  onToggleStatus: (strategy: Strategy) => void
  onOpenDetail: (strategy: Strategy) => void
  onOpenEditUser: (strategy: Strategy) => void
  onOpenDelete: (strategy: Strategy) => void
  onUnpublish: (strategy: Strategy) => void
}) {
  const router = useRouter()

  return (
    <div className="border rounded-lg p-4 bg-white space-y-3">
      {/* 策略名称和操作 */}
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-base">{strategy.display_name || strategy.name}</div>
          {strategy.description && (
            <div className="text-sm text-gray-500 mt-1">{strategy.description}</div>
          )}
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="shrink-0">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onOpenDetail(strategy)}>
              <Info className="mr-2 h-4 w-4" />
              查看详情
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push(`/strategies/edit/${strategy.id}`)}>
              <Edit className="mr-2 h-4 w-4" />
              编辑
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => router.push(`/strategies/validate/${strategy.id}`)}>
              <AlertCircle className="mr-2 h-4 w-4" />
              验证
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => onOpenEditUser(strategy)}>
              <Users className="mr-2 h-4 w-4" />
              分配用户
            </DropdownMenuItem>
            {strategy.publish_status !== 'approved' && (
              <DropdownMenuItem onClick={() => router.push(`/strategies/publish/${strategy.id}`)}>
                <ClipboardList className="mr-2 h-4 w-4" />
                发布管理
              </DropdownMenuItem>
            )}
            {strategy.publish_status === 'approved' && (
              <DropdownMenuItem onClick={() => onUnpublish(strategy)}>
                <Ban className="mr-2 h-4 w-4" />
                取消发布
              </DropdownMenuItem>
            )}
            <DropdownMenuItem
              onClick={() => onOpenDelete(strategy)}
              className="text-red-600"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              删除
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* 类型和状态标签 */}
      <div className="flex flex-wrap gap-2">
        <Badge className={strategyTypeColors[strategy.strategy_type as keyof typeof strategyTypeColors] || 'bg-gray-100 text-gray-800'}>
          {strategyTypeNames[strategy.strategy_type as keyof typeof strategyTypeNames] || strategy.strategy_type}
        </Badge>
        <Badge className={sourceTypeColors[strategy.source_type as keyof typeof sourceTypeColors] || 'bg-gray-100 text-gray-800'}>
          {sourceTypeNames[strategy.source_type as keyof typeof sourceTypeNames] || strategy.source_type}
        </Badge>
        <PublishStatusBadge status={strategy.publish_status || 'draft'} />
      </div>

      {/* 验证和风险信息 */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          <Badge className={validationStatusColors[strategy.validation_status as keyof typeof validationStatusColors] || 'bg-gray-100 text-gray-800'}>
            {strategy.validation_status === 'pending' && '待验证'}
            {strategy.validation_status === 'passed' && '已通过'}
            {strategy.validation_status === 'failed' && '未通过'}
            {strategy.validation_status === 'validating' && '验证中'}
          </Badge>
          <Badge className={riskLevelColors[strategy.risk_level as keyof typeof riskLevelColors] || 'bg-gray-100 text-gray-800'}>
            风险: {strategy.risk_level || '未知'}
          </Badge>
        </div>
        <Switch
          checked={strategy.is_enabled}
          onCheckedChange={() => onToggleStatus(strategy)}
          className="data-[state=checked]:bg-green-600"
        />
      </div>

      {/* 用户信息 */}
      <div className="text-sm text-gray-500 pt-2 border-t">
        用户: {strategy.username || (strategy.user_id ? `用户#${strategy.user_id}` : '系统')}
      </div>
    </div>
  )
}
