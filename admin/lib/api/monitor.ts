/**
 * @file lib/api/monitor.ts
 * @description 系统监控相关 API
 * @author Claude
 * @created 2024-03-20
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

// ============== 类型定义 ==============

export interface HealthCheckResponse {
  status: 'healthy' | 'degraded' | 'unhealthy'
  timestamp: string
  services: {
    database: boolean
    redis: boolean
    celery: boolean
  }
}

export interface SystemMetrics {
  cpu_usage: number
  memory_usage: number
  disk_usage: number
  network: {
    bytes_sent: number
    bytes_recv: number
  }
  uptime: number
}

export interface DatabaseStats {
  total_size: string
  tables: Array<{
    table_name: string
    row_count: number
    table_size: string
  }>
  connections: {
    active: number
    idle: number
    total: number
  }
}

export interface ApiPerformance {
  total_requests: number
  avg_response_time: number
  error_rate: number
  endpoints: Array<{
    path: string
    count: number
    avg_time: number
  }>
}

export interface NotificationChannel {
  id: number
  name: string
  type: 'email' | 'telegram' | 'webhook'
  enabled: boolean
  config: Record<string, any>
}

// ============== API 类 ==============

export class MonitorApiClient extends BaseApiClient {
  /**
   * 健康检查
   * @returns 健康状态
   */
  async healthCheck(): Promise<ApiResponse<HealthCheckResponse>> {
    return this.get('/api/health')
  }

  /**
   * 获取系统状态
   * @returns 系统状态详情
   */
  async getSystemStatus(): Promise<ApiResponse<{
    status: string
    version: string
    uptime: number
    services: Record<string, any>
  }>> {
    return this.get('/api/monitor/status')
  }

  /**
   * 获取系统指标
   * @returns 系统指标数据
   */
  async getSystemMetrics(): Promise<ApiResponse<SystemMetrics>> {
    return this.get('/api/monitor/metrics')
  }

  /**
   * 获取数据库统计信息
   * @returns 数据库统计
   */
  async getDatabaseStats(): Promise<ApiResponse<DatabaseStats>> {
    return this.get('/api/monitor/database/stats')
  }

  /**
   * 获取API性能统计
   * @param params 查询参数
   * @returns API性能数据
   */
  async getApiPerformance(params?: {
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<ApiPerformance>> {
    return this.get('/api/monitor/api/performance', { params })
  }

  /**
   * 获取通知渠道列表
   * @returns 通知渠道列表
   */
  async getNotificationChannels(): Promise<ApiResponse<NotificationChannel[]>> {
    return this.get('/api/monitor/notifications/channels')
  }

  /**
   * 测试通知渠道
   * @param channelId 渠道ID
   * @returns 测试结果
   */
  async testNotificationChannel(channelId: number): Promise<ApiResponse<{
    success: boolean
    message: string
  }>> {
    return this.post(`/api/monitor/notifications/channels/${channelId}/test`)
  }

  /**
   * 发送通知
   * @param params 通知参数
   * @returns 发送结果
   */
  async sendNotification(params: {
    channel_id: number
    title: string
    message: string
    priority?: 'low' | 'normal' | 'high'
  }): Promise<ApiResponse<{ message_id: string }>> {
    return this.post('/api/monitor/notifications/send', params)
  }
}

// ============== 单例导出 ==============

export const monitorApi = new MonitorApiClient()
