/**
 * 错误信息格式化工具
 * 用于处理各种错误格式，特别是 Pydantic 验证错误
 */

/**
 * Pydantic 验证错误格式
 */
interface PydanticValidationError {
  type: string
  loc: (string | number)[]
  msg: string
  input?: any
}

/**
 * 格式化错误信息为字符串
 * 处理 Pydantic 验证错误等复杂对象
 *
 * @param error - 任何类型的错误对象
 * @returns 格式化后的错误字符串
 *
 * @example
 * // 字符串错误
 * formatErrorMessage("网络错误") // "网络错误"
 *
 * // Pydantic 验证错误数组
 * formatErrorMessage([
 *   { type: "value_error", loc: ["body", "name"], msg: "field required" }
 * ]) // "body.name: field required"
 *
 * // 标准 Error 对象
 * formatErrorMessage(new Error("Something went wrong")) // "Something went wrong"
 *
 * // 未知对象
 * formatErrorMessage({ code: 500, message: "Internal error" }) // '{"code":500,"message":"Internal error"}'
 */
export function formatErrorMessage(error: any): string {
  // 如果已经是字符串，直接返回
  if (typeof error === 'string') {
    return error
  }

  // 如果是数组（Pydantic 验证错误）
  if (Array.isArray(error)) {
    return error
      .map((err: any) => {
        if (typeof err === 'string') return err

        // Pydantic 错误格式: {type, loc, msg, input}
        if (err.msg && err.loc) {
          const location = Array.isArray(err.loc) ? err.loc.join('.') : err.loc
          return `${location}: ${err.msg}`
        }

        return err.msg || JSON.stringify(err)
      })
      .join('; ')
  }

  // 如果是对象，尝试提取错误信息
  if (typeof error === 'object' && error !== null) {
    // 标准错误对象
    if (error.message) return error.message
    // Pydantic 单个错误
    if (error.msg) {
      if (error.loc) {
        const location = Array.isArray(error.loc) ? error.loc.join('.') : error.loc
        return `${location}: ${error.msg}`
      }
      return error.msg
    }
    // 其他对象，转为 JSON
    try {
      return JSON.stringify(error)
    } catch {
      return String(error)
    }
  }

  // 其他情况
  return String(error)
}

/**
 * 从 API 错误响应中提取错误信息
 *
 * @param error - Axios 错误对象或其他错误
 * @param fallbackMessage - 默认错误信息
 * @returns 格式化后的错误字符串
 *
 * @example
 * extractApiError(axiosError, "操作失败")
 */
export function extractApiError(error: any, fallbackMessage: string = '操作失败'): string {
  // 尝试从不同的错误结构中提取信息
  const errorDetail =
    error?.response?.data?.detail ||  // FastAPI 错误
    error?.response?.data?.message || // 自定义错误格式
    error?.response?.data ||          // 其他格式
    error?.message ||                 // 标准错误对象
    fallbackMessage

  return formatErrorMessage(errorDetail)
}
