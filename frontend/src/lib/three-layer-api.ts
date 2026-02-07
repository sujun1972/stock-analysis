/**
 * 三层架构API服务层
 * 封装后端 /api/three-layer 接口
 */

import axios, { AxiosInstance, AxiosError } from 'axios'
import type {
  SelectorInfo,
  EntryInfo,
  ExitInfo,
  StrategyConfig,
  BacktestResult,
  ValidationResult,
  ApiResponse,
} from './three-layer-types'

/**
 * API基础配置
 */
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const THREE_LAYER_API_PREFIX = '/api/three-layer'
const DEFAULT_TIMEOUT = 60000 // 60秒
const BACKTEST_TIMEOUT = 300000 // 回测超时时间5分钟

/**
 * 重试配置
 */
const RETRY_CONFIG = {
  maxRetries: 3,
  retryDelay: 1000, // 1秒
  retryableStatusCodes: [408, 429, 500, 502, 503, 504],
}

/**
 * 自定义错误类
 */
export class ThreeLayerApiError extends Error {
  statusCode?: number
  response?: any

  constructor(message: string, statusCode?: number, response?: any) {
    super(message)
    this.name = 'ThreeLayerApiError'
    this.statusCode = statusCode
    this.response = response
  }
}

/**
 * 延迟函数
 */
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

/**
 * 判断是否应该重试
 */
const shouldRetry = (error: AxiosError, retryCount: number): boolean => {
  if (retryCount >= RETRY_CONFIG.maxRetries) {
    return false
  }

  // 网络错误
  if (!error.response) {
    return true
  }

  // 特定状态码
  const status = error.response.status
  return RETRY_CONFIG.retryableStatusCodes.includes(status)
}

/**
 * 三层架构API类
 */
class ThreeLayerAPI {
  private axiosInstance: AxiosInstance

  constructor() {
    this.axiosInstance = axios.create({
      baseURL: API_BASE_URL,
      timeout: DEFAULT_TIMEOUT,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // 请求拦截器
    this.axiosInstance.interceptors.request.use(
      (config) => {
        // 可以在这里添加认证token
        // if (token) {
        //   config.headers.Authorization = `Bearer ${token}`
        // }
        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // 响应拦截器
    this.axiosInstance.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        // 统一错误处理
        if (error.response) {
          // 服务器返回错误响应
          const message = (error.response.data as any)?.message || error.message
          throw new ThreeLayerApiError(
            message,
            error.response.status,
            error.response.data
          )
        } else if (error.request) {
          // 请求发出但没有收到响应
          throw new ThreeLayerApiError('网络错误：无法连接到服务器')
        } else {
          // 请求配置错误
          throw new ThreeLayerApiError(error.message)
        }
      }
    )
  }

  /**
   * 带重试的请求方法
   */
  private async requestWithRetry<T>(
    requestFn: () => Promise<T>,
    retryCount: number = 0
  ): Promise<T> {
    try {
      return await requestFn()
    } catch (error) {
      if (error instanceof AxiosError && shouldRetry(error, retryCount)) {
        // 指数退避
        const delayTime = RETRY_CONFIG.retryDelay * Math.pow(2, retryCount)
        await delay(delayTime)
        return this.requestWithRetry(requestFn, retryCount + 1)
      }
      throw error
    }
  }

  /**
   * 获取选股器列表
   * GET /api/three-layer/selectors
   */
  async getSelectors(): Promise<SelectorInfo[]> {
    return this.requestWithRetry(async () => {
      const response = await this.axiosInstance.get<ApiResponse<SelectorInfo[]>>(
        `${THREE_LAYER_API_PREFIX}/selectors`
      )
      return response.data.data || []
    })
  }

  /**
   * 获取入场策略列表
   * GET /api/three-layer/entries
   */
  async getEntries(): Promise<EntryInfo[]> {
    return this.requestWithRetry(async () => {
      const response = await this.axiosInstance.get<ApiResponse<EntryInfo[]>>(
        `${THREE_LAYER_API_PREFIX}/entries`
      )
      return response.data.data || []
    })
  }

  /**
   * 获取退出策略列表
   * GET /api/three-layer/exits
   */
  async getExits(): Promise<ExitInfo[]> {
    return this.requestWithRetry(async () => {
      const response = await this.axiosInstance.get<ApiResponse<ExitInfo[]>>(
        `${THREE_LAYER_API_PREFIX}/exits`
      )
      return response.data.data || []
    })
  }

  /**
   * 获取所有组件列表（并行获取）
   */
  async getAllComponents(): Promise<{
    selectors: SelectorInfo[]
    entries: EntryInfo[]
    exits: ExitInfo[]
  }> {
    const [selectors, entries, exits] = await Promise.all([
      this.getSelectors(),
      this.getEntries(),
      this.getExits(),
    ])

    return { selectors, entries, exits }
  }

  /**
   * 验证策略配置
   * POST /api/three-layer/validate
   */
  async validateStrategy(config: StrategyConfig): Promise<ValidationResult> {
    return this.requestWithRetry(async () => {
      const response = await this.axiosInstance.post<ApiResponse<ValidationResult>>(
        `${THREE_LAYER_API_PREFIX}/validate`,
        config
      )
      return (
        response.data.data || {
          valid: false,
          errors: ['验证失败：未收到响应'],
          warnings: [],
        }
      )
    })
  }

  /**
   * 运行回测
   * POST /api/three-layer/backtest
   */
  async runBacktest(config: StrategyConfig): Promise<BacktestResult> {
    // 回测不重试，因为可能耗时很长
    try {
      const response = await this.axiosInstance.post<ApiResponse<BacktestResult>>(
        `${THREE_LAYER_API_PREFIX}/backtest`,
        config,
        {
          timeout: BACKTEST_TIMEOUT, // 使用更长的超时时间
        }
      )

      // 后端可能直接返回结果，或者包装在data字段中
      const result = response.data.data || response.data

      return {
        status: result.status || 'success',
        message: result.message,
        data: result.data,
      } as BacktestResult
    } catch (error) {
      if (error instanceof ThreeLayerApiError) {
        return {
          status: 'error',
          message: error.message,
          error: error.message,
        }
      }
      throw error
    }
  }

  /**
   * 获取选股器详情
   */
  async getSelectorById(id: string): Promise<SelectorInfo | null> {
    const selectors = await this.getSelectors()
    return selectors.find((s) => s.id === id) || null
  }

  /**
   * 获取入场策略详情
   */
  async getEntryById(id: string): Promise<EntryInfo | null> {
    const entries = await this.getEntries()
    return entries.find((e) => e.id === id) || null
  }

  /**
   * 获取退出策略详情
   */
  async getExitById(id: string): Promise<ExitInfo | null> {
    const exits = await this.getExits()
    return exits.find((x) => x.id === id) || null
  }

  /**
   * 验证单个参数值
   */
  validateParameter(
    param: { name: string; type: string; min_value?: number; max_value?: number },
    value: any
  ): { valid: boolean; error?: string } {
    // 类型检查
    if (param.type === 'integer' && !Number.isInteger(value)) {
      return { valid: false, error: `${param.name} 必须是整数` }
    }

    if (param.type === 'float' && typeof value !== 'number') {
      return { valid: false, error: `${param.name} 必须是数字` }
    }

    if (param.type === 'boolean' && typeof value !== 'boolean') {
      return { valid: false, error: `${param.name} 必须是布尔值` }
    }

    // 范围检查
    if (typeof value === 'number') {
      if (param.min_value !== undefined && value < param.min_value) {
        return {
          valid: false,
          error: `${param.name} 不能小于 ${param.min_value}`,
        }
      }
      if (param.max_value !== undefined && value > param.max_value) {
        return {
          valid: false,
          error: `${param.name} 不能大于 ${param.max_value}`,
        }
      }
    }

    return { valid: true }
  }

  /**
   * 客户端验证策略配置
   */
  async clientValidateStrategy(
    config: StrategyConfig
  ): Promise<{ valid: boolean; errors: string[] }> {
    const errors: string[] = []

    // 检查必填字段
    if (!config.selector_id) errors.push('请选择选股器')
    if (!config.entry_id) errors.push('请选择入场策略')
    if (!config.exit_id) errors.push('请选择退出策略')
    if (!config.stock_codes || config.stock_codes.length === 0) {
      errors.push('请至少选择一只股票')
    }
    if (!config.start_date) errors.push('请选择开始日期')
    if (!config.end_date) errors.push('请选择结束日期')

    // 日期有效性检查
    if (config.start_date && config.end_date) {
      const startDate = new Date(config.start_date)
      const endDate = new Date(config.end_date)
      if (startDate >= endDate) {
        errors.push('开始日期必须早于结束日期')
      }
    }

    // 参数验证
    try {
      const [selector, entry, exit] = await Promise.all([
        this.getSelectorById(config.selector_id),
        this.getEntryById(config.entry_id),
        this.getExitById(config.exit_id),
      ])

      // 验证选股器参数
      if (selector) {
        for (const param of selector.parameters) {
          const value = config.selector_params[param.name]
          if (value !== undefined) {
            const result = this.validateParameter(param, value)
            if (!result.valid) {
              errors.push(result.error!)
            }
          }
        }
      }

      // 验证入场策略参数
      if (entry) {
        for (const param of entry.parameters) {
          const value = config.entry_params[param.name]
          if (value !== undefined) {
            const result = this.validateParameter(param, value)
            if (!result.valid) {
              errors.push(result.error!)
            }
          }
        }
      }

      // 验证退出策略参数
      if (exit) {
        for (const param of exit.parameters) {
          const value = config.exit_params[param.name]
          if (value !== undefined) {
            const result = this.validateParameter(param, value)
            if (!result.valid) {
              errors.push(result.error!)
            }
          }
        }
      }
    } catch (error) {
      errors.push('获取组件信息失败')
    }

    return { valid: errors.length === 0, errors }
  }
}

// 导出单例
export const threeLayerApi = new ThreeLayerAPI()
export default threeLayerApi
