/**
 * @file lib/api/index.ts
 * @description API 客户端统一导出文件
 * @author Claude
 * @created 2024-03-16
 * @updated 2024-03-16
 */

// 导出基础类和实例
export { BaseApiClient, axiosInstance, API_BASE_URL } from './base'

// 导出认证 API
export { AuthApiClient, authApi } from './auth'
export type { LoginRequest, LoginResponse, RegisterRequest, UpdatePasswordRequest, UpdateProfileRequest } from './auth'

// 导出股票 API
export { StockApiClient, stockApi } from './stocks'
export type { StockListParams, UpdateStockRequest, StockConceptRequest } from './stocks'

// 导出策略 API
export { StrategyApiClient, strategyApi } from './strategies'
export type { StrategyListParams, AssignStrategyRequest } from './strategies'

// 导出用户 API
export { UserApiClient, userApi } from './users'
export type {
  User,
  UserListParams,
  CreateUserRequest,
  UpdateUserRequest,
  UserStatistics,
  UserQuota
} from './users'

// 创建统一的 API 客户端对象（向后兼容）
export const apiClient = {
  // 认证相关
  login: authApi.login.bind(authApi),
  register: authApi.register.bind(authApi),
  refresh: authApi.refresh.bind(authApi),
  logout: authApi.logout.bind(authApi),
  getCurrentUser: authApi.getCurrentUser.bind(authApi),
  updatePassword: authApi.updatePassword.bind(authApi),
  updateProfile: authApi.updateProfile.bind(authApi),

  // 用户管理
  getUsers: userApi.getUsers.bind(userApi),
  getUser: userApi.getUser.bind(userApi),
  createUser: userApi.createUser.bind(userApi),
  updateUser: userApi.updateUser.bind(userApi),
  deleteUser: userApi.deleteUser.bind(userApi),
  batchDeleteUsers: userApi.batchDeleteUsers.bind(userApi),
  toggleUserStatus: userApi.toggleUserStatus.bind(userApi),
  resetUserPassword: userApi.resetUserPassword.bind(userApi),
  getUserStatistics: userApi.getUserStatistics.bind(userApi),
  getUserQuota: userApi.getUserQuota.bind(userApi),
  updateUserQuota: userApi.updateUserQuota.bind(userApi),

  // 股票相关
  getStockList: stockApi.getStockList.bind(stockApi),
  getStock: stockApi.getStock.bind(stockApi),
  updateStock: stockApi.updateStock.bind(stockApi),
  updateStockList: stockApi.updateStockList.bind(stockApi),
  getStockConcepts: stockApi.getStockConcepts.bind(stockApi),
  updateStockConcepts: stockApi.updateStockConcepts.bind(stockApi),
  batchUpdateStockConcepts: stockApi.batchUpdateStockConcepts.bind(stockApi),
  getStockDaily: stockApi.getStockDaily.bind(stockApi),
  getStockMinute: stockApi.getStockMinute.bind(stockApi),
  syncStockData: stockApi.syncStockData.bind(stockApi),
  batchSyncStockData: stockApi.batchSyncStockData.bind(stockApi),
  searchStocks: stockApi.searchStocks.bind(stockApi),

  // 策略相关
  getStrategies: strategyApi.getStrategies.bind(strategyApi),
  getStrategy: strategyApi.getStrategy.bind(strategyApi),
  createStrategy: strategyApi.createStrategy.bind(strategyApi),
  updateStrategy: strategyApi.updateStrategy.bind(strategyApi),
  deleteStrategy: strategyApi.deleteStrategy.bind(strategyApi),
  batchDeleteStrategies: strategyApi.batchDeleteStrategies.bind(strategyApi),
  validateStrategy: strategyApi.validateStrategy.bind(strategyApi),
  testStrategy: strategyApi.testStrategy.bind(strategyApi),
  runBacktest: strategyApi.runBacktest.bind(strategyApi),
  toggleStrategy: strategyApi.toggleStrategy.bind(strategyApi),
  togglePublish: strategyApi.togglePublish.bind(strategyApi),
  cloneStrategy: strategyApi.cloneStrategy.bind(strategyApi),
  getStrategyStatistics: strategyApi.getStrategyStatistics.bind(strategyApi),
  getUserStrategies: strategyApi.getUserStrategies.bind(strategyApi),
  assignStrategiesToUser: strategyApi.assignStrategiesToUser.bind(strategyApi),
  removeUserStrategy: strategyApi.removeUserStrategy.bind(strategyApi),
  getStrategyTypes: strategyApi.getStrategyTypes.bind(strategyApi),
  exportStrategy: strategyApi.exportStrategy.bind(strategyApi),
  importStrategy: strategyApi.importStrategy.bind(strategyApi),
  getStrategyLogs: strategyApi.getStrategyLogs.bind(strategyApi),
  clearStrategyLogs: strategyApi.clearStrategyLogs.bind(strategyApi),

  // 保留原有的通用方法
  get: axiosInstance.get.bind(axiosInstance),
  post: axiosInstance.post.bind(axiosInstance),
  put: axiosInstance.put.bind(axiosInstance),
  patch: axiosInstance.patch.bind(axiosInstance),
  delete: axiosInstance.delete.bind(axiosInstance),
}

// 导出默认实例
export default apiClient