/**
 * 数据同步相关的 React Query Hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { syncApi, axiosInstance } from '@/lib/api';
import { queryKeys } from '@/lib/query/keys';
import { getQueryConfig, QUERY_TIME } from '@/lib/query/config';
import { toast } from 'sonner';
import { useSyncQueryHelper } from '@/hooks/use-query-client';

// 类型定义
export interface StockListSyncStatus {
  status: 'idle' | 'running' | 'completed' | 'failed';
  progress?: number;
  total?: number;
  message?: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  stats?: {
    total_stocks?: number;
    new_stocks?: number;
    updated_stocks?: number;
    delisted_stocks?: number;
    failed_stocks?: number;
  };
}

export interface DailyDataSyncStatus {
  status: 'idle' | 'running' | 'completed' | 'failed';
  current_stock?: string;
  current_index?: number;
  total_stocks?: number;
  progress_percentage?: number;
  message?: string;
  started_at?: string;
  completed_at?: string;
  error?: string;
  stats?: {
    synced_stocks?: number;
    failed_stocks?: number;
    total_records?: number;
    average_speed?: number; // 条/秒
  };
}

export interface MinuteDataSyncStatus {
  status: 'idle' | 'running' | 'completed' | 'failed';
  current_stock?: string;
  progress?: number;
  total?: number;
  message?: string;
  error?: string;
}

export interface DelistedStock {
  code: string;
  name: string;
  delist_date: string;
  list_date?: string;
  reason?: string;
}

export interface NewStock {
  code: string;
  name: string;
  list_date: string;
  issue_price?: number;
  market_cap?: number;
  pe_ratio?: number;
}

export interface SyncBatchParams {
  stock_codes?: string[];
  start_date?: string;
  end_date?: string;
  force_update?: boolean;
  batch_size?: number;
}

/**
 * 获取股票列表同步状态
 */
export function useStockListSyncStatus(enabled = true) {
  return useQuery({
    queryKey: queryKeys.sync.stockListStatus(),
    queryFn: async () => {
      const response = await axiosInstance.get('/api/sync/stock-list/status') as any;
      if (response.code !== 200) {
        throw new Error(response.message || '获取同步状态失败');
      }
      return response.data as StockListSyncStatus;
    },
    enabled,
    refetchInterval: (query) => {
      // 如果正在运行，每3秒刷新一次
      return query.state.data?.status === 'running' ? 3000 : false;
    },
    ...getQueryConfig('POLLING'),
  });
}

/**
 * 同步股票列表
 */
export function useSyncStockList() {
  const { invalidateStockListSync } = useSyncQueryHelper();

  return useMutation({
    mutationFn: async () => {
      const response = await syncApi.syncStockList();
      if (response.code !== 200) {
        throw new Error(response.message || '启动股票列表同步失败');
      }
      return response.data;
    },
    onSuccess: () => {
      invalidateStockListSync();
      toast.success('股票列表同步已启动');
    },
    onError: (error: Error) => {
      console.error('股票列表同步失败:', error);
      toast.error(error.message || '股票列表同步失败');
    },
  });
}

/**
 * 获取日线数据同步状态
 */
export function useDailyDataSyncStatus(enabled = true) {
  return useQuery({
    queryKey: queryKeys.sync.dailyDataStatus(),
    queryFn: async () => {
      const response = await axiosInstance.get('/api/sync/daily/status') as any;
      if (response.code !== 200) {
        throw new Error(response.message || '获取日线同步状态失败');
      }
      return response.data as DailyDataSyncStatus;
    },
    enabled,
    refetchInterval: (query) => {
      // 如果正在运行，每2秒刷新一次
      return query.state.data?.status === 'running' ? 2000 : false;
    },
    ...getQueryConfig('POLLING'),
  });
}

/**
 * 批量同步日线数据
 */
