/**
 * 用户筛选组件
 */
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Search, RefreshCw } from 'lucide-react'

interface UserFiltersProps {
  search: string
  setSearch: (search: string) => void
  roleFilter: string
  setRoleFilter: (role: string) => void
  onSearch: () => void
  onRefresh: () => void
  isLoading: boolean
}

export function UserFilters({
  search,
  setSearch,
  roleFilter,
  setRoleFilter,
  onSearch,
  onRefresh,
  isLoading,
}: UserFiltersProps) {
  return (
    <div className="flex flex-col sm:flex-row gap-3">
      <div className="flex-1 flex gap-2">
        <Input
          placeholder="搜索用户名或邮箱..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onSearch()}
        />
        <Button onClick={onSearch} variant="secondary" size="icon" className="shrink-0">
          <Search className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex gap-2">
        <Select value={roleFilter} onValueChange={setRoleFilter}>
          <SelectTrigger className="w-full sm:w-40">
            <SelectValue placeholder="角色筛选" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">全部角色</SelectItem>
            <SelectItem value="admin">管理员</SelectItem>
            <SelectItem value="user">普通用户</SelectItem>
          </SelectContent>
        </Select>

        <Button
          onClick={onRefresh}
          variant="outline"
          size="icon"
          className="shrink-0"
          disabled={isLoading}
        >
          <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
        </Button>
      </div>
    </div>
  )
}
