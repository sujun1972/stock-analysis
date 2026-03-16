/**
 * 策略表格行组件
 * 使用 React.memo 优化，避免不必要的重渲染
 */

import React from 'react'
import { useRouter } from 'next/navigation'
import { Edit, Trash2, Code, Users, Info, MoreVertical, Ban } from 'lucide-react'
import { Strategy } from '@/types/strategy'
import PublishStatusBadge from '@/components/strategies/PublishStatusBadge'
import { Switch } from '@/components/ui/switch'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

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
  high: 'bg-orange-100 text-orange-800',
  extreme: 'bg-red-100 text-red-800',
  unknown: 'bg-gray-100 text-gray-800',
}

// 风险等级显示名称
const riskLevelNames = {
  safe: '安全',
  low: '低风险',
  medium: '中风险',
  high: '高风险',
  extreme: '极高风险',
  unknown: '未知',
}

interface StrategyTableRowProps {
  strategy: Strategy
  onToggleEnabled: (id: number, enabled: boolean) => void
  onView: (strategy: Strategy) => void
  onEdit: (id: number) => void
  onValidate: (id: number) => void
  onAssign: (strategy: Strategy) => void
  onPublishChange: (strategy: Strategy) => void
  onDelete: (id: number, name: string) => void
}

export const StrategyTableRow = React.memo<StrategyTableRowProps>(
  ({
    strategy,
    onToggleEnabled,
    onView,
    onEdit,
    onValidate,
    onAssign,
    onPublishChange,
    onDelete,
  }) => {
    const router = useRouter()

    return (
      <tr className="hover:bg-gray-50 transition-colors">
        <td className="px-6 py-4 whitespace-nowrap">
          <div className="flex items-center">
            <div>
              <div className="font-medium text-gray-900">{strategy.name}</div>
              {strategy.description && (
                <div className="text-sm text-gray-500 max-w-md truncate">
                  {strategy.description}
                </div>
              )}
            </div>
          </div>
        </td>
        <td className="px-6 py-4 whitespace-nowrap">
          <span
            className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
              strategyTypeColors[strategy.strategy_type as keyof typeof strategyTypeColors]
            }`}
          >
            {strategyTypeNames[strategy.strategy_type as keyof typeof strategyTypeNames]}
          </span>
        </td>
        <td className="px-6 py-4 whitespace-nowrap">
          <span
            className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
              sourceTypeColors[strategy.source_type as keyof typeof sourceTypeColors]
            }`}
          >
            {sourceTypeNames[strategy.source_type as keyof typeof sourceTypeNames]}
          </span>
        </td>
        <td className="px-6 py-4 whitespace-nowrap">
          <span
            className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
              validationStatusColors[
                strategy.validation_status as keyof typeof validationStatusColors
              ]
            }`}
          >
            {strategy.validation_status === 'pending' && '待验证'}
            {strategy.validation_status === 'passed' && '已通过'}
            {strategy.validation_status === 'failed' && '验证失败'}
            {strategy.validation_status === 'validating' && '验证中'}
          </span>
        </td>
        <td className="px-6 py-4 whitespace-nowrap">
          <span
            className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
              riskLevelColors[strategy.risk_level as keyof typeof riskLevelColors]
            }`}
          >
            {riskLevelNames[strategy.risk_level as keyof typeof riskLevelNames] ||
              '未知'}
          </span>
        </td>
        <td className="px-6 py-4 whitespace-nowrap">
          <PublishStatusBadge status={strategy.publish_status || 'draft'} />
        </td>
        <td className="px-6 py-4 whitespace-nowrap">
          <Switch
            checked={strategy.is_enabled}
            onCheckedChange={(checked) => onToggleEnabled(strategy.id, checked)}
          />
        </td>
        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
          <div className="flex items-center justify-end gap-2">
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                  <MoreVertical className="h-4 w-4" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => onView(strategy)}>
                  <Info className="mr-2 h-4 w-4" />
                  查看详情
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onEdit(strategy.id)}>
                  <Edit className="mr-2 h-4 w-4" />
                  编辑
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onValidate(strategy.id)}>
                  <Code className="mr-2 h-4 w-4" />
                  验证代码
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onAssign(strategy)}>
                  <Users className="mr-2 h-4 w-4" />
                  分配用户
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onPublishChange(strategy)}>
                  <Ban className="mr-2 h-4 w-4" />
                  发布管理
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => onDelete(strategy.id, strategy.name)}
                  className="text-red-600"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  删除
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </td>
      </tr>
    )
  },
  (prevProps, nextProps) => {
    // 自定义比较函数，只在相关属性变化时重新渲染
    return (
      prevProps.strategy.id === nextProps.strategy.id &&
      prevProps.strategy.is_enabled === nextProps.strategy.is_enabled &&
      prevProps.strategy.publish_status === nextProps.strategy.publish_status &&
      prevProps.strategy.validation_status === nextProps.strategy.validation_status
    )
  }
)

StrategyTableRow.displayName = 'StrategyTableRow'
