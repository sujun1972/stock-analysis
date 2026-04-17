/**
 * 日期工具函数
 *
 * 性能优化：统一管理 date-fns 导入，减少打包体积
 * - 使用 ES Module 路径直接导入（如 'date-fns/format'）
 * - 避免导入整个 date-fns 包（减少约 500KB）
 * - 提供常用日期格式化工具函数，保持 API 一致性
 *
 * 使用方法：
 * ```typescript
 * import { format, zhCN, formatDate } from '@/lib/date-utils'
 * ```
 */

// 按需导入核心函数，支持 tree-shaking
import { format as dateFnsFormat } from 'date-fns/format'
import { zhCN as zhCNLocale } from 'date-fns/locale/zh-CN'

export { format } from 'date-fns/format'
export { subDays } from 'date-fns/subDays'
export { subMonths } from 'date-fns/subMonths'
export { subYears } from 'date-fns/subYears'
export { addDays } from 'date-fns/addDays'
export { addMonths } from 'date-fns/addMonths'
export { parseISO } from 'date-fns/parseISO'
export { isValid } from 'date-fns/isValid'
export { startOfDay } from 'date-fns/startOfDay'
export { endOfDay } from 'date-fns/endOfDay'

// 中文语言包
export { zhCN } from 'date-fns/locale/zh-CN'

/**
 * 时区安全的日期字符串构建（YYYY-MM-DD）。
 * 使用本地时间，避免 toISOString() 在 UTC+8 偏移 -1 天的问题。
 */
export function toDateStr(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

/**
 * 格式化日期为 YYYY-MM-DD
 */
export function formatDate(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return dateFnsFormat(d, 'yyyy-MM-dd')
}

/**
 * 格式化日期时间
 */
export function formatDateTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return dateFnsFormat(d, 'yyyy-MM-dd HH:mm:ss')
}

/**
 * 格式化为中文日期
 */
export function formatDateCN(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return dateFnsFormat(d, 'yyyy年MM月dd日', { locale: zhCNLocale })
}
