'use client'

import { Fragment, useEffect, useMemo, useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuthStore } from '@/stores/auth-store'

/**
 * 近 N 日龙虎榜明细
 *
 * - 基础列表：GET /api/top-list?ts_code=...&start_date=...&end_date=...&page_size=200
 *   字段（金额已换算为万元）：trade_date, name, reason, l_buy, l_sell, net_amount,
 *                              close, pct_change, turnover_rate, amount, float_values
 * - 席位明细（按需展开行时拉取）：GET /api/top-inst?ts_code=...&trade_date=...&page_size=50
 *   字段（金额单位：万元，原始 buy/sell 已是元，自行换算）：exalter, side(0买/1卖), buy, sell, net_buy
 *
 * UI：
 *  顶部聚合（上榜次数 / 平均净额 / 机构席位次数）
 *  默认收起；展开后表格列出每条上榜，点击行展开席位明细
 */

interface BillboardItem {
  trade_date: string  // YYYY-MM-DD
  ts_code: string
  name: string
  reason: string | null
  close: number | null
  pct_change: number | null
  turnover_rate: number | null
  amount: number | null
  l_buy: number | null      // 万元
  l_sell: number | null     // 万元
  net_amount: number | null // 万元
}

interface InstItem {
  trade_date: string
  ts_code: string
  exalter: string
  side: string  // '0' 买 / '1' 卖
  buy: number | null    // 元
  sell: number | null   // 元
  net_buy: number | null // 元
}

const LOOKBACK_DAYS = 60

/** 万元 → 字符串（≥1 亿换算成"亿"，否则"万"；带 +/- 符号） */
function fmtWan(v: number | null | undefined, withSign = false): string {
  if (v == null || !isFinite(v)) return '-'
  const sign = withSign && v > 0 ? '+' : ''
  const abs = Math.abs(v)
  if (abs >= 1e4) return `${sign}${(v / 1e4).toFixed(2)} 亿`
  return `${sign}${v.toFixed(0)} 万`
}

/** 元 → 字符串（与 fmtWan 同输出，但输入单位是元） */
function fmtYuan(v: number | null | undefined, withSign = false): string {
  if (v == null || !isFinite(v)) return '-'
  return fmtWan(v / 1e4, withSign)
}

/** 席位类别识别：基于席位名称关键字，与 stock_data_collection_service 的 _SEAT_TAGS 同口径 */
function classifySeat(exalter: string): { kind: 'org' | 'hgt' | 'hot' | 'other'; label: string } {
  if (!exalter) return { kind: 'other', label: '其他' }
  if (exalter.includes('机构专用')) return { kind: 'org', label: '机构' }
  if (exalter.includes('沪股通') || exalter.includes('深股通') || exalter.includes('港资')) return { kind: 'hgt', label: '北向' }
  return { kind: 'hot', label: '游资' }
}

const SEAT_BADGE: Record<string, string> = {
  org:   'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300',
  hgt:   'bg-emerald-100 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
  hot:   'bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300',
  other: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-300',
}

/** 计算近 LOOKBACK_DAYS 自然日的起止日期（YYYY-MM-DD） */
function calcDateRange(): { start: string; end: string } {
  const today = new Date()
  const end = today.toISOString().slice(0, 10)
  const startDate = new Date(today)
  startDate.setDate(today.getDate() - LOOKBACK_DAYS)
  const start = startDate.toISOString().slice(0, 10)
  return { start, end }
}

