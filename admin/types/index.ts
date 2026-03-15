export * from './stock'
export * from './strategy'

// 统一的 API 响应类型（优先级最高，覆盖其他文件中的定义）
export type {
  ApiResponse,
  PaginatedResponse,
  PaginatedData,
  DeprecationWarning,
} from './api'

// 类型守卫函数
export {
  isSuccessResponse,
  isErrorResponse,
  isPaginatedResponse,
} from './api'

// 注意: LegacyApiResponse、toLegacyFormat、fromLegacyFormat 已弃用
// 如需使用，请从 '@/types/api' 直接导入（不推荐）