export function useSyncDailyDataBatch() {
  const { invalidateDailyData } = useSyncQueryHelper();

  return useMutation({
    mutationFn: async (params: SyncBatchParams) => {
      const response = await syncApi.syncDailyBatch({
        stock_codes: params.stock_codes,
        start_date: params.start_date,
        end_date: params.end_date
      });
      if (response.code !== 200) {
        throw new Error(response.message || '启动日线数据同步失败');
      }
      return response.data;
    },
    onSuccess: () => {
      invalidateDailyData();
      toast.success('日线数据同步已启动');
    },
    onError: (error: Error) => {
      console.error('日线数据同步失败:', error);
      toast.error(error.message || '日线数据同步失败');
    },
  });
}

/**
 * 获取分钟数据同步状态
 */
export function useMinuteDataSyncStatus(enabled = true) {
  return useQuery({
    queryKey: [...queryKeys.sync.all, 'minute-status'],
    queryFn: async () => {
      const response = await axiosInstance.get('/api/sync/minute/status') as any;
      if (response.code !== 200) {
        throw new Error(response.message || '获取分钟数据同步状态失败');
      }
      return response.data as MinuteDataSyncStatus;
    },
    enabled,
    refetchInterval: (query) => {
      return query.state.data?.status === 'running' ? 3000 : false;
    },
    ...getQueryConfig('POLLING'),
  });
}

/**
 * 同步分钟数据
 */
export function useSyncMinuteData() {
  return useMutation({
    mutationFn: async (params: {
      stock_codes: string[];
      start_date?: string;
      end_date?: string;
      frequency?: '1min' | '5min' | '15min' | '30min' | '60min';
    }) => {
      // 注意：syncMinuteData 只支持单个股票，需要遍历处理
      const results = [];
      for (const code of params.stock_codes) {
        const response = await syncApi.syncMinuteData({
          stock_codes: [code],
          freq: params.frequency,
        });
        if (response.code !== 200) {
          throw new Error(response.message || `同步 ${code} 分钟数据失败`);
        }
        results.push(response.data);
      }
      return results;
    },
    onSuccess: () => {
      toast.success('分钟数据同步已启动');
    },
    onError: (error: Error) => {
      console.error('分钟数据同步失败:', error);
      toast.error(error.message || '分钟数据同步失败');
    },
  });
}

/**
 * 获取退市股票列表
 */
export function useDelistedStocks(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  start_date?: string;
  end_date?: string;
}) {
  return useQuery({
    queryKey: queryKeys.sync.delistedStocks(),
    queryFn: async () => {
      const response = await axiosInstance.get('/api/stocks/delisted', { params }) as any;
      if (response.code !== 200) {
        throw new Error(response.message || '获取退市股票列表失败');
      }
      return response.data as {
        items: DelistedStock[];
        total: number;
      };
    },
    ...getQueryConfig('LIST'),
  });
}

/**
 * 同步退市股票
 */
export function useSyncDelistedStocks() {
  return useMutation({
    mutationFn: async () => {
      const response = await axiosInstance.post('/api/sync/delisted-stocks') as any;
      if (response.code !== 200) {
        throw new Error(response.message || '同步退市股票失败');
      }
      return response.data;
    },
    onSuccess: (data) => {
      toast.success(`成功同步 ${data.count || 0} 只退市股票`);
    },
    onError: (error: Error) => {
      console.error('同步退市股票失败:', error);
      toast.error(error.message || '同步退市股票失败');
    },
  });
}

/**
 * 获取新股列表
 */
export function useNewStocks(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  list_date_start?: string;
  list_date_end?: string;
}) {
  return useQuery({
    queryKey: queryKeys.sync.newStocks(),
    queryFn: async () => {
      const response = await axiosInstance.get('/api/stocks/new', { params }) as any;
      if (response.code !== 200) {
        throw new Error(response.message || '获取新股列表失败');
      }
      return response.data as {
        items: NewStock[];
        total: number;
      };
    },
    ...getQueryConfig('LIST'),
  });
}

/**
 * 同步新股数据
 */
