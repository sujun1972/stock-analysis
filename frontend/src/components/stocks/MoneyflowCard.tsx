'use client'

import { useEffect, useMemo, useState } from 'react'
import { apiClient } from '@/lib/api-client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuthStore } from '@/stores/auth-store'

/**
 * 资金流向面板（个股 N 日聚合）
 *
 * - 数据源：GET /api/moneyflow（Tushare 个股资金流向）
 * - 字段单位：所有 *_amount 字段为万元（核对自 moneyflow 表 / Tushare 文档）
 * - 主力定义：大单(20-100万) + 超大单(≥100万)；中单(4-20万)；小单(<4万)
 *
 * 视图：
 *  左栏：当日 4 档买/卖堆叠条 + 主力净流入数字
 *  右栏：N 日主力净流入逐日柱图（红=净流入/绿=净流出，与 §1 涨跌色对齐）
 */

interface MoneyflowItem {
  trade_date: string  // YYYYMMDD
  buy_sm_amount: number
  sell_sm_amount: number
  buy_md_amount: number
  sell_md_amount: number
  buy_lg_amount: number
  sell_lg_amount: number
  buy_elg_amount: number
  sell_elg_amount: number
  net_mf_amount: number
}

const PERIODS = [
  { key: 1,  label: '今日' },
  { key: 5,  label: '5日' },
  { key: 10, label: '10日' },
  { key: 20, label: '20日' },
]

/** 万元 → 字符串（≥1 亿换算成"亿"，否则"万"；带 +/- 符号） */
function fmtWan(v: number, withSign = false): string {
  if (v == null || !isFinite(v)) return '-'
  const sign = withSign && v > 0 ? '+' : ''
  const abs = Math.abs(v)
  if (abs >= 1e4) return `${sign}${(v / 1e4).toFixed(2)} 亿`
  return `${sign}${v.toFixed(0)} 万`
}

/** 当前交易日往回算 N 日的请求范围（end=今天，start=今天-N×1.6 天给非交易日缓冲） */
function calcDateRange(days: number): { start: string; end: string } {
  const today = new Date()
  const end = today.toISOString().slice(0, 10)
  const startDate = new Date(today)
  // 1.6 倍是经验值：覆盖周末 + 节假日；后端会按真实交易日返回
  startDate.setDate(today.getDate() - Math.ceil(days * 1.6) - 5)
  const start = startDate.toISOString().slice(0, 10)
  return { start, end }
}

