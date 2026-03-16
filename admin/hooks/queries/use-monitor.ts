/**
 * 监控相关的 React Query Hooks
 */

import { useQuery, useMutation } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { queryKeys } from '@/lib/query/keys';
import { getQueryConfig, QUERY_TIME } from '@/lib/query/config';
import { toast } from 'sonner';

// 类型定义
export interface MonitorData {
  database: {
    status: 'connected' | 'disconnected' | 'error';
    response_time_ms: number;
    active_connections?: number;
    max_connections?: number;
    query_count?: number;
    slow_queries?: number;
    error?: string;
  };
  redis?: {
    status: 'connected' | 'disconnected' | 'error';
    response_time_ms: number;
    memory_usage_mb?: number;
    connected_clients?: number;
    ops_per_sec?: number;
    error?: string;
  };
  services: {
    [key: string]: {
      name: string;
      status: 'running' | 'stopped' | 'error' | 'unknown';
      uptime_seconds?: number;
      memory_usage_mb?: number;
      cpu_usage_percent?: number;
      last_health_check?: string;
      error?: string;
    };
  };
  circuit_breakers?: {
    [key: string]: {
      state: 'closed' | 'open' | 'half_open';
      failure_count: number;
      success_count: number;
      last_failure_time?: string;
      next_attempt_time?: string;
    };
  };
  system?: {
    cpu_usage_percent: number;
    memory_usage_percent: number;
    disk_usage_percent: number;
    load_average?: number[];
    uptime_seconds: number;
  };
  timestamp: string;
}

export interface ActiveTask {
  id: string;
  name: string;
  type: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress?: number;
  started_at: string;
  updated_at?: string;
  completed_at?: string;
  error?: string;
  metadata?: {
    [key: string]: any;
  };
}

export interface TaskStatistics {
  total_tasks: number;
  pending_tasks: number;
  running_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  cancelled_tasks: number;
  average_duration_seconds?: number;
  success_rate?: number;
}

/**
 * 获取监控数据
 * @param refetchInterval 自动刷新间隔（毫秒）
 */
export function useMonitorData(refetchInterval?: number) {
  return useQuery({
    queryKey: queryKeys.monitor.health(),
    queryFn: async () => {
      const response = await apiClient.get('/api/monitor');
      if (response.code !== 200) {
        throw new Error(response.message || '获取监控数据失败');
      }
      return response.data as MonitorData;
    },
    ...getQueryConfig('MONITOR'),
    refetchInterval: refetchInterval || QUERY_TIME.SECOND * 10,
    refetchIntervalInBackground: false,
  });
}

/**
 * 获取活动任务列表
 * @param autoRefresh 是否自动刷新
 */
export function useActiveTasks(autoRefresh = true) {
  return useQuery({
    queryKey: queryKeys.monitor.activeTasks(),
    queryFn: async () => {
      const response = await apiClient.get('/api/sentiment/tasks/active');
      if (response.code !== 200) {
        throw new Error(response.message || '获取活动任务失败');
      }
      return response.data?.tasks as ActiveTask[] || [];
    },
    ...getQueryConfig('POLLING'),
    refetchInterval: autoRefresh ? QUERY_TIME.SECOND * 5 : false,
    refetchIntervalInBackground: false,
  });
}

/**
 * 获取任务统计信息
 */
export function useTaskStatistics() {
  return useQuery({
    queryKey: [...queryKeys.monitor.all, 'task-statistics'],
    queryFn: async () => {
      const response = await apiClient.get('/api/tasks/statistics');
      if (response.code !== 200) {
        throw new Error(response.message || '获取任务统计失败');
      }
      return response.data as TaskStatistics;
    },
    ...getQueryConfig('LIST'),
    staleTime: QUERY_TIME.MINUTE, // 1分钟刷新一次统计数据
  });
}

/**
 * 取消任务
 */
export function useCancelTask() {
  return useMutation({
    mutationFn: async (taskId: string) => {
      const response = await apiClient.post(`/api/tasks/${taskId}/cancel`);
      if (response.code !== 200) {
        throw new Error(response.message || '取消任务失败');
      }
      return response.data;
    },
    onSuccess: () => {
      toast.success('任务已取消');
    },
    onError: (error: Error) => {
      console.error('取消任务失败:', error);
      toast.error(error.message || '取消任务失败');
    },
  });
}

/**
 * 重试失败的任务
 */
export function useRetryTask() {
  return useMutation({
    mutationFn: async (taskId: string) => {
      const response = await apiClient.post(`/api/tasks/${taskId}/retry`);
      if (response.code !== 200) {
        throw new Error(response.message || '重试任务失败');
      }
      return response.data;
    },
    onSuccess: () => {
      toast.success('任务已重新启动');
    },
    onError: (error: Error) => {
      console.error('重试任务失败:', error);
      toast.error(error.message || '重试任务失败');
    },
  });
}

/**
 * 清理已完成的任务
 */
export function useCleanupTasks() {
  return useMutation({
    mutationFn: async (params?: {
      status?: 'completed' | 'failed' | 'cancelled';
      older_than_days?: number;
    }) => {
      const response = await apiClient.post('/api/tasks/cleanup', params);
      if (response.code !== 200) {
        throw new Error(response.message || '清理任务失败');
      }
      return response.data as { deleted_count: number };
    },
    onSuccess: (data) => {
      toast.success(`已清理 ${data.deleted_count} 个任务`);
    },
    onError: (error: Error) => {
      console.error('清理任务失败:', error);
      toast.error(error.message || '清理任务失败');
    },
  });
}

/**
 * 获取服务日志
 */
export function useServiceLogs(service: string, params?: {
  lines?: number;
  level?: 'debug' | 'info' | 'warning' | 'error';
  search?: string;
}) {
  return useQuery({
    queryKey: [...queryKeys.monitor.all, 'service-logs', service, params],
    queryFn: async () => {
      const response = await apiClient.get(`/api/services/${service}/logs`, { params });
      if (response.code !== 200) {
        throw new Error(response.message || '获取服务日志失败');
      }
      return response.data as {
        logs: string[];
        total_lines: number;
      };
    },
    ...getQueryConfig('LIST'),
    staleTime: QUERY_TIME.SECOND * 30,
  });
}

/**
 * 重置熔断器
 */
export function useResetCircuitBreaker() {
  return useMutation({
    mutationFn: async (breakerName: string) => {
      const response = await apiClient.post(`/api/circuit-breakers/${breakerName}/reset`);
      if (response.code !== 200) {
        throw new Error(response.message || '重置熔断器失败');
      }
      return response.data;
    },
    onSuccess: (_, breakerName) => {
      toast.success(`熔断器 ${breakerName} 已重置`);
    },
    onError: (error: Error) => {
      console.error('重置熔断器失败:', error);
      toast.error(error.message || '重置熔断器失败');
    },
  });
}

/**
 * 获取性能指标历史数据
 */
export function usePerformanceHistory(params?: {
  metric: 'cpu' | 'memory' | 'disk' | 'network' | 'requests';
  period?: '1h' | '6h' | '24h' | '7d';
  interval?: '1m' | '5m' | '15m' | '1h';
}) {
  return useQuery({
    queryKey: [...queryKeys.monitor.all, 'performance-history', params],
    queryFn: async () => {
      const response = await apiClient.get('/api/metrics/history', { params });
      if (response.code !== 200) {
        throw new Error(response.message || '获取性能历史数据失败');
      }
      return response.data as {
        metric: string;
        period: string;
        interval: string;
        data: Array<{
          timestamp: string;
          value: number;
        }>;
      };
    },
    ...getQueryConfig('LIST'),
    staleTime: QUERY_TIME.MINUTE * 5,
  });
}

/**
 * 获取告警列表
 */
export function useAlerts(params?: {
  status?: 'active' | 'resolved' | 'acknowledged';
  severity?: 'critical' | 'warning' | 'info';
  limit?: number;
}) {
  return useQuery({
    queryKey: [...queryKeys.monitor.all, 'alerts', params],
    queryFn: async () => {
      const response = await apiClient.get('/api/alerts', { params });
      if (response.code !== 200) {
        throw new Error(response.message || '获取告警列表失败');
      }
      return response.data as {
        alerts: Array<{
          id: string;
          name: string;
          message: string;
          severity: 'critical' | 'warning' | 'info';
          status: 'active' | 'resolved' | 'acknowledged';
          created_at: string;
          updated_at: string;
          resolved_at?: string;
          acknowledged_at?: string;
          acknowledged_by?: string;
          metadata?: any;
        }>;
        total: number;
      };
    },
    ...getQueryConfig('POLLING'),
    refetchInterval: QUERY_TIME.SECOND * 30,
  });
}

/**
 * 确认告警
 */
export function useAcknowledgeAlert() {
  return useMutation({
    mutationFn: async ({ alertId, note }: { alertId: string; note?: string }) => {
      const response = await apiClient.post(`/api/alerts/${alertId}/acknowledge`, { note });
      if (response.code !== 200) {
        throw new Error(response.message || '确认告警失败');
      }
      return response.data;
    },
    onSuccess: () => {
      toast.success('告警已确认');
    },
    onError: (error: Error) => {
      console.error('确认告警失败:', error);
      toast.error(error.message || '确认告警失败');
    },
  });
}

/**
 * 解决告警
 */
export function useResolveAlert() {
  return useMutation({
    mutationFn: async ({ alertId, resolution }: { alertId: string; resolution?: string }) => {
      const response = await apiClient.post(`/api/alerts/${alertId}/resolve`, { resolution });
      if (response.code !== 200) {
        throw new Error(response.message || '解决告警失败');
      }
      return response.data;
    },
    onSuccess: () => {
      toast.success('告警已解决');
    },
    onError: (error: Error) => {
      console.error('解决告警失败:', error);
      toast.error(error.message || '解决告警失败');
    },
  });
}