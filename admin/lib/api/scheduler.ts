/**
 * @file lib/api/scheduler.ts
 * @description 定时任务相关 API
 * @author Claude
 * @created 2024-03-20
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

// ============== 类型定义 ==============

export interface CreateScheduledTaskRequest {
  task_name: string
  module: string
  description?: string
  cron_expression: string
  enabled?: boolean
  params?: any
}

export interface UpdateScheduledTaskRequest {
  display_name?: string
  description?: string
  category?: string
  display_order?: number
  points_consumption?: number
  cron_expression?: string
  enabled?: boolean
  params?: any
}

export interface TaskExecutionStatusResponse {
  status: string
  celery_task_id?: string
  result?: any
  error?: string
  progress?: number
}

export interface TaskExecutionResult {
  task_id: number
  task_name: string
  celery_task_id: string
  status: string
}

// ============== API 类 ==============

export class SchedulerApiClient extends BaseApiClient {
  /**
   * 获取所有定时任务
   * @returns 定时任务列表
   */
  async getScheduledTasks(): Promise<ApiResponse<any[]>> {
    return this.get('/api/scheduler/tasks')
  }

  /**
   * 获取单个定时任务详情
   * @param taskId 任务ID
   * @returns 任务详情
   */
  async getScheduledTask(taskId: number): Promise<ApiResponse<any>> {
    return this.get(`/api/scheduler/tasks/${taskId}`)
  }

  /**
   * 创建定时任务
   * @param data 任务数据
   * @returns 创建结果
   */
  async createScheduledTask(data: CreateScheduledTaskRequest): Promise<ApiResponse<{ id: number }>> {
    return this.post('/api/scheduler/tasks', data)
  }

  /**
   * 更新定时任务
   * @param taskId 任务ID
   * @param data 更新数据
   * @returns 更新结果
   */
  async updateScheduledTask(taskId: number, data: UpdateScheduledTaskRequest): Promise<ApiResponse<{ id: number }>> {
    return this.put(`/api/scheduler/tasks/${taskId}`, data)
  }

  /**
   * 删除定时任务
   * @param taskId 任务ID
   * @returns 删除结果
   */
  async deleteScheduledTask(taskId: number): Promise<ApiResponse<{ id: number }>> {
    return this.delete(`/api/scheduler/tasks/${taskId}`)
  }

  /**
   * 切换定时任务启用状态
   * @param taskId 任务ID
   * @returns 切换结果
   */
  async toggleScheduledTask(taskId: number): Promise<ApiResponse<{ enabled: boolean }>> {
    return this.post(`/api/scheduler/tasks/${taskId}/toggle`)
  }

  /**
   * 立即执行定时任务
   * @param taskId 任务ID
   * @returns 执行结果
   */
  async executeScheduledTask(taskId: number): Promise<ApiResponse<TaskExecutionResult>> {
    return this.post(`/api/scheduler/tasks/${taskId}/execute`)
  }

  /**
   * 获取任务执行状态
   * @param taskId 任务ID
   * @param celeryTaskId Celery任务ID（可选）
   * @returns 执行状态
   */
  async getTaskExecutionStatus(taskId: number, celeryTaskId?: string): Promise<ApiResponse<TaskExecutionStatusResponse>> {
    const params = celeryTaskId ? { celery_task_id: celeryTaskId } : {}
    return this.get(`/api/scheduler/tasks/${taskId}/status`, { params })
  }

  /**
   * 获取任务执行历史
   * @param taskId 任务ID
   * @param limit 返回记录数，默认20条
   * @returns 执行历史列表
   */
  async getTaskExecutionHistory(taskId: number, limit: number = 20): Promise<ApiResponse<any[]>> {
    return this.get(`/api/scheduler/tasks/${taskId}/history`, { params: { limit } })
  }

  /**
   * 获取最近的任务执行历史
   * @param limit 返回记录数，默认50条
   * @returns 执行历史列表
   */
  async getRecentExecutionHistory(limit: number = 50): Promise<ApiResponse<any[]>> {
    return this.get('/api/scheduler/history/recent', { params: { limit } })
  }

  /**
   * 验证Cron表达式
   * @param expression Cron表达式
   * @returns 验证结果
   */
  async validateCronExpression(expression: string): Promise<ApiResponse<{
    valid: boolean
    error?: string
    next_run?: string
  }>> {
    return this.post('/api/scheduler/validate-cron', { expression })
  }
}

// ============== 单例导出 ==============

export const schedulerApi = new SchedulerApiClient()
