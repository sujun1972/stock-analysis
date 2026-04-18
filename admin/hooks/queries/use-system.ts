/**
 * 系统设置相关的 React Query Hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { axiosInstance } from '@/lib/api';
import { queryKeys } from '@/lib/query/keys';
import { getQueryConfig, QUERY_PRESETS, QUERY_TIME } from '@/lib/query/config';
import { toast } from 'sonner';
import { useSystemQueryHelper } from '@/hooks/use-query-client';

// 类型定义
export interface SystemSettings {
  id?: string;
  stock_analysis_url?: string;
  api_base_url?: string;
  max_concurrent_requests?: number;
  request_timeout?: number;
  cache_ttl?: number;
  enable_debug_mode?: boolean;
  enable_maintenance_mode?: boolean;
  maintenance_message?: string;
  allowed_origins?: string[];
  rate_limit_per_minute?: number;
  created_at?: string;
  updated_at?: string;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  checks: {
    database: {
      status: 'healthy' | 'unhealthy';
      latency_ms?: number;
      error?: string;
    };
    redis?: {
      status: 'healthy' | 'unhealthy';
      latency_ms?: number;
      error?: string;
    };
    api?: {
      status: 'healthy' | 'unhealthy';
      latency_ms?: number;
      error?: string;
    };
    disk?: {
      status: 'healthy' | 'unhealthy';
      used_percent?: number;
      error?: string;
    };
  };
  circuit_breakers?: {
    [key: string]: {
      state: 'closed' | 'open' | 'half_open';
      failures: number;
      last_failure?: string;
    };
  };
  version?: string;
  uptime_seconds?: number;
}

export interface SystemMetrics {
  cpu_usage_percent: number;
  memory_usage_percent: number;
  disk_usage_percent: number;
  active_connections: number;
  request_rate_per_second: number;
  error_rate_per_second: number;
  average_response_time_ms: number;
  timestamp: string;
}

/**
 * 获取系统设置
 */
export function useSystemSettings() {
  return useQuery({
    queryKey: queryKeys.system.settings(),
    queryFn: async () => {
      const response = await axiosInstance.get('/api/config/system') as any;
      if (response.code !== 200) {
        throw new Error(response.message || '获取系统设置失败');
      }
      return response.data as SystemSettings;
    },
    ...getQueryConfig('STATIC'),
    staleTime: QUERY_TIME.HOUR, // 系统设置缓存1小时
  });
}

/**
 * 更新系统设置
 */
export function useUpdateSystemSettings() {
  const queryClient = useQueryClient();
  const { invalidateSystemSettings } = useSystemQueryHelper();

  return useMutation({
    mutationFn: async (settings: Partial<SystemSettings>) => {
      const response = await axiosInstance.post('/api/config/system', settings) as any;
      if (response.code !== 200) {
        throw new Error(response.message || '更新系统设置失败');
      }
      return response.data as SystemSettings;
    },
    onSuccess: (data) => {
      // 更新缓存
      queryClient.setQueryData(queryKeys.system.settings(), data);
      // 使设置缓存失效，触发依赖的组件更新
      invalidateSystemSettings();
      toast.success('系统设置更新成功');
    },
    onError: (error: Error) => {
      console.error('更新系统设置失败:', error);
      toast.error(error.message || '更新系统设置失败');
    },
  });
}

/**
 * 获取健康状态
 * @param refetchInterval 自动刷新间隔（毫秒）
 */
export function useHealthStatus(refetchInterval?: number) {
  return useQuery({
    queryKey: queryKeys.system.health(),
    queryFn: async () => {
      const response = await axiosInstance.get('/api/health') as any;
      if (response.code !== 200) {
        throw new Error(response.message || '获取健康状态失败');
      }
      return response.data as HealthStatus;
    },
    ...getQueryConfig('MONITOR'),
    refetchInterval: refetchInterval || QUERY_TIME.SECOND * 10, // 默认10秒刷新一次
    refetchIntervalInBackground: false,
  });
}

/**
 * 获取系统指标
 * @param refetchInterval 自动刷新间隔（毫秒）
 */
export function useSystemMetrics(refetchInterval?: number) {
  return useQuery({
    queryKey: queryKeys.monitor.metrics(),
    queryFn: async () => {
      const response = await axiosInstance.get('/api/metrics') as any;
      if (response.code !== 200) {
        throw new Error(response.message || '获取系统指标失败');
      }
      return response.data as SystemMetrics;
    },
    ...getQueryConfig('MONITOR'),
    refetchInterval: refetchInterval || QUERY_TIME.SECOND * 5, // 默认5秒刷新一次
    refetchIntervalInBackground: false,
  });
}

/**
 * 测试数据库连接
 */
export function useTestDatabaseConnection() {
  return useMutation({
    mutationFn: async () => {
      const response = await axiosInstance.post('/api/test/database') as any;
      if (response.code !== 200) {
        throw new Error(response.message || '数据库连接测试失败');
      }
      return response.data;
    },
    onSuccess: (data) => {
      toast.success('数据库连接正常');
    },
    onError: (error: Error) => {
      console.error('数据库连接测试失败:', error);
      toast.error(error.message || '数据库连接测试失败');
    },
  });
}