export function useSyncNewStocks() {
  return useMutation({
    mutationFn: async (params?: {
      days?: number; // 获取最近N天的新股
    }) => {
      const response = await axiosInstance.post('/api/sync/new-stocks', params) as any;
      if (response.code !== 200) {
        throw new Error(response.message || '同步新股数据失败');
      }
      return response.data;
    },
    onSuccess: (data) => {
      toast.success(`成功同步 ${data.count || 0} 只新股数据`);
    },
    onError: (error: Error) => {
      console.error('同步新股数据失败:', error);
      toast.error(error.message || '同步新股数据失败');
    },
  });
}

/**
 * 获取实时数据同步状态
 */
export function useRealtimeDataStatus() {
  return useQuery({
    queryKey: queryKeys.sync.realtimeData(),
    queryFn: async () => {
      const response = await axiosInstance.get('/api/sync/realtime/status') as any;
      if (response.code !== 200) {
        throw new Error(response.message || '获取实时数据状态失败');
      }
      return response.data as {
        is_active: boolean;
        stocks_count: number;
        last_update?: string;
        update_frequency_seconds: number;
        websocket_connected?: boolean;
      };
    },
    refetchInterval: 5000, // 每5秒刷新状态
    ...getQueryConfig('POLLING'),
  });
}

/**
 * 启动/停止实时数据同步
 */
export function useToggleRealtimeSync() {
  return useMutation({
    mutationFn: async (params: {
      action: 'start' | 'stop';
      stock_codes?: string[];
      update_frequency?: number; // 秒
    }) => {
      const endpoint = params.action === 'start'
        ? '/api/sync/realtime/start'
        : '/api/sync/realtime/stop';

      const response = await axiosInstance.post(endpoint, {
        stock_codes: params.stock_codes,
        update_frequency: params.update_frequency,
      }) as any;

      if (response.code !== 200) {
        throw new Error(response.message || `${params.action === 'start' ? '启动' : '停止'}实时同步失败`);
      }
      return response.data;
    },
    onSuccess: (_, variables) => {
      toast.success(
        variables.action === 'start' ? '实时数据同步已启动' : '实时数据同步已停止'
      );
    },
    onError: (error: Error) => {
      console.error('切换实时同步状态失败:', error);
      toast.error(error.message || '操作失败');
    },
  });
}

/**
 * 取消正在进行的同步任务
 */
export function useCancelSyncTask() {
  return useMutation({
    mutationFn: async (taskType: 'stock-list' | 'daily' | 'minute' | 'realtime') => {
      const response = await axiosInstance.post(`/api/sync/${taskType}/cancel`) as any;
      if (response.code !== 200) {
        throw new Error(response.message || '取消同步任务失败');
      }
      return response.data;
    },
    onSuccess: () => {
      toast.success('同步任务已取消');
    },
    onError: (error: Error) => {
      console.error('取消同步任务失败:', error);
      toast.error(error.message || '取消同步任务失败');
    },
  });
}

/**
 * 获取同步任务历史记录
 */
export function useSyncHistory(params?: {
  task_type?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
  limit?: number;
}) {
  return useQuery({
    queryKey: [...queryKeys.sync.all, 'history', params],
    queryFn: async () => {
      const response = await axiosInstance.get('/api/sync/history', { params }) as any;
      if (response.code !== 200) {
        throw new Error(response.message || '获取同步历史失败');
      }
      return response.data as {
        items: Array<{
          id: string;
          task_type: string;
          status: string;
          started_at: string;
          completed_at?: string;
          duration_seconds?: number;
          stats?: any;
          error?: string;
        }>;
        total: number;
      };
    },
    ...getQueryConfig('LIST'),
  });
}

/**
 * 清理历史同步数据
 */
export function useCleanupSyncData() {
  return useMutation({
    mutationFn: async (params: {
      data_type: 'daily' | 'minute' | 'realtime';
      older_than_days: number;
    }) => {
      const response = await axiosInstance.post('/api/sync/cleanup', params) as any;
      if (response.code !== 200) {
        throw new Error(response.message || '清理数据失败');
      }
      return response.data as { deleted_count: number };
    },
    onSuccess: (data) => {
      toast.success(`已清理 ${data.deleted_count} 条历史数据`);
    },
    onError: (error: Error) => {
      console.error('清理数据失败:', error);
      toast.error(error.message || '清理数据失败');
    },
  });
}