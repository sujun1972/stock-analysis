/**
 * @file lib/api/moneyflow.ts
 * @description 资金流向相关 API（沪深港通、大盘、板块、个股）
 * @author Claude
 * @created 2024-03-20
 */

import { BaseApiClient } from './base'
import type { ApiResponse } from '@/types/api'

// ============== 类型定义 ==============

export interface SyncMoneyflowParams {
  trade_date?: string  // YYYY-MM-DD
  start_date?: string  // YYYY-MM-DD
  end_date?: string    // YYYY-MM-DD
  ts_code?: string     // 股票代码（个股资金流向）
}

export interface SyncTaskResponse {
  celery_task_id: string
  task_name: string
  display_name: string
  status: string
}

export interface MoneyflowHsgtParams {
  start_date?: string
  end_date?: string
  limit?: number
  offset?: number
}

export interface MoneyflowMktDcParams {
  start_date?: string
  end_date?: string
  limit?: number
  offset?: number
}

export interface MoneyflowIndDcParams {
  trade_date?: string    // 单日查询（优先于 start/end_date，YYYY-MM-DD）
  start_date?: string
  end_date?: string
  content_type?: string  // 数据类型(行业、概念、地域)
  ts_code?: string       // 板块代码
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: string
  // 旧参数保留向后兼容
  limit?: number
  offset?: number
}

export interface MoneyflowStockDcParams {
  ts_code?: string
  trade_date?: string   // 单日查询（优先于 start/end_date，YYYY-MM-DD）
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
  sort_by?: string
  sort_order?: string
}

export interface MoneyflowParams {
  ts_code?: string
  trade_date?: string  // YYYY-MM-DD，单日筛选（优先于 start/end_date）
  start_date?: string
  end_date?: string
  limit?: number
  offset?: number
}

export interface TopMoneyflowParams {
  limit?: number
  trade_date?: string
}

// ============== API 类 ==============

export class MoneyflowApiClient extends BaseApiClient {
  // ========== 沪深港通资金流向 ==========

  /**
   * 获取沪深港通资金流向数据
   * @param params 查询参数
   * @returns 沪深港通资金流向数据
   */
  async getMoneyflowHsgt(params?: MoneyflowHsgtParams): Promise<ApiResponse<any>> {
    return this.get('/api/moneyflow-hsgt', { params })
  }

  /**
   * 异步同步沪深港通资金流向数据
   * 通过Celery任务异步执行，立即返回任务ID
   * @param params 同步参数
   * @returns 任务信息
   */
  async syncMoneyflowHsgtAsync(params?: SyncMoneyflowParams): Promise<ApiResponse<SyncTaskResponse>> {
    return this.post('/api/moneyflow-hsgt/sync-async', null, { params })
  }

  // ========== 大盘资金流向（DC） ==========

  /**
   * 获取大盘资金流向数据
   * @param params 查询参数
   * @returns 大盘资金流向数据
   */
  async getMoneyflowMktDc(params: MoneyflowMktDcParams): Promise<ApiResponse<any>> {
    return this.get('/api/moneyflow-mkt-dc', { params })
  }

  /**
   * 异步同步大盘资金流向数据
   * 通过Celery任务异步执行，立即返回任务ID
   * @param params 同步参数
   * @returns 任务信息
   */
  async syncMoneyflowMktDcAsync(params?: SyncMoneyflowParams): Promise<ApiResponse<SyncTaskResponse>> {
    return this.post('/api/moneyflow-mkt-dc/sync-async', null, { params })
  }

  // ========== 板块资金流向（DC） ==========

  /**
   * 获取板块资金流向数据
   * @param params 查询参数
   * @returns 板块资金流向数据
   */
  async getMoneyflowIndDc(params: MoneyflowIndDcParams): Promise<ApiResponse<any>> {
    return this.get('/api/moneyflow-ind-dc', { params })
  }

  /**
   * 异步同步板块资金流向数据
   * 通过Celery任务异步执行，立即返回任务ID
   * @param params 同步参数
   * @returns 任务信息
   */
  async syncMoneyflowIndDcAsync(params?: SyncMoneyflowParams): Promise<ApiResponse<SyncTaskResponse>> {
    return this.post('/api/moneyflow-ind-dc/sync-async', null, { params })
  }

  /**
   * 获取板块资金流入排名前N的板块（东方财富DC）
   * @param params 查询参数
   * @returns 排名数据
   */
  async getTopMoneyflowIndustries(params?: TopMoneyflowParams): Promise<ApiResponse<any>> {
    return this.get('/api/moneyflow-ind-dc/top', { params })
  }

  // ========== 个股资金流向（DC） ==========

  /**
   * 获取个股资金流向数据（东方财富DC）
   * @param params 查询参数
   * @returns 个股资金流向数据
   */
  async getMoneyflowStockDc(params: MoneyflowStockDcParams): Promise<ApiResponse<any>> {
    return this.get('/api/moneyflow-stock-dc', { params })
  }

  /**
   * 异步同步个股资金流向数据（东方财富DC）
   * 通过Celery任务异步执行，立即返回任务ID
   * @param params 同步参数
   * @returns 任务信息
   */
  async syncMoneyflowStockDcAsync(params?: SyncMoneyflowParams): Promise<ApiResponse<SyncTaskResponse>> {
    return this.post('/api/moneyflow-stock-dc/sync-async', null, { params })
  }

  /**
   * 获取主力资金流入排名前N的股票（东方财富DC）
   * @param params 查询参数
   * @returns 排名数据
   */
  async getTopMoneyflowStocks(params?: TopMoneyflowParams): Promise<ApiResponse<any>> {
    return this.get('/api/moneyflow-stock-dc/top', { params })
  }

  // ========== 个股资金流向（Tushare标准） ==========

  /**
   * 获取个股资金流向数据（Tushare标准接口）
   * @param params 查询参数
   * @returns 个股资金流向数据
   */
  async getMoneyflow(params?: MoneyflowParams): Promise<ApiResponse<any>> {
    return this.get('/api/moneyflow', { params })
  }

  /**
   * 异步同步个股资金流向数据（Tushare标准接口）
   * 通过Celery任务异步执行，立即返回任务ID
   * @param params 同步参数
   * @returns 任务信息
   */
  async syncMoneyflowAsync(params?: SyncMoneyflowParams): Promise<ApiResponse<SyncTaskResponse>> {
    return this.post('/api/moneyflow/sync-async', null, { params })
  }

  /**
   * 获取资金净流入排名前N的股票（Tushare标准接口）
   * @param params 查询参数
   * @returns 排名数据
   */
  async getTopMoneyflowTushare(params?: TopMoneyflowParams): Promise<ApiResponse<any>> {
    return this.get('/api/moneyflow/top', { params })
  }
}

// ============== 单例导出 ==============

export const moneyflowApi = new MoneyflowApiClient()
