'use client'

import { useEffect, useMemo, useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { apiClient } from '@/lib/api-client'
import { Card, CardContent, CardHeader } from '@/components/ui/card'

/**
 * 财报简报卡（4 期趋势）
 *
 * - 数据源（均无需登录）：
 *   GET /api/income?ts_code=...&limit=4         (revenue, n_income_attr_p, basic_eps；单位万元/元)
 *   GET /api/cashflow?ts_code=...&limit=4       (n_cashflow_act 经营性现金流；万元)
 *   GET /api/fina-indicator?ts_code=...&limit=4 (roe, debt_to_assets, netprofit_margin, or_yoy, netprofit_yoy)
 * - 端点都按 end_date desc 返回最新 4 期
 *
 * UI: 默认收起；标题行 1 句摘要；展开后表格列出 4 期 + 同比
 */

interface IncomeItem {
  ann_date: string  // YYYY-MM-DD
  end_date: string  // YYYY-MM-DD
  revenue: number | null            // 万元
  n_income_attr_p: number | null    // 万元（归母净利润）
  basic_eps: number | null          // 元/股
  total_revenue: number | null
}

interface CashflowItem {
  ann_date: string
  end_date: string
  n_cashflow_act: number | null     // 万元（经营活动产生的现金流量净额）
}

interface FinaIndItem {
  ann_date: string
  end_date: string
  roe: number | null                // %
  roe_waa: number | null
  debt_to_assets: number | null     // %
  netprofit_margin: number | null   // %
  or_yoy: number | null             // 营收同比 %
  netprofit_yoy: number | null      // 净利润同比 %
}

/** 万元 → 字符串（≥1 亿换算亿，否则万；带 +/- 符号选项） */
function fmtWan(v: number | null | undefined, withSign = false): string {
  if (v == null || !isFinite(v)) return '-'
  const sign = withSign && v > 0 ? '+' : ''
  const abs = Math.abs(v)
  if (abs >= 1e4) return `${sign}${(v / 1e4).toFixed(2)} 亿`
  return `${sign}${v.toFixed(0)} 万`
}

/** 百分比格式化（输入已是百分数，如 5.91 表示 5.91%） */
function fmtPct(v: number | null | undefined, withSign = false): string {
  if (v == null || !isFinite(v)) return '-'
  const sign = withSign && v > 0 ? '+' : ''
  return `${sign}${v.toFixed(2)}%`
}

/** YYYYMMDD → YYYY-MM-DD（已带连字符的原样返回） */
function normDate(s: string | null | undefined): string {
  if (!s) return ''
  if (s.includes('-')) return s
  if (s.length === 8) return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`
  return s
}

/** 把 dict 中的 end_date / ann_date 字段标准化为 YYYY-MM-DD */
function normalizeDates<T extends { end_date?: any; ann_date?: any }>(item: T): T {
  return { ...item, end_date: normDate(item.end_date), ann_date: normDate(item.ann_date) }
}

/** 距披露日的自然日数 */
function daysSince(dateStr: string): number | null {
  if (!dateStr) return null
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return null
  return Math.floor((Date.now() - d.getTime()) / 86_400_000)
}

/** 报告期简记：2025-12-31 → 2025年报；09-30 → 三季报；06-30 → 半年报；03-31 → 一季报 */
function periodLabel(endDate: string): string {
  if (!endDate) return ''
  const md = endDate.slice(5)
  const y = endDate.slice(0, 4)
  if (md === '12-31') return `${y}年报`
  if (md === '09-30') return `${y}三季报`
  if (md === '06-30') return `${y}中报`
  if (md === '03-31') return `${y}一季报`
  return endDate
}

const TREND_COLOR = (v: number | null | undefined) =>
  v == null ? 'text-gray-400' : v > 0 ? 'text-positive' : v < 0 ? 'text-negative' : 'text-gray-500'

export function FinancialBriefCard({ tsCode }: { tsCode: string }) {
  const [expanded, setExpanded] = useState(false)
  const [income, setIncome] = useState<IncomeItem[] | null>(null)
  const [cashflow, setCashflow] = useState<CashflowItem[] | null>(null)
  const [fina, setFina] = useState<FinaIndItem[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!tsCode) return
    let cancelled = false
    setLoading(true)
    setError(null)
    Promise.all([
      apiClient.get<{ items: IncomeItem[] }>(`/api/income?ts_code=${encodeURIComponent(tsCode)}&limit=4`),
      apiClient.get<{ items: CashflowItem[] }>(`/api/cashflow?ts_code=${encodeURIComponent(tsCode)}&limit=4`),
      apiClient.get<{ items: FinaIndItem[] }>(`/api/fina-indicator?ts_code=${encodeURIComponent(tsCode)}&limit=4`),
    ]).then(([incRes, cfRes, fiRes]) => {
      if (cancelled) return
      // 三个端点 end_date/ann_date 格式不一致：income/cashflow=YYYY-MM-DD，fina-indicator=YYYYMMDD
      // 统一规范化为 YYYY-MM-DD，确保 Map 按 end_date 对齐能命中
      setIncome((incRes?.data?.items ?? []).map(normalizeDates))
      setCashflow((cfRes?.data?.items ?? []).map(normalizeDates))
      setFina((fiRes?.data?.items ?? []).map(normalizeDates))
    }).catch((err: any) => {
      if (cancelled) return
      setError(err?.message || '加载失败')
    }).finally(() => {
      if (!cancelled) setLoading(false)
    })
    return () => { cancelled = true }
  }, [tsCode])

  // 找出 income 与 fina 中最新一期，并按 end_date 对齐
  const latest = useMemo(() => {
    if (!income || income.length === 0) return null
    const inc = income[0]
    const fi = fina?.find(f => f.end_date === inc.end_date) ?? fina?.[0] ?? null
    const cf = cashflow?.find(c => c.end_date === inc.end_date) ?? cashflow?.[0] ?? null
    return { inc, fi, cf, lagDays: daysSince(inc.ann_date) }
  }, [income, fina, cashflow])

  const periods = useMemo(() => {
    // 取 income 的 4 期 end_date，对齐 fina/cashflow（按 end_date 匹配）
    if (!income) return []
    const incomeMap = new Map(income.map(i => [i.end_date, i]))
    const finaMap = new Map((fina ?? []).map(f => [f.end_date, f]))
    const cashflowMap = new Map((cashflow ?? []).map(c => [c.end_date, c]))
    const ends = income.map(i => i.end_date)
    return ends.map(end_date => ({
      end_date,
      inc: incomeMap.get(end_date) || null,
      fi: finaMap.get(end_date) || null,
      cf: cashflowMap.get(end_date) || null,
    }))
  }, [income, fina, cashflow])

  return (
    <Card>
      <CardHeader className="pb-3">
        <button
          type="button"
          onClick={() => setExpanded(e => !e)}
          className="w-full flex items-center justify-between gap-3 text-left focus-ring rounded"
          aria-expanded={expanded}
        >
          <div className="flex items-baseline gap-3 flex-wrap min-w-0">
            <span className="text-base font-semibold text-gray-900 dark:text-white shrink-0">财报简报</span>
            {loading && <span className="text-xs text-gray-500 dark:text-gray-400">加载中...</span>}
            {error && <span className="text-xs text-amber-600 dark:text-amber-400">{error}</span>}
            {!loading && !error && latest && (
              <span className="text-xs text-gray-500 dark:text-gray-400 flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                <span>报告期 <span className="text-gray-900 dark:text-white font-medium">{periodLabel(latest.inc.end_date)}</span></span>
                <span className="text-gray-300 dark:text-gray-700">·</span>
                <span>ROE <span className={`font-semibold tabular-nums ${TREND_COLOR(latest.fi?.roe)}`}>{fmtPct(latest.fi?.roe)}</span></span>
                <span className="text-gray-300 dark:text-gray-700">·</span>
                <span>净利同比 <span className={`font-semibold tabular-nums ${TREND_COLOR(latest.fi?.netprofit_yoy)}`}>{fmtPct(latest.fi?.netprofit_yoy, true)}</span></span>
                {latest.lagDays != null && (
                  <>
                    <span className="text-gray-300 dark:text-gray-700">·</span>
                    <span>距披露 <span className="tabular-nums">{latest.lagDays}</span> 天</span>
                  </>
                )}
              </span>
            )}
          </div>
          {expanded ? <ChevronDown className="h-4 w-4 text-gray-400 shrink-0" /> : <ChevronRight className="h-4 w-4 text-gray-400 shrink-0" />}
        </button>
      </CardHeader>
      {expanded && !loading && !error && periods.length > 0 && (
        <CardContent>
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full min-w-[720px] text-xs">
              <thead className="text-gray-500 dark:text-gray-400 border-b border-gray-100 dark:border-gray-800">
                <tr>
                  <th className="text-left font-normal py-1.5 px-2">指标</th>
                  {periods.map(p => (
                    <th key={p.end_date} className="text-right font-normal py-1.5 px-2 whitespace-nowrap">{periodLabel(p.end_date)}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <Row label="营业收入" hint="单位：万元；来源 income.revenue">
                  {periods.map(p => <td key={p.end_date} className="text-right py-1 px-2 tabular-nums">{fmtWan(p.inc?.revenue)}</td>)}
                </Row>
                <Row label="营收同比" hint="同比增长率，fina_indicator.or_yoy">
                  {periods.map(p => <td key={p.end_date} className={`text-right py-1 px-2 tabular-nums ${TREND_COLOR(p.fi?.or_yoy)}`}>{fmtPct(p.fi?.or_yoy, true)}</td>)}
                </Row>
                <Row label="归母净利润" hint="income.n_income_attr_p；单位：万元">
                  {periods.map(p => <td key={p.end_date} className="text-right py-1 px-2 tabular-nums">{fmtWan(p.inc?.n_income_attr_p)}</td>)}
                </Row>
                <Row label="净利同比" hint="fina_indicator.netprofit_yoy">
                  {periods.map(p => <td key={p.end_date} className={`text-right py-1 px-2 tabular-nums ${TREND_COLOR(p.fi?.netprofit_yoy)}`}>{fmtPct(p.fi?.netprofit_yoy, true)}</td>)}
                </Row>
                <Row label="ROE(%)" hint="fina_indicator.roe，净资产收益率">
                  {periods.map(p => <td key={p.end_date} className={`text-right py-1 px-2 tabular-nums ${TREND_COLOR(p.fi?.roe)}`}>{fmtPct(p.fi?.roe)}</td>)}
                </Row>
                <Row label="净利率(%)" hint="fina_indicator.netprofit_margin">
                  {periods.map(p => <td key={p.end_date} className={`text-right py-1 px-2 tabular-nums ${TREND_COLOR(p.fi?.netprofit_margin)}`}>{fmtPct(p.fi?.netprofit_margin)}</td>)}
                </Row>
                <Row label="资产负债率(%)" hint="fina_indicator.debt_to_assets；越低越稳健">
                  {periods.map(p => <td key={p.end_date} className="text-right py-1 px-2 tabular-nums">{fmtPct(p.fi?.debt_to_assets)}</td>)}
                </Row>
                <Row label="经营现金流" hint="cashflow.n_cashflow_act；单位：万元；为正且接近净利润视为质量良好">
                  {periods.map(p => <td key={p.end_date} className={`text-right py-1 px-2 tabular-nums ${(p.cf?.n_cashflow_act ?? 0) > 0 ? 'text-positive' : (p.cf?.n_cashflow_act ?? 0) < 0 ? 'text-negative' : ''}`}>{fmtWan(p.cf?.n_cashflow_act, true)}</td>)}
                </Row>
                <Row label="基本 EPS" hint="income.basic_eps；元/股">
                  {periods.map(p => <td key={p.end_date} className="text-right py-1 px-2 tabular-nums">{p.inc?.basic_eps != null ? p.inc.basic_eps.toFixed(2) : '-'}</td>)}
                </Row>
                <Row label="披露日期" hint="income.ann_date">
                  {periods.map(p => <td key={p.end_date} className="text-right py-1 px-2 tabular-nums text-gray-500 dark:text-gray-400">{p.inc?.ann_date ?? '-'}</td>)}
                </Row>
              </tbody>
            </table>
          </div>
          <p className="mt-3 text-[10px] text-gray-400 dark:text-gray-600">
            金额单位：万元（≥1 亿换算亿）；同比/比率为已计算的百分数；红=正向（涨）/绿=负向（跌），与 A 股语义一致
          </p>
        </CardContent>
      )}
      {expanded && !loading && !error && periods.length === 0 && (
        <CardContent>
          <p className="text-sm text-gray-500 dark:text-gray-400">暂无财报数据</p>
        </CardContent>
      )}
    </Card>
  )
}

function Row({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <tr className="border-b border-gray-50 dark:border-gray-900">
      <td className="py-1 px-2 text-gray-600 dark:text-gray-400" title={hint}>{label}</td>
      {children}
    </tr>
  )
}
