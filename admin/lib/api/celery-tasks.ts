/**
 * @file lib/api/celery-tasks.ts
 * @description Celery 任务管理 API
 * @author Claude
 * @created 2024-03-20
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

// ============== 类型定义 ==============

export interface CeleryTaskParams {
  status?: 'pending' | 'running' | 'success' | 'failure' | 'revoked'
  task_name?: string
  user_id?: number
  limit?: number
  offset?: number
}

export interface CeleryTask {
  id: number
  celery_task_id: string
  task_name: string
  display_name: string
  task_type: string
  status: string
  progress: number
  result: any
  error: string | null
  user_id: number
  created_at: string
  started_at: string | null
  completed_at: string | null
  duration_ms: number | null
}

// ============== API 类 ==============

export class CeleryTasksApiClient extends BaseApiClient {
  /**
   * 获取任务列表
   * @param params 查询参数
   * @returns 任务列表
   */
  async getTasks(params?: CeleryTaskParams): Promise<ApiResponse<{
    data: CeleryTask[]
    total: number
  }>> {
    return this.get('/api/celery/task-history', { params })
  }

  /**
   * 获取活跃任务列表
   * @returns 活跃任务列表
   */
  async getActiveTasks(): Promise<ApiResponse<{
    data: CeleryTask[]
    total: number
  }>> {
    return this.get('/api/celery/task-history/active')
  }

  /**
   * 获取最近任务历史
   * @param limit 返回记录数
   * @returns 任务历史列表
   */
  async getRecentHistory(limit?: number): Promise<ApiResponse<{
    data: CeleryTask[]
    total: number
  }>> {
    return this.get('/api/celery/task-history/recent', { params: { limit } })
  }

  /**
   * 获取任务统计信息
   * @returns 统计信息
   */
  async getStatistics(): Promise<ApiResponse<{
    total: number
    pending: number
    running: number
    success: number
    failure: number
  }>> {
    return this.get('/api/celery/task-history/statistics/summary')
  }

  /**
   * 获取单个任务详情
   * @param taskId 任务ID
   * @returns 任务详情
   */
  async getTask(taskId: string): Promise<ApiResponse<CeleryTask>> {
    return this.get(`/api/celery/task/${taskId}`)
  }

  /**
   * 取消任务
   * @param taskId 任务ID
   * @returns 取消结果
   */
  async cancelTask(taskId: string): Promise<ApiResponse<{ message: string }>> {
    return this.post(`/api/celery/task/${taskId}/revoke`)
  }

  /**
   * 删除任务记录
   * @param taskId 任务ID
   * @returns 删除结果
   */
  async deleteTask(taskId: string): Promise<ApiResponse<{ message: string }>> {
    return this.delete(`/api/celery/task-history/${taskId}`)
  }
}

// ============== 单例导出 ==============

export const celeryTasksApi = new CeleryTasksApiClient()
