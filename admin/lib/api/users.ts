/**
 * @file lib/api/users.ts
 * @description 用户管理相关 API
 * @author Claude
 * @created 2024-03-16
 * @updated 2024-03-16
 */

import { BaseApiClient } from './base'
import { ApiResponse, PaginatedResponse } from '@/types/api'

export interface User {
  id: number
  email: string
  full_name: string | null
  role: string
  is_active: boolean
  created_at: string
  updated_at: string
  last_login?: string
  login_count?: number
}

export interface UserListParams {
  page?: number
  page_size?: number
  search?: string
  role?: string
  is_active?: boolean
  sort_by?: string
  sort_order?: string
}

export interface CreateUserRequest {
  email: string
  password: string
  full_name?: string
  role?: string
  is_active?: boolean
}

export interface UpdateUserRequest {
  email?: string
  full_name?: string
  role?: string
  is_active?: boolean
  password?: string
}

export interface UserStatistics {
  total_users: number
  active_users: number
  users_by_role: Record<string, number>
  new_users_today: number
  new_users_this_week: number
  new_users_this_month: number
}

export interface UserQuota {
  user_id: number
  max_strategies: number
  used_strategies: number
  max_api_calls_per_day: number
  used_api_calls_today: number
  max_storage_mb: number
  used_storage_mb: number
  expires_at?: string
}

/**
 * 用户管理 API 客户端
 */
export class UserApiClient extends BaseApiClient {
  /**
   * 获取用户列表
   */
  async getUsers(params?: UserListParams): Promise<ApiResponse<PaginatedResponse<User>>> {
    return this.get('/api/users', { params })
  }

  /**
   * 获取单个用户详情
   */
  async getUser(id: number): Promise<ApiResponse<User>> {
    return this.get(`/api/users/${id}`)
  }

  /**
   * 创建用户
   */
  async createUser(data: CreateUserRequest): Promise<ApiResponse<User>> {
    return this.post('/api/users', data)
  }

  /**
   * 更新用户
   */
  async updateUser(id: number, data: UpdateUserRequest): Promise<ApiResponse<User>> {
    return this.patch(`/api/users/${id}`, data)
  }

  /**
   * 删除用户
   */
  async deleteUser(id: number): Promise<ApiResponse<{ message: string }>> {
    return this.delete(`/api/users/${id}`)
  }

  /**
   * 批量删除用户
   */
  async batchDeleteUsers(ids: number[]): Promise<ApiResponse<{
    deleted_count: number
    failed_ids: number[]
  }>> {
    return this.post('/api/users/batch-delete', { ids })
  }

  /**
   * 激活/停用用户
   */
  async toggleUserStatus(id: number, active: boolean): Promise<ApiResponse<User>> {
    return this.patch(`/api/users/${id}`, { is_active: active })
  }

  /**
   * 重置用户密码
   */
  async resetUserPassword(id: number, newPassword: string): Promise<ApiResponse<{ message: string }>> {
    return this.post(`/api/users/${id}/reset-password`, { new_password: newPassword })
  }

  /**
   * 发送密码重置邮件
   */
  async sendPasswordResetEmail(id: number): Promise<ApiResponse<{ message: string }>> {
    return this.post(`/api/users/${id}/send-reset-email`)
  }

  /**
   * 获取用户统计信息
   */
  async getUserStatistics(): Promise<ApiResponse<UserStatistics>> {
    return this.get('/api/users/statistics')
  }

  /**
   * 获取用户配额信息
   */
  async getUserQuota(id: number): Promise<ApiResponse<UserQuota>> {
    return this.get(`/api/users/${id}/quota`)
  }

  /**
   * 更新用户配额
   */
  async updateUserQuota(id: number, quota: Partial<UserQuota>): Promise<ApiResponse<UserQuota>> {
    return this.patch(`/api/users/${id}/quota`, quota)
  }

  /**
   * 获取用户活动日志
   */
  async getUserActivityLog(id: number, params?: {
    page?: number
    page_size?: number
    start_date?: string
    end_date?: string
    action_type?: string
  }): Promise<ApiResponse<PaginatedResponse<{
    id: number
    user_id: number
    action: string
    resource?: string
    resource_id?: number
    ip_address?: string
    user_agent?: string
    created_at: string
  }>>> {
    return this.get(`/api/users/${id}/activity-log`, { params })
  }

  /**
   * 导出用户列表
   */
  async exportUsers(format: 'csv' | 'excel' = 'csv', params?: UserListParams): Promise<Blob> {
    const response = await this.instance.get('/api/users/export', {
      params: { format, ...params },
      responseType: 'blob'
    })
    return response.data
  }

  /**
   * 批量导入用户
   */
  async importUsers(file: File): Promise<ApiResponse<{
    imported_count: number
    failed_count: number
    errors?: Array<{ row: number; error: string }>
  }>> {
    const formData = new FormData()
    formData.append('file', file)

    return this.post('/api/users/import', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
  }

  /**
   * 获取用户角色列表
   */
  async getUserRoles(): Promise<ApiResponse<Array<{
    value: string
    label: string
    permissions?: string[]
  }>>> {
    return this.get('/api/users/roles')
  }

  /**
   * 检查邮箱是否已存在
   */
  async checkEmailExists(email: string): Promise<ApiResponse<{ exists: boolean }>> {
    return this.get('/api/users/check-email', {
      params: { email }
    })
  }
}

export const userApi = new UserApiClient()