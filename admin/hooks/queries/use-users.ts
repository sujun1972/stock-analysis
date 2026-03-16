/**
 * 用户管理相关的 React Query Hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import { queryKeys } from '@/lib/query/keys';
import { getQueryConfig, QUERY_PRESETS } from '@/lib/query/config';
import { toast } from 'sonner';
import { useUserQueryHelper } from '@/hooks/use-query-client';

// 类型定义
export interface User {
  id: string;
  username: string;
  email: string;
  role: 'admin' | 'user';
  is_active: boolean;
  is_email_verified: boolean;
  created_at: string;
  updated_at: string;
  last_login?: string;
  quota?: {
    max_requests_per_day: number;
    used_requests_today: number;
    reset_time: string;
  };
}

export interface UserListParams {
  page?: number;
  page_size?: number;
  search?: string;
  role?: 'admin' | 'user';
  is_active?: boolean;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

export interface UserListResponse {
  items: User[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface CreateUserDto {
  username: string;
  email: string;
  password: string;
  role: 'admin' | 'user';
  is_active?: boolean;
}

export interface UpdateUserDto {
  username?: string;
  email?: string;
  role?: 'admin' | 'user';
  is_active?: boolean;
  password?: string;
}

/**
 * 获取用户列表
 */
export function useUserList(params?: UserListParams) {
  return useQuery({
    queryKey: queryKeys.users.list(params),
    queryFn: async () => {
      const response = await apiClient.getUsers(params);
      if (response.code !== 200) {
        throw new Error(response.message || '获取用户列表失败');
      }
      return response.data as UserListResponse;
    },
    ...getQueryConfig('LIST'),
  });
}

/**
 * 获取单个用户详情
 */
export function useUser(id: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.users.detail(id),
    queryFn: async () => {
      const response = await apiClient.getUser(id);
      if (response.code !== 200) {
        throw new Error(response.message || '获取用户详情失败');
      }
      return response.data as User;
    },
    enabled: enabled && !!id,
    ...getQueryConfig('DETAIL'),
  });
}

/**
 * 创建用户
 */
export function useCreateUser() {
  const queryClient = useQueryClient();
  const { invalidateUserList } = useUserQueryHelper();

  return useMutation({
    mutationFn: async (data: CreateUserDto) => {
      const response = await apiClient.createUser(data);
      if (response.code !== 200) {
        throw new Error(response.message || '创建用户失败');
      }
      return response.data as User;
    },
    onSuccess: (data) => {
      // 使用户列表缓存失效
      invalidateUserList();
      toast.success(`用户 ${data.username} 创建成功`);
    },
    onError: (error: Error) => {
      console.error('创建用户失败:', error);
      toast.error(error.message || '创建用户失败');
    },
  });
}

/**
 * 更新用户信息
 */
export function useUpdateUser() {
  const queryClient = useQueryClient();
  const { invalidateUserList, invalidateUser } = useUserQueryHelper();

  return useMutation({
    mutationFn: async ({ id, data }: { id: string; data: UpdateUserDto }) => {
      const response = await apiClient.updateUser(id, data);
      if (response.code !== 200) {
        throw new Error(response.message || '更新用户失败');
      }
      return response.data as User;
    },
    onSuccess: (data, variables) => {
      // 使用户列表和详情缓存失效
      invalidateUserList();
      invalidateUser(variables.id);
      toast.success('用户信息更新成功');
    },
    onError: (error: Error) => {
      console.error('更新用户失败:', error);
      toast.error(error.message || '更新用户失败');
    },
  });
}

/**
 * 删除用户
 */
export function useDeleteUser() {
  const queryClient = useQueryClient();
  const { invalidateUserList } = useUserQueryHelper();

  return useMutation({
    mutationFn: async (id: string) => {
      const response = await apiClient.deleteUser(id);
      if (response.code !== 200) {
        throw new Error(response.message || '删除用户失败');
      }
      return response.data;
    },
    onSuccess: (_, id) => {
      // 使用户列表缓存失效
      invalidateUserList();
      // 移除用户详情缓存
      queryClient.removeQueries({ queryKey: queryKeys.users.detail(id) });
      toast.success('用户删除成功');
    },
    onError: (error: Error) => {
      console.error('删除用户失败:', error);
      toast.error(error.message || '删除用户失败');
    },
  });
}

/**
 * 批量删除用户
 */
export function useBatchDeleteUsers() {
  const { invalidateUserList } = useUserQueryHelper();

  return useMutation({
    mutationFn: async (ids: string[]) => {
      const results = await Promise.all(
        ids.map((id) => apiClient.deleteUser(id))
      );
      const failed = results.filter((r) => r.code !== 200);
      if (failed.length > 0) {
        throw new Error(`${failed.length} 个用户删除失败`);
      }
      return results;
    },
    onSuccess: (_, ids) => {
      invalidateUserList();
      toast.success(`成功删除 ${ids.length} 个用户`);
    },
    onError: (error: Error) => {
      console.error('批量删除用户失败:', error);
      toast.error(error.message || '批量删除用户失败');
    },
  });
}

/**
 * 重置用户密码
 */
export function useResetUserPassword() {
  const { invalidateUser } = useUserQueryHelper();

  return useMutation({
    mutationFn: async ({ id, password }: { id: string; password: string }) => {
      const response = await apiClient.updateUser(id, { password });
      if (response.code !== 200) {
        throw new Error(response.message || '重置密码失败');
      }
      return response.data;
    },
    onSuccess: (_, variables) => {
      invalidateUser(variables.id);
      toast.success('密码重置成功');
    },
    onError: (error: Error) => {
      console.error('重置密码失败:', error);
      toast.error(error.message || '重置密码失败');
    },
  });
}

/**
 * 重置用户配额
 */
export function useResetUserQuota() {
  const { invalidateUser } = useUserQueryHelper();

  return useMutation({
    mutationFn: async (id: string) => {
      const response = await apiClient.post(`/api/users/${id}/reset-quota`);
      if (response.code !== 200) {
        throw new Error(response.message || '重置配额失败');
      }
      return response.data;
    },
    onSuccess: (_, id) => {
      invalidateUser(id);
      toast.success('配额重置成功');
    },
    onError: (error: Error) => {
      console.error('重置配额失败:', error);
      toast.error(error.message || '重置配额失败');
    },
  });
}

/**
 * 切换用户状态（启用/禁用）
 */
export function useToggleUserStatus() {
  const { invalidateUserList, invalidateUser } = useUserQueryHelper();

  return useMutation({
    mutationFn: async ({ id, is_active }: { id: string; is_active: boolean }) => {
      const response = await apiClient.updateUser(id, { is_active });
      if (response.code !== 200) {
        throw new Error(response.message || '切换用户状态失败');
      }
      return response.data as User;
    },
    onSuccess: (data, variables) => {
      invalidateUserList();
      invalidateUser(variables.id);
      toast.success(
        data.is_active ? '用户已启用' : '用户已禁用'
      );
    },
    onError: (error: Error) => {
      console.error('切换用户状态失败:', error);
      toast.error(error.message || '切换用户状态失败');
    },
  });
}

/**
 * 发送验证邮件
 */
export function useSendVerificationEmail() {
  return useMutation({
    mutationFn: async (id: string) => {
      const response = await apiClient.post(`/api/users/${id}/send-verification`);
      if (response.code !== 200) {
        throw new Error(response.message || '发送验证邮件失败');
      }
      return response.data;
    },
    onSuccess: () => {
      toast.success('验证邮件已发送');
    },
    onError: (error: Error) => {
      console.error('发送验证邮件失败:', error);
      toast.error(error.message || '发送验证邮件失败');
    },
  });
}

/**
 * 搜索用户（用于下拉选择等场景）
 */
export function useSearchUsers(keyword: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.users.list({ search: keyword, page_size: 20 }),
    queryFn: async () => {
      if (!keyword || keyword.length < 2) {
        return { items: [], total: 0 } as UserListResponse;
      }

      const response = await apiClient.getUsers({
        search: keyword,
        page_size: 20,
      });

      if (response.code !== 200) {
        throw new Error(response.message || '搜索用户失败');
      }
      return response.data as UserListResponse;
    },
    enabled: enabled && keyword.length >= 2,
    ...getQueryConfig('SEARCH'),
  });
}

/**
 * 获取用户统计信息
 */
export function useUserStatistics() {
  return useQuery({
    queryKey: [...queryKeys.users.all, 'statistics'],
    queryFn: async () => {
      const response = await apiClient.get('/api/users/statistics');
      if (response.code !== 200) {
        throw new Error(response.message || '获取用户统计失败');
      }
      return response.data as {
        total: number;
        active: number;
        inactive: number;
        admin_count: number;
        user_count: number;
        verified_email_count: number;
      };
    },
    ...getQueryConfig('STATIC'),
  });
}