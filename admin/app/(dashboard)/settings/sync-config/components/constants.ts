export const STRATEGY_LABELS: Record<string, string> = {
  by_ts_code: '逐只股票',
  by_date: '按日切片',
  by_week: '按周切片',
  by_month: '按月切片',
  by_quarter: '按季度切片',
  snapshot: '快照',
  none: '无全量',
}

export const STRATEGY_OPTIONS = [
  { value: 'by_ts_code', label: '逐只股票' },
  { value: 'by_date', label: '按日切片' },
  { value: 'by_week', label: '按周切片' },
  { value: 'by_month', label: '按月切片' },
  { value: 'by_quarter', label: '按季度切片' },
  { value: 'snapshot', label: '快照' },
  { value: 'none', label: '无全量' },
]

// 增量同步策略选项（比全量策略更精简）
export const INCREMENTAL_STRATEGY_OPTIONS = [
  { value: 'by_ts_code', label: '逐只股票' },
  { value: 'by_date_range', label: '按时间段' },
  { value: 'by_date', label: '逐日切片' },
  { value: 'snapshot', label: '快照' },
  { value: 'none', label: '无' },
]

export const CATEGORY_ORDER = [
  '基础数据', '行情数据', '财务数据', '参考数据',
  '特色数据', '两融及转融通', '资金流向', '打板专题',
]
