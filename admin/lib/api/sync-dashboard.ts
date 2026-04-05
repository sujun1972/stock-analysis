import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

/** 最近一次任务执行记录（简化） */
export interface LastTaskRecord {
  celery_task_id: string
  status: 'pending' | 'running' | 'success' | 'failure'
  started_at: string | null
  completed_at: string | null
  duration_ms: number | null
  error: string | null
}

/** Redis 全量同步进度 */
export interface RedisProgress {
  redis_key: string
  completed_count: number
}

/** 同步配置条目 */
export interface SyncConfig {
  id: number
  table_key: string
  display_name: string
  category: string
  display_order: number
  incremental_task_name: string | null
  incremental_default_days: number
  full_sync_task_name: string | null
  full_sync_strategy: 'by_ts_code' | 'by_date' | 'by_quarter' | 'snapshot' | 'none' | null
  full_sync_concurrency: number
  passive_sync_enabled: boolean
  passive_sync_task_name: string | null
  page_url: string | null
  api_prefix: string | null
  notes: string | null
  api_name: string | null
  description: string | null
  doc_url: string | null
  data_source: string | null
  updated_at: string | null
}

/** 仪表盘概览条目（配置 + 运行状态） */
export interface SyncOverviewItem extends SyncConfig {
  last_incremental: LastTaskRecord | null
  last_full_sync: LastTaskRecord | null
  redis_progress: RedisProgress | null
}

/** 分类统计 */
export interface CategoryStat {
  name: string
  count: number
}

export interface SyncOverviewResponse {
  items: SyncOverviewItem[]
  total: number
  categories: CategoryStat[]
}

export interface SyncConfigUpdate {
  incremental_default_days?: number
  full_sync_strategy?: string
  full_sync_concurrency?: number
  passive_sync_enabled?: boolean
  passive_sync_task_name?: string | null
  notes?: string | null
  api_name?: string | null
  description?: string | null
  doc_url?: string | null
  data_source?: string | null
}

export class SyncDashboardApiClient extends BaseApiClient {
  /** 获取所有数据表同步状态概览 */
  async getOverview(category?: string): Promise<ApiResponse<SyncOverviewResponse>> {
    return this.get('/api/sync-dashboard/overview', { params: category ? { category } : {} })
  }

  /** 获取所有同步配置（编辑用） */
  async getConfigs(category?: string): Promise<ApiResponse<{ items: SyncConfig[]; total: number }>> {
    return this.get('/api/sync-dashboard/configs', { params: category ? { category } : {} })
  }

  /** 更新单条同步配置 */
  async updateConfig(tableKey: string, data: SyncConfigUpdate): Promise<ApiResponse<SyncConfig>> {
    return this.put(`/api/sync-dashboard/configs/${tableKey}`, data)
  }

  /** 查询单表 Redis 全量同步进度 */
  async getTableProgress(tableKey: string): Promise<ApiResponse<{
    table_key: string
    has_progress: boolean
    redis_key?: string
    completed_count?: number
  }>> {
    return this.get(`/api/sync-dashboard/${tableKey}/progress`)
  }

  /** 清除 Redis 全量同步进度（重置，下次从头同步） */
  async clearProgress(tableKey: string): Promise<ApiResponse<{
    table_key: string
    redis_key: string
    deleted: boolean
  }>> {
    return this.post(`/api/sync-dashboard/${tableKey}/clear-progress`, {})
  }
}

export const syncDashboardApi = new SyncDashboardApiClient()
