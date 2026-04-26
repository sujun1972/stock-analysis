import type { StockAnalysisRecord } from '@/types'

/**
 * AI 分析的逻辑标的是"交易日"，同一交易日下同 (ts_code, analysis_type) 可能存在多版本
 * （重新生成、提示词调整、模型切换等）。后端 `version` 列在 (ts_code, analysis_type) 范围内
 * 全局递增，UI 上若直接展示会让用户看到"4-20=v3 / 4-25=v4"这种跨日错觉。
 *
 * 这里提供两个纯函数把后端 DESC 排序的历史扁平数组转成"交易日 → 版本组"结构，
 * 同日内的 displayVersion 从 1 起按时间正序重排，符合用户心智。
 */

/** 把 'YYYYMMDD' / 'YYYY-MM-DD' / created_at ISO 统一规整成 'YYYY-MM-DD'，无效返回 null。 */
export function normalizeTradeDate(record: StockAnalysisRecord): string | null {
  const td = record.trade_date
  if (td) {
    if (/^\d{8}$/.test(td)) return `${td.slice(0, 4)}-${td.slice(4, 6)}-${td.slice(6, 8)}`
    if (/^\d{4}-\d{2}-\d{2}/.test(td)) return td.slice(0, 10)
  }
  // 旧数据兜底：用 created_at 的日期部分（注意 ISO 时区可能影响日期，但本系统时间戳是本地存储，截前 10 位足够近似）
  if (record.created_at && record.created_at.length >= 10) return record.created_at.slice(0, 10)
  return null
}

export interface TradeDateGroup {
  /** 'YYYY-MM-DD' */
  tradeDate: string
  /** 该日所有版本，按 created_at ASC 排序后，displayVersion 从 1 起编号 */
  versions: Array<StockAnalysisRecord & { displayVersion: number; displayTotal: number }>
}

/**
 * 把后端按 created_at DESC 排序的扁平历史按交易日分组。
 * 返回数组按交易日 DESC（最新交易日在前），便于日历 default 选最近一天。
 */
export function groupRecordsByTradeDate(records: StockAnalysisRecord[]): TradeDateGroup[] {
  const buckets = new Map<string, StockAnalysisRecord[]>()
  for (const r of records) {
    const td = normalizeTradeDate(r)
    if (!td) continue
    const list = buckets.get(td)
    if (list) list.push(r)
    else buckets.set(td, [r])
  }
  // Map 插入顺序就是 DESC（输入即 DESC），但保险起见显式按 key 排
  const sortedKeys = Array.from(buckets.keys()).sort((a, b) => (a < b ? 1 : a > b ? -1 : 0))
  return sortedKeys.map((tradeDate) => {
    const asc = (buckets.get(tradeDate) ?? []).slice().sort((a, b) => {
      // created_at ISO 字符串可直接字典序比较（同时区下严格单调）
      if (a.created_at < b.created_at) return -1
      if (a.created_at > b.created_at) return 1
      // created_at 完全相同（理论上不会）时按 id 兜底
      return a.id - b.id
    })
    const total = asc.length
    return {
      tradeDate,
      versions: asc.map((r, i) => ({ ...r, displayVersion: i + 1, displayTotal: total })),
    }
  })
}

/** 'YYYY-MM-DD' → Date（local 0:00）；非法返回 undefined。 */
export function parseTradeDateToDate(tradeDate: string | null | undefined): Date | undefined {
  if (!tradeDate || !/^\d{4}-\d{2}-\d{2}$/.test(tradeDate)) return undefined
  // 用 'YYYY-MM-DDT00:00:00' 避免被解析成 UTC 后回退一天
  const d = new Date(`${tradeDate}T00:00:00`)
  return isNaN(d.getTime()) ? undefined : d
}

/** Date → 'YYYY-MM-DD'（local），与 normalizeTradeDate 同步。 */
export function formatDateToTradeDate(date: Date): string {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}
