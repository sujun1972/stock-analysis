/**
 * @file lib/api/index.ts
 * @description API 客户端统一导出文件
 * @author Claude
 * @created 2024-03-16
 * @updated 2024-03-16
 */

// 导入所有需要的模块
// 使用别名避免名称冲突，确保正确的模块导入和导出
import { BaseApiClient, axiosInstance as axiosInst, API_BASE_URL } from './base'
import { AuthApiClient, authApi as authApiInst } from './auth'
import { StockApiClient, stockApi as stockApiInst } from './stocks'
import { StrategyApiClient, strategyApi as strategyApiInst } from './strategies'
import { UserApiClient, userApi as userApiInst } from './users'

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

  // 保留原有的通用方法
  get: axiosInst.get.bind(axiosInst),
  post: axiosInst.post.bind(axiosInst),
  put: axiosInst.put.bind(axiosInst),
  patch: axiosInst.patch.bind(axiosInst),
  delete: axiosInst.delete.bind(axiosInst),
}

// 导出默认实例
export default apiClient