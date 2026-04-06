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

export type SyncStrategy = 'by_ts_code' | 'by_date_range' | 'by_date' | 'by_week' | 'by_month' | 'by_quarter' | 'snapshot' | 'none'

/** 同步配置条目 */
export interface SyncConfig {
  id: number
  table_key: string
  display_name: string
  category: string
  display_order: number
  incremental_task_name: string | null
  incremental_default_days: number
  incremental_sync_strategy: SyncStrategy | null
  full_sync_task_name: string | null
  full_sync_strategy: SyncStrategy | null
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
  api_limit: number | null
  max_requests_per_minute: number | null
  updated_at: string | null
}

/** 增量任务的定时调度配置 */
export interface IncrementalSchedule {
  schedule_id: number
  cron_expression: string | null
  enabled: boolean
}

/** 仪表盘概览条目（配置 + 运行状态） */
export interface SyncOverviewItem extends SyncConfig {
  last_incremental: LastTaskRecord | null
  last_full_sync: LastTaskRecord | null
  redis_progress: RedisProgress | null
  incremental_schedule: IncrementalSchedule | null
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
  incremental_sync_strategy?: SyncStrategy | null
  full_sync_strategy?: SyncStrategy | null
  full_sync_concurrency?: number
  passive_sync_enabled?: boolean
  passive_sync_task_name?: string | null
  notes?: string | null
  api_name?: string | null
  description?: string | null
  doc_url?: string | null
  data_source?: string | null
  api_limit?: number | null
  max_requests_per_minute?: number | null
}

export interface ScheduleUpdate {
  enabled?: boolean
  cron_expression?: string | null
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

  /** 更新增量同步任务的定时调度配置（启用/禁用、Cron 表达式） */
  async updateSchedule(tableKey: string, data: ScheduleUpdate): Promise<ApiResponse<IncrementalSchedule & { task_name: string }>> {
    return this.put(`/api/sync-dashboard/configs/${tableKey}/schedule`, data)
  }

  /** 获取指定表增量同步的建议起始日期（YYYYMMDD） */
  async getSuggestStartDate(apiPrefix: string): Promise<ApiResponse<{ suggested_start_date: string | null }>> {
    return this.get(`/api${apiPrefix}/suggest-start-date`)
  }
}

export const syncDashboardApi = new SyncDashboardApiClient()
