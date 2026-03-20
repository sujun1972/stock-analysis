/**
 * 用户筛选和分页 Hook
 */
import { useState, useMemo } from 'react'
import { useDebounce } from '@/hooks/use-debounce'

export function useUserFilters() {
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState<string>('all')
  const [page, setPage] = useState(1)
  const pageSize = 20

  // 使用防抖的搜索词
  const debouncedSearch = useDebounce(search, 500)

  // 构建查询参数
  const queryParams = useMemo(() => ({
    page,
    page_size: pageSize,
    search: debouncedSearch || undefined,
    role: roleFilter !== 'all' ? roleFilter as any : undefined,
  }), [page, debouncedSearch, roleFilter])

  // 搜索
  const handleSearch = () => {
    setPage(1)
  }

  return {
    search,
    setSearch,
    roleFilter,
    setRoleFilter,
    page,
    setPage,
    pageSize,
    queryParams,
    handleSearch,
  }
}
