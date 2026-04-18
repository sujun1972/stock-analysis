// ============== 类型定义 ==============

export interface MoneyflowIndDcData {
  trade_date: string
  content_type: string
  ts_code: string
  name: string
  pct_change: number | null
  close: number | null
  net_amount: number | null
  net_amount_rate: number | null
  buy_elg_amount: number | null
  buy_elg_amount_rate: number | null
  buy_lg_amount: number | null
  buy_lg_amount_rate: number | null
  buy_md_amount: number | null
  buy_md_amount_rate: number | null
  buy_sm_amount: number | null
  buy_sm_amount_rate: number | null
  buy_sm_amount_stock: string
  rank: number | null
}

export interface Statistics {
  avg_net_amount: number
  max_net_amount: number
  min_net_amount: number
  total_net_amount: number
  avg_buy_elg_amount: number
  max_buy_elg_amount: number
  avg_buy_lg_amount: number
  max_buy_lg_amount: number
  latest_date: string
  earliest_date: string
  count: number
  sector_count: number
}

// ============== 工具函数 ==============

export const toYi = (val: number | null | undefined) => {
  if (val === null || val === undefined) return '-'
  return (val >= 0 ? '+' : '') + val.toFixed(2) + '亿'
}

export const pctColor = (val: number | null | undefined) =>
  (val ?? 0) >= 0 ? 'text-red-600' : 'text-green-600'