export function BillboardCard({ tsCode }: { tsCode: string }) {
  const [expanded, setExpanded] = useState(false)
  const [items, setItems] = useState<BillboardItem[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const isAuthenticated = useAuthStore(s => s.isAuthenticated)

  // 行级展开：trade_date → 席位列表（已加载即缓存，避免重复请求）
  const [instOpen, setInstOpen] = useState<Record<string, boolean>>({})
  const [instData, setInstData] = useState<Record<string, InstItem[] | 'loading' | 'error'>>({})

  useEffect(() => {
    if (!tsCode || !isAuthenticated) return
    let cancelled = false
    setLoading(true)
    setError(null)
    const { start, end } = calcDateRange()
    apiClient.get<{ code: number; data: { items: BillboardItem[] } }>(
      `/api/top-list?ts_code=${encodeURIComponent(tsCode)}&start_date=${start}&end_date=${end}&page_size=200`
    ).then(res => {
      if (cancelled) return
      const list: BillboardItem[] = res?.data?.items ?? []
      // 后端 DESC 返回，UI 也按时间降序排列（最近上榜在最前）
      setItems(list)
    }).catch((err: any) => {
      if (cancelled) return
      setError(err?.message || '加载失败')
    }).finally(() => {
      if (!cancelled) setLoading(false)
    })
    return () => { cancelled = true }
  }, [tsCode, isAuthenticated])

  const stats = useMemo(() => {
    if (!items || items.length === 0) return null
    const totalNet = items.reduce((a, it) => a + (it.net_amount || 0), 0)
    const avgNet = totalNet / items.length
    return {
      count: items.length,
      avgNet,
      totalNet,
    }
  }, [items])

  function handleToggleInst(date: string) {
    const dateKey = date  // YYYY-MM-DD
    if (instOpen[dateKey]) {
      setInstOpen(s => ({ ...s, [dateKey]: false }))
      return
    }
    setInstOpen(s => ({ ...s, [dateKey]: true }))
    if (instData[dateKey]) return  // 已加载（含错误态）
    setInstData(s => ({ ...s, [dateKey]: 'loading' }))
    apiClient.get<{ code: number; data: { items: InstItem[] } }>(
      `/api/top-inst?ts_code=${encodeURIComponent(tsCode)}&trade_date=${dateKey}&page_size=50`
    ).then(res => {
      const list: InstItem[] = res?.data?.items ?? []
      // 按 net_buy 降序
      list.sort((a, b) => (b.net_buy || 0) - (a.net_buy || 0))
      setInstData(s => ({ ...s, [dateKey]: list }))
    }).catch(() => {
      setInstData(s => ({ ...s, [dateKey]: 'error' }))
    })
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-base">近 {LOOKBACK_DAYS} 日龙虎榜</CardTitle>
          {stats && (
            <div className="flex items-baseline gap-3 text-xs tabular-nums text-gray-500 dark:text-gray-400">
              <span>上榜 <span className="font-semibold text-gray-900 dark:text-white">{stats.count}</span> 次</span>
              <span>累计净额 <span className={`font-semibold ${stats.totalNet > 0 ? 'text-positive' : stats.totalNet < 0 ? 'text-negative' : 'text-gray-900 dark:text-white'}`}>{fmtWan(stats.totalNet, true)}</span></span>
              <button
                type="button"
                onClick={() => setExpanded(e => !e)}
                className="inline-flex items-center gap-0.5 text-info hover:underline focus-ring rounded"
                aria-expanded={expanded}
                aria-label={expanded ? '收起明细' : '展开明细'}
              >
                {expanded ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                <span>{expanded ? '收起' : '展开'}</span>
              </button>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {!isAuthenticated && (
          <div className="py-6 text-center">
            <p className="text-sm text-gray-500 dark:text-gray-400">龙虎榜数据需登录后查看</p>
            <a href="/login" className="mt-2 inline-block text-xs text-info hover:underline">前往登录 →</a>
          </div>
        )}
        {isAuthenticated && loading && <p className="text-sm text-gray-500 dark:text-gray-400">加载中...</p>}
        {isAuthenticated && error && <p className="text-sm text-amber-600 dark:text-amber-400">{error}</p>}
        {isAuthenticated && !loading && !error && items && items.length === 0 && (
          <p className="text-sm text-gray-500 dark:text-gray-400">近 {LOOKBACK_DAYS} 日未上榜</p>
        )}
        {isAuthenticated && !loading && !error && expanded && items && items.length > 0 && (
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full min-w-[640px] text-xs">
              <thead className="text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-800">
                <tr>
                  <th className="text-left font-normal py-1.5 px-2">日期</th>
                  <th className="text-left font-normal py-1.5 px-2">上榜原因</th>
                  <th className="text-right font-normal py-1.5 px-2">买入</th>
                  <th className="text-right font-normal py-1.5 px-2">卖出</th>
                  <th className="text-right font-normal py-1.5 px-2">净额</th>
                  <th className="text-right font-normal py-1.5 px-2">涨跌</th>
                  <th className="w-6"></th>
                </tr>
              </thead>
              <tbody>
                {items.map(it => {
                  const isOpen = instOpen[it.trade_date]
                  const inst = instData[it.trade_date]
                  return (
                    <Fragment key={it.trade_date}>
                      <tr
                        className="border-b border-gray-50 dark:border-gray-900 hover:bg-gray-50 dark:hover:bg-gray-900/50 cursor-pointer"
                        onClick={() => handleToggleInst(it.trade_date)}
                      >
                        <td className="py-1.5 px-2 tabular-nums">{it.trade_date}</td>
                        <td className="py-1.5 px-2 max-w-[260px] truncate" title={it.reason ?? ''}>{it.reason ?? '-'}</td>
                        <td className="py-1.5 px-2 text-right tabular-nums text-positive">{fmtWan(it.l_buy)}</td>
                        <td className="py-1.5 px-2 text-right tabular-nums text-negative">{fmtWan(it.l_sell)}</td>
                        <td className={`py-1.5 px-2 text-right tabular-nums font-semibold ${(it.net_amount ?? 0) > 0 ? 'text-positive' : (it.net_amount ?? 0) < 0 ? 'text-negative' : ''}`}>
                          {fmtWan(it.net_amount, true)}
                        </td>
                        <td className={`py-1.5 px-2 text-right tabular-nums ${(it.pct_change ?? 0) > 0 ? 'text-positive' : (it.pct_change ?? 0) < 0 ? 'text-negative' : ''}`}>
                          {it.pct_change != null ? `${it.pct_change > 0 ? '+' : ''}${it.pct_change.toFixed(2)}%` : '-'}
                        </td>
                        <td className="py-1.5 px-2 text-gray-400">
                          {isOpen ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                        </td>
                      </tr>
                      {isOpen && (
                        <tr className="bg-gray-50 dark:bg-gray-900/30">
                          <td colSpan={7} className="py-2 px-2">
                            {inst === 'loading' && <span className="text-gray-500 dark:text-gray-400">席位加载中...</span>}
                            {inst === 'error' && <span className="text-amber-600 dark:text-amber-400">席位加载失败</span>}
                            {Array.isArray(inst) && inst.length === 0 && <span className="text-gray-500 dark:text-gray-400">无席位明细</span>}
                            {Array.isArray(inst) && inst.length > 0 && (
                              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1">
                                {inst.map((s, idx) => {
                                  const cls = classifySeat(s.exalter)
                                  return (
                                    <div key={`${s.exalter}-${s.side}-${idx}`} className="flex items-baseline justify-between gap-2">
                                      <div className="flex items-baseline gap-1.5 min-w-0">
                                        <span className={`shrink-0 px-1.5 py-0 rounded text-[10px] ${SEAT_BADGE[cls.kind]}`}>{cls.label}</span>
                                        <span className="truncate" title={s.exalter}>{s.exalter}</span>
                                      </div>
                                      <span className={`shrink-0 tabular-nums ${(s.net_buy ?? 0) > 0 ? 'text-positive' : (s.net_buy ?? 0) < 0 ? 'text-negative' : ''}`}>
                                        {fmtYuan(s.net_buy, true)}
                                      </span>
                                    </div>
                                  )
                                })}
                              </div>
                            )}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
        <p className="mt-3 text-[10px] text-gray-400 dark:text-gray-600">
          口径：买入/卖出 = 龙虎榜营业部上榜买入/卖出额；净额 = 买入-卖出；席位类别按名称关键字识别（机构=蓝/北向=绿/游资=橙）；点击行展开当日席位
        </p>
      </CardContent>
    </Card>
  )
}
