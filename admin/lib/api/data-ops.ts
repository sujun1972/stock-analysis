/**
 * @file lib/api/data-ops.ts
 * @description 数据操作 API（清空表等）
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

export interface ClearTableParams {
  table_key: string
  start_date?: string
  end_date?: string
}

export interface ClearTableResult {
  table: string
  deleted: number
  mode: string
}

export class DataOpsApiClient extends BaseApiClient {
  /**
   * 清空指定数据表（全表 TRUNCATE 或按日期范围删除）
   */
  async clearTableData(params: ClearTableParams): Promise<ApiResponse<ClearTableResult>> {
    const { table_key, ...query } = params
    return this.post(`/api/data-ops/clear/${table_key}`, {}, { params: query })
  }
}

export const dataOpsApi = new DataOpsApiClient()
