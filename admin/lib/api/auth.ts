/**
 * @file lib/api/auth.ts
 * @description 认证相关 API
 * @author Claude
 * @created 2024-03-16
 * @updated 2024-03-16
 */

import { BaseApiClient } from './base'
import { ApiResponse } from '@/types/api'

export interface LoginRequest {
  email: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: {
    id: number
    email: string
    full_name: string | null
    role: string
    is_active: boolean
  }
}

export interface RegisterRequest {
  email: string
  password: string
  full_name?: string
  role?: string
}

export interface UpdatePasswordRequest {
  old_password: string
  new_password: string
}

export interface UpdateProfileRequest {
  full_name?: string
  email?: string
}

/**
 * 认证 API 客户端
 */
export class AuthApiClient extends BaseApiClient {
  /**
   * 用户登录
   */
  async login(data: LoginRequest): Promise<ApiResponse<LoginResponse>> {
    return this.post('/api/auth/login', data)
  }

  /**
   * 用户注册
   */
  async register(data: RegisterRequest): Promise<ApiResponse<LoginResponse>> {
    return this.post('/api/auth/register', data)
  }

  /**
   * 刷新Token
   */
  async refresh(refreshToken: string): Promise<ApiResponse<{
    access_token: string
    refresh_token: string
    token_type: string
  }>> {
    return this.post('/api/auth/refresh', { refresh_token: refreshToken })
  }

  /**
   * 用户登出
   */
  async logout(): Promise<ApiResponse<{ message: string }>> {
    return this.post('/api/auth/logout')
  }

  /**
   * 获取当前用户信息
   */
  async getCurrentUser(): Promise<ApiResponse<{
    id: number
    email: string
    full_name: string | null
    role: string
    is_active: boolean
    created_at: string
    updated_at: string
  }>> {
    return this.get('/api/auth/me')
  }

  /**
   * 更新密码
   */
  async updatePassword(data: UpdatePasswordRequest): Promise<ApiResponse<{ message: string }>> {
    return this.post('/api/auth/change-password', data)
  }

  /**
   * 更新用户资料
   */
  async updateProfile(data: UpdateProfileRequest): Promise<ApiResponse<{
    id: number
    email: string
    full_name: string | null
    role: string
  }>> {
    return this.patch('/api/auth/profile', data)
  }

  /**
   * 请求重置密码
   */
  async requestPasswordReset(email: string): Promise<ApiResponse<{ message: string }>> {
    return this.post('/api/auth/request-password-reset', { email })
  }

  /**
   * 重置密码
   */
  async resetPassword(token: string, newPassword: string): Promise<ApiResponse<{ message: string }>> {
    return this.post('/api/auth/reset-password', {
      token,
      new_password: newPassword
    })
  }
}

export const authApi = new AuthApiClient()