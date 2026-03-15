import { QueryClient } from '@tanstack/react-query'

/**
 * React Query 客户端配置
 * 优化后的缓存策略，提升页面加载性能
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 数据保持新鲜时间：10分钟（从5分钟增加，减少不必要的请求）
      staleTime: 10 * 60 * 1000,

      // 垃圾回收时间：30分钟（从10分钟增加，保持更长缓存）
      gcTime: 30 * 60 * 1000,

      // 失败重试次数：1次
      retry: 1,

      // 禁用窗口焦点时自动刷新（避免不必要的请求）
      refetchOnWindowFocus: false,

      // 禁用网络重连时自动刷新
      refetchOnReconnect: false,

      // 禁用组件挂载时自动刷新（避免重复请求）
      refetchOnMount: false,

      // 启用结构共享，减少内存占用
      structuralSharing: true,

      // 启用请求去重（防止并发相同请求）
      refetchInterval: false,
    },
    mutations: {
      // Mutation 不重试
      retry: 0,
    },
  },
})

/**
 * 批量请求处理工具
 * 用于并行请求多个 API
 */
export async function batchRequest<T>(
  requests: Promise<T>[]
): Promise<T[]> {
  return Promise.all(requests)
}

/**
 * 预取查询
 * 用于在页面加载前预加载数据
 */
export async function prefetchQuery<T>(
  queryKey: string[],
  queryFn: () => Promise<T>
) {
  await queryClient.prefetchQuery({
    queryKey,
    queryFn,
    staleTime: 10 * 60 * 1000,
  })
}
