/**
 * 用户认证相关类型定义
 */

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

export interface UserQuota {
  id: number;
  user_id: number;
  backtest_quota_total: number;
  backtest_quota_used: number;
  backtest_quota_reset_at: string | null;
  ml_prediction_quota_total: number;
  ml_prediction_quota_used: number;
  ml_prediction_quota_reset_at: string | null;
  max_strategies: number;
  current_strategies: number;
  created_at: string;
  updated_at: string;
}

export interface UserWithQuota extends User {
  quota: UserQuota | null;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
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
