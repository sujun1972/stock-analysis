/**
 * 统一的 API 响应类型定义
 *
 * 与后端完全一致: backend/app/models/api_response.py
 * 版本: 2.0
 * 更新日期: 2026-03-14
 *
 * 重要: 所有 API 调用必须使用此类型，禁止使用 any 或自定义响应类型
 */

/**
 * API 弃用警告信息
 *
 * 当调用已弃用的 API 端点时，响应中会包含此信息
 */
export interface DeprecationWarning {
  deprecated: boolean
  deprecated_since: string
  removal_date?: string
  alternative?: string
  reason?: string
}

/**
 * 统一的 API 响应类型（与后端完全一致）
 *
 * 后端对应: backend/app/models/api_response.py::ApiResponse
 *
 * @example
 * // 成功响应
 * {
 *   code: 200,
 *   message: "success",
 *   data: { user_id: 123 },
 *   success: true,
 *   timestamp: "2026-03-14T12:00:00"
 * }
 *
 * @example
 * // 错误响应
 * {
 *   code: 404,
 *   message: "Resource not found",
 *   data: null,
 *   success: false
 * }
 */
export interface ApiResponse<T = any> {
  /** HTTP 状态码 (200, 400, 500, etc.) */
  code: number

  /** 响应消息 */
  message: string

  /** 响应数据（泛型）*/
  data?: T

  /** 便捷成功标识（后端自动计算：code < 400）*/
  success?: boolean

  /** 响应时间戳 (ISO 8601 格式) */
  timestamp?: string

  /** 请求追踪 ID（用于日志追踪和调试）*/
  request_id?: string

  /** API 版本号 */
  api_version?: string

  /** API 弃用警告（当调用已弃用的端点时出现）*/
  deprecation?: DeprecationWarning
}

/**
 * 分页数据结构
 */
export interface PaginatedData<T> {
  /** 当前页的数据列表 */
  items: T[]

  /** 总记录数 */
  total: number

  /** 当前页码 (从 1 开始) */
  page: number

  /** 每页大小 */
  page_size: number

  /** 总页数 */
  total_pages: number
}

/**
 * 分页响应类型（完整的 API 响应包含分页数据）
 */
export type PaginatedResponse<T> = ApiResponse<PaginatedData<T>>

// ==================== 类型守卫函数 ====================

/**
 * 类型守卫：检查响应是否成功
 *
 * @param response API 响应对象
 * @returns 如果成功且有数据，返回 true
 *
 * @example
 * const response = await axiosInstance.get('/api/users')
 * if (isSuccessResponse(response)) {
 *   // TypeScript 知道 response.data 一定存在
 *   console.log(response.data)
 * }
 */
export function isSuccessResponse<T>(
  response: ApiResponse<T>
): response is ApiResponse<T> & { data: T } {
  return (
    response.code >= 200 &&
    response.code < 300 &&
    response.data !== undefined &&
    response.data !== null
  )
}

/**
 * 类型守卫：检查是否为错误响应
 *
 * @param response API 响应对象
 * @returns 如果是错误响应（code >= 400），返回 true
 */
export function isErrorResponse(response: ApiResponse<any>): boolean {
  return response.code >= 400
}

/**
 * 类型守卫：检查是否为分页响应
 *
 * @param response API 响应对象
 * @returns 如果是有效的分页响应，返回 true
 */
export function isPaginatedResponse<T>(
  response: ApiResponse<any>
): response is PaginatedResponse<T> {
  return (
    isSuccessResponse(response) &&
    typeof response.data === 'object' &&
    'items' in response.data &&
    'total' in response.data &&
    Array.isArray(response.data.items)
  )
}

// ==================== 向后兼容（已弃用）====================

/**
 * 旧版 API 响应格式（已弃用）
 *
 * @deprecated 使用 ApiResponse 代替
 *
 * 此类型仅用于向后兼容，新代码不应使用
 */
export interface LegacyApiResponse<T> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

/**
 * 转换函数：将标准响应转换为旧格式
 *
 * @deprecated 仅用于渐进式迁移，应尽快移除
 *
 * @param response 标准 API 响应
 * @returns 旧格式的响应
 */
export function toLegacyFormat<T>(response: ApiResponse<T>): LegacyApiResponse<T> {
  return {
    success: response.code < 400,
    data: response.data,
    message: response.message,
    error: response.code >= 400 ? response.message : undefined,
  }
}

/**
 * 转换函数：将旧格式转换为标准响应
 *
 * @deprecated 仅用于渐进式迁移，应尽快移除
 *
 * @param legacy 旧格式的响应
 * @returns 标准 API 响应
 */
export function fromLegacyFormat<T>(legacy: LegacyApiResponse<T>): ApiResponse<T> {
  return {
    code: legacy.success ? 200 : 400,
    message: legacy.message || (legacy.success ? 'success' : legacy.error || 'error'),
    data: legacy.data,
    success: legacy.success,
  }
}
