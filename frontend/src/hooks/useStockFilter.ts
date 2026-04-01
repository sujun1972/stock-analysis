/**
 * 可复用的股票筛选 Hook
 *
 * 提供股票列表的筛选、搜索、分页、排序功能
 * 用于股票列表页和股票选择弹窗
 */

import { useState, useCallback, useEffect } from 'react'
import { apiClient } from '@/lib/api-client'
import type { StockInfo } from '@/types/stock'

export interface StockFilterParams {
  /** 市场筛选 */
  market?: string
  /** 行业筛选 */
  industry?: string
  /** 概念筛选 */
  concepts?: string
  /** 搜索关键词 */
  search?: string
  /** 排序字段 */
  sortBy?: string
  /** 排序方向 */
  sortOrder?: 'asc' | 'desc'
  /** 当前页码 */
  page?: number
  /** 每页条数 */
  pageSize?: number
}

export interface UseStockFilterResult {
  /** 股票列表 */
  stocks: StockInfo[]
  /** 总数 */
  total: number
  /** 总页数 */
  totalPages: number
  /** 加载中 */
  loading: boolean
  /** 错误信息 */
  error: string | null
  /** 筛选参数 */
  filters: StockFilterParams
  /** 更新筛选参数 */
  updateFilters: (params: Partial<StockFilterParams>) => void
  /** 重新加载 */
  reload: () => Promise<void>
  /** 跳转到指定页 */
  goToPage: (page: number) => void
  /** 设置每页条数 */
  setPageSize: (size: number) => void
  /** 设置排序 */
  setSort: (sortBy: string, sortOrder: 'asc' | 'desc') => void
}

/**
 * 使用股票筛选 Hook
 * @param initialFilters 初始筛选参数
 * @param autoLoad 是否自动加载（默认 true）
 */
export function useStockFilter(
  initialFilters?: Partial<StockFilterParams>,
  autoLoad: boolean = true
): UseStockFilterResult {
  const [stocks, setStocks] = useState<StockInfo[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [filters, setFilters] = useState<StockFilterParams>({
    market: 'all',
    industry: 'all',
    concepts: 'all',
    search: '',
    sortBy: 'pct_change',
    sortOrder: 'desc',
    page: 1,
    pageSize: 20,
    ...initialFilters
  })

  /**
   * 加载股票列表
   */
  const loadStocks = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params: any = {
        skip: ((filters.page || 1) - 1) * (filters.pageSize || 20),
        limit: filters.pageSize || 20,
        sort_by: filters.sortBy || 'pct_change',
        sort_order: filters.sortOrder || 'desc',
        list_status: 'L',  // 只显示上市股票，过滤退市股票
      }

      if (filters.market && filters.market !== 'all') {
        params.market = filters.market
      }

      if (filters.industry && filters.industry !== 'all') {
        params.industry = filters.industry
      }

      if (filters.concepts && filters.concepts !== 'all') {
        params.concepts = filters.concepts
      }

      if (filters.search && filters.search.trim()) {
        params.search = filters.search.trim()
      }

      const response = await apiClient.getStockList(params)
      setStocks(response.items || [])
      setTotal(response.total ?? 0)
    } catch (err: any) {
      setError(err.message || '加载股票列表失败')
      setStocks([])
      setTotal(0)
      console.error('Failed to load stocks:', err)
    } finally {
      setLoading(false)
    }
  }, [filters])

  /**
   * 更新筛选参数
   */
  const updateFilters = useCallback((params: Partial<StockFilterParams>) => {
    setFilters(prev => {
      // 如果筛选条件改变，重置到第一页
      const shouldResetPage =
        params.market !== undefined ||
        params.industry !== undefined ||
        params.concepts !== undefined ||
        params.search !== undefined

      return {
        ...prev,
        ...params,
        page: shouldResetPage && params.page === undefined ? 1 : (params.page ?? prev.page)
      }
    })
  }, [])

  /**
   * 跳转到指定页
   */
  const goToPage = useCallback((page: number) => {
    setFilters(prev => ({ ...prev, page }))
  }, [])

  /**
   * 设置每页条数
   */
  const setPageSize = useCallback((pageSize: number) => {
    setFilters(prev => ({ ...prev, pageSize, page: 1 }))
  }, [])

  /**
   * 设置排序
   */
  const setSort = useCallback((sortBy: string, sortOrder: 'asc' | 'desc') => {
    setFilters(prev => ({ ...prev, sortBy, sortOrder }))
  }, [])

  // 自动加载
  useEffect(() => {
    if (autoLoad) {
      loadStocks()
    }
  }, [autoLoad, loadStocks])

  const totalPages = Math.ceil(total / (filters.pageSize || 20))

  return {
    stocks,
    total,
    totalPages,
    loading,
    error,
    filters,
    updateFilters,
    reload: loadStocks,
    goToPage,
    setPageSize,
    setSort
  }
}

/**
 * 获取所有符合筛选条件的股票代码（用于全选所有）
 * @param filters 筛选参数
 * @param maxLimit 最大数量限制
 */
export async function fetchAllStockCodes(
  filters: Omit<StockFilterParams, 'page' | 'pageSize'>,
  maxLimit: number = 500
): Promise<string[]> {
  try {
    const params: any = {
      limit: maxLimit,
    }

    if (filters.market && filters.market !== 'all') {
      params.market = filters.market
    }

    if (filters.industry && filters.industry !== 'all') {
      params.industry = filters.industry
    }

    if (filters.concepts && filters.concepts !== 'all') {
      params.concepts = filters.concepts
    }

    if (filters.search && filters.search.trim()) {
      params.search = filters.search.trim()
    }

    // 调用专用的股票代码接口，性能更优
    const response = await apiClient.getStockCodes(params)
    return response.codes || []
  } catch (err) {
    console.error('Failed to fetch all stock codes:', err)
    throw err
  }
}
