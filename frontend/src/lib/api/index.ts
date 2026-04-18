/**
 * API 模块化导出
 *
 * 推荐用法（按领域导入）：
 *   import { getStockList } from '@/lib/api/stocks'
 *   import { runAsyncBacktest } from '@/lib/api/backtest'
 *
 * 向后兼容（apiClient 单例保持不变）：
 *   import { apiClient } from '@/lib/api-client'
 */

export { axiosInstance, API_BASE_URL, apiGet, apiPost, apiPut, apiPatch, apiDelete } from './axios-instance'

export * from './stocks'
export * from './strategies'
export * from './backtest'
export * from './sync'
export * from './system'
