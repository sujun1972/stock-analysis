'use client'

import { Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface StrategyFiltersProps {
  searchTerm: string
  onSearchTermChange: (value: string) => void
  filterStrategyType: string
  onFilterStrategyTypeChange: (value: string) => void
  filterSourceType: string
  onFilterSourceTypeChange: (value: string) => void
  filterPublishStatus: string
  onFilterPublishStatusChange: (value: string) => void
  filterUserId: string
  onFilterUserIdChange: (value: string) => void
  onResetFilters: () => void
}

export function StrategyFilters({
  searchTerm,
  onSearchTermChange,
  filterStrategyType,
  onFilterStrategyTypeChange,
  filterSourceType,
  onFilterSourceTypeChange,
  filterPublishStatus,
  onFilterPublishStatusChange,
  filterUserId,
  onFilterUserIdChange,
  onResetFilters,
}: StrategyFiltersProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>筛选和搜索</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* 搜索框 */}
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="搜索策略名称或描述..."
              value={searchTerm}
              onChange={(e) => onSearchTermChange(e.target.value)}
              className="pl-10"
            />
          </div>
          <Button onClick={onResetFilters} variant="outline">
            重置
          </Button>
        </div>

        {/* 筛选选项 */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Select value={filterStrategyType} onValueChange={onFilterStrategyTypeChange}>
            <SelectTrigger>
              <SelectValue placeholder="策略类型" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部类型</SelectItem>
              <SelectItem value="stock_selection">选股策略</SelectItem>
              <SelectItem value="entry">入场策略</SelectItem>
              <SelectItem value="exit">离场策略</SelectItem>
            </SelectContent>
          </Select>

          <Select value={filterSourceType} onValueChange={onFilterSourceTypeChange}>
            <SelectTrigger>
              <SelectValue placeholder="来源类型" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部来源</SelectItem>
              <SelectItem value="builtin">系统内置</SelectItem>
              <SelectItem value="ai">AI生成</SelectItem>
              <SelectItem value="custom">用户自定义</SelectItem>
            </SelectContent>
          </Select>

          <Select value={filterPublishStatus} onValueChange={onFilterPublishStatusChange}>
            <SelectTrigger>
              <SelectValue placeholder="发布状态" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部状态</SelectItem>
              <SelectItem value="draft">草稿</SelectItem>
              <SelectItem value="pending_review">待审核</SelectItem>
              <SelectItem value="approved">已发布</SelectItem>
              <SelectItem value="rejected">已拒绝</SelectItem>
            </SelectContent>
          </Select>

          <Select value={filterUserId} onValueChange={onFilterUserIdChange}>
            <SelectTrigger>
              <SelectValue placeholder="用户筛选" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部用户</SelectItem>
              <SelectItem value="system">系统策略</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardContent>
    </Card>
  )
}