export function MoneyflowCard({ tsCode }: { tsCode: string }) {
  const [period, setPeriod] = useState<number>(5)
  const [items, setItems] = useState<MoneyflowItem[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // 未登录用户不发请求——避免 401 触发全局 axios 拦截器把整页面踢到 /login
  // /api/moneyflow 当前需 Token；frontend 用户侧的 K 线/行情面板等公开端点不受影响
  const isAuthenticated = useAuthStore(s => s.isAuthenticated)

  useEffect(() => {
    if (!tsCode || !isAuthenticated) return
    let cancelled = false
    setLoading(true)
    setError(null)
    const { start, end } = calcDateRange(period)
    apiClient.get<{ code: number; data: { items: MoneyflowItem[] } }>(
      `/api/moneyflow?ts_code=${encodeURIComponent(tsCode)}&start_date=${start}&end_date=${end}&limit=${period + 5}`
    ).then(res => {
      if (cancelled) return
      const list: MoneyflowItem[] = (res?.data?.items ?? []).slice(0, period)
      // 后端按 trade_date DESC 返回，N 日折线/柱图需要按时间正序
      setItems(list.slice().reverse())
    }).catch((err: any) => {
      if (cancelled) return
      setError(err?.message || '加载失败')
    }).finally(() => {
      if (!cancelled) setLoading(false)
    })
    return () => { cancelled = true }
  }, [tsCode, period, isAuthenticated])

  // 聚合：4 档买/卖、主力净流入合计
  const agg = useMemo(() => {
    if (!items || items.length === 0) return null
    const sum = items.reduce(
      (a, it) => ({
        buy_sm: a.buy_sm + (it.buy_sm_amount || 0),
        sell_sm: a.sell_sm + (it.sell_sm_amount || 0),
        buy_md: a.buy_md + (it.buy_md_amount || 0),
        sell_md: a.sell_md + (it.sell_md_amount || 0),
        buy_lg: a.buy_lg + (it.buy_lg_amount || 0),
        sell_lg: a.sell_lg + (it.sell_lg_amount || 0),
        buy_elg: a.buy_elg + (it.buy_elg_amount || 0),
        sell_elg: a.sell_elg + (it.sell_elg_amount || 0),
        net_mf: a.net_mf + (it.net_mf_amount || 0),
      }),
      { buy_sm: 0, sell_sm: 0, buy_md: 0, sell_md: 0, buy_lg: 0, sell_lg: 0, buy_elg: 0, sell_elg: 0, net_mf: 0 }
    )
    const main_buy = sum.buy_lg + sum.buy_elg
    const main_sell = sum.sell_lg + sum.sell_elg
    return { ...sum, main_buy, main_sell }
  }, [items])

  // 4 档分布堆叠条：每档显示买入/卖出（占同档总额的比例）
  const bands = useMemo(() => {
    if (!agg) return []
    return [
      { label: '超大单', buy: agg.buy_elg, sell: agg.sell_elg, hint: '≥100 万元' },
      { label: '大单',   buy: agg.buy_lg,  sell: agg.sell_lg,  hint: '20–100 万元' },
      { label: '中单',   buy: agg.buy_md,  sell: agg.sell_md,  hint: '4–20 万元' },
      { label: '小单',   buy: agg.buy_sm,  sell: agg.sell_sm,  hint: '<4 万元' },
    ]
  }, [agg])

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-base">资金流向</CardTitle>
          <div className="flex items-center gap-1">
            {PERIODS.map(p => (
              <button
                key={p.key}
                type="button"
                onClick={() => setPeriod(p.key)}
                className={`text-xs px-2 py-0.5 rounded transition-colors ${
                  period === p.key
                    ? 'bg-info text-white'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {!isAuthenticated && (
          <div className="py-6 text-center">
            <p className="text-sm text-gray-500 dark:text-gray-400">
              资金流向数据需登录后查看
            </p>
            <a href="/login" className="mt-2 inline-block text-xs text-info hover:underline">
              前往登录 →
            </a>
          </div>
        )}
        {isAuthenticated && loading && <p className="text-sm text-gray-500 dark:text-gray-400">加载中...</p>}
        {isAuthenticated && error && <p className="text-sm text-amber-600 dark:text-amber-400">{error}</p>}
        {isAuthenticated && !loading && !error && agg && items && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-x-8 gap-y-4">
            {/* 左栏：4 档买卖堆叠条 + 主力净流入摘要 */}
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">4 档买/卖（{period} 日累计）</p>
              <div className="space-y-2">
                {bands.map(b => {
                  const total = b.buy + b.sell || 1
                  const buyPct = (b.buy / total) * 100
                  const sellPct = (b.sell / total) * 100
                  return (
                    <div key={b.label}>
                      <div className="flex items-baseline justify-between text-xs mb-0.5">
                        <span className="text-gray-600 dark:text-gray-400" title={b.hint}>{b.label}</span>
                        <span className="tabular-nums text-gray-500 dark:text-gray-400">
                          买 <span className="text-positive font-semibold">{fmtWan(b.buy)}</span>
                          {' / '}
                          卖 <span className="text-negative font-semibold">{fmtWan(b.sell)}</span>
                        </span>
                      </div>
                      <div className="flex h-2 rounded-sm overflow-hidden bg-gray-100 dark:bg-gray-800">
                        <div className="bg-positive" style={{ width: `${buyPct}%` }} title={`买入占比 ${buyPct.toFixed(1)}%`} />
                        <div className="bg-negative" style={{ width: `${sellPct}%` }} title={`卖出占比 ${sellPct.toFixed(1)}%`} />
                      </div>
                    </div>
                  )
                })}
              </div>
              <div className="mt-3 pt-3 border-t border-gray-100 dark:border-gray-800 flex items-baseline justify-between">
                <span className="text-xs text-gray-500 dark:text-gray-400">主力净流入</span>
                <span className={`text-sm font-semibold tabular-nums ${
                  agg.net_mf > 0 ? 'text-positive' : agg.net_mf < 0 ? 'text-negative' : 'text-gray-500'
                }`}>
                  {fmtWan(agg.net_mf, true)}
                </span>
              </div>
            </div>

            {/* 右栏：N 日主力净流入柱图（仅在 ≥5 日 时显示，单日只看左栏即可） */}
            <div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{period} 日主力净流入</p>
              {items.length <= 1 ? (
                <p className="text-xs text-gray-400 dark:text-gray-600">单日数据见左栏</p>
              ) : (
                <NetFlowBarChart items={items} />
              )}
            </div>
          </div>
        )}
        {isAuthenticated && !loading && !error && (!items || items.length === 0) && (
          <p className="text-sm text-gray-500 dark:text-gray-400">暂无资金流向数据</p>
        )}
        <p className="mt-3 text-[10px] text-gray-400 dark:text-gray-600">
          口径：主力 = 超大单(≥100 万) + 大单(20–100 万)；单位：万元；数据来源：Tushare moneyflow
        </p>
      </CardContent>
    </Card>
  )
}

/** 简易 SVG 柱图：每根柱表示一天的主力净流入（红=正/绿=负），固定高 80px */
function NetFlowBarChart({ items }: { items: MoneyflowItem[] }) {
  const W = 360
  const H = 80
  const pad = 4
  const n = items.length
  const max = Math.max(1, ...items.map(it => Math.abs(it.net_mf_amount || 0)))
  const barW = (W - pad * 2) / n - 2

  return (
    <div className="w-full max-w-full overflow-hidden">
      <svg width="100%" height={H + 16} viewBox={`0 0 ${W} ${H + 16}`} preserveAspectRatio="none">
        {/* 0 轴 */}
        <line x1={0} x2={W} y1={H / 2} y2={H / 2} stroke="currentColor" strokeOpacity={0.2} className="text-gray-400 dark:text-gray-600" />
        {items.map((it, i) => {
          const v = it.net_mf_amount || 0
          const h = (Math.abs(v) / max) * (H / 2 - 2)
          const x = pad + i * (barW + 2)
          const y = v >= 0 ? H / 2 - h : H / 2
          const fill = v > 0 ? 'hsl(var(--positive))' : v < 0 ? 'hsl(var(--negative))' : 'hsl(var(--muted-foreground))'
          const date = it.trade_date
          const mmdd = `${date.slice(4, 6)}-${date.slice(6, 8)}`
          return (
            <g key={i}>
              <title>{`${mmdd}：${v > 0 ? '+' : ''}${(v / 1e4).toFixed(2)} 亿`}</title>
              <rect x={x} y={y} width={Math.max(2, barW)} height={Math.max(1, h)} fill={fill} opacity={0.85} />
            </g>
          )
        })}
        {/* 首尾日期标签 */}
        {n > 0 && (
          <>
            <text x={pad} y={H + 12} textAnchor="start" className="fill-gray-500 dark:fill-gray-400" style={{ fontSize: 9 }}>
              {`${items[0].trade_date.slice(4, 6)}-${items[0].trade_date.slice(6, 8)}`}
            </text>
            <text x={W - pad} y={H + 12} textAnchor="end" className="fill-gray-500 dark:fill-gray-400" style={{ fontSize: 9 }}>
              {`${items[n - 1].trade_date.slice(4, 6)}-${items[n - 1].trade_date.slice(6, 8)}`}
            </text>
          </>
        )}
      </svg>
    </div>
  )
}
