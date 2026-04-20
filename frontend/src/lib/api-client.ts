/**
 * 向后兼容的 API 客户端单例
 *
 * 新代码推荐直接导入领域模块：
 *   import { getStockList } from '@/lib/api/stocks'
 *   import { runAsyncBacktest } from '@/lib/api/backtest'
 *
 * 旧代码可继续使用 apiClient.xxx()：
 *   import { apiClient } from '@/lib/api-client'
 */

import { apiGet, apiPost, apiPut, apiPatch, apiDelete } from './api/axios-instance'
import * as stocksApi from './api/stocks'
import * as strategiesApi from './api/strategies'
import * as backtestApi from './api/backtest'
import * as syncApi from './api/sync'
import * as systemApi from './api/system'

import type { AxiosRequestConfig } from 'axios'

class ApiClient {
  // 基础HTTP方法
  get<T = unknown>(url: string, config?: AxiosRequestConfig) { return apiGet<T>(url, config) }
  post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig) { return apiPost<T>(url, data, config) }
  put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig) { return apiPut<T>(url, data, config) }
  patch<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig) { return apiPatch<T>(url, data, config) }
  delete<T = unknown>(url: string, config?: AxiosRequestConfig) { return apiDelete<T>(url, config) }

  // 健康检查
  healthCheck = systemApi.healthCheck

  // 股票
  getStockList = stocksApi.getStockList
  getStockIndustries = stocksApi.getStockIndustries
  getConceptBoards = stocksApi.getConceptBoards
  getStock = stocksApi.getStock
  getStockQuotePanel = stocksApi.getStockQuotePanel
  getStockBasicInfo = stocksApi.getStockBasicInfo
  getChipsDistribution = stocksApi.getChipsDistribution
  getStockCodes = stocksApi.getStockCodes
  updateStockList = stocksApi.updateStockList

  // 概念
  getConceptsList = stocksApi.getConceptsList
  getConcept = stocksApi.getConcept
  getConceptStocks = stocksApi.getConceptStocks
  getStockConcepts = stocksApi.getStockConcepts
  syncConcepts = stocksApi.syncConcepts
  updateStockConcepts = stocksApi.updateStockConcepts

  // 数据
  getDailyData = stocksApi.getDailyData
  downloadData = stocksApi.downloadData
  getFeatures = stocksApi.getFeatures
  calculateFeatures = stocksApi.calculateFeatures
  getMinuteData = stocksApi.getMinuteData
  getMinuteDataRange = stocksApi.getMinuteDataRange
  getPrediction = stocksApi.getPrediction

  // 用户股票列表
  getUserStockLists = stocksApi.getUserStockLists
  createStockList = stocksApi.createStockList
  renameStockList = stocksApi.renameStockList
  deleteStockList = stocksApi.deleteStockList
  getStockListItems = stocksApi.getStockListItems
  getStockListTsCodes = stocksApi.getStockListTsCodes
  addStocksToList = stocksApi.addStocksToList
  removeStocksFromList = stocksApi.removeStocksFromList

  // AI分析
  saveStockAnalysis = stocksApi.saveStockAnalysis
  getLatestStockAnalysis = stocksApi.getLatestStockAnalysis
  getStockAnalysisHistory = stocksApi.getStockAnalysisHistory
  updateStockAnalysis = stocksApi.updateStockAnalysis
  deleteStockAnalysis = stocksApi.deleteStockAnalysis
  generateStockAnalysis = stocksApi.generateStockAnalysis
  generateReviewAnalysis = stocksApi.generateReviewAnalysis
  generateMultiAnalysis = stocksApi.generateMultiAnalysis
  submitBatchAnalysis = stocksApi.submitBatchAnalysis
  getBatchAnalysisProgress = stocksApi.getBatchAnalysisProgress
  getActiveBatchTsCodes = stocksApi.getActiveBatchTsCodes
  collectStockData = stocksApi.collectStockData
  getPromptTemplateByKey = stocksApi.getPromptTemplateByKey

  // 统一策略 (V2.0)
  getStrategies = strategiesApi.getStrategies
  getStrategy = strategiesApi.getStrategy
  createStrategy = strategiesApi.createStrategy
  updateStrategy = strategiesApi.updateStrategy
  deleteStrategy = strategiesApi.deleteStrategy
  validateStrategy = strategiesApi.validateStrategy
  getStrategyStatistics = strategiesApi.getStrategyStatistics
  getStrategyCode = strategiesApi.getStrategyCode
  testStrategy = strategiesApi.testStrategy

  // 策略发布
  requestPublishStrategy = strategiesApi.requestPublishStrategy
  withdrawPublishRequest = strategiesApi.withdrawPublishRequest
  getMyStrategies = strategiesApi.getMyStrategies

  // 策略配置（旧版）
  getStrategyTypes = strategiesApi.getStrategyTypes
  createStrategyConfig = strategiesApi.createStrategyConfig
  getStrategyConfigs = strategiesApi.getStrategyConfigs
  getStrategyConfig = strategiesApi.getStrategyConfig
  updateStrategyConfig = strategiesApi.updateStrategyConfig
  deleteStrategyConfig = strategiesApi.deleteStrategyConfig
  testStrategyConfig = strategiesApi.testStrategyConfig
  validateStrategyConfig = strategiesApi.validateStrategyConfig

  // 动态策略
  createDynamicStrategy = strategiesApi.createDynamicStrategy
  getDynamicStrategies = strategiesApi.getDynamicStrategies
  getDynamicStrategy = strategiesApi.getDynamicStrategy
  getDynamicStrategyCode = strategiesApi.getDynamicStrategyCode
  updateDynamicStrategy = strategiesApi.updateDynamicStrategy
  deleteDynamicStrategy = strategiesApi.deleteDynamicStrategy
  testDynamicStrategy = strategiesApi.testDynamicStrategy
  validateDynamicStrategy = strategiesApi.validateDynamicStrategy
  getDynamicStrategyStatistics = strategiesApi.getDynamicStrategyStatistics

  // AI策略生成
  generateStrategyAsync = strategiesApi.generateStrategyAsync
  getAIGenerationStatus = strategiesApi.getAIGenerationStatus
  cancelAIGeneration = strategiesApi.cancelAIGeneration

  // 回测
  runBacktestV2 = backtestApi.runBacktestV2
  runUnifiedBacktest = backtestApi.runUnifiedBacktest
  runAsyncBacktest = backtestApi.runAsyncBacktest
  getBacktestStatus = backtestApi.getBacktestStatus
  cancelBacktest = backtestApi.cancelBacktest
  getBacktestResult = backtestApi.getBacktestResult
  runBacktest = backtestApi.runBacktest
  getStrategyList = backtestApi.getStrategyList
  getStrategyMetadata = backtestApi.getStrategyMetadata

  // 同步
  getSyncStatus = syncApi.getSyncStatus
  syncStockList = syncApi.syncStockList
  syncNewStocks = syncApi.syncNewStocks
  syncDelistedStocks = syncApi.syncDelistedStocks
  syncDailyBatch = syncApi.syncDailyBatch
  syncDailyStock = syncApi.syncDailyStock
  abortSync = syncApi.abortSync
  syncMinuteData = syncApi.syncMinuteData
  syncRealtimeQuotes = syncApi.syncRealtimeQuotes
  getSyncHistory = syncApi.getSyncHistory
  getModuleSyncStatus = syncApi.getModuleSyncStatus

  // 系统配置
  getDataSourceConfig = systemApi.getDataSourceConfig
  updateDataSourceConfig = systemApi.updateDataSourceConfig
  getAllConfigs = systemApi.getAllConfigs
  trainModel = systemApi.trainModel

  // 定时任务
  getScheduledTasks = systemApi.getScheduledTasks
  getScheduledTask = systemApi.getScheduledTask
  createScheduledTask = systemApi.createScheduledTask
  updateScheduledTask = systemApi.updateScheduledTask
  deleteScheduledTask = systemApi.deleteScheduledTask
  toggleScheduledTask = systemApi.toggleScheduledTask
  getTaskExecutionHistory = systemApi.getTaskExecutionHistory
  getRecentExecutionHistory = systemApi.getRecentExecutionHistory

  // 市场状态
  getMarketStatus = systemApi.getMarketStatus
  checkDataFreshness = systemApi.checkDataFreshness
  getRealtimeInfo = systemApi.getRealtimeInfo

  // 个人资料
  getProfile = systemApi.getProfile
  updateProfile = systemApi.updateProfile
  changePassword = systemApi.changePassword
  getQuota = systemApi.getQuota

  // 通知
  getNotificationSettings = systemApi.getNotificationSettings
  updateNotificationSettings = systemApi.updateNotificationSettings
  getInAppNotifications = systemApi.getInAppNotifications
  markNotificationAsRead = systemApi.markNotificationAsRead
  markAllNotificationsAsRead = systemApi.markAllNotificationsAsRead
  getUnreadCount = systemApi.getUnreadCount
  getNotificationLogs = systemApi.getNotificationLogs
}

export const apiClient = new ApiClient()
export default apiClient
