/**
 * 通知渠道相关的 React Query Hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { queryKeys } from '@/lib/query/keys';
import { getQueryConfig, QUERY_TIME } from '@/lib/query/config';
import { toast } from 'sonner';

// 类型定义
export interface NotificationChannel {
  channel_type: 'email' | 'telegram' | 'webhook' | 'sms';
  is_enabled: boolean;
  config: {
    // Email配置
    smtp_host?: string;
    smtp_port?: number;
    smtp_username?: string;
    smtp_password?: string;
    smtp_use_tls?: boolean;
    from_email?: string;
    to_emails?: string[];

    // Telegram配置
    bot_token?: string;
    chat_id?: string;

    // Webhook配置
    webhook_url?: string;
    webhook_method?: 'GET' | 'POST';
    webhook_headers?: Record<string, string>;

    // SMS配置
    sms_provider?: string;
    sms_api_key?: string;
    sms_from?: string;
    sms_to?: string[];
  };
  test_status?: {
    last_test_at?: string;
    last_test_result?: 'success' | 'failed';
    last_test_message?: string;
  };
  created_at?: string;
  updated_at?: string;
}

export interface ScheduledTask {
  id: string;
  name: string;
  task_type: string;
  schedule: {
    cron?: string;
    interval?: string;
    time?: string;
    weekdays?: number[];
    enabled: boolean;
  };
  config: Record<string, any>;
  notification_channels?: string[];
  is_active: boolean;
  last_run?: {
    executed_at: string;
    status: 'success' | 'failed';
    duration_seconds: number;
    error?: string;
  };
  next_run?: string;
  created_at: string;
  updated_at: string;
}

export interface NotificationTemplate {
  id: string;
  name: string;
  channel_type: string;
  template_type: string;
  subject?: string;
  content: string;
  variables?: string[];
  is_default?: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * 获取通知渠道列表
 */
export function useNotificationChannels() {
  return useQuery({
    queryKey: queryKeys.notifications.channels(),
    queryFn: async () => {
      const response = await apiClient.getNotificationChannels();
      if (response?.code !== 200) {
        throw new Error(response?.message || '获取通知渠道失败');
      }
      return response.data as NotificationChannel[];
    },
    ...getQueryConfig('STATIC'),
    staleTime: QUERY_TIME.HOUR,
  });
}

/**
 * 获取单个通知渠道配置
 */
export function useNotificationChannel(channelType: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.notifications.channel(channelType),
    queryFn: async () => {
      const response = await apiClient.get(`/api/notification-channels/${channelType}`);
      if (response.code !== 200) {
        throw new Error(response.message || '获取通知渠道配置失败');
      }
      return response.data as NotificationChannel;
    },
    enabled,
    ...getQueryConfig('STATIC'),
  });
}

/**
 * 更新通知渠道配置
 */
export function useUpdateNotificationChannel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      channelType,
      config,
    }: {
      channelType: string;
      config: NotificationChannel['config'];
    }) => {
      const response = await apiClient.patch(`/api/notification-channels/${channelType}`, {
        config,
      });
      if (response.code !== 200) {
        throw new Error(response.message || '更新通知渠道失败');
      }
      return response.data as NotificationChannel;
    },
    onSuccess: (data, variables) => {
      // 更新缓存
      queryClient.setQueryData(
        queryKeys.notifications.channel(variables.channelType),
        data
      );
      queryClient.invalidateQueries({
        queryKey: queryKeys.notifications.channels(),
      });
      toast.success('通知渠道配置已更新');
    },
    onError: (error: Error) => {
      console.error('更新通知渠道失败:', error);
      toast.error(error.message || '更新通知渠道失败');
    },
  });
}

/**
 * 切换通知渠道状态
 */
export function useToggleNotificationChannel() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (channelType: string) => {
      const response = await apiClient.toggleNotificationChannel(channelType);
      if (response.code !== 200) {
        throw new Error(response.message || '切换通知渠道状态失败');
      }
      return response.data as NotificationChannel;
    },
    onSuccess: (data, channelType) => {
      queryClient.setQueryData(
        queryKeys.notifications.channel(channelType),
        data
      );
      queryClient.invalidateQueries({
        queryKey: queryKeys.notifications.channels(),
      });
      toast.success(
        data.is_enabled ? '通知渠道已启用' : '通知渠道已禁用'
      );
    },
    onError: (error: Error) => {
      console.error('切换通知渠道状态失败:', error);
      toast.error(error.message || '切换通知渠道状态失败');
    },
  });
}

/**
 * 测试通知渠道
 */
export function useTestNotificationChannel() {
  return useMutation({
    mutationFn: async ({
      channelType,
      testMessage,
    }: {
      channelType: string;
      testMessage?: string;
    }) => {
      const response = await apiClient.testNotificationChannel(
        channelType,
        testMessage || '这是一条测试消息'
      );
      if (response.code !== 200) {
        throw new Error(response.message || '测试通知渠道失败');
      }
      return response.data;
    },
    onSuccess: () => {
      toast.success('测试消息已发送');
    },
    onError: (error: Error) => {
      console.error('测试通知渠道失败:', error);
      toast.error(error.message || '测试通知渠道失败');
    },
  });
}

/**
 * 获取定时任务列表
 */
export function useScheduledTasks(params?: {
  task_type?: string;
  is_active?: boolean;
  page?: number;
  page_size?: number;
}) {
  return useQuery({
    queryKey: queryKeys.notifications.scheduledTasks(),
    queryFn: async () => {
      const response = await apiClient.getScheduledTasks();
      if (response.code !== 200) {
        throw new Error(response.message || '获取定时任务失败');
      }
      return response.data as {
        items: ScheduledTask[];
        total: number;
      };
    },
    ...getQueryConfig('LIST'),
  });
}

/**
 * 获取单个定时任务
 */
export function useScheduledTask(taskId: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.notifications.scheduledTask(taskId),
    queryFn: async () => {
      const response = await apiClient.get(`/api/scheduled-tasks/${taskId}`);
      if (response.code !== 200) {
        throw new Error(response.message || '获取定时任务详情失败');
      }
      return response.data as ScheduledTask;
    },
    enabled,
    ...getQueryConfig('DETAIL'),
  });
}

/**
 * 创建定时任务
 */
export function useCreateScheduledTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (task: Omit<ScheduledTask, 'id' | 'created_at' | 'updated_at'>) => {
      const response = await apiClient.createScheduledTask(task);
      if (response.code !== 200) {
        throw new Error(response.message || '创建定时任务失败');
      }
      return response.data as ScheduledTask;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: queryKeys.notifications.scheduledTasks(),
      });
      toast.success('定时任务创建成功');
    },
    onError: (error: Error) => {
      console.error('创建定时任务失败:', error);
      toast.error(error.message || '创建定时任务失败');
    },
  });
}

/**
 * 更新定时任务
 */
export function useUpdateScheduledTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      taskId,
      updates,
    }: {
      taskId: string;
      updates: Partial<ScheduledTask>;
    }) => {
      const response = await apiClient.updateScheduledTask(taskId, updates);
      if (response.code !== 200) {
        throw new Error(response.message || '更新定时任务失败');
      }
      return response.data as ScheduledTask;
    },
    onSuccess: (data, variables) => {
      queryClient.setQueryData(
        queryKeys.notifications.scheduledTask(variables.taskId),
        data
      );
      queryClient.invalidateQueries({
        queryKey: queryKeys.notifications.scheduledTasks(),
      });
      toast.success('定时任务更新成功');
    },
    onError: (error: Error) => {
      console.error('更新定时任务失败:', error);
      toast.error(error.message || '更新定时任务失败');
    },
  });
}

/**
 * 删除定时任务
 */
export function useDeleteScheduledTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (taskId: string) => {
      const response = await apiClient.deleteScheduledTask(taskId);
      if (response.code !== 200) {
        throw new Error(response.message || '删除定时任务失败');
      }
      return response.data;
    },
    onSuccess: (_, taskId) => {
      queryClient.removeQueries({
        queryKey: queryKeys.notifications.scheduledTask(taskId),
      });
      queryClient.invalidateQueries({
        queryKey: queryKeys.notifications.scheduledTasks(),
      });
      toast.success('定时任务已删除');
    },
    onError: (error: Error) => {
      console.error('删除定时任务失败:', error);
      toast.error(error.message || '删除定时任务失败');
    },
  });
}

/**
 * 立即执行定时任务
 */
export function useRunScheduledTask() {
  return useMutation({
    mutationFn: async (taskId: string) => {
      const response = await apiClient.post(`/api/scheduled-tasks/${taskId}/run`);
      if (response.code !== 200) {
        throw new Error(response.message || '执行定时任务失败');
      }
      return response.data;
    },
    onSuccess: () => {
      toast.success('定时任务已开始执行');
    },
    onError: (error: Error) => {
      console.error('执行定时任务失败:', error);
      toast.error(error.message || '执行定时任务失败');
    },
  });
}

/**
 * 切换定时任务状态
 */
export function useToggleScheduledTask() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (taskId: string) => {
      const response = await apiClient.post(`/api/scheduled-tasks/${taskId}/toggle`);
      if (response.code !== 200) {
        throw new Error(response.message || '切换任务状态失败');
      }
      return response.data as ScheduledTask;
    },
    onSuccess: (data, taskId) => {
      queryClient.setQueryData(
        queryKeys.notifications.scheduledTask(taskId),
        data
      );
      queryClient.invalidateQueries({
        queryKey: queryKeys.notifications.scheduledTasks(),
      });
      toast.success(
        data.is_active ? '定时任务已启用' : '定时任务已禁用'
      );
    },
    onError: (error: Error) => {
      console.error('切换任务状态失败:', error);
      toast.error(error.message || '切换任务状态失败');
    },
  });
}

/**
 * 获取通知模板列表
 */
export function useNotificationTemplates(channelType?: string) {
  return useQuery({
    queryKey: [...queryKeys.notifications.all, 'templates', channelType],
    queryFn: async () => {
      const response = await apiClient.get('/api/notification-templates', {
        params: { channel_type: channelType },
      });
      if (response.code !== 200) {
        throw new Error(response.message || '获取通知模板失败');
      }
      return response.data as NotificationTemplate[];
    },
    ...getQueryConfig('STATIC'),
  });
}

/**
 * 发送测试通知
 */
export function useSendTestNotification() {
  return useMutation({
    mutationFn: async (params: {
      channel_type: string;
      template_id?: string;
      variables?: Record<string, any>;
      recipients?: string[];
    }) => {
      const response = await apiClient.post('/api/notifications/send-test', params);
      if (response.code !== 200) {
        throw new Error(response.message || '发送测试通知失败');
      }
      return response.data;
    },
    onSuccess: () => {
      toast.success('测试通知已发送');
    },
    onError: (error: Error) => {
      console.error('发送测试通知失败:', error);
      toast.error(error.message || '发送测试通知失败');
    },
  });
}