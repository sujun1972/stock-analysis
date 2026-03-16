/**
 * @file hooks/queries/use-stocks.ts
 * @description 股票相关的 React Query hooks
 * @author Claude
 * @created 2024-03-16
 * @updated 2024-03-16
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { stockApi, StockListParams, UpdateStockRequest } from '@/lib/api'
import { toast } from 'sonner'

/**
 * 获取股票列表
 */
export function useStockList(params?: StockListParams) {
  return useQuery({
    queryKey: ['stocks', params],
    queryFn: () => stockApi.getStockList(params),
    staleTime: 5 * 60 * 1000, // 5分钟
  })
}

/**
 * 获取单个股票信息
 */
export function useStock(code: string, enabled = true) {
  return useQuery({
    queryKey: ['stock', code],
    queryFn: () => stockApi.getStock(code),
    enabled: !!code && enabled,
    staleTime: 10 * 60 * 1000, // 10分钟
  })
}

/**
 * 更新股票信息
 */
export function useUpdateStock() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ code, data }: { code: string; data: UpdateStockRequest }) =>
      stockApi.updateStock(code, data),
    onSuccess: (response, variables) => {
      toast.success('股票信息更新成功')
      // 使相关查询失效
      queryClient.invalidateQueries({ queryKey: ['stocks'] })
      queryClient.invalidateQueries({ queryKey: ['stock', variables.code] })
    },
    onError: (error: any) => {
      toast.error(error.message || '更新失败')
    },
  })
}

/**
 * 同步股票列表
 */
export function useSyncStockList() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: () => stockApi.updateStockList(),
    onSuccess: (response) => {
      toast.success(`成功同步 ${response.data?.total || 0} 只股票`)
      queryClient.invalidateQueries({ queryKey: ['stocks'] })
    },
    onError: (error: any) => {
      toast.error(error.message || '同步失败')
    },
  })
}

/**
 * 获取股票概念
 */
export function useStockConcepts(code: string, enabled = true) {
  return useQuery({
    queryKey: ['stock-concepts', code],
    queryFn: () => stockApi.getStockConcepts(code),
    enabled: !!code && enabled,
    staleTime: 10 * 60 * 1000,
  })
}

/**
 * 更新股票概念
 */
export function useUpdateStockConcepts() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ code, conceptIds }: { code: string; conceptIds: number[] }) =>
      stockApi.updateStockConcepts(code, conceptIds),
    onSuccess: (response, variables) => {
      toast.success('概念更新成功')
      queryClient.invalidateQueries({ queryKey: ['stock-concepts', variables.code] })
      queryClient.invalidateQueries({ queryKey: ['stocks'] })
    },
    onError: (error: any) => {
      toast.error(error.message || '更新失败')
    },
  })
}

/**
 * 搜索股票
 */
export function useSearchStocks(keyword: string, limit = 10, enabled = true) {
  return useQuery({
    queryKey: ['stock-search', keyword, limit],
    queryFn: () => stockApi.searchStocks(keyword, limit),
    enabled: !!keyword && keyword.length > 0 && enabled,
    staleTime: 30 * 1000, // 30秒
  })
}

/**
 * 批量同步股票数据
 */
export function useBatchSyncStockData() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ codes, dataType }: {
      codes: string[]
      dataType: 'daily' | 'minute' | 'features'
    }) => stockApi.batchSyncStockData(codes, dataType),
    onSuccess: (response) => {
      const { success = [], failed = [] } = response.data || {}

      if (success.length > 0) {
        toast.success(`成功同步 ${success.length} 只股票`)
      }

      if (failed.length > 0) {
        toast.error(`${failed.length} 只股票同步失败`)
      }

      // 使相关查询失效
      queryClient.invalidateQueries({ queryKey: ['stocks'] })
      success.forEach(code => {
        queryClient.invalidateQueries({ queryKey: ['stock', code] })
      })
    },
    onError: (error: any) => {
      toast.error(error.message || '批量同步失败')
    },
  })
}

/**
 * 获取行业列表
 */
export function useIndustries() {
  return useQuery({
    queryKey: ['industries'],
    queryFn: () => stockApi.getIndustries(),
    staleTime: 24 * 60 * 60 * 1000, // 24小时
  })
}

/**
 * 获取市场列表
 */
export function useMarkets() {
  return useQuery({
    queryKey: ['markets'],
    queryFn: () => stockApi.getMarkets(),
    staleTime: 24 * 60 * 60 * 1000, // 24小时
  })
}