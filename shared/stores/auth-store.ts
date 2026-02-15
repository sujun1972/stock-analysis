/**
 * 认证状态管理（Zustand）
 * 在Admin和Frontend项目中共享
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { AuthStore, LoginResponse, RegisterRequest, User } from '../types/auth';

// 注意：这里的apiClient需要在各项目中单独配置
// Admin项目使用: admin/lib/api-client
// Frontend项目使用: frontend/src/lib/api-client

const TOKEN_STORAGE_KEY = 'auth_tokens';
const USER_STORAGE_KEY = 'auth_user';

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // 状态
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // 登录
      login: async (email: string, password: string) => {
        set({ isLoading: true, error: null });
        try {
          // 动态导入apiClient（避免循环依赖）
          const { apiClient } = await import('./api-client-instance');

          const response = await apiClient.post<LoginResponse>('/auth/login', {
            email,
            password,
          });

          const { access_token, refresh_token, user } = response.data;

          set({
            user,
            accessToken: access_token,
            refreshToken: refresh_token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });

          // 保存到localStorage
          localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify({
            accessToken: access_token,
            refreshToken: refresh_token,
          }));
          localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
        } catch (error: any) {
          const errorMessage = error.response?.data?.detail || '登录失败，请检查邮箱和密码';
          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
            isLoading: false,
            error: errorMessage,
          });
          throw new Error(errorMessage);
        }
      },

      // 注册
      register: async (data: RegisterRequest) => {
        set({ isLoading: true, error: null });
        try {
          const { apiClient } = await import('./api-client-instance');

          await apiClient.post('/auth/register', data);

          set({
            isLoading: false,
            error: null,
          });
        } catch (error: any) {
          const errorMessage = error.response?.data?.detail || '注册失败';
          set({
            isLoading: false,
            error: errorMessage,
          });
          throw new Error(errorMessage);
        }
      },

      // 登出
      logout: async () => {
        const { refreshToken } = get();

        try {
          const { apiClient } = await import('./api-client-instance');

          if (refreshToken) {
            // 撤销refresh token
            await apiClient.post('/auth/logout', {
              refresh_token: refreshToken,
            }).catch(() => {
              // 忽略登出错误
            });
          }
        } catch (error) {
          // 忽略错误，继续登出
        } finally {
          // 清除状态
          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
            error: null,
          });

          // 清除localStorage
          localStorage.removeItem(TOKEN_STORAGE_KEY);
          localStorage.removeItem(USER_STORAGE_KEY);
        }
      },

      // 刷新Token
      refreshAccessToken: async () => {
        const { refreshToken } = get();

        if (!refreshToken) {
          throw new Error('没有刷新令牌');
        }

        try {
          const { apiClient } = await import('./api-client-instance');

          const response = await apiClient.post('/auth/refresh', {
            refresh_token: refreshToken,
          });

          const { access_token, refresh_token: new_refresh_token } = response.data;

          set({
            accessToken: access_token,
            refreshToken: new_refresh_token,
          });

          // 更新localStorage
          localStorage.setItem(TOKEN_STORAGE_KEY, JSON.stringify({
            accessToken: access_token,
            refreshToken: new_refresh_token,
          }));
        } catch (error) {
          // Token刷新失败，清除登录状态
          get().logout();
          throw error;
        }
      },

      // 更新个人资料
      updateProfile: async (data: Partial<User>) => {
        set({ isLoading: true, error: null });
        try {
          const { apiClient } = await import('./api-client-instance');

          const response = await apiClient.patch<User>('/profile', data);

          set({
            user: response.data,
            isLoading: false,
            error: null,
          });

          // 更新localStorage
          localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(response.data));
        } catch (error: any) {
          const errorMessage = error.response?.data?.detail || '更新失败';
          set({
            isLoading: false,
            error: errorMessage,
          });
          throw new Error(errorMessage);
        }
      },

      // 检查认证状态（从localStorage恢复或验证Token）
      checkAuth: async () => {
        const { accessToken } = get();

        if (!accessToken) {
          // 尝试从localStorage恢复
          const storedTokens = localStorage.getItem(TOKEN_STORAGE_KEY);
          const storedUser = localStorage.getItem(USER_STORAGE_KEY);

          if (storedTokens && storedUser) {
            const tokens = JSON.parse(storedTokens);
            const user = JSON.parse(storedUser);

            set({
              user,
              accessToken: tokens.accessToken,
              refreshToken: tokens.refreshToken,
              isAuthenticated: true,
            });
          }
          return;
        }

        // 验证Token是否有效
        try {
          const { apiClient } = await import('./api-client-instance');

          const response = await apiClient.get<User>('/auth/me');

          set({
            user: response.data,
            isAuthenticated: true,
          });

          // 更新localStorage中的用户信息
          localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(response.data));
        } catch (error) {
          // Token无效，尝试刷新
          try {
            await get().refreshAccessToken();
            await get().checkAuth(); // 递归验证
          } catch (refreshError) {
            // 刷新失败，清除登录状态
            get().logout();
          }
        }
      },

      // 清除错误
      clearError: () => {
        set({ error: null });
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        // 只持久化这些字段
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);

// 辅助函数：获取当前Token
export const getAccessToken = () => useAuthStore.getState().accessToken;
export const getRefreshToken = () => useAuthStore.getState().refreshToken;

// 辅助函数：检查是否为管理员
export const isAdmin = () => {
  const user = useAuthStore.getState().user;
  return user?.role === 'admin' || user?.role === 'super_admin';
};

export const isSuperAdmin = () => {
  const user = useAuthStore.getState().user;
  return user?.role === 'super_admin';
};
