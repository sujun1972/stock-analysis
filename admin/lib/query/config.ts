/**
 * React Query 默认配置
 * 定义全局的查询和变更配置
 */

import { QueryClient, type DefaultOptions } from '@tanstack/react-query';

// 时间常量（毫秒）
export const QUERY_TIME = {
  SECOND: 1000,
  MINUTE: 60 * 1000,
  FIVE_MINUTES: 5 * 60 * 1000,
  TEN_MINUTES: 10 * 60 * 1000,
  THIRTY_MINUTES: 30 * 60 * 1000,
  HOUR: 60 * 60 * 1000,
  DAY: 24 * 60 * 60 * 1000,
} as const;

// 默认的查询配置
export const DEFAULT_QUERY_CONFIG = {
  // 数据过期时间（数据被认为是新鲜的时间）
  staleTime: QUERY_TIME.FIVE_MINUTES,
  // 缓存时间（数据在缓存中保留的时间）
  gcTime: QUERY_TIME.TEN_MINUTES,
  // 重试配置
  retry: 3,
  retryDelay: (attemptIndex: number) => Math.min(1000 * 2 ** attemptIndex, 30000),
  // 窗口焦点时重新获取
  refetchOnWindowFocus: false,
  // 重新连接时重新获取
  refetchOnReconnect: 'always',
} as const;

// 不同类型数据的配置预设
export const QUERY_PRESETS = {
  // 静态数据（如系统配置、类型列表等）
  STATIC: {
    staleTime: QUERY_TIME.DAY,
    gcTime: QUERY_TIME.DAY,
    refetchOnMount: false,
  },

  // 频繁变化的数据（如实时行情）
  REALTIME: {
    staleTime: QUERY_TIME.SECOND * 10,
    gcTime: QUERY_TIME.MINUTE,
    refetchInterval: QUERY_TIME.SECOND * 30,
  },

  // 列表数据（如用户列表、股票列表）
  LIST: {
    staleTime: QUERY_TIME.FIVE_MINUTES,
    gcTime: QUERY_TIME.TEN_MINUTES,
  },

  // 详情数据（如用户详情、策略详情）
  DETAIL: {
    staleTime: QUERY_TIME.TEN_MINUTES,
    gcTime: QUERY_TIME.THIRTY_MINUTES,
  },

  // 搜索结果
  SEARCH: {
    staleTime: QUERY_TIME.SECOND * 30,
    gcTime: QUERY_TIME.FIVE_MINUTES,
  },

  // 轮询数据（如任务状态、健康检查）
  POLLING: {
    staleTime: 0,
    gcTime: QUERY_TIME.MINUTE,
    refetchInterval: QUERY_TIME.SECOND * 3,
    refetchIntervalInBackground: false,
  },

  // 监控数据
  MONITOR: {
    staleTime: QUERY_TIME.SECOND * 10,
    gcTime: QUERY_TIME.MINUTE,
    refetchInterval: QUERY_TIME.SECOND * 10,
    refetchIntervalInBackground: false,
  },
} as const;

// 创建默认的 QueryClient 配置
export const createQueryClientConfig = (): DefaultOptions => ({
  queries: {
    ...DEFAULT_QUERY_CONFIG,
    // 全局错误处理
    throwOnError: false,
  },
  mutations: {
    // 变更默认不重试
    retry: 0,
    // 全局错误处理
    throwOnError: false,
  },
});

// 创建 QueryClient 实例
export const createQueryClient = () => {
  return new QueryClient({
    defaultOptions: createQueryClientConfig(),
  });
};

// 辅助函数：根据数据类型获取配置
export const getQueryConfig = (type: keyof typeof QUERY_PRESETS) => {
  return {
    ...DEFAULT_QUERY_CONFIG,
    ...QUERY_PRESETS[type],
  };
};

// 辅助函数：创建带轮询的查询配置
export const createPollingConfig = (intervalMs: number, backgroundRefetch = false) => ({
  ...DEFAULT_QUERY_CONFIG,
  staleTime: 0,
  refetchInterval: intervalMs,
  refetchIntervalInBackground: backgroundRefetch,
});

// 辅助函数：创建带缓存的查询配置
export const createCachedConfig = (staleTimeMs: number, gcTimeMs?: number) => ({
  ...DEFAULT_QUERY_CONFIG,
  staleTime: staleTimeMs,
  gcTime: gcTimeMs || staleTimeMs * 2,
});

// 导出类型
export type QueryPresetType = keyof typeof QUERY_PRESETS;