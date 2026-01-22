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
 * 可以在这里添加认证token等全局请求配置
 */
axiosInstance.interceptors.request.use(
  (config) => {
    // TODO: 添加认证token
    // if (token) {
    //   config.headers.Authorization = `Bearer ${token}`
    // }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

/**
 * 响应拦截器
 * 统一处理API错误和网络错误
 */
axiosInstance.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // 统一错误处理
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
  }): Promise<PaginatedResponse<StockInfo>> {
    const response = await axiosInstance.get('/api/stocks/list', { params })
    return response.data
  }

  // 获取单只股票信息
  async getStock(code: string): Promise<StockInfo> {
    // 通过搜索API获取单个股票信息
    const response = await axiosInstance.get(`/api/stocks/list`, {
      params: { search: code, limit: 1 }
    })
    const data = response.data as PaginatedResponse<StockInfo>
    if (data.data && data.data.length > 0) {
      return data.data[0]
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
    return response.data
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
  async syncRealtimeQuotes(codes?: string[]): Promise<ApiResponse<{
    total: number
    updated_at: string
  }>> {
    const response = await axiosInstance.post('/api/sync/realtime', { codes })
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

  // ========== 回测相关API ==========

  // 运行回测
  async runBacktest(params: {
    symbols: string | string[]
    start_date: string
    end_date: string
    initial_cash?: number
    strategy_id?: string
    strategy_params?: Record<string, any>
  }): Promise<ApiResponse<any>> {
    const response = await axiosInstance.post('/api/backtest/run', params)
    return response.data
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
}

// 导出单例
export const apiClient = new ApiClient()
export default apiClient
