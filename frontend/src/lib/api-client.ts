import axios, { AxiosInstance } from 'axios'
import type {
  StockInfo,
  StockDaily,
  FeatureData,
  Prediction,
  BacktestResult,
  ApiResponse,
  PaginatedResponse,
  MinuteData,
  Concept,
  // V2.0 统一策略类型
  Strategy,
  CreateStrategyRequest,
  UpdateStrategyRequest,
  StrategyValidationResponse,
  StrategyStatistics,
  StrategyTestResponse,
  BacktestRequest,
  // V1.0 旧类型（向后兼容）
  StrategyTypeMeta,
  StrategyConfig,
  CreateStrategyConfigRequest,
  UpdateStrategyConfigRequest,
  StrategyConfigValidationResponse,
  StrategyConfigTestResponse,
  DynamicStrategy,
  CreateDynamicStrategyRequest,
  UpdateDynamicStrategyRequest,
  DynamicStrategyCodeResponse,
  DynamicStrategyValidationResponse,
  DynamicStrategyTestResponse,
  DynamicStrategyStatistics,
} from '@/types'

/**
 * API基础URL配置
 * 优先使用环境变量NEXT_PUBLIC_API_URL，否则默认为本地开发地址
 */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

/**
 * 创建axios实例
 * 配置了基础URL、超时时间和默认headers
 */
const axiosInstance: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 600000, // 增加到 600 秒 (10分钟)，用于处理大批量同步操作
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * 请求拦截器
 * 自动添加认证token到请求头
 */
axiosInstance.interceptors.request.use(
  (config) => {
    // 只在浏览器环境中访问localStorage
    if (typeof window === 'undefined') {
      return config
    }

    // 从localStorage获取Token（由auth-store管理）
    const authStorage = localStorage.getItem('auth-storage')
    if (authStorage) {
      try {
        const { state } = JSON.parse(authStorage)
        const accessToken = state?.accessToken
        if (accessToken) {
          config.headers.Authorization = `Bearer ${accessToken}`
        }
      } catch (error) {
        console.error('Failed to parse auth storage:', error)
      }
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

/**
 * 响应拦截器
 * 统一处理API错误、Token过期自动刷新
 */
axiosInstance.interceptors.response.use(
  (response) => {
    return response
  },
  async (error) => {
    const originalRequest = error.config

    // Token过期，尝试刷新
    // 注意：不对refresh请求本身进行刷新，避免死循环
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes('/api/auth/refresh') &&
      !originalRequest.url?.includes('/api/auth/login')
    ) {
      originalRequest._retry = true

      try {
        // 动态导入auth store以避免循环依赖
        const { useAuthStore } = await import('@/stores/auth-store')
        await useAuthStore.getState().refreshAccessToken()

        // 重新获取新Token并重试请求
        const authStorage = localStorage.getItem('auth-storage')
        if (authStorage) {
          const { state } = JSON.parse(authStorage)
          const accessToken = state?.accessToken
          if (accessToken) {
            originalRequest.headers.Authorization = `Bearer ${accessToken}`
          }
        }

        return axiosInstance(originalRequest)
      } catch (refreshError) {
        // Token刷新失败，需要重新登录
        console.error('Token refresh failed, redirecting to login...')

        // 清除认证状态
        const { useAuthStore } = await import('@/stores/auth-store')
        useAuthStore.getState().logout()

        // 重定向到登录页
        if (typeof window !== 'undefined') {
          window.location.href = '/login'
        }

        return Promise.reject(refreshError)
      }
    }

    // 其他错误统一处理
    if (error.response) {
      console.error('API Error:', error.response.data)
    } else if (error.request) {
      console.error('Network Error:', error.request)
    } else {
      console.error('Error:', error.message)
    }
    return Promise.reject(error)
  }
)

/**
 * API客户端类
 * 封装所有后端API调用
 */
class ApiClient {
  // ========== 基础HTTP方法 ==========

  /**
   * 通用GET请求
   */
  async get<T = any>(url: string, config?: any): Promise<ApiResponse<T>> {
    const response = await axiosInstance.get(url, config)
    return response.data
  }

  /**
   * 通用POST请求
   */
  async post<T = any>(url: string, data?: any, config?: any): Promise<ApiResponse<T>> {
    const response = await axiosInstance.post(url, data, config)
    return response.data
  }

  /**
   * 通用PATCH请求
   */
  async patch<T = any>(url: string, data?: any, config?: any): Promise<ApiResponse<T>> {
    const response = await axiosInstance.patch(url, data, config)
    return response.data
  }

  /**
   * 通用DELETE请求
   */
  async delete<T = any>(url: string, config?: any): Promise<ApiResponse<T>> {
    const response = await axiosInstance.delete(url, config)
    return response.data
  }

  /**
   * 通用PUT请求
   */
  async put<T = any>(url: string, data?: any, config?: any): Promise<ApiResponse<T>> {
    const response = await axiosInstance.put(url, data, config)
    return response.data
  }

  // 健康检查
  async healthCheck(): Promise<ApiResponse<any>> {
    const response = await axiosInstance.get('/health')
    return response.data
  }

  // ========== 股票相关API ==========

  // 获取股票列表
  async getStockList(params?: {
    market?: string
    status?: string
    skip?: number
    limit?: number
    search?: string
    concepts?: string
    sort_by?: string
    sort_order?: string
  }): Promise<PaginatedResponse<StockInfo>> {
    const response = await axiosInstance.get('/api/stocks/list', { params })
    const result = response.data as ApiResponse<PaginatedResponse<StockInfo>>
    // 返回嵌套在 data 字段中的分页数据
    return result.data || { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 }
  }

  // 获取单只股票信息
  async getStock(code: string): Promise<StockInfo> {
    // 通过搜索API获取单个股票信息
    const response = await axiosInstance.get(`/api/stocks/list`, {
      params: { search: code, limit: 1 }
    })
    const result = response.data as ApiResponse<PaginatedResponse<StockInfo>>
    if (result.data?.items && result.data.items.length > 0) {
      return result.data.items[0]
    }
    throw new Error(`Stock ${code} not found`)
  }

  /**
   * 更新股票列表（从数据源获取最新列表）
   * @returns 包含更新股票总数的响应对象
   */
  async updateStockList(): Promise<ApiResponse<{ total: number }>> {
    const response = await axiosInstance.post('/api/stocks/update')
    return response.data
  }

  // ========== 概念相关API ==========

  // 获取概念列表
  async getConceptsList(params?: {
    limit?: number
    search?: string
  }): Promise<{ items: Concept[]; total: number }> {
    const response = await axiosInstance.get('/api/concepts/list', { params })
    return response.data.data || { items: [], total: 0 }
  }

  // 获取概念详情
  async getConcept(conceptId: number): Promise<Concept> {
    const response = await axiosInstance.get(`/api/concepts/${conceptId}`)
    return response.data.data
  }

  // 获取概念包含的股票
  async getConceptStocks(conceptId: number, limit?: number): Promise<{ items: StockInfo[]; total: number }> {
    const response = await axiosInstance.get(`/api/concepts/${conceptId}/stocks`, {
      params: { limit }
    })
    return response.data.data || { items: [], total: 0 }
  }

  // 获取股票的概念
  async getStockConcepts(stockCode: string): Promise<Concept[]> {
    const response = await axiosInstance.get(`/api/concepts/stock/${stockCode}`)
    return response.data.data || []
  }

  // 同步概念数据
  async syncConcepts(source: string = 'ths'): Promise<ApiResponse<any>> {
    const response = await axiosInstance.post('/api/concepts/sync', null, {
      params: { source }
    })
    return response.data
  }

  // 更新股票的概念标签
  async updateStockConcepts(stockCode: string, conceptIds: number[]): Promise<ApiResponse<any>> {
    const response = await axiosInstance.put(`/api/concepts/stock/${stockCode}/concepts`, {
      concept_ids: conceptIds
    })
    return response.data
  }

  // ========== 数据相关API ==========

  // 获取日线数据
  async getDailyData(
    code: string,
    params?: { start_date?: string; end_date?: string }
  ): Promise<StockDaily[]> {
    const response = await axiosInstance.get(`/api/data/daily/${code}`, { params })
    return response.data.data
  }

  // 下载股票数据
  async downloadData(params: {
    stock_codes: string[]
    years?: number
  }): Promise<ApiResponse<{ task_id: string }>> {
    const response = await axiosInstance.post('/api/data/download', params)
    return response.data
  }

  // ========== 特征相关API ==========

  // 获取特征数据
  async getFeatures(
    code: string,
    params?: {
      feature_type?: string
      limit?: number
      end_date?: string
    }
  ): Promise<{
    code: string
    feature_type: string
    total: number
    returned: number
    has_more: boolean
    columns: string[]
    data: FeatureData[]
  }> {
    const response = await axiosInstance.get(`/api/features/${code}`, { params })
    // 后端返回的结构是 { code: 200, message: "...", data: {...} }
    // 需要返回 data 字段中的内容
    return response.data.data
  }

  // 计算特征
  async calculateFeatures(
    code: string,
    params?: { feature_types?: string[] }
  ): Promise<ApiResponse<any>> {
    const response = await axiosInstance.post(`/api/features/calculate/${code}`, params)
    return response.data
  }

  // ========== 模型相关API ==========

  // 训练模型
  async trainModel(params: {
    model_type: string
    stock_codes: string[]
    train_config?: Record<string, any>
  }): Promise<ApiResponse<{ task_id: string }>> {
    const response = await axiosInstance.post('/api/models/train', params)
    return response.data
  }

  // ========== 数据引擎配置API ==========

  /**
   * 获取数据源配置
   */
  async getDataSourceConfig(): Promise<ApiResponse<{
    data_source: string
    minute_data_source: string
    realtime_data_source: string
    tushare_token: string
  }>> {
    const response = await axiosInstance.get('/api/config/source')
    return response.data
  }

  /**
   * 更新数据源配置
   */
  async updateDataSourceConfig(params: {
    data_source: string
    minute_data_source?: string
    realtime_data_source?: string
    tushare_token?: string
  }): Promise<ApiResponse<any>> {
    const response = await axiosInstance.post('/api/config/source', params)
    return response.data
  }

  /**
   * 获取所有系统配置
   */
  async getAllConfigs(): Promise<ApiResponse<Record<string, any>>> {
    const response = await axiosInstance.get('/api/config/all')
    return response.data
  }

  // ========== 数据同步API ==========

  /**
   * 获取同步状态
   */
  async getSyncStatus(): Promise<ApiResponse<{
    status: string
    last_sync_date: string
    progress: number
    total: number
    completed: number
  }>> {
    const response = await axiosInstance.get('/api/sync/status')
    return response.data
  }

  /**
   * 同步股票列表
   */
  async syncStockList(): Promise<ApiResponse<{ total: number }>> {
    const response = await axiosInstance.post('/api/sync/stock-list')
    return response.data
  }

  /**
   * 同步新股列表
   */
  async syncNewStocks(days: number = 30): Promise<ApiResponse<{ total: number }>> {
    const response = await axiosInstance.post('/api/sync/new-stocks', { days })
    return response.data
  }

  /**
   * 同步退市列表
   */
  async syncDelistedStocks(): Promise<ApiResponse<{ total: number }>> {
    const response = await axiosInstance.post('/api/sync/delisted-stocks')
    return response.data
  }

  /**
   * 批量同步日线数据
   */
  async syncDailyBatch(params: {
    codes?: string[]
    start_date?: string  // 开始日期，格式: YYYY-MM-DD
    end_date?: string    // 结束日期，格式: YYYY-MM-DD
    years?: number       // 兼容旧参数
    max_stocks?: number  // 已废弃
  }): Promise<ApiResponse<{
    success: number
    failed: number
    skipped: number
    total: number
    aborted: boolean
  }>> {
    const response = await axiosInstance.post('/api/sync/daily/batch', params)
    return response.data
  }

  /**
   * 同步单只股票日线数据
   */
  async syncDailyStock(code: string, years: number = 5): Promise<ApiResponse<{
    code: string
    records: number
  }>> {
    const response = await axiosInstance.post(`/api/sync/daily/${code}`, { years })
    return response.data
  }

  /**
   * 中止当前正在运行的同步任务
   */
  async abortSync(): Promise<ApiResponse<any>> {
    const response = await axiosInstance.post('/api/sync/abort')
    return response.data
  }

  /**
   * 同步分时数据
   */
  async syncMinuteData(code: string, params: {
    period?: string
    days?: number
  }): Promise<ApiResponse<any>> {
    const response = await axiosInstance.post(`/api/sync/minute/${code}`, params)
    return response.data
  }

  /**
   * 更新实时行情
   */
  async syncRealtimeQuotes(params?: {
    codes?: string[]
    batch_size?: number
    update_oldest?: boolean
  }): Promise<ApiResponse<{
    total: number
    batch_size: number | string
    update_mode: string
    updated_at: string
  }>> {
    const response = await axiosInstance.post('/api/sync/realtime', params || {})
    return response.data
  }

  /**
   * 获取同步历史记录
   */
  async getSyncHistory(params?: {
    limit?: number
    offset?: number
  }): Promise<ApiResponse<any[]>> {
    const response = await axiosInstance.get('/api/sync/history', { params })
    return response.data
  }

  // ========== 分时数据相关API ==========

  /**
   * 获取股票1分钟K线数据（按需加载）
   *
   * 注意：后端只返回1分钟数据，前端需要自行聚合为其他周期
   */
  async getMinuteData(
    code: string,
    date?: string,
    forceRefresh: boolean = false
  ): Promise<ApiResponse<{
    code: string
    date: string
    records: MinuteData[]
    from_cache: boolean
    completeness?: number
    record_count: number
  }>> {
    const params: any = {}
    if (date) params.date = date
    if (forceRefresh) params.force_refresh = true

    const response = await axiosInstance.get(`/api/stocks/${code}/minute`, { params })
    return response.data
  }

  /**
   * 获取股票分时数据（日期范围）
   */
  async getMinuteDataRange(
    code: string,
    period: string = '5',
    startDate?: string,
    endDate?: string,
    limit: number = 1000
  ): Promise<ApiResponse<{
    code: string
    period: string
    start_date: string
    end_date: string
    records: MinuteData[]
    record_count: number
  }>> {
    const params: any = { period, limit }
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate

    const response = await axiosInstance.get(`/api/stocks/${code}/minute/range`, { params })
    return response.data
  }

  // 获取预测结果
  async getPrediction(
    code: string,
    params?: { model_name?: string }
  ): Promise<Prediction> {
    const response = await axiosInstance.get(`/api/models/predict/${code}`, { params })
    return response.data
  }

  // ========== 统一策略相关API (V2.0) ==========

  /**
   * 获取统一策略列表
   */
  async getStrategies(params?: {
    source_type?: 'builtin' | 'ai' | 'custom'
    strategy_type?: 'entry' | 'exit'
    category?: string
    is_enabled?: boolean
    search?: string
  }): Promise<ApiResponse<Strategy[]>> {
    const response = await axiosInstance.get('/api/strategies', { params })
    return response.data
  }

  /**
   * 获取单个策略详情
   */
  async getStrategy(id: number): Promise<ApiResponse<Strategy>> {
    const response = await axiosInstance.get(`/api/strategies/${id}`)
    return response.data
  }

  /**
   * 创建新策略
   */
  async createStrategy(data: CreateStrategyRequest): Promise<ApiResponse<{ strategy_id: number }>> {
    const response = await axiosInstance.post('/api/strategies', data)
    return response.data
  }

  /**
   * 更新策略
   */
  async updateStrategy(id: number, data: UpdateStrategyRequest): Promise<ApiResponse<{ strategy_id: number }>> {
    const response = await axiosInstance.put(`/api/strategies/${id}`, data)
    return response.data
  }

  /**
   * 删除策略
   */
  async deleteStrategy(id: number): Promise<ApiResponse<void>> {
    const response = await axiosInstance.delete(`/api/strategies/${id}`)
    return response.data
  }

  /**
   * 验证策略代码
   */
  async validateStrategy(code: string): Promise<ApiResponse<StrategyValidationResponse>> {
    const response = await axiosInstance.post('/api/strategies/validate', { code })
    return response.data
  }

  /**
   * 获取策略统计信息
   */
  async getStrategyStatistics(): Promise<ApiResponse<StrategyStatistics>> {
    const response = await axiosInstance.get('/api/strategies/statistics')
    return response.data
  }

  /**
   * 获取策略代码
   */
  async getStrategyCode(id: number): Promise<ApiResponse<{ code: string }>> {
    const response = await axiosInstance.get(`/api/strategies/${id}/code`)
    return response.data
  }

  /**
   * 测试策略
   */
  async testStrategy(id: number): Promise<ApiResponse<StrategyTestResponse>> {
    const response = await axiosInstance.post(`/api/strategies/${id}/test`)
    return response.data
  }

  /**
   * 运行统一回测 (V2.0)
   */
  async runBacktestV2(params: BacktestRequest): Promise<ApiResponse<any>> {
    const response = await axiosInstance.post('/api/backtest/run-v3', params)
    return response.data
  }

  // ========== 策略配置相关API（旧版，向后兼容）==========

  /**
   * 获取可用策略类型列表
   */
  async getStrategyTypes(): Promise<ApiResponse<StrategyTypeMeta[]>> {
    const response = await axiosInstance.get('/api/strategy-configs/types')
    return response.data
  }

  /**
   * 创建策略配置
   */
  async createStrategyConfig(data: CreateStrategyConfigRequest): Promise<ApiResponse<{ config_id: number }>> {
    const response = await axiosInstance.post('/api/strategy-configs', data)
    return response.data
  }

  /**
   * 获取策略配置列表
   */
  async getStrategyConfigs(params?: {
    strategy_type?: string
    is_active?: boolean
    page?: number
    page_size?: number
  }): Promise<ApiResponse<PaginatedResponse<StrategyConfig>>> {
    const response = await axiosInstance.get('/api/strategy-configs', { params })
    return response.data
  }

  /**
   * 获取单个策略配置详情
   */
  async getStrategyConfig(id: number): Promise<ApiResponse<StrategyConfig>> {
    const response = await axiosInstance.get(`/api/strategy-configs/${id}`)
    return response.data
  }

  /**
   * 更新策略配置
   */
  async updateStrategyConfig(id: number, data: UpdateStrategyConfigRequest): Promise<ApiResponse<{ config_id: number }>> {
    const response = await axiosInstance.put(`/api/strategy-configs/${id}`, data)
    return response.data
  }

  /**
   * 删除策略配置
   */
  async deleteStrategyConfig(id: number): Promise<ApiResponse<void>> {
    const response = await axiosInstance.delete(`/api/strategy-configs/${id}`)
    return response.data
  }

  /**
   * 测试策略配置
   */
  async testStrategyConfig(id: number): Promise<ApiResponse<StrategyConfigTestResponse>> {
    const response = await axiosInstance.post(`/api/strategy-configs/${id}/test`)
    return response.data
  }

  /**
   * 验证策略配置参数
   */
  async validateStrategyConfig(data: {
    strategy_type: string
    config: Record<string, any>
  }): Promise<ApiResponse<StrategyConfigValidationResponse>> {
    const response = await axiosInstance.post('/api/strategy-configs/validate', data)
    return response.data
  }

  // ========== 动态策略相关API ==========

  /**
   * 创建动态策略
   */
  async createDynamicStrategy(data: CreateDynamicStrategyRequest): Promise<ApiResponse<{ strategy_id: number }>> {
    const response = await axiosInstance.post('/api/dynamic-strategies', data)
    return response.data
  }

  /**
   * 获取动态策略列表
   */
  async getDynamicStrategies(params?: {
    validation_status?: string
    is_enabled?: boolean
    page?: number
    page_size?: number
  }): Promise<ApiResponse<PaginatedResponse<DynamicStrategy>>> {
    const response = await axiosInstance.get('/api/dynamic-strategies', { params })
    return response.data
  }

  /**
   * 获取单个动态策略详情
   */
  async getDynamicStrategy(id: number): Promise<ApiResponse<DynamicStrategy>> {
    const response = await axiosInstance.get(`/api/dynamic-strategies/${id}`)
    return response.data
  }

  /**
   * 获取动态策略代码
   */
  async getDynamicStrategyCode(id: number): Promise<ApiResponse<DynamicStrategyCodeResponse>> {
    const response = await axiosInstance.get(`/api/dynamic-strategies/${id}/code`)
    return response.data
  }

  /**
   * 更新动态策略
   */
  async updateDynamicStrategy(id: number, data: UpdateDynamicStrategyRequest): Promise<ApiResponse<{ strategy_id: number }>> {
    const response = await axiosInstance.put(`/api/dynamic-strategies/${id}`, data)
    return response.data
  }

  /**
   * 删除动态策略
   */
  async deleteDynamicStrategy(id: number): Promise<ApiResponse<void>> {
    const response = await axiosInstance.delete(`/api/dynamic-strategies/${id}`)
    return response.data
  }

  /**
   * 测试动态策略
   */
  async testDynamicStrategy(id: number): Promise<ApiResponse<DynamicStrategyTestResponse>> {
    const response = await axiosInstance.post(`/api/dynamic-strategies/${id}/test`)
    return response.data
  }

  /**
   * 验证动态策略代码
   */
  async validateDynamicStrategy(id: number): Promise<ApiResponse<DynamicStrategyValidationResponse>> {
    const response = await axiosInstance.post(`/api/dynamic-strategies/${id}/validate`)
    return response.data
  }

  /**
   * 获取动态策略统计信息
   */
  async getDynamicStrategyStatistics(): Promise<ApiResponse<DynamicStrategyStatistics>> {
    const response = await axiosInstance.get('/api/dynamic-strategies/statistics')
    return response.data
  }

  // ========== 统一回测API ==========

  /**
   * 运行统一回测（支持三种策略类型）
   */
  async runUnifiedBacktest(params: BacktestRequest): Promise<ApiResponse<any>> {
    const response = await axiosInstance.post('/api/backtest', params)
    return response.data
  }

  // ========== 回测相关API（旧版，向后兼容）==========

  /**
   * 运行回测
   * @deprecated 使用 runUnifiedBacktest 代替
   */
  async runBacktest(params: {
    symbols: string | string[]
    start_date: string
    end_date: string
    initial_cash?: number
    strategy_id?: string
    strategy_params?: Record<string, any>
  }): Promise<ApiResponse<any>> {
    // 转换为新格式，调用统一回测接口
    return this.runUnifiedBacktest({
      strategy_type: 'predefined',
      strategy_name: params.strategy_id || 'momentum',
      strategy_config: params.strategy_params || {},
      stock_pool: Array.isArray(params.symbols) ? params.symbols : [params.symbols],
      start_date: params.start_date,
      end_date: params.end_date,
      initial_capital: params.initial_cash
    })
  }

  // 获取策略列表
  async getStrategyList(): Promise<ApiResponse<any[]>> {
    const response = await axiosInstance.get('/api/strategy/list')
    return response.data
  }

  // 获取策略元数据
  async getStrategyMetadata(strategyId: string = 'complex_indicator'): Promise<ApiResponse<any>> {
    const response = await axiosInstance.get('/api/strategy/metadata', {
      params: { strategy_id: strategyId }
    })
    return response.data
  }

  // 获取回测结果
  async getBacktestResult(taskId: string): Promise<ApiResponse<any>> {
    const response = await axiosInstance.get(`/api/backtest/result/${taskId}`)
    return response.data
  }

  /**
   * 获取特定模块的同步状态
   */
  async getModuleSyncStatus(module: string): Promise<ApiResponse<{
    status: string
    total: number
    success: number
    failed: number
    progress: number
    error_message: string
    started_at: string
    completed_at: string
  }>> {
    const response = await axiosInstance.get(`/api/sync/status/${module}`)
    return response.data
  }

  // ========== Scheduler API ==========

  /**
   * 获取所有定时任务
   */
  async getScheduledTasks(): Promise<ApiResponse<any[]>> {
    const response = await axiosInstance.get('/api/scheduler/tasks')
    return response.data
  }

  /**
   * 获取单个定时任务详情
   */
  async getScheduledTask(taskId: number): Promise<ApiResponse<any>> {
    const response = await axiosInstance.get(`/api/scheduler/tasks/${taskId}`)
    return response.data
  }

  /**
   * 创建定时任务
   */
  async createScheduledTask(data: {
    task_name: string
    module: string
    description?: string
    cron_expression: string
    enabled?: boolean
    params?: any
  }): Promise<ApiResponse<{ id: number }>> {
    const response = await axiosInstance.post('/api/scheduler/tasks', data)
    return response.data
  }

  /**
   * 更新定时任务
   */
  async updateScheduledTask(taskId: number, data: {
    description?: string
    cron_expression?: string
    enabled?: boolean
    params?: any
  }): Promise<ApiResponse<{ id: number }>> {
    const response = await axiosInstance.put(`/api/scheduler/tasks/${taskId}`, data)
    return response.data
  }

  /**
   * 删除定时任务
   */
  async deleteScheduledTask(taskId: number): Promise<ApiResponse<{ id: number }>> {
    const response = await axiosInstance.delete(`/api/scheduler/tasks/${taskId}`)
    return response.data
  }

  /**
   * 切换定时任务启用状态
   */
  async toggleScheduledTask(taskId: number): Promise<ApiResponse<{ enabled: boolean }>> {
    const response = await axiosInstance.post(`/api/scheduler/tasks/${taskId}/toggle`)
    return response.data
  }

  /**
   * 获取任务执行历史
   */
  async getTaskExecutionHistory(taskId: number, limit: number = 20): Promise<ApiResponse<any[]>> {
    const response = await axiosInstance.get(`/api/scheduler/tasks/${taskId}/history`, {
      params: { limit }
    })
    return response.data
  }

  /**
   * 获取最近的任务执行历史
   */
  async getRecentExecutionHistory(limit: number = 50): Promise<ApiResponse<any[]>> {
    const response = await axiosInstance.get('/api/scheduler/history/recent', {
      params: { limit }
    })
    return response.data
  }

  // ========== 市场状态相关API ==========

  /**
   * 获取当前市场状态
   */
  async getMarketStatus(): Promise<ApiResponse<{
    status: string
    description: string
    is_trading: boolean
    should_refresh: boolean
    next_session_time: string | null
    next_session_desc: string | null
  }>> {
    const response = await axiosInstance.get('/api/market/status')
    return response.data
  }

  /**
   * 检查实时数据新鲜度
   */
  async checkDataFreshness(params?: {
    codes?: string[]
    force?: boolean
  }): Promise<ApiResponse<{
    should_refresh: boolean
    reason: string
    market_status: string
    market_description: string
    last_update: string | null
    codes_count: number | null
  }>> {
    const response = await axiosInstance.get('/api/market/refresh-check', { params: params || {} })
    return response.data
  }

  /**
   * 获取单只股票的实时信息（包含新鲜度）
   */
  async getRealtimeInfo(code: string): Promise<ApiResponse<any>> {
    const response = await axiosInstance.get(`/api/market/realtime-info/${code}`)
    return response.data
  }

  // ========== 个人资料相关API ==========

  /**
   * 获取个人资料
   */
  async getProfile(): Promise<ApiResponse<any>> {
    const response = await axiosInstance.get('/api/profile')
    return response.data
  }

  /**
   * 更新个人资料
   */
  async updateProfile(data: {
    full_name?: string
    phone?: string
    avatar_url?: string
  }): Promise<ApiResponse<any>> {
    const response = await axiosInstance.patch('/api/profile', data)
    return response.data
  }

  /**
   * 修改密码
   */
  async changePassword(oldPassword: string, newPassword: string): Promise<ApiResponse<any>> {
    const response = await axiosInstance.post('/api/profile/change-password', {
      old_password: oldPassword,
      new_password: newPassword,
    })
    return response.data
  }

  /**
   * 获取个人配额
   */
  async getQuota(): Promise<ApiResponse<any>> {
    const response = await axiosInstance.get('/api/profile/quota')
    return response.data
  }
}

// 导出单例
export const apiClient = new ApiClient()
export default apiClient
