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
  input?: unknown
}

interface ErrorLike {
  message?: string
  msg?: string
  loc?: (string | number)[] | string
}

export function formatErrorMessage(error: unknown): string {
  if (typeof error === 'string') {
    return error
  }

  if (Array.isArray(error)) {
    return error
      .map((err: unknown) => {
        if (typeof err === 'string') return err

        const e = err as PydanticValidationError
        if (e.msg && e.loc) {
          const location = Array.isArray(e.loc) ? e.loc.join('.') : e.loc
          return `${location}: ${e.msg}`
        }

        return e.msg || JSON.stringify(err)
      })
      .join('; ')
  }

  if (typeof error === 'object' && error !== null) {
    const e = error as ErrorLike
    if (e.message) return e.message
    if (e.msg) {
      if (e.loc) {
        const location = Array.isArray(e.loc) ? e.loc.join('.') : e.loc
        return `${location}: ${e.msg}`
      }
      return e.msg
    }
    try {
      return JSON.stringify(error)
    } catch {
      return String(error)
    }
  }

  return String(error)
}

export function extractApiError(error: unknown, fallbackMessage: string = '操作失败'): string {
  const e = error as { response?: { data?: { detail?: unknown; message?: string } }; message?: string } | null
  const errorDetail =
    e?.response?.data?.detail ||
    e?.response?.data?.message ||
    e?.response?.data ||
    e?.message ||
    fallbackMessage

  return formatErrorMessage(errorDetail)
}
