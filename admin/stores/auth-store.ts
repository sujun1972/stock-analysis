/**
 * Admin项目认证Store (Zustand)
 *
 * 功能:
 * 1. 管理用户登录状态和Token
 * 2. 自动Token刷新机制
 * 3. localStorage持久化
 *
 * 优化:
 * - checkAuth不再调用API，只从localStorage恢复状态
 * - 登录时已获取完整用户信息，无需重复请求
 * - Token刷新在请求拦截器中自动处理
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

// 先设置API客户端实例
import { apiClient } from '@/lib/api-client'

if (typeof window !== 'undefined') {
  ;(window as any).__apiClientInstance = apiClient
}

// 类型定义
export type UserRole = 'super_admin' | 'admin' | 'vip_user' | 'normal_user' | 'trial_user';

export interface User {
  id: number;
  email: string;
  username: string;
  role: UserRole;
  is_active: boolean;
  is_email_verified: boolean;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
  login_count: number;
  full_name: string | null;
  avatar_url: string | null;
  phone: string | null;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface AuthActions {
  login: (email: string, password: string) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshAccessToken: () => Promise<void>;
  updateProfile: (data: Partial<User>) => Promise<void>;
  checkAuth: () => Promise<void>;
  clearError: () => void;
}

export type AuthStore = AuthState & AuthActions;

// 已移除冗余的 TOKEN_STORAGE_KEY 和 USER_STORAGE_KEY
// 现在统一使用 Zustand persist 中间件管理 localStorage (键名: 'auth-storage')

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
          // 注意：/api/auth/login 直接返回数据，不包裹在 ApiResponse 中
          const response = await apiClient.post<{
            access_token: string;
            refresh_token: string;
            user: User;
          }>('/api/auth/login', {
            email,
            password,
          });

          // 认证端点直接返回数据对象（不在 response.data 中）
          const { access_token, refresh_token, user } = response as any;

          set({
            user,
            accessToken: access_token,
            refreshToken: refresh_token,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });

          // Zustand persist 中间件会自动保存到 localStorage (键名: 'auth-storage')
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
          await apiClient.post('/api/auth/register', data);

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
          if (refreshToken) {
            // 撤销refresh token
            await apiClient.post('/api/auth/logout', {
              refresh_token: refreshToken,
            }).catch(() => {
              // 忽略登出错误
            });
          }
        } catch (error) {
          // 忽略错误，继续登出
        } finally {
          // 清除状态 (Zustand persist 会自动同步到 localStorage)
          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
            error: null,
          });
        }
      },

      // 刷新Token
      refreshAccessToken: async () => {
        const { refreshToken } = get();

        if (!refreshToken) {
          const error = new Error('没有刷新令牌');
          console.error('Token refresh failed: no refresh token available');
          throw error;
        }

        try {
          // 注意：/api/auth/refresh 直接返回数据，不包裹在 ApiResponse 中
          const response = await apiClient.post<{
            access_token: string;
            refresh_token: string;
          }>('/api/auth/refresh', {
            refresh_token: refreshToken,
          });

          // 认证端点直接返回数据对象（不在 response.data 中）
          const { access_token, refresh_token: new_refresh_token } = response as any;

          set({
            accessToken: access_token,
            refreshToken: new_refresh_token,
          });

          // Zustand persist 中间件会自动保存到 localStorage (键名: 'auth-storage')
        } catch (error: any) {
          // Token刷新失败，清除登录状态
          console.error('Token refresh failed:', error.message || error);

          // 记录错误详情以便调试
          if (error.response) {
            console.error('Refresh error response:', {
              status: error.response.status,
              data: error.response.data,
            });
          }

          // 清除登录状态（会触发登出流程）
          get().logout();
          throw error;
        }
      },

      // 更新个人资料
      updateProfile: async (data: Partial<User>) => {
        set({ isLoading: true, error: null });
        try {
          const response = await apiClient.patch<User>('/api/profile', data);

          if (!response.data) {
            throw new Error('更新响应数据为空');
          }

          set({
            user: response.data,
            isLoading: false,
            error: null,
          });

          // Zustand persist 中间件会自动保存到 localStorage (键名: 'auth-storage')
        } catch (error: any) {
          const errorMessage = error.response?.data?.detail || '更新失败';
          set({
            isLoading: false,
            error: errorMessage,
          });
          throw new Error(errorMessage);
        }
      },

      /**
       * 检查认证状态（从localStorage恢复,不调用API）
       *
       * 优化说明:
       * - 不再调用 /api/auth/me 验证Token
       * - Zustand persist 中间件会自动从 localStorage 恢复状态
       * - Token验证在请求拦截器中自动处理
       * - 避免页面切换时的重复API调用
       */
      checkAuth: async () => {
        const { accessToken, user } = get();

        // 如果已经有用户信息,直接返回,不需要再次验证
        // Zustand persist 中间件会自动在初始化时恢复状态
        if (accessToken && user) {
          return;
        }

        // 状态已由 Zustand persist 中间件自动恢复
        // 如果没有恢复到数据，说明用户未登录或数据已过期
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
