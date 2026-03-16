/**
 * @file hooks/queries/use-strategies.ts
 * @description 策略相关的 React Query hooks
 * @author Claude
 * @created 2024-03-16
 * @updated 2024-03-16
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { strategyApi, StrategyListParams } from '@/lib/api'
import { CreateStrategyRequest, UpdateStrategyRequest } from '@/types'
import { toast } from 'sonner'

/**
 * 获取策略列表
 */
export function useStrategyList(params?: StrategyListParams) {
  return useQuery({
    queryKey: ['strategies', params],
    queryFn: () => strategyApi.getStrategies(params),
    staleTime: 5 * 60 * 1000, // 5分钟
  })
}

/**
 * 获取单个策略详情
 */
export function useStrategy(id: number, enabled = true) {
  return useQuery({
    queryKey: ['strategy', id],
    queryFn: () => strategyApi.getStrategy(id),
    enabled: !!id && enabled,
    staleTime: 10 * 60 * 1000, // 10分钟
  })
}

/**
 * 创建策略
 */
export function useCreateStrategy() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateStrategyRequest) => strategyApi.createStrategy(data),
    onSuccess: () => {
      toast.success('策略创建成功')
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
    },
    onError: (error: any) => {
      toast.error(error.message || '创建失败')
    },
  })
}

/**
 * 更新策略
 */
export function useUpdateStrategy() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateStrategyRequest }) =>
      strategyApi.updateStrategy(id, data),
    onSuccess: (response, variables) => {
      toast.success('策略更新成功')
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
      queryClient.invalidateQueries({ queryKey: ['strategy', variables.id] })
    },
    onError: (error: any) => {
      toast.error(error.message || '更新失败')
    },
  })
}

/**
 * 删除策略
 */
export function useDeleteStrategy() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => strategyApi.deleteStrategy(id),
    onSuccess: () => {
      toast.success('策略删除成功')
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
    },
    onError: (error: any) => {
      toast.error(error.message || '删除失败')
    },
  })
}

/**
 * 批量删除策略
 */
export function useBatchDeleteStrategies() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (ids: number[]) => strategyApi.batchDeleteStrategies(ids),
    onSuccess: (response) => {
      const deletedCount = response.data?.deleted_count || 0
      toast.success(`成功删除 ${deletedCount} 个策略`)
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
    },
    onError: (error: any) => {
      toast.error(error.message || '批量删除失败')
    },
  })
}

/**
 * 验证策略代码
 */
export function useValidateStrategy() {
  return useMutation({
    mutationFn: (code: string) => strategyApi.validateStrategy(code),
    onError: (error: any) => {
      toast.error(error.message || '验证失败')
    },
  })
}

/**
 * 测试策略
 */
export function useTestStrategy() {
  return useMutation({
    mutationFn: ({ id, params }: {
      id: number
      params?: {
        stock_codes?: string[]
        start_date?: string
        end_date?: string
      }
    }) => strategyApi.testStrategy(id, params),
    onError: (error: any) => {
      toast.error(error.message || '测试失败')
    },
  })
}

/**
 * 启用/禁用策略
 */
export function useToggleStrategy() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, enabled }: { id: number; enabled: boolean }) =>
      strategyApi.toggleStrategy(id, enabled),
    onSuccess: (response, variables) => {
      const status = variables.enabled ? '启用' : '禁用'
      toast.success(`策略已${status}`)
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
      queryClient.invalidateQueries({ queryKey: ['strategy', variables.id] })
    },
    onError: (error: any) => {
      toast.error(error.message || '操作失败')
    },
  })
}

/**
 * 发布/取消发布策略
 */
export function useTogglePublish() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, published }: { id: number; published: boolean }) =>
      strategyApi.togglePublish(id, published),
    onSuccess: (response, variables) => {
      const status = variables.published ? '发布' : '取消发布'
      toast.success(`策略已${status}`)
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
      queryClient.invalidateQueries({ queryKey: ['strategy', variables.id] })
    },
    onError: (error: any) => {
      toast.error(error.message || '操作失败')
    },
  })
}

/**
 * 复制策略
 */
export function useCloneStrategy() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, newName }: { id: number; newName: string }) =>
      strategyApi.cloneStrategy(id, newName),
    onSuccess: () => {
      toast.success('策略复制成功')
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
    },
    onError: (error: any) => {
      toast.error(error.message || '复制失败')
    },
  })
}

/**
 * 获取策略统计信息
 */
export function useStrategyStatistics(id: number, enabled = true) {
  return useQuery({
    queryKey: ['strategy-statistics', id],
    queryFn: () => strategyApi.getStrategyStatistics(id),
    enabled: !!id && enabled,
    staleTime: 5 * 60 * 1000, // 5分钟
  })
}

/**
 * 获取策略类型列表
 */
export function useStrategyTypes() {
  return useQuery({
    queryKey: ['strategy-types'],
    queryFn: () => strategyApi.getStrategyTypes(),
    staleTime: 24 * 60 * 60 * 1000, // 24小时
  })
}

/**
 * 导出策略
 */
export function useExportStrategy() {
  return useMutation({
    mutationFn: ({ id, format }: { id: number; format: 'json' | 'python' }) =>
      strategyApi.exportStrategy(id, format),
    onSuccess: (response, variables) => {
      // 创建下载链接
      const blob = new Blob([response.data?.content || ''], {
        type: variables.format === 'json' ? 'application/json' : 'text/plain'
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = response.data?.filename || `strategy.${variables.format}`
      a.click()
      URL.revokeObjectURL(url)

      toast.success('策略导出成功')
    },
    onError: (error: any) => {
      toast.error(error.message || '导出失败')
    },
  })
}

/**
 * 导入策略
 */
export function useImportStrategy() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (file: File) => strategyApi.importStrategy(file),
    onSuccess: () => {
      toast.success('策略导入成功')
      queryClient.invalidateQueries({ queryKey: ['strategies'] })
    },
    onError: (error: any) => {
      toast.error(error.message || '导入失败')
    },
  })
}