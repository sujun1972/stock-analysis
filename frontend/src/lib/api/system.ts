import axiosInstance, { apiGet, apiPost, apiPut, apiPatch } from './axios-instance'
import type { ApiResponse, InAppNotification, NotificationSettings } from '@/types'

// ========== 健康检查 ==========

export async function healthCheck(): Promise<ApiResponse<{ status: string }>> {
  const response = await axiosInstance.get('/health')
  return response.data
}

// ========== 数据引擎配置API ==========

export async function getDataSourceConfig(): Promise<ApiResponse<{
  data_source: string
  minute_data_source: string
  realtime_data_source: string
  tushare_token: string
}>> {
  return apiGet('/api/config/source')
}

export async function updateDataSourceConfig(params: {
  data_source: string
  minute_data_source?: string
  realtime_data_source?: string
  tushare_token?: string
}): Promise<ApiResponse<{ message: string }>> {
  return apiPost('/api/config/source', params)
}

export async function getAllConfigs(): Promise<ApiResponse<Record<string, unknown>>> {
  return apiGet('/api/config/all')
}

// ========== 模型相关API ==========

export async function trainModel(params: {
  model_type: string
  stock_codes: string[]
  train_config?: Record<string, unknown>
}): Promise<ApiResponse<{ task_id: string }>> {
  return apiPost('/api/models/train', params)
}

// ========== Scheduler API ==========

export async function getScheduledTasks(): Promise<ApiResponse<Array<Record<string, unknown>>>> {
  return apiGet('/api/scheduler/tasks')
}

export async function getScheduledTask(taskId: number): Promise<ApiResponse<Record<string, unknown>>> {
  return apiGet(`/api/scheduler/tasks/${taskId}`)
}

export async function createScheduledTask(data: {
  task_name: string
  module: string
  description?: string
  cron_expression: string
  enabled?: boolean
  params?: unknown
}): Promise<ApiResponse<{ id: number }>> {
  return apiPost('/api/scheduler/tasks', data)
}

export async function updateScheduledTask(taskId: number, data: {
  description?: string
  cron_expression?: string
  enabled?: boolean
  params?: unknown
}): Promise<ApiResponse<{ id: number }>> {
  return apiPut(`/api/scheduler/tasks/${taskId}`, data)
}

export async function deleteScheduledTask(taskId: number): Promise<ApiResponse<{ id: number }>> {
  const response = await axiosInstance.delete(`/api/scheduler/tasks/${taskId}`)
  return response.data
}

export async function toggleScheduledTask(taskId: number): Promise<ApiResponse<{ enabled: boolean }>> {
  return apiPost(`/api/scheduler/tasks/${taskId}/toggle`)
}

export async function getTaskExecutionHistory(taskId: number, limit: number = 20): Promise<ApiResponse<Array<Record<string, unknown>>>> {
  return apiGet(`/api/scheduler/tasks/${taskId}/history`, { params: { limit } })
}

export async function getRecentExecutionHistory(limit: number = 50): Promise<ApiResponse<Array<Record<string, unknown>>>> {
  return apiGet('/api/scheduler/history/recent', { params: { limit } })
}

// ========== 市场状态相关API ==========

export async function getMarketStatus(): Promise<ApiResponse<{
  status: string
  description: string
  is_trading: boolean
  should_refresh: boolean
  next_session_time: string | null
  next_session_desc: string | null
}>> {
  return apiGet('/api/market/status')
}

export async function checkDataFreshness(params?: {
  codes?: string[]
  force?: boolean
}): Promise<ApiResponse<{
  should_refresh: boolean
  reason: string
  market_status: string
  market_description: string
  last_update: string | null
  codes_count: number | null
}>> {
  return apiGet('/api/market/refresh-check', { params: params || {} })
}

export async function getRealtimeInfo(code: string): Promise<ApiResponse<Record<string, unknown>>> {
  return apiGet(`/api/market/realtime-info/${code}`)
}

// ========== 个人资料相关API ==========

export async function getProfile(): Promise<ApiResponse<Record<string, unknown>>> {
  return apiGet('/api/profile')
}

export async function updateProfile(data: {
  full_name?: string
  phone?: string
  avatar_url?: string
}): Promise<ApiResponse<Record<string, unknown>>> {
  return apiPatch('/api/profile', data)
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<ApiResponse<{ message: string }>> {
  return apiPost('/api/profile/change-password', {
    old_password: oldPassword,
    new_password: newPassword,
  })
}

export async function getQuota(): Promise<ApiResponse<Record<string, unknown>>> {
  return apiGet('/api/profile/quota')
}

// ========== 用户通知相关API ==========

export async function getNotificationSettings(): Promise<ApiResponse<NotificationSettings>> {
  return apiGet('/api/notifications/settings')
}

export async function updateNotificationSettings(
  settings: NotificationSettings
): Promise<ApiResponse<NotificationSettings>> {
  return apiPut('/api/notifications/settings', settings)
}

export async function getInAppNotifications(params?: {
  unread_only?: boolean
  limit?: number
  offset?: number
}): Promise<ApiResponse<InAppNotification[]>> {
  return apiGet('/api/notifications/in-app', { params })
}

export async function markNotificationAsRead(id: number): Promise<ApiResponse<void>> {
  return apiPost(`/api/notifications/in-app/${id}/read`)
}

export async function markAllNotificationsAsRead(): Promise<ApiResponse<{ count: number }>> {
  return apiPost('/api/notifications/in-app/read-all')
}

export async function getUnreadCount(): Promise<ApiResponse<{ unread_count: number }>> {
  return apiGet('/api/notifications/unread-count')
}

export async function getNotificationLogs(params?: {
  limit?: number
  offset?: number
}): Promise<ApiResponse<Array<Record<string, unknown>>>> {
  return apiGet('/api/notifications/logs', { params })
}
