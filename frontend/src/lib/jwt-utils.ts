/**
 * JWT 工具函数
 * 用于解析和检查 JWT token 的有效性
 */

interface JWTPayload {
  exp?: number // 过期时间（Unix 时间戳，秒）
  iat?: number // 签发时间（Unix 时间戳，秒）
  sub?: string // 主题（通常是用户 ID）
  [key: string]: any
}

/**
 * 解码 JWT token（不验证签名）
 * @param token JWT token 字符串
 * @returns 解码后的 payload，解析失败返回 null
 */
export function decodeJWT(token: string): JWTPayload | null {
  try {
    // JWT 格式: header.payload.signature
    const parts = token.split('.')
    if (parts.length !== 3) {
      console.error('Invalid JWT format: expected 3 parts')
      return null
    }

    // Base64URL 解码 payload（第二部分）
    const payload = parts[1]
    const base64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    )

    return JSON.parse(jsonPayload)
  } catch (error) {
    console.error('Failed to decode JWT:', error)
    return null
  }
}

/**
 * 检查 token 是否已过期
 * @param token JWT token 字符串
 * @returns true 表示已过期，false 表示未过期
 */
export function isTokenExpired(token: string): boolean {
  const payload = decodeJWT(token)
  if (!payload || !payload.exp) {
    return true
  }

  // exp 是秒级时间戳，需要转换为毫秒
  const expirationTime = payload.exp * 1000
  const now = Date.now()

  return now >= expirationTime
}

/**
 * 检查 token 是否即将过期（在指定时间内）
 * @param token JWT token 字符串
 * @param thresholdMinutes 提前多少分钟算作"即将过期"，默认 5 分钟
 * @returns true 表示即将过期，false 表示还有足够时间
 */
export function isTokenExpiringSoon(token: string, thresholdMinutes: number = 5): boolean {
  const payload = decodeJWT(token)
  if (!payload || !payload.exp) {
    return true
  }

  const expirationTime = payload.exp * 1000
  const now = Date.now()
  const threshold = thresholdMinutes * 60 * 1000

  // 如果剩余时间小于阈值，返回 true
  return (expirationTime - now) <= threshold
}

/**
 * 获取 token 的剩余有效时间（毫秒）
 * @param token JWT token 字符串
 * @returns 剩余时间（毫秒），如果已过期或无效返回 0
 */
export function getTokenRemainingTime(token: string): number {
  const payload = decodeJWT(token)
  if (!payload || !payload.exp) {
    return 0
  }

  const expirationTime = payload.exp * 1000
  const now = Date.now()
  const remaining = expirationTime - now

  return remaining > 0 ? remaining : 0
}

/**
 * 获取 token 的过期时间（Date 对象）
 * @param token JWT token 字符串
 * @returns 过期时间，如果无效返回 null
 */
export function getTokenExpirationDate(token: string): Date | null {
  const payload = decodeJWT(token)
  if (!payload || !payload.exp) {
    return null
  }

  return new Date(payload.exp * 1000)
}
