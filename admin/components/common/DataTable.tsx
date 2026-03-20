/**
 * @file components/common/DataTable.tsx
 * @description DataTable 兼容性重定向文件
 * @deprecated 此文件仅用于向后兼容，请使用 DataTable/index.tsx
 * @created 2026-03-20
 */

// 重新导出所有内容，保持向后兼容
export { DataTable, default } from './DataTable/index'
export type {
  Column,
  PaginationConfig,
  SortConfig,
  DataTableProps,
} from './DataTable/types'