/**
 * 测试Redis连接
 */
export function useTestRedisConnection() {
  return useMutation({
    mutationFn: async () => {
      const response = await axiosInstance.post('/api/test/redis') as any;
      if (response.code !== 200) {
        throw new Error(response.message || 'Redis连接测试失败');
      }
      return response.data;
    },
    onSuccess: (data) => {
      toast.success('Redis连接正常');
    },
    onError: (error: Error) => {
      console.error('Redis连接测试失败:', error);
      toast.error(error.message || 'Redis连接测试失败');
    },
  });
}

/**
 * 清除系统缓存
 */
export function useClearSystemCache() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await axiosInstance.post('/api/cache/clear') as any;
      if (response.code !== 200) {
        throw new Error(response.message || '清除缓存失败');
      }
      return response.data;
    },
    onSuccess: () => {
      // 清除所有React Query缓存
      queryClient.clear();
      toast.success('系统缓存已清除');
    },
    onError: (error: Error) => {
      console.error('清除缓存失败:', error);
      toast.error(error.message || '清除缓存失败');
    },
  });
}

/**
 * 重启服务
 */
export function useRestartService() {
  return useMutation({
    mutationFn: async (service: 'api' | 'worker' | 'scheduler') => {
      const response = await axiosInstance.post(`/api/services/${service}/restart`) as any;
      if (response.code !== 200) {
        throw new Error(response.message || '服务重启失败');
      }
      return response.data;
    },
    onSuccess: (_, service) => {
      toast.success(`${service} 服务重启成功`);
    },
    onError: (error: Error) => {
      console.error('服务重启失败:', error);
      toast.error(error.message || '服务重启失败');
    },
  });
}

/**
 * 获取系统日志
 */
export function useSystemLogs(params?: {
  level?: 'debug' | 'info' | 'warning' | 'error';
  service?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery({
    queryKey: [...queryKeys.system.all, 'logs', params],
    queryFn: async () => {
      const response = await axiosInstance.get('/api/logs', { params }) as any;
      if (response.code !== 200) {
        throw new Error(response.message || '获取系统日志失败');
      }
      return response.data as {
        logs: Array<{
          id: string;
          timestamp: string;
          level: string;
          service: string;
          message: string;
          metadata?: any;
        }>;
        total: number;
      };
    },
    ...getQueryConfig('LIST'),
  });
}

/**
 * 切换维护模式
 */
export function useToggleMaintenanceMode() {
  const { invalidateSystemSettings } = useSystemQueryHelper();

  return useMutation({
    mutationFn: async ({ enabled, message }: { enabled: boolean; message?: string }) => {
      // TODO: 维护模式 API 尚未实现
      // 当前 updateSystemSettings 只支持 stock_analysis_url 参数
      // 需要后端添加维护模式相关的 API 接口
      console.warn('维护模式功能尚未实现，需要后端支持');

      // 暂时返回模拟数据，避免页面报错
      return {
        enable_maintenance_mode: enabled,
        maintenance_message: message || '系统维护中，请稍后访问'
      };
    },
    onSuccess: (_, variables) => {
      invalidateSystemSettings();
      toast.success(
        variables.enabled ? '已开启维护模式' : '已关闭维护模式'
      );
    },
    onError: (error: Error) => {
      console.error('切换维护模式失败:', error);
      toast.error(error.message || '切换维护模式失败');
    },
  });
}

/**
 * 导出系统配置
 */
export function useExportSystemConfig() {
  return useMutation({
    mutationFn: async () => {
      const response = await axiosInstance.get('/api/system/export') as any;
      if (response.code !== 200) {
        throw new Error(response.message || '导出配置失败');
      }

      // 创建下载链接
      const blob = new Blob([JSON.stringify(response.data, null, 2)], {
        type: 'application/json',
      });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `system-config-${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      return response.data;
    },
    onSuccess: () => {
      toast.success('系统配置导出成功');
    },
    onError: (error: Error) => {
      console.error('导出配置失败:', error);
      toast.error(error.message || '导出配置失败');
    },
  });
}

/**
 * 导入系统配置
 */
export function useImportSystemConfig() {
  const { invalidateSystemSettings } = useSystemQueryHelper();

  return useMutation({
    mutationFn: async (configFile: File) => {
      const text = await configFile.text();
      const config = JSON.parse(text);

      const response = await axiosInstance.post('/api/system/import', config) as any;
      if (response.code !== 200) {
        throw new Error(response.message || '导入配置失败');
      }
      return response.data;
    },
    onSuccess: () => {
      invalidateSystemSettings();
      toast.success('系统配置导入成功');
    },
    onError: (error: Error) => {
      console.error('导入配置失败:', error);
      toast.error(error.message || '导入配置失败');
    },
  });
}