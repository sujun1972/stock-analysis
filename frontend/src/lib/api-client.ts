import axios, { AxiosInstance } from 'axios'
import type {
  StockInfo,
  StockDaily,
  FeatureData,
  Prediction,
  BacktestResult,
  ApiResponse,
  PaginatedResponse,
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
  timeout: 30000,
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
    const response = await axiosInstance.get(`/api/stocks/${code}`)
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
    params?: { feature_type?: string }
  ): Promise<FeatureData[]> {
    const response = await axiosInstance.get(`/api/features/${code}`, { params })
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
    strategy: string
    stock_codes: string[]
    start_date: string
    end_date: string
    initial_capital?: number
    config?: Record<string, any>
  }): Promise<ApiResponse<{ task_id: string }>> {
    const response = await axiosInstance.post('/api/backtest/run', params)
    return response.data
  }

  // 获取回测结果
  async getBacktestResult(taskId: string): Promise<BacktestResult> {
    const response = await axiosInstance.get(`/api/backtest/result/${taskId}`)
    return response.data
  }
}

// 导出单例
export const apiClient = new ApiClient()
export default apiClient
