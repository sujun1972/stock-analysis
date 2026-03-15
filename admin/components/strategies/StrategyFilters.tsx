/**
 * 策略筛选器组件
 * 用于策略列表页面的筛选功能
 */

import React from 'react'
import { Search, Filter } from 'lucide-react'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface StrategyFiltersProps {
  searchTerm: string
  onSearchChange: (value: string) => void
  filterType: string
  onFilterTypeChange: (value: string) => void
  filterSource: string
  onFilterSourceChange: (value: string) => void
  filterStatus: string
  onFilterStatusChange: (value: string) => void
  filterPublishStatus: string
  onFilterPublishStatusChange: (value: string) => void
  filterOwnership: string
  onFilterOwnershipChange: (value: string) => void
}

export const StrategyFilters = React.memo<StrategyFiltersProps>(({
  searchTerm,
  onSearchChange,
  filterType,
  onFilterTypeChange,
  filterSource,
  onFilterSourceChange,
  filterStatus,
  onFilterStatusChange,
  filterPublishStatus,
  onFilterPublishStatusChange,
  filterOwnership,
  onFilterOwnershipChange,
}) => {
  return (
    <div className="space-y-4">
      {/* 搜索框 */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input
          type="text"
          placeholder="搜索策略名称或描述..."
          value={searchTerm}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full rounded-lg border border-input bg-background pl-10 pr-4 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        />
      </div>

      {/* 筛选器 */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <div className="space-y-2">
          <Label className="text-xs text-muted-foreground flex items-center gap-1">
            <Filter className="h-3 w-3" />
            策略类型
          </Label>
          <Select value={filterType} onValueChange={onFilterTypeChange}>
            <SelectTrigger>
              <SelectValue placeholder="全部类型" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部类型</SelectItem>
              <SelectItem value="stock_selection">选股策略</SelectItem>
              <SelectItem value="entry">入场策略</SelectItem>
              <SelectItem value="exit">离场策略</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label className="text-xs text-muted-foreground">来源</Label>
          <Select value={filterSource} onValueChange={onFilterSourceChange}>
            <SelectTrigger>
              <SelectValue placeholder="全部来源" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部来源</SelectItem>
              <SelectItem value="builtin">系统内置</SelectItem>
              <SelectItem value="ai">AI生成</SelectItem>
              <SelectItem value="custom">用户自定义</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label className="text-xs text-muted-foreground">验证状态</Label>
          <Select value={filterStatus} onValueChange={onFilterStatusChange}>
            <SelectTrigger>
              <SelectValue placeholder="全部状态" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部状态</SelectItem>
              <SelectItem value="pending">待验证</SelectItem>
              <SelectItem value="passed">已通过</SelectItem>
              <SelectItem value="failed">验证失败</SelectItem>
              <SelectItem value="validating">验证中</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label className="text-xs text-muted-foreground">发布状态</Label>
          <Select value={filterPublishStatus} onValueChange={onFilterPublishStatusChange}>
            <SelectTrigger>
              <SelectValue placeholder="全部状态" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部状态</SelectItem>
              <SelectItem value="draft">草稿</SelectItem>
              <SelectItem value="pending_review">待审核</SelectItem>
              <SelectItem value="published">已发布</SelectItem>
              <SelectItem value="archived">已归档</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label className="text-xs text-muted-foreground">归属</Label>
          <Select value={filterOwnership} onValueChange={onFilterOwnershipChange}>
            <SelectTrigger>
              <SelectValue placeholder="全部归属" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部归属</SelectItem>
              <SelectItem value="mine">我的策略</SelectItem>
              <SelectItem value="system">系统策略</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  )
})

StrategyFilters.displayName = 'StrategyFilters'
