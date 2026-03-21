/**
 * @file lib/api/index.ts
 * @description API 客户端统一导出文件
 * @author Claude
 * @created 2024-03-16
 * @updated 2024-03-20
 */

// 导入所有需要的模块
// 使用别名避免名称冲突，确保正确的模块导入和导出
import { BaseApiClient, axiosInstance as axiosInst, API_BASE_URL } from './base'
import { AuthApiClient, authApi as authApiInst } from './auth'
import { StockApiClient, stockApi as stockApiInst } from './stocks'
import { StrategyApiClient, strategyApi as strategyApiInst } from './strategies'
import { UserApiClient, userApi as userApiInst } from './users'
import { SentimentApiClient, sentimentApi as sentimentApiInst } from './sentiment'
import { MoneyflowApiClient, moneyflowApi as moneyflowApiInst } from './moneyflow'
import { MarginApiClient, marginApi as marginApiInst } from './margin'
import { MarginSecsApi, marginSecsApi as marginSecsApiInst } from './margin-secs'
import { SlbLenApiClient, slbLenApi as slbLenApiInst } from './slb-len'
import { SchedulerApiClient, schedulerApi as schedulerApiInst } from './scheduler'
import { CeleryTasksApiClient, celeryTasksApi as celeryTasksApiInst } from './celery-tasks'
import { ConceptsApiClient, conceptsApi as conceptsApiInst } from './concepts'
import { ConfigApiClient, configApi as configApiInst } from './config'
import { SyncApiClient, syncApi as syncApiInst } from './sync'
import { ExtendedDataApiClient, extendedDataApi as extendedDataApiInst } from './extended-data'
import { MonitorApiClient, monitorApi as monitorApiInst } from './monitor'
import { TopListApiClient, topListApi as topListApiInst } from './top-list'
import { TopInstApiClient, topInstApi as topInstApiInst } from './top-inst'
import { LimitListApiClient, limitListApi as limitListApiInst } from './limit-list'

// 重新导出基础类和实例
export { BaseApiClient, API_BASE_URL }
export const axiosInstance = axiosInst

// 重新导出认证 API
export { AuthApiClient }
export const authApi = authApiInst
export type { LoginRequest, LoginResponse, RegisterRequest, UpdatePasswordRequest, UpdateProfileRequest } from './auth'

// 重新导出股票 API
export { StockApiClient }
export const stockApi = stockApiInst
export type { StockListParams, UpdateStockRequest, StockConceptRequest } from './stocks'

// 重新导出策略 API
export { StrategyApiClient }
export const strategyApi = strategyApiInst
export type { StrategyListParams, AssignStrategyRequest } from './strategies'

// 重新导出用户 API
export { UserApiClient }
export const userApi = userApiInst
export type {
  User,
  UserListParams,
  CreateUserRequest,
  UpdateUserRequest,
  UserStatistics,
  UserQuota
} from './users'

// 重新导出市场情绪 API
export { SentimentApiClient }
export const sentimentApi = sentimentApiInst
export type { SentimentListParams, SyncSentimentBatchParams, DragonTigerListParams, TradingCalendarParams } from './sentiment'

// 重新导出资金流向 API
export { MoneyflowApiClient }
export const moneyflowApi = moneyflowApiInst
export type {
  SyncMoneyflowParams,
  SyncTaskResponse,
  MoneyflowHsgtParams,
  MoneyflowMktDcParams,
  MoneyflowIndDcParams,
  MoneyflowStockDcParams,
  MoneyflowParams,
  TopMoneyflowParams
} from './moneyflow'

// 重新导出融资融券 API
export { MarginApiClient }
export const marginApi = marginApiInst
export type {
  MarginParams,
  MarginStatistics,
  SyncMarginParams,
  MarginDetailParams,
  MarginDetailStatistics,
  MarginDetailTopParams
} from './margin'

// 重新导出融资融券标的 API
export { MarginSecsApi }
export const marginSecsApi = marginSecsApiInst
export type {
  MarginSecsParams,
  MarginSecsItem,
  MarginSecsStatistics,
  MarginSecsData,
  LatestMarginSecsData,
  SyncMarginSecsParams
} from './margin-secs'

// 重新导出转融资交易汇总 API
export { SlbLenApiClient }
export const slbLenApi = slbLenApiInst
export type {
  SlbLenParams,
  SlbLenData,
  SlbLenStatistics,
  SyncSlbLenParams
} from './slb-len'

// 重新导出定时任务 API
export { SchedulerApiClient }
export const schedulerApi = schedulerApiInst
export type {
  CreateScheduledTaskRequest,
  UpdateScheduledTaskRequest,
  TaskExecutionStatusResponse,
  TaskExecutionResult
} from './scheduler'

// 重新导出 Celery 任务 API
export { CeleryTasksApiClient }
export const celeryTasksApi = celeryTasksApiInst
export type { CeleryTaskParams, CeleryTask } from './celery-tasks'

// 重新导出概念板块 API
export { ConceptsApiClient }
export const conceptsApi = conceptsApiInst
export type { ConceptListParams, ConceptStocksParams, UpdateConceptRequest } from './concepts'

// 重新导出系统配置 API
export { ConfigApiClient }
export const configApi = configApiInst
export type {
  DataSourceConfig,
  UpdateDataSourceConfigRequest,
  AIProviderConfig
} from './config'

// 重新导出数据同步 API
export { SyncApiClient }
export const syncApi = syncApiInst
export type {
  SyncStatusResponse,
  BatchSyncParams,
  ModuleSyncStatusResponse
} from './sync'

// 重新导出扩展数据 API
export { ExtendedDataApiClient }
export const extendedDataApi = extendedDataApiInst
export type {
  DateRangeParams,
  DailyBasicParams,
  HkHoldParams,
  LimitPricesParams,
  BlockTradeParams,
  ExtendedDataSummary
} from './extended-data'

// 重新导出系统监控 API
export { MonitorApiClient }
export const monitorApi = monitorApiInst
export type {
  HealthCheckResponse,
  SystemMetrics,
  DatabaseStats,
  ApiPerformance,
  NotificationChannel
} from './monitor'

// 重新导出龙虎榜 API
export { TopListApiClient }
export const topListApi = topListApiInst

// 重新导出龙虎榜机构明细 API
export { TopInstApiClient }
export const topInstApi = topInstApiInst
export type {
  TopListParams,
  TopListItem,
  TopListStatistics
} from './top-list'
export type {
  TopInstParams,
  TopInstItem,
  TopInstStatistics
} from './top-inst'

// 重新导出涨跌停列表 API
export { LimitListApiClient }
export const limitListApi = limitListApiInst
export type {
  LimitListParams,
  LimitListData,
  LimitListStatistics
} from './limit-list'

// 创建统一的 API 客户端对象（向后兼容）
export const apiClient = {
  // 认证相关
  login: authApiInst.login.bind(authApiInst),
  register: authApiInst.register.bind(authApiInst),
  refresh: authApiInst.refresh.bind(authApiInst),
  logout: authApiInst.logout.bind(authApiInst),
  getCurrentUser: authApiInst.getCurrentUser.bind(authApiInst),
  updatePassword: authApiInst.updatePassword.bind(authApiInst),
  updateProfile: authApiInst.updateProfile.bind(authApiInst),

  // 用户管理
  getUsers: userApiInst.getUsers.bind(userApiInst),
  getUser: userApiInst.getUser.bind(userApiInst),
  createUser: userApiInst.createUser.bind(userApiInst),
  updateUser: userApiInst.updateUser.bind(userApiInst),
  deleteUser: userApiInst.deleteUser.bind(userApiInst),
  batchDeleteUsers: userApiInst.batchDeleteUsers.bind(userApiInst),
  toggleUserStatus: userApiInst.toggleUserStatus.bind(userApiInst),
  resetUserPassword: userApiInst.resetUserPassword.bind(userApiInst),
  getUserStatistics: userApiInst.getUserStatistics.bind(userApiInst),
  getUserQuota: userApiInst.getUserQuota.bind(userApiInst),
  updateUserQuota: userApiInst.updateUserQuota.bind(userApiInst),

  // 股票相关
  getStockList: stockApiInst.getStockList.bind(stockApiInst),
  getStock: stockApiInst.getStock.bind(stockApiInst),
  updateStock: stockApiInst.updateStock.bind(stockApiInst),
  updateStockList: stockApiInst.updateStockList.bind(stockApiInst),
  getStockConcepts: stockApiInst.getStockConcepts.bind(stockApiInst),
  updateStockConcepts: stockApiInst.updateStockConcepts.bind(stockApiInst),
  batchUpdateStockConcepts: stockApiInst.batchUpdateStockConcepts.bind(stockApiInst),
  getStockDaily: stockApiInst.getStockDaily.bind(stockApiInst),
  getStockMinute: stockApiInst.getStockMinute.bind(stockApiInst),
  syncStockData: stockApiInst.syncStockData.bind(stockApiInst),
  batchSyncStockData: stockApiInst.batchSyncStockData.bind(stockApiInst),
  searchStocks: stockApiInst.searchStocks.bind(stockApiInst),

  // 策略相关
  getStrategies: strategyApiInst.getStrategies.bind(strategyApiInst),
  getStrategy: strategyApiInst.getStrategy.bind(strategyApiInst),
  createStrategy: strategyApiInst.createStrategy.bind(strategyApiInst),
  updateStrategy: strategyApiInst.updateStrategy.bind(strategyApiInst),
  deleteStrategy: strategyApiInst.deleteStrategy.bind(strategyApiInst),
  batchDeleteStrategies: strategyApiInst.batchDeleteStrategies.bind(strategyApiInst),
  validateStrategy: strategyApiInst.validateStrategy.bind(strategyApiInst),
  testStrategy: strategyApiInst.testStrategy.bind(strategyApiInst),
  runBacktest: strategyApiInst.runBacktest.bind(strategyApiInst),
  toggleStrategy: strategyApiInst.toggleStrategy.bind(strategyApiInst),
  togglePublish: strategyApiInst.togglePublish.bind(strategyApiInst),
  cloneStrategy: strategyApiInst.cloneStrategy.bind(strategyApiInst),
  getStrategyStatistics: strategyApiInst.getStrategyStatistics.bind(strategyApiInst),
  getUserStrategies: strategyApiInst.getUserStrategies.bind(strategyApiInst),
  assignStrategiesToUser: strategyApiInst.assignStrategiesToUser.bind(strategyApiInst),
  removeUserStrategy: strategyApiInst.removeUserStrategy.bind(strategyApiInst),
  getStrategyTypes: strategyApiInst.getStrategyTypes.bind(strategyApiInst),
  exportStrategy: strategyApiInst.exportStrategy.bind(strategyApiInst),
  importStrategy: strategyApiInst.importStrategy.bind(strategyApiInst),
  getStrategyLogs: strategyApiInst.getStrategyLogs.bind(strategyApiInst),
  clearStrategyLogs: strategyApiInst.clearStrategyLogs.bind(strategyApiInst),

  // 市场情绪相关
  getSentimentList: sentimentApiInst.getSentimentList.bind(sentimentApiInst),
  getSentimentDaily: sentimentApiInst.getSentimentDaily.bind(sentimentApiInst),
  syncSentimentData: sentimentApiInst.syncSentimentData.bind(sentimentApiInst),
  syncSentimentBatch: sentimentApiInst.syncSentimentBatch.bind(sentimentApiInst),
  getSyncTaskStatus: sentimentApiInst.getSyncTaskStatus.bind(sentimentApiInst),
  getLimitUpPool: sentimentApiInst.getLimitUpPool.bind(sentimentApiInst),
  getLimitUpTrend: sentimentApiInst.getLimitUpTrend.bind(sentimentApiInst),
  getDragonTigerList: sentimentApiInst.getDragonTigerList.bind(sentimentApiInst),
  getStockDragonTigerHistory: sentimentApiInst.getStockDragonTigerHistory.bind(sentimentApiInst),
  getTradingCalendar: sentimentApiInst.getTradingCalendar.bind(sentimentApiInst),
  syncTradingCalendar: sentimentApiInst.syncTradingCalendar.bind(sentimentApiInst),
  getSentimentStatistics: sentimentApiInst.getSentimentStatistics.bind(sentimentApiInst),

  // 资金流向相关
  syncMoneyflowHsgtAsync: moneyflowApiInst.syncMoneyflowHsgtAsync.bind(moneyflowApiInst),
  getMoneyflowMktDc: moneyflowApiInst.getMoneyflowMktDc.bind(moneyflowApiInst),
  syncMoneyflowMktDcAsync: moneyflowApiInst.syncMoneyflowMktDcAsync.bind(moneyflowApiInst),
  getMoneyflowIndDc: moneyflowApiInst.getMoneyflowIndDc.bind(moneyflowApiInst),
  syncMoneyflowIndDcAsync: moneyflowApiInst.syncMoneyflowIndDcAsync.bind(moneyflowApiInst),
  getTopMoneyflowIndustries: moneyflowApiInst.getTopMoneyflowIndustries.bind(moneyflowApiInst),
  getMoneyflowStockDc: moneyflowApiInst.getMoneyflowStockDc.bind(moneyflowApiInst),
  syncMoneyflowStockDcAsync: moneyflowApiInst.syncMoneyflowStockDcAsync.bind(moneyflowApiInst),
  getTopMoneyflowStocks: moneyflowApiInst.getTopMoneyflowStocks.bind(moneyflowApiInst),
  getMoneyflow: moneyflowApiInst.getMoneyflow.bind(moneyflowApiInst),
  syncMoneyflowAsync: moneyflowApiInst.syncMoneyflowAsync.bind(moneyflowApiInst),
  getTopMoneyflowTushare: moneyflowApiInst.getTopMoneyflowTushare.bind(moneyflowApiInst),

  // 融资融券相关
  getMargin: marginApiInst.getMargin.bind(marginApiInst),
  getMarginStatistics: marginApiInst.getMarginStatistics.bind(marginApiInst),
  syncMarginAsync: marginApiInst.syncMarginAsync.bind(marginApiInst),
  getMarginDetail: marginApiInst.getMarginDetail.bind(marginApiInst),
  getMarginDetailStatistics: marginApiInst.getMarginDetailStatistics.bind(marginApiInst),
  getMarginDetailTopStocks: marginApiInst.getMarginDetailTopStocks.bind(marginApiInst),
  syncMarginDetailAsync: marginApiInst.syncMarginDetailAsync.bind(marginApiInst),

  // 融资融券标的相关
  getMarginSecs: marginSecsApiInst.getMarginSecs.bind(marginSecsApiInst),
  getLatestMarginSecs: marginSecsApiInst.getLatestMarginSecs.bind(marginSecsApiInst),
  syncMarginSecsAsync: marginSecsApiInst.syncMarginSecsAsync.bind(marginSecsApiInst),
  getMarginSecsStatistics: marginSecsApiInst.getMarginSecsStatistics.bind(marginSecsApiInst),

  // 转融资交易汇总相关
  getSlbLen: slbLenApiInst.getSlbLen.bind(slbLenApiInst),
  getSlbLenStatistics: slbLenApiInst.getSlbLenStatistics.bind(slbLenApiInst),
  getLatestSlbLen: slbLenApiInst.getLatestSlbLen.bind(slbLenApiInst),
  syncSlbLenAsync: slbLenApiInst.syncSlbLenAsync.bind(slbLenApiInst),

  // 定时任务相关
  getScheduledTasks: schedulerApiInst.getScheduledTasks.bind(schedulerApiInst),
  getScheduledTask: schedulerApiInst.getScheduledTask.bind(schedulerApiInst),
  createScheduledTask: schedulerApiInst.createScheduledTask.bind(schedulerApiInst),
  updateScheduledTask: schedulerApiInst.updateScheduledTask.bind(schedulerApiInst),
  deleteScheduledTask: schedulerApiInst.deleteScheduledTask.bind(schedulerApiInst),
  toggleScheduledTask: schedulerApiInst.toggleScheduledTask.bind(schedulerApiInst),
  executeScheduledTask: schedulerApiInst.executeScheduledTask.bind(schedulerApiInst),
  getTaskExecutionStatus: schedulerApiInst.getTaskExecutionStatus.bind(schedulerApiInst),
  getTaskExecutionHistory: schedulerApiInst.getTaskExecutionHistory.bind(schedulerApiInst),
  getRecentExecutionHistory: schedulerApiInst.getRecentExecutionHistory.bind(schedulerApiInst),
  validateCronExpression: schedulerApiInst.validateCronExpression.bind(schedulerApiInst),

  // Celery 任务相关
  getTasks: celeryTasksApiInst.getTasks.bind(celeryTasksApiInst),
  getActiveTasks: celeryTasksApiInst.getActiveTasks.bind(celeryTasksApiInst),
  getRecentHistory: celeryTasksApiInst.getRecentHistory.bind(celeryTasksApiInst),
  getStatistics: celeryTasksApiInst.getStatistics.bind(celeryTasksApiInst),
  getTask: celeryTasksApiInst.getTask.bind(celeryTasksApiInst),
  cancelTask: celeryTasksApiInst.cancelTask.bind(celeryTasksApiInst),
  deleteTask: celeryTasksApiInst.deleteTask.bind(celeryTasksApiInst),

  // 概念板块相关
  getConcepts: conceptsApiInst.getConcepts.bind(conceptsApiInst),
  getConcept: conceptsApiInst.getConcept.bind(conceptsApiInst),
  getConceptStocks: conceptsApiInst.getConceptStocks.bind(conceptsApiInst),
  syncConcepts: conceptsApiInst.syncConcepts.bind(conceptsApiInst),
  updateConcept: conceptsApiInst.updateConcept.bind(conceptsApiInst),
  deleteConcept: conceptsApiInst.deleteConcept.bind(conceptsApiInst),

  // 系统配置相关
  getDataSourceConfig: configApiInst.getDataSourceConfig.bind(configApiInst),
  updateDataSourceConfig: configApiInst.updateDataSourceConfig.bind(configApiInst),
  getAllConfigs: configApiInst.getAllConfigs.bind(configApiInst),
  getAIProviders: configApiInst.getAIProviders.bind(configApiInst),
  getAIProvider: configApiInst.getAIProvider.bind(configApiInst),
  createAIProvider: configApiInst.createAIProvider.bind(configApiInst),
  updateAIProvider: configApiInst.updateAIProvider.bind(configApiInst),
  deleteAIProvider: configApiInst.deleteAIProvider.bind(configApiInst),
  testAIProvider: configApiInst.testAIProvider.bind(configApiInst),
  setDefaultAIProvider: configApiInst.setDefaultAIProvider.bind(configApiInst),

  // 数据同步相关
  getSyncStatus: syncApiInst.getSyncStatus.bind(syncApiInst),
  syncStockList: syncApiInst.syncStockList.bind(syncApiInst),
  syncNewStocks: syncApiInst.syncNewStocks.bind(syncApiInst),
  syncDelistedStocks: syncApiInst.syncDelistedStocks.bind(syncApiInst),
  syncDailyBatch: syncApiInst.syncDailyBatch.bind(syncApiInst),
  syncDailyStock: syncApiInst.syncDailyStock.bind(syncApiInst),
  syncMinuteData: syncApiInst.syncMinuteData.bind(syncApiInst),
  syncRealtimeQuotes: syncApiInst.syncRealtimeQuotes.bind(syncApiInst),
  abortSync: syncApiInst.abortSync.bind(syncApiInst),
  pauseSync: syncApiInst.pauseSync.bind(syncApiInst),
  resumeSync: syncApiInst.resumeSync.bind(syncApiInst),
  getSyncHistory: syncApiInst.getSyncHistory.bind(syncApiInst),
  getSyncStatistics: syncApiInst.getSyncStatistics.bind(syncApiInst),
  getModuleSyncStatus: syncApiInst.getModuleSyncStatus.bind(syncApiInst),
  getAllModulesStatus: syncApiInst.getAllModulesStatus.bind(syncApiInst),
  syncAllModules: syncApiInst.syncAllModules.bind(syncApiInst),
  syncExtendedData: syncApiInst.syncExtendedData.bind(syncApiInst),

  // 扩展数据相关
  getDailyBasic: extendedDataApiInst.getDailyBasic.bind(extendedDataApiInst),
  syncDailyBasic: extendedDataApiInst.syncDailyBasic.bind(extendedDataApiInst),
  getHkHold: extendedDataApiInst.getHkHold.bind(extendedDataApiInst),
  syncHkHold: extendedDataApiInst.syncHkHold.bind(extendedDataApiInst),
  getLimitPrices: extendedDataApiInst.getLimitPrices.bind(extendedDataApiInst),
  syncLimitPrices: extendedDataApiInst.syncLimitPrices.bind(extendedDataApiInst),
  getBlockTrade: extendedDataApiInst.getBlockTrade.bind(extendedDataApiInst),
  syncBlockTrade: extendedDataApiInst.syncBlockTrade.bind(extendedDataApiInst),
  getAdjFactor: extendedDataApiInst.getAdjFactor.bind(extendedDataApiInst),
  syncAdjFactor: extendedDataApiInst.syncAdjFactor.bind(extendedDataApiInst),
  getSuspendInfo: extendedDataApiInst.getSuspendInfo.bind(extendedDataApiInst),
  getExtendedDataSummary: extendedDataApiInst.getExtendedDataSummary.bind(extendedDataApiInst),

  // 系统监控相关
  healthCheck: monitorApiInst.healthCheck.bind(monitorApiInst),
  getSystemStatus: monitorApiInst.getSystemStatus.bind(monitorApiInst),
  getSystemMetrics: monitorApiInst.getSystemMetrics.bind(monitorApiInst),
  getDatabaseStats: monitorApiInst.getDatabaseStats.bind(monitorApiInst),
  getApiPerformance: monitorApiInst.getApiPerformance.bind(monitorApiInst),
  getNotificationChannels: monitorApiInst.getNotificationChannels.bind(monitorApiInst),
  testNotificationChannel: monitorApiInst.testNotificationChannel.bind(monitorApiInst),
  sendNotification: monitorApiInst.sendNotification.bind(monitorApiInst),

  // 龙虎榜相关
  getTopList: topListApiInst.getTopList.bind(topListApiInst),
  getTopListStatistics: topListApiInst.getStatistics.bind(topListApiInst),
  getLatestTopList: topListApiInst.getLatest.bind(topListApiInst),
  getTopListTopRank: topListApiInst.getTopRank.bind(topListApiInst),
  syncTopListAsync: topListApiInst.syncAsync.bind(topListApiInst),

  // 龙虎榜机构明细相关
  getTopInst: topInstApiInst.getTopInst.bind(topInstApiInst),
  getTopInstStatistics: topInstApiInst.getStatistics.bind(topInstApiInst),
  getLatestTopInst: topInstApiInst.getLatest.bind(topInstApiInst),
  syncTopInstAsync: topInstApiInst.syncAsync.bind(topInstApiInst),

  // 涨跌停列表相关
  getLimitList: limitListApiInst.getData.bind(limitListApiInst),
  getLimitListStatistics: limitListApiInst.getStatistics.bind(limitListApiInst),
  getLatestLimitList: limitListApiInst.getLatest.bind(limitListApiInst),
  getTopLimitUp: limitListApiInst.getTopLimitUp.bind(limitListApiInst),
  syncLimitListAsync: limitListApiInst.syncAsync.bind(limitListApiInst),

  // 保留原有的通用方法
  get: axiosInst.get.bind(axiosInst),
  post: axiosInst.post.bind(axiosInst),
  put: axiosInst.put.bind(axiosInst),
  patch: axiosInst.patch.bind(axiosInst),
  delete: axiosInst.delete.bind(axiosInst),
}

// 导出默认实例
export default apiClient