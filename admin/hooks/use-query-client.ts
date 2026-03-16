/**
 * Query Client 辅助 Hooks
 * 提供便捷的 Query Client 操作方法
 */

import { useQueryClient } from '@tanstack/react-query';
import { useCallback } from 'react';
import { queryKeys } from '@/lib/query/keys';

/**
 * 便捷的 Query Client 操作 Hook
 */
export function useQueryHelper() {
  const queryClient = useQueryClient();

  // 使某个查询失效
  const invalidateQuery = useCallback(
    (queryKey: readonly unknown[]) => {
      return queryClient.invalidateQueries({ queryKey });
    },
    [queryClient]
  );

  // 批量使查询失效
  const invalidateQueries = useCallback(
    (queryKeys: readonly (readonly unknown[])[]) => {
      return Promise.all(
        queryKeys.map((key) => queryClient.invalidateQueries({ queryKey: key }))
      );
    },
    [queryClient]
  );

  // 预取数据
  const prefetchQuery = useCallback(
    async (queryKey: readonly unknown[], queryFn: () => Promise<any>) => {
      return queryClient.prefetchQuery({
        queryKey,
        queryFn,
      });
    },
    [queryClient]
  );

  // 设置查询数据
  const setQueryData = useCallback(
    <TData = unknown>(queryKey: readonly unknown[], data: TData) => {
      queryClient.setQueryData(queryKey, data);
    },
    [queryClient]
  );

  // 获取查询数据
  const getQueryData = useCallback(
    <TData = unknown>(queryKey: readonly unknown[]): TData | undefined => {
      return queryClient.getQueryData<TData>(queryKey);
    },
    [queryClient]
  );

  // 取消查询
  const cancelQueries = useCallback(
    (queryKey?: readonly unknown[]) => {
      return queryClient.cancelQueries(queryKey ? { queryKey } : undefined);
    },
    [queryClient]
  );

  // 移除查询
  const removeQueries = useCallback(
    (queryKey?: readonly unknown[]) => {
      return queryClient.removeQueries(queryKey ? { queryKey } : undefined);
    },
    [queryClient]
  );

  // 重置查询
  const resetQueries = useCallback(
    (queryKey?: readonly unknown[]) => {
      return queryClient.resetQueries(queryKey ? { queryKey } : undefined);
    },
    [queryClient]
  );

  // 重新获取查询
  const refetchQueries = useCallback(
    (queryKey?: readonly unknown[]) => {
      return queryClient.refetchQueries(queryKey ? { queryKey } : undefined);
    },
    [queryClient]
  );

  return {
    queryClient,
    invalidateQuery,
    invalidateQueries,
    prefetchQuery,
    setQueryData,
    getQueryData,
    cancelQueries,
    removeQueries,
    resetQueries,
    refetchQueries,
  };
}

/**
 * 用户相关查询操作
 */
export function useUserQueryHelper() {
  const { invalidateQuery, refetchQueries } = useQueryHelper();

  const invalidateUserList = useCallback(() => {
    return invalidateQuery(queryKeys.users.lists());
  }, [invalidateQuery]);

  const invalidateUser = useCallback(
    (id: string) => {
      return invalidateQuery(queryKeys.users.detail(id));
    },
    [invalidateQuery]
  );

  const refetchUsers = useCallback(() => {
    return refetchQueries(queryKeys.users.all);
  }, [refetchQueries]);

  return {
    invalidateUserList,
    invalidateUser,
    refetchUsers,
  };
}

/**
 * 系统相关查询操作
 */
export function useSystemQueryHelper() {
  const { invalidateQuery, refetchQueries } = useQueryHelper();

  const invalidateSystemSettings = useCallback(() => {
    return invalidateQuery(queryKeys.system.settings());
  }, [invalidateQuery]);

  const invalidateHealth = useCallback(() => {
    return invalidateQuery(queryKeys.system.health());
  }, [invalidateQuery]);

  const refetchSystem = useCallback(() => {
    return refetchQueries(queryKeys.system.all);
  }, [refetchQueries]);

  return {
    invalidateSystemSettings,
    invalidateHealth,
    refetchSystem,
  };
}

/**
 * 同步相关查询操作
 */
export function useSyncQueryHelper() {
  const { invalidateQuery, refetchQueries } = useQueryHelper();

  const invalidateStockListSync = useCallback(() => {
    return invalidateQuery(queryKeys.sync.stockList());
  }, [invalidateQuery]);

  const invalidateDailyData = useCallback(() => {
    return invalidateQuery(queryKeys.sync.dailyData());
  }, [invalidateQuery]);

  const refetchSyncStatus = useCallback(() => {
    return refetchQueries(queryKeys.sync.all);
  }, [refetchQueries]);

  return {
    invalidateStockListSync,
    invalidateDailyData,
    refetchSyncStatus,
  };
}

/**
 * 情绪相关查询操作
 */
export function useSentimentQueryHelper() {
  const { invalidateQuery, refetchQueries } = useQueryHelper();

  const invalidatePremarket = useCallback(
    (date: string) => {
      return invalidateQuery(queryKeys.sentiment.premarket(date));
    },
    [invalidateQuery]
  );

  const invalidateLimitUp = useCallback(
    (date: string) => {
      return invalidateQuery(queryKeys.sentiment.limitUp(date));
    },
    [invalidateQuery]
  );

  const refetchSentiment = useCallback(() => {
    return refetchQueries(queryKeys.sentiment.all);
  }, [refetchQueries]);

  return {
    invalidatePremarket,
    invalidateLimitUp,
    refetchSentiment,
  };
}

/**
 * 股票相关查询操作
 */
export function useStockQueryHelper() {
  const { invalidateQuery, refetchQueries, setQueryData } = useQueryHelper();

  const invalidateStockList = useCallback(() => {
    return invalidateQuery(queryKeys.stocks.lists());
  }, [invalidateQuery]);

  const invalidateStock = useCallback(
    (code: string) => {
      return invalidateQuery(queryKeys.stocks.detail(code));
    },
    [invalidateQuery]
  );

  const updateStockInList = useCallback(
    (code: string, updater: (old: any) => any) => {
      const lists = queryKeys.stocks.lists();
      setQueryData(lists, updater);
    },
    [setQueryData]
  );

  const refetchStocks = useCallback(() => {
    return refetchQueries(queryKeys.stocks.all);
  }, [refetchQueries]);

  return {
    invalidateStockList,
    invalidateStock,
    updateStockInList,
    refetchStocks,
  };
}