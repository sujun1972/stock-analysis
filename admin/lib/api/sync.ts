/**
 * @file lib/api/sync.ts
 * @description 数据同步相关 API
 * @author Claude
 * @created 2024-03-20
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

// ============== 类型定义 ==============

export interface SyncStatusResponse {
  status: string
  last_sync_date: string
  progress: number
  total: number
  completed: number
}

export interface BatchSyncParams {
  stock_codes?: string[]
  years?: number
  start_date?: string
  end_date?: string
}

export interface ModuleSyncStatusResponse {
  module: string
  status: string
  last_sync_time: string
  total: number
  success: number
  failed: number
  progress: number
  error_message: string
  started_at: string
  completed_at: string
}

// ============== API 类 ==============

export class SyncApiClient extends BaseApiClient {
  /**
   * 获取同步状态
   * @returns 同步状态
   */
  async getSyncStatus(): Promise<ApiResponse<SyncStatusResponse>> {
    return this.get('/api/sync/status')
  }

  /**
   * 同步股票列表
   * @returns 同步结果
   */
  async syncStockList(): Promise<ApiResponse<{ total: number }>> {
    return this.post('/api/sync/stock-list')
  }

  /**
   * 同步新股列表
   * @param days 天数，默认30天
   * @returns 同步结果
   */
  async syncNewStocks(days: number = 30): Promise<ApiResponse<{ total: number }>> {
    return this.post('/api/sync/new-stocks', { days })
  }

  /**
   * 同步退市股票
   * @returns 同步结果
   */
  async syncDelistedStocks(): Promise<ApiResponse<{ total: number }>> {
    return this.post('/api/sync/delisted-stocks')
  }

  /**
   * 批量同步日线数据
   * @param params 同步参数
   * @returns 同步结果
   */
  async syncDailyBatch(params: BatchSyncParams): Promise<ApiResponse<{
    task_id: string
    total: number
  }>> {
    return this.post('/api/sync/daily-batch', params)
  }

  /**
   * 同步单只股票日线数据
   * @param tsCode 股票代码
   * @param params 同步参数
   * @returns 同步结果
   */
  async syncDailyStock(tsCode: string, params?: {
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<{ count: number }>> {
    return this.post(`/api/sync/daily/${tsCode}`, params)
  }

  /**
   * 同步分钟数据
   * @param params 同步参数
   * @returns 同步结果
   */
  async syncMinuteData(params: {
    stock_codes: string[]
    freq?: string
  }): Promise<ApiResponse<{ task_id: string }>> {
    return this.post('/api/sync/minute', params)
  }

  /**
   * 同步实时行情
   * @param codes 股票代码列表（可选）
   * @returns 同步结果
   */
  async syncRealtimeQuotes(codes?: string[]): Promise<ApiResponse<{ total: number }>> {
    return this.post('/api/sync/realtime', { codes })
  }

  /**
   * 中止同步任务
   * @param syncId 同步任务ID
   * @returns 中止结果
   */
  async abortSync(syncId: string): Promise<ApiResponse<{ message: string }>> {
    return this.post(`/api/sync/${syncId}/abort`)
  }

  /**
   * 暂停同步任务
   * @param syncId 同步任务ID
   * @returns 暂停结果
   */
  async pauseSync(syncId: string): Promise<ApiResponse<{ message: string }>> {
    return this.post(`/api/sync/${syncId}/pause`)
  }

  /**
   * 恢复同步任务
   * @param syncId 同步任务ID
   * @returns 恢复结果
   */
  async resumeSync(syncId: string): Promise<ApiResponse<{ message: string }>> {
    return this.post(`/api/sync/${syncId}/resume`)
  }

  /**
   * 获取同步历史
   * @param params 查询参数
   * @returns 同步历史列表
   */
  async getSyncHistory(params?: {
    module?: string
    status?: string
    limit?: number
  }): Promise<ApiResponse<any[]>> {
    return this.get('/api/sync/history', { params })
  }

  /**
   * 获取同步统计信息
   * @returns 统计信息
   */
  async getSyncStatistics(): Promise<ApiResponse<{
    total: number
    success: number
    failed: number
    in_progress: number
  }>> {
    return this.get('/api/sync/statistics')
  }

  /**
   * 获取模块同步状态
   * @param module 模块名称
   * @returns 模块同步状态
   */
  async getModuleSyncStatus(module: string): Promise<ApiResponse<ModuleSyncStatusResponse>> {
    return this.get(`/api/sync/status/${module}`)
  }

  /**
   * 获取所有模块同步状态
   * @returns 所有模块同步状态
   */
  async getAllModulesStatus(): Promise<ApiResponse<Record<string, ModuleSyncStatusResponse>>> {
    return this.get('/api/sync/modules/status')
  }

  /**
   * 同步所有模块
   * @param params 同步参数
   * @returns 同步结果
   */
  async syncAllModules(params?: BatchSyncParams): Promise<ApiResponse<{ task_id: string }>> {
    return this.post('/api/sync/all', params)
  }

  /**
   * 同步扩展数据
   * @param date 日期 (YYYY-MM-DD)
   * @returns 同步结果
   */
  async syncExtendedData(date: string): Promise<ApiResponse<{ task_id: string }>> {
    return this.post('/api/sync/extended', { date })
  }
}

// ============== 单例导出 ==============

export const syncApi = new SyncApiClient()
