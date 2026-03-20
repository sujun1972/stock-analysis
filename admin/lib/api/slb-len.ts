/**
 * @file lib/api/slb-len.ts
 * @description 转融资交易汇总 API
 * @author Claude
 * @created 2024-03-20
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

// ============== 类型定义 ==============

export interface SlbLenParams {
  start_date?: string   // YYYY-MM-DD
  end_date?: string     // YYYY-MM-DD
  limit?: number        // 返回记录数（最大5000）
}

export interface SlbLenData {
  trade_date: string    // 交易日期
  ob: number            // 期初余额(亿元)
  auc_amount: number    // 竞价成交金额(亿元)
  repo_amount: number   // 再借成交金额(亿元)
  repay_amount: number  // 偿还金额(亿元)
  cb: number            // 期末余额(亿元)
  created_at?: string
  updated_at?: string
}

export interface SlbLenStatistics {
  avg_cb: number              // 平均期末余额
  max_cb: number              // 最大期末余额
  min_cb: number              // 最小期末余额
  avg_ob: number              // 平均期初余额
  total_auc_amount: number    // 累计竞价成交金额
  total_repo_amount: number   // 累计再借成交金额
  total_repay_amount: number  // 累计偿还金额
  latest_date: string         // 最新日期
  earliest_date: string       // 最早日期
  count: number               // 记录数
}

export interface SyncSlbLenParams {
  trade_date?: string   // YYYY-MM-DD
  start_date?: string   // YYYY-MM-DD
  end_date?: string     // YYYY-MM-DD
}

export interface SyncTaskResponse {
  celery_task_id: string
  task_name: string
  display_name: string
  status: string
}

// ============== API 类 ==============

export class SlbLenApiClient extends BaseApiClient {
  /**
   * 获取转融资交易汇总数据
   * @param params 查询参数
   * @returns 汇总数据列表
   */
  async getSlbLen(params?: SlbLenParams): Promise<ApiResponse<{
    items: SlbLenData[]
    total: number
  }>> {
    return this.get('/api/slb-len', { params })
  }

  /**
   * 获取转融资交易汇总统计数据
   * @param params 统计参数（日期范围）
   * @returns 统计数据
   */
  async getSlbLenStatistics(params?: {
    start_date?: string
    end_date?: string
  }): Promise<ApiResponse<SlbLenStatistics>> {
    return this.get('/api/slb-len/statistics', { params })
  }

  /**
   * 获取最新交易日的转融资数据
   * @returns 最新数据
   */
  async getLatestSlbLen(): Promise<ApiResponse<SlbLenData>> {
    return this.get('/api/slb-len/latest')
  }

  /**
   * 异步同步转融资交易汇总数据
   * 通过Celery任务异步执行，立即返回任务ID
   * @param params 同步参数
   * @returns 任务信息
   */
  async syncSlbLenAsync(params?: SyncSlbLenParams): Promise<ApiResponse<SyncTaskResponse>> {
    return this.post('/api/slb-len/sync-async', {}, { params })
  }
}

// ============== 导出单例 ==============

export const slbLenApi = new SlbLenApiClient()
