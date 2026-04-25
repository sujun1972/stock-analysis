'use client'

import { useEffect, useState, Suspense, useMemo, useRef } from 'react'
import dynamic from 'next/dynamic'
import { useSearchParams } from 'next/navigation'
import { apiClient } from '@/lib/api-client'
import type { StockInfo, StockQuotePanel } from '@/types'
import { HotMoneyViewDialog } from '@/components/stocks/HotMoneyViewDialog'
import { MoneyflowCard } from '@/components/stocks/MoneyflowCard'

// 动态导入StockPriceCard组件（统一的图表组件）
const StockPriceCard = dynamic(() => import('@/components/StockPriceCard'), {
  ssr: false,
  loading: () => <div className="flex items-center justify-center h-[600px] bg-gray-50 dark:bg-gray-900 rounded-lg">加载图表中...</div>
})
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useSmartRefresh, useMarketStatus } from '@/hooks/useMarketStatus'

// ─────────────────────────────────────────
// 辅助组件
// ─────────────────────────────────────────

function InfoItem({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null
  return (
    <div>
      <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
      <p className="text-sm font-medium text-gray-900 dark:text-white truncate" title={value}>{value}</p>
    </div>
  )
}

/** 数字格式化：保留指定小数位，无值显示 '-' */
function fmt(v: number | null | undefined, decimals = 2, suffix = '') {
  if (v === null || v === undefined) return '-'
  return v.toFixed(decimals) + suffix
}

/** 成交量：股 → 万股 */
function fmtVol(v: number | null | undefined) {
  if (!v) return '-'
  if (v >= 1e8) return (v / 1e8).toFixed(2) + '亿股'
  return (v / 1e4).toFixed(2) + '万股'
}

/** 成交额：元 → 亿元 */
function fmtAmt(v: number | null | undefined) {
  if (!v) return '-'
  if (v >= 1e8) return (v / 1e8).toFixed(2) + '亿'
  return (v / 1e4).toFixed(2) + '万'
}

/** 市值：已转亿元 */
function fmtMv(v: number | null | undefined) {
  if (!v) return '-'
  return v.toFixed(2) + '亿'
}

/** 股本：万股 → 亿股（若 >= 10000 万） */
function fmtShare(v: number | null | undefined) {
  if (!v) return '-'
  if (v >= 10000) return (v / 10000).toFixed(2) + '亿股'
  return v.toFixed(2) + '万股'
}

/** 涨跌颜色（A 股配色：正数红、负数绿，用语义 token） */
function priceColor(pct?: number | null) {
  if (pct === null || pct === undefined) return 'text-gray-900 dark:text-white'
  if (pct > 0) return 'text-positive'
  if (pct < 0) return 'text-negative'
  return 'text-gray-900 dark:text-white'
}

/**
 * 价值类指标色阶（ROC / EY / 安全边际）
 * 用 score-* 蓝-金-紫色阶，避免与行情红绿混淆。
 * 各指标语境不同，调用方传自己的 [mid, high] 阈值边界（小数形式：0.15 = 15%）。
 * 负值统一显示 muted（不再借用行情绿，避免与"跌"语义混淆）。
 */
function valueScaleColor(v: number | null | undefined, mid: number, high: number) {
  if (v == null || !isFinite(v)) return ''
  if (v < 0) return 'text-muted-foreground'
  if (v >= high) return 'text-score-high'
  if (v >= mid) return 'text-score-mid'
  return 'text-score-low'
}

/** 评分色阶（4 专家共用：≥8 紫、≥6 金、≥4 蓝、其余灰；与行情红绿独立） */
function scoreColor(s?: number | null) {
  if (s == null) return 'text-gray-400 dark:text-gray-500'
  if (s >= 8) return 'text-score-high'
  if (s >= 6) return 'text-score-mid'
  if (s >= 4) return 'text-score-low'
  return 'text-muted-foreground'
}

/** 百分比（小数 → %，用于 ROC / 收益率 / 安全边际） */
function fmtPct(v?: number | null, decimals = 1) {
  if (v == null || !isFinite(v)) return '-'
  return (v * 100).toFixed(decimals) + '%'
}

/** 评分格式化：整数补一位小数，缺失显示 '-' */
function fmtScore(s?: number | null) {
  if (s == null) return '-'
  return Number.isInteger(s) ? s.toFixed(1) : String(s)
}

/** 估值日期 "20260424" → "2026-04-24"；非 8 位返回原值，避免破坏未知格式 */
function fmtDailyDate(s?: string | null): string {
  if (!s) return '-'
  if (/^\d{8}$/.test(s)) return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`
  return s
}

/**
 * 行情时效 chip：根据 trade_time 距今分档显示"实时 / 延迟 / 收盘"。
 * - trade_time 为 ISO/SQL 时间字符串；解析失败按"无数据"处理。
 * - isTrading=true 且差 ≤30s → 实时（绿）
 * - isTrading=true 且差 ≤15min → 延迟（橙）
 * - 其他（非交易时段 / 跨日陈旧）→ 收盘（灰）
 */
function FreshnessChip({ tradeTime, isTrading }: { tradeTime?: string | null; isTrading: boolean }) {
  // 每秒更新 now，让"实时 HH:mm:ss"走时
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  if (!tradeTime) {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
        <span className="h-1.5 w-1.5 rounded-full bg-gray-400" />
        无行情时间
      </span>
    )
  }

  // SQL 字符串 "2026-04-24 14:36:53" 跨浏览器兼容性差（Safari 不认空格分隔），用 'T' 替换；微秒部分忽略
  const parsed = new Date(tradeTime.replace(' ', 'T').split('.')[0])
  if (isNaN(parsed.getTime())) {
    return (
      <span className="inline-flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
        <span className="h-1.5 w-1.5 rounded-full bg-gray-400" />
        时间解析失败
      </span>
    )
  }

  const diffSec = Math.max(0, Math.floor((now.getTime() - parsed.getTime()) / 1000))
  const pad = (n: number) => String(n).padStart(2, '0')
  const hh = pad(parsed.getHours())
  const mm = pad(parsed.getMinutes())
  const ss = pad(parsed.getSeconds())
  const yyyy = parsed.getFullYear()
  const dateStr = `${yyyy}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())}`

  let dot = 'bg-gray-400'
  let label = ''
  let title = `行情时间：${dateStr} ${hh}:${mm}:${ss}（距今 ${diffSec} 秒）`

  if (isTrading && diffSec <= 30) {
    // 实时绿点用 emerald-500（信号灯绿），与 A 股"跌色"绿在视觉上区分
    dot = 'bg-emerald-500'
    label = `实时 · ${hh}:${mm}:${ss}`
  } else if (isTrading && diffSec <= 15 * 60) {
    dot = 'bg-amber-500'
    label = `延迟 ${Math.ceil(diffSec / 60)} 分钟 · ${hh}:${mm}`
  } else {
    dot = 'bg-gray-400'
    // 同日 → "收盘 · HH:mm"；跨日 → "收盘 · YYYY-MM-DD HH:mm"
    const todayStr = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`
    label = dateStr === todayStr ? `收盘 · ${hh}:${mm}` : `收盘 · ${dateStr} ${hh}:${mm}`
  }

  return (
    <span
      className="inline-flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 tabular-nums"
      title={title}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
      {label}
    </span>
  )
}

// 昨收兜底：stock_realtime.pre_close 在数据同步层偶有 0 值（Tushare 增量回补延迟），
// 此时用 latest_price - change_amount 推算，避免卡片出现 "-"
function resolvePreClose(q: StockQuotePanel): number | null {
  if (q.pre_close != null && q.pre_close > 0) return q.pre_close
  if (q.latest_price != null && q.change_amount != null) return q.latest_price - q.change_amount
  return null
}

/**
 * 名称行状态 Badge（央企 / 主板 / 沪股通 等）
 * 数据源：stock_basic 表（act_ent_type / market / is_hs）
 * §13 会扩展更全的状态（ST / 退市风险 / 融资融券）；当前仅做有数据的字段
 */
function StatusBadges({ basic }: { basic: StockInfo | null }) {
  if (!basic) return null
  const badges: { text: string; tone: 'neutral' | 'info' | 'warning' }[] = []

  // 实控人性质 → 央企 / 国企 / 民企（act_ent_type 字段）
  // Tushare 实际值如"中央企业"/"地方国有企业"/"民营企业"/"外资企业"——按关键字匹配，避免漏分类
  const ent = basic.act_ent_type
  if (ent) {
    if (/中央/.test(ent)) badges.push({ text: '央企', tone: 'info' })
    else if (/地方|国有/.test(ent)) badges.push({ text: '国企', tone: 'info' })
    else if (/民营/.test(ent)) badges.push({ text: '民企', tone: 'neutral' })
    else if (/外资|外商/.test(ent)) badges.push({ text: '外资', tone: 'neutral' })
    else if (/集体/.test(ent)) badges.push({ text: '集体', tone: 'neutral' })
  }
  // 市场板块（market 字段：主板 / 创业板 / 科创板 / 北交所 / CDR）
  if (basic.market) {
    badges.push({ text: basic.market, tone: 'neutral' })
  }
  // 沪深港通（is_hs：H=沪股通 S=深股通 N=否）
  if (basic.is_hs === 'H') badges.push({ text: '沪股通', tone: 'info' })
  else if (basic.is_hs === 'S') badges.push({ text: '深股通', tone: 'info' })
  // 退市状态（list_status：D=退市 P=暂停）
  if (basic.list_status === 'D') badges.push({ text: '已退市', tone: 'warning' })
  else if (basic.list_status === 'P') badges.push({ text: '暂停上市', tone: 'warning' })

  if (badges.length === 0) return null
  const toneClass = (t: 'neutral' | 'info' | 'warning') =>
    t === 'info'    ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300 border-blue-200 dark:border-blue-800'
    : t === 'warning' ? 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300 border-amber-200 dark:border-amber-800'
    :                   'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300 border-gray-200 dark:border-gray-700'

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {badges.map((b, i) => (
        <span key={i} className={`inline-flex items-center px-1.5 py-0.5 rounded border text-[10px] leading-tight ${toneClass(b.tone)}`}>
          {b.text}
        </span>
      ))}
    </div>
  )
}

// ─────────────────────────────────────────
// 行情卡片：辅助子组件
// ─────────────────────────────────────────

/** 横向 chip 列表（估值组 / 规模组 / 价值组通用） */
function ChipGroup({ title, items }: { title: string; items: { label: string; value: string; color?: string; title?: string }[] }) {
  const visible = items.filter(it => it.value && it.value !== '-')
  if (visible.length === 0) return null
  return (
    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1.5">
      <span className="text-xs text-gray-400 dark:text-gray-500 shrink-0">{title}</span>
      {visible.map((it, i) => (
        <span key={it.label} className="inline-flex items-baseline gap-1 text-xs" title={it.title || undefined}>
          <span className="text-gray-500 dark:text-gray-400">{it.label}</span>
          <span className={`font-semibold tabular-nums ${it.color ?? 'text-gray-900 dark:text-white'}`}>{it.value}</span>
          {i < visible.length - 1 && <span className="ml-1 text-gray-300 dark:text-gray-700">│</span>}
        </span>
      ))}
    </div>
  )
}

/**
 * 4 维度迷你雷达图（手写 SVG，无第三方依赖）
 * 4 个轴：游资 / 中线 / 价值 / CIO；满分 10 分映射到外圈
 * 节点用 score-* 色阶，与 §1 评分色对齐
 */
function MiniRadarChart({
  scores,
  size = 120,
}: {
  scores: { label: string; score: number | null | undefined }[]
  size?: number
}) {
  // 上下左右各预留 24px 给标签（"游资 2.5"等双行文字宽度），雷达本体放在中央
  // viewBox 比 size 大一圈：避免 4 个轴方向的标签溢出 SVG 边界
  const PAD = 24
  const vbSize = size + PAD * 2
  const cx = vbSize / 2
  const cy = vbSize / 2
  const radius = size * 0.36
  const labelRadius = size * 0.5 + 6  // 数据顶点之外、SVG 边缘之内
  // 4 个轴朝向：上/右/下/左（顺时针）
  const angles = scores.map((_, i) => -Math.PI / 2 + (i * 2 * Math.PI) / scores.length)

  // 评分→坐标（满分 10 → radius；空值 → 0.5×radius 占位避免雷达图空塌）
  const points = scores.map((s, i) => {
    const v = (s.score ?? 0) / 10
    const r = Math.max(0.05, Math.min(1, v)) * radius
    return { x: cx + r * Math.cos(angles[i]), y: cy + r * Math.sin(angles[i]), score: s.score }
  })
  const polyline = points.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')

  // 三层同心圈（25/50/75/100% 满刻度参考）
  const rings = [0.25, 0.5, 0.75, 1.0]

  // 用 score-* token 取颜色：高分紫、中分金、低分蓝
  const fillByScore = (s: number | null | undefined): string => {
    if (s == null) return 'hsl(var(--muted-foreground))'
    if (s >= 8) return 'hsl(var(--score-high))'
    if (s >= 6) return 'hsl(var(--score-mid))'
    if (s >= 4) return 'hsl(var(--score-low))'
    return 'hsl(var(--muted-foreground))'
  }

  return (
    <svg width={vbSize} height={vbSize} viewBox={`0 0 ${vbSize} ${vbSize}`} className="shrink-0">
      {/* 同心圈（淡灰参考） */}
      {rings.map(r => (
        <circle key={r} cx={cx} cy={cy} r={radius * r} fill="none" stroke="currentColor" strokeOpacity={0.12} strokeWidth={0.5} className="text-gray-400 dark:text-gray-600" />
      ))}
      {/* 4 条轴线 */}
      {angles.map((a, i) => (
        <line key={i} x1={cx} y1={cy} x2={cx + radius * Math.cos(a)} y2={cy + radius * Math.sin(a)} stroke="currentColor" strokeOpacity={0.15} strokeWidth={0.5} className="text-gray-400 dark:text-gray-600" />
      ))}
      {/* 数据多边形（半透明 fill + 描边） */}
      <polygon points={polyline} fill="hsl(var(--score-low))" fillOpacity={0.18} stroke="hsl(var(--score-low))" strokeWidth={1.2} />
      {/* 各维度顶点圆点（按分数着色） */}
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={2.5} fill={fillByScore(p.score)} />
      ))}
      {/* 维度文字（轴外侧） */}
      {angles.map((a, i) => {
        const tx = cx + labelRadius * Math.cos(a)
        const ty = cy + labelRadius * Math.sin(a)
        const score = scores[i].score
        return (
          <g key={i}>
            <text x={tx} y={ty - 3} textAnchor="middle" className="fill-gray-500 dark:fill-gray-400" style={{ fontSize: 9 }}>{scores[i].label}</text>
            <text x={tx} y={ty + 8} textAnchor="middle" fill={fillByScore(score)} style={{ fontSize: 10, fontWeight: 600, fontVariantNumeric: 'tabular-nums' }}>
              {score == null ? '—' : Number.isInteger(score) ? score.toFixed(1) : score.toString()}
            </text>
          </g>
        )
      })}
    </svg>
  )
}

/** 1280 视口降级：横向 4 个 ring 进度条 */
function ScoreRings({ scores }: { scores: { label: string; score: number | null | undefined }[] }) {
  const fillByScore = (s: number | null | undefined): string => {
    if (s == null) return 'hsl(var(--muted-foreground))'
    if (s >= 8) return 'hsl(var(--score-high))'
    if (s >= 6) return 'hsl(var(--score-mid))'
    if (s >= 4) return 'hsl(var(--score-low))'
    return 'hsl(var(--muted-foreground))'
  }
  const ringSize = 44
  const stroke = 4
  const r = (ringSize - stroke) / 2
  const c = 2 * Math.PI * r
  return (
    <div className="grid grid-cols-4 gap-2">
      {scores.map(({ label, score }) => {
        const pct = Math.max(0, Math.min(1, (score ?? 0) / 10))
        const dash = c * pct
        return (
          <div key={label} className="flex flex-col items-center gap-1">
            <div className="relative" style={{ width: ringSize, height: ringSize }}>
              <svg width={ringSize} height={ringSize} viewBox={`0 0 ${ringSize} ${ringSize}`}>
                <circle cx={ringSize / 2} cy={ringSize / 2} r={r} fill="none" stroke="currentColor" strokeOpacity={0.15} strokeWidth={stroke} className="text-gray-400 dark:text-gray-600" />
                <circle
                  cx={ringSize / 2}
                  cy={ringSize / 2}
                  r={r}
                  fill="none"
                  stroke={fillByScore(score)}
                  strokeWidth={stroke}
                  strokeLinecap="round"
                  strokeDasharray={`${dash.toFixed(1)} ${c.toFixed(1)}`}
                  transform={`rotate(-90 ${ringSize / 2} ${ringSize / 2})`}
                />
              </svg>
              <span
                className="absolute inset-0 flex items-center justify-center text-xs font-semibold tabular-nums"
                style={{ color: fillByScore(score) }}
              >
                {score == null ? '—' : Number.isInteger(score) ? score.toFixed(1) : score}
              </span>
            </div>
            <span className="text-[10px] text-gray-500 dark:text-gray-400">{label}</span>
          </div>
        )
      })}
    </div>
  )
}

// ─────────────────────────────────────────
// 行情卡片
// ─────────────────────────────────────────

function QuotePanel({ q, stock }: { q: StockQuotePanel; stock: StockInfo | null }) {
  const pc = q.pct_change
  const priceTone = priceColor(pc)
  const preClose = resolvePreClose(q)

  const vm = stock?.value_metrics ?? null
  // CIO 复查触发器：time_triggers 取最近一个 expected_date；price_triggers 分上/下方向
  const triggers = stock?.latest_analysis_cio?.followup_triggers
  const nearestTime = triggers?.time_triggers
    ?.filter(t => !!t.expected_date)
    .sort((a, b) => String(a.expected_date).localeCompare(String(b.expected_date)))[0]
  const breakUp = triggers?.price_triggers?.find(t => t.direction === 'break_up' && t.price != null)
  const breakDown = triggers?.price_triggers?.find(t => t.direction === 'break_down' && t.price != null)

  // 涨跌徽章配色：红底白字（涨）/ 绿底白字（跌）/ 灰（平/无）
  const badgeBg = pc == null ? 'bg-gray-200 dark:bg-gray-700' : pc > 0 ? 'bg-positive' : pc < 0 ? 'bg-negative' : 'bg-gray-200 dark:bg-gray-700'
  const badgeText = pc == null || pc === 0 ? 'text-gray-700 dark:text-gray-200' : 'text-white'
  const arrow = pc == null ? '' : pc > 0 ? '▲' : pc < 0 ? '▼' : '·'
  const pctText = pc == null ? '-' : `${pc > 0 ? '+' : ''}${pc.toFixed(2)}%`
  const changeText = q.change_amount == null ? '-' : `${q.change_amount > 0 ? '+' : ''}${q.change_amount.toFixed(2)}`

  // 估值组（PE/PB/PS/股息率）
  const valuationItems = [
    { label: 'PE(TTM)', value: fmt(q.pe_ttm), title: '滚动市盈率（最近 4 个季度）' },
    { label: 'PE',      value: fmt(q.pe),     title: '静态市盈率' },
    { label: 'PB',      value: fmt(q.pb),     title: '市净率' },
    { label: 'PS(TTM)', value: fmt(q.ps_ttm), title: '滚动市销率' },
    { label: '股息率',  value: fmt(q.dv_ttm ?? q.dv_ratio, 2, '%'), title: '股息率 TTM' },
  ]
  // 规模组（市值/股本）
  const scaleItems = [
    { label: '总市值',   value: fmtMv(q.total_mv) },
    { label: '流通',     value: fmtMv(q.circ_mv) },
    { label: '总股本',   value: fmtShare(q.total_share) },
    { label: '流通股本', value: fmtShare(q.float_share) },
  ]
  // 价值类指标（ROC / EY / 安全边际，独立成组——色阶用 score-*）
  const valueItems = [
    { label: 'ROC',      value: fmtPct(vm?.roc),              color: valueScaleColor(vm?.roc, 0.15, 0.30),              title: '资本收益率 ROC = EBIT / (净营运资本 + 净固定资产)' },
    { label: '收益率',   value: fmtPct(vm?.earnings_yield),    color: valueScaleColor(vm?.earnings_yield, 0.10, 0.20),    title: '收益率 EY = EBIT / EV' },
    { label: '安全边际', value: fmtPct(vm?.intrinsic_margin, 0), color: valueScaleColor(vm?.intrinsic_margin, 0.30, 1.00),  title: vm?.intrinsic_value != null ? `格雷厄姆内在价值 ${vm.intrinsic_value.toFixed(2)} 元（g=${((vm.g_rate ?? 0) * 100).toFixed(1)}%）` : '格雷厄姆内在价值数据不足' },
  ]

  // 4 专家评分（雷达图数据）
  const scoreData = [
    { label: '游资', score: stock?.latest_analysis_hot_money?.score },
    { label: '中线', score: stock?.latest_analysis_midline?.score },
    { label: '价值', score: stock?.latest_analysis_longterm?.score },
    { label: 'CIO',  score: stock?.latest_analysis_cio?.score },
  ]

  return (
    <div className="space-y-4">
      {/* 顶部：左大字号最新价 + 涨跌徽章 + 右侧次要数值 */}
      <div className="flex flex-wrap items-start gap-x-8 gap-y-3">
        {/* 价格区 */}
        <div className="flex flex-col gap-1.5">
          <div className="flex items-baseline gap-3">
            <span className={`text-4xl font-semibold tabular-nums leading-none ${priceTone}`}>{fmt(q.latest_price)}</span>
            <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-semibold tabular-nums ${badgeBg} ${badgeText}`}>
              {arrow && <span className="text-[10px]">{arrow}</span>}
              <span>{changeText}</span>
              <span>({pctText})</span>
            </span>
          </div>
          {/* 第二行：今开/最高/最低/昨收 */}
          <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs tabular-nums">
            <span><span className="text-gray-500 dark:text-gray-400">今开 </span><span className="font-semibold text-gray-900 dark:text-white">{fmt(q.open)}</span></span>
            <span><span className="text-gray-500 dark:text-gray-400">最高 </span><span className="font-semibold text-gray-900 dark:text-white">{fmt(q.high)}</span></span>
            <span><span className="text-gray-500 dark:text-gray-400">最低 </span><span className="font-semibold text-gray-900 dark:text-white">{fmt(q.low)}</span></span>
            <span><span className="text-gray-500 dark:text-gray-400">昨收 </span><span className="font-semibold text-gray-900 dark:text-white">{fmt(preClose)}</span></span>
          </div>
        </div>
        {/* 右侧次要数值（振幅/换手/量比/成交额） */}
        <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs tabular-nums">
          <span><span className="text-gray-500 dark:text-gray-400">振幅 </span><span className="font-semibold text-gray-900 dark:text-white">{fmt(q.amplitude, 2, '%')}</span></span>
          <span><span className="text-gray-500 dark:text-gray-400">换手 </span><span className="font-semibold text-gray-900 dark:text-white">{fmt(q.turnover_rate ?? q.turnover, 2, '%')}</span></span>
          <span><span className="text-gray-500 dark:text-gray-400">量比 </span><span className="font-semibold text-gray-900 dark:text-white">{fmt(q.volume_ratio)}</span></span>
          <span><span className="text-gray-500 dark:text-gray-400">成交 </span><span className="font-semibold text-gray-900 dark:text-white">{fmtAmt(q.amount)}</span></span>
        </div>
      </div>

      {/* 估值 + 规模分组 chip 列表 */}
      <div className="space-y-2 pt-3 border-t border-gray-100 dark:border-gray-800">
        <ChipGroup title="估值" items={valuationItems} />
        <ChipGroup title="规模" items={scaleItems} />
        <ChipGroup title="价值" items={valueItems} />
        {q.daily_date && (
          <p
            className="text-[11px] text-gray-400 dark:text-gray-600 tabular-nums pt-1"
            title="daily_basic 表的快照日期（每日收盘后更新；PE/PB/换手率/股息率等估值类字段以此日为准）"
          >
            估值数据 · {fmtDailyDate(q.daily_date)}
          </p>
        )}
      </div>

      {/* 雷达图 + 复查触发（≥1440 雷达图，<1440 ring 进度条；§5 文档明确要求 1280 用 ring 降级） */}
      <div className="flex flex-col min-[1440px]:flex-row items-start gap-4 pt-3 border-t border-gray-100 dark:border-gray-800">
        <div className="hidden min-[1440px]:block">
          <MiniRadarChart scores={scoreData} size={140} />
        </div>
        <div className="min-[1440px]:hidden w-full">
          <ScoreRings scores={scoreData} />
        </div>
        <div className="flex-1 space-y-1.5 text-xs">
          <div className="flex flex-wrap items-baseline gap-x-3">
            <span className="text-gray-400 dark:text-gray-500 shrink-0">下次复查</span>
            {breakUp && (
              <span className="inline-flex items-baseline gap-1" title={breakUp.price_basis ?? '上破触发'}>
                <span className="text-gray-500 dark:text-gray-400">上破</span>
                <span className="font-semibold text-positive tabular-nums">{breakUp.price?.toFixed(2)}</span>
              </span>
            )}
            {breakUp && breakDown && <span className="text-gray-300 dark:text-gray-700">/</span>}
            {breakDown && (
              <span className="inline-flex items-baseline gap-1" title={breakDown.price_basis ?? '下破触发'}>
                <span className="text-gray-500 dark:text-gray-400">下破</span>
                <span className="font-semibold text-negative tabular-nums">{breakDown.price?.toFixed(2)}</span>
              </span>
            )}
            {!breakUp && !breakDown && <span className="text-gray-400 dark:text-gray-600">价格未设</span>}
          </div>
          <div className="flex flex-wrap items-baseline gap-x-3">
            <span className="text-gray-400 dark:text-gray-500 shrink-0">关注时间</span>
            <span className="tabular-nums text-gray-900 dark:text-white" title={nearestTime?.reason ?? ''}>
              {nearestTime?.expected_date ?? '未设'}
            </span>
            {stock?.latest_analysis_cio?.created_at && (
              <span className="text-gray-400 dark:text-gray-600">
                · 由 CIO {stock.latest_analysis_cio.created_at.slice(0, 10)} 设定
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}


// ─────────────────────────────────────────
// 主页面
// ─────────────────────────────────────────

function AnalysisContent() {
  const searchParams = useSearchParams()
  const code = searchParams.get('code')
  const { isTrading } = useMarketStatus()

  const [stockInfo, setStockInfo] = useState<StockInfo | null>(null)
  const [basicInfo, setBasicInfo] = useState<StockInfo | null>(null)
  const [quotePanel, setQuotePanel] = useState<StockQuotePanel | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  // 筹码分布数据（嵌入到 K 线主图右侧）
  const [chipsData, setChipsData] = useState<{ price: number; percent: number }[]>([])
  // 筹码历史（Map<YYYY-MM-DD, ChipItem[]>）：K 线 hover 按日期切换
  const [chipsHistory, setChipsHistory] = useState<Map<string, { price: number; percent: number }[]>>(new Map())
  // 按需拉取缓存管理
  // fetchedRanges 改用 state，让子组件通过 prop 拿到最新值，区分"加载中"/"已确认无数据"
  const [fetchedChipsRanges, setFetchedChipsRanges] = useState<Array<{ start: string; end: string }>>([])
  const inflightChipsRangesRef = useRef<Array<{ start: string; end: string }>>([])  // 正在拉的区间
  const chipsMissDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null)   // 防抖句柄

  // ── AI 分析弹窗 ──
  const [hotMoneyOpen, setHotMoneyOpen] = useState(false)
  const [hotMoneyContent, setHotMoneyContent] = useState('')
  const [hotMoneyLoading, setHotMoneyLoading] = useState(false)
  const [dataCollectionContent, setDataCollectionContent] = useState('')
  const [dataCollectionLoading, setDataCollectionLoading] = useState(false)
  const [midlineContent, setMidlineContent] = useState('')
  const [midlineLoading, setMidlineLoading] = useState(false)
  const [longtermContent, setLongtermContent] = useState('')
  const [longtermLoading, setLongtermLoading] = useState(false)
  const [cioContent, setCioContent] = useState('')
  const [cioLoading, setCioLoading] = useState(false)

  useEffect(() => {
    if (code) {
      loadStockInfo()
    } else {
      setIsLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code])

  // 加载筹码分布（单日快照 + 近 6 个月历史，用于 K 线 hover 联动）
  // 历史数据按交易日分组到 Map，前端用 dataIndex 找对应日期即可 O(1) 切换
  useEffect(() => {
    const tsCode = basicInfo?.ts_code || (code ? toTsCode(code) : null)
    if (!tsCode) return
    let cancelled = false

    // 最新一日快照（兜底，首屏立即显示）
    apiClient.getChipsDistribution(tsCode).then(items => {
      if (cancelled) return
      setChipsData(items ?? [])
    }).catch(() => {
      if (!cancelled) setChipsData([])
    })

    // 近 6 个月筹码历史（约 120 个交易日 × 100 档位 ≈ 12000 行，单请求 < 500ms）
    const today = new Date()
    const start = new Date(today)
    start.setMonth(start.getMonth() - 6)
    const fmt = (d: Date) =>
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
    const startStr = fmt(start)
    const endStr = fmt(today)

    // 切换股票时重置缓存
    setFetchedChipsRanges([])
    inflightChipsRangesRef.current = []

    apiClient.getChipsDistributionHistory(tsCode, startStr, endStr).then(history => {
      if (cancelled) return
      setChipsHistory(history)
      setFetchedChipsRanges([{ start: startStr, end: endStr }])
    }).catch(() => {
      if (!cancelled) setChipsHistory(new Map())
    })

    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [basicInfo?.ts_code, code])

  /**
   * 按需拉取某日期附近的筹码数据（K 线 hover 触发）
   * - 防抖 300ms：鼠标快速划过时避免狂发请求
   * - 区间覆盖检查：date 已在 fetched 或 inflight 区间内则跳过
   * - 窗口策略：以 date 为中心 ±45 天，单次拉回一片，摊薄网络开销
   */
  const onChipsDateMiss = (date: string) => {
    if (chipsMissDebounceRef.current) clearTimeout(chipsMissDebounceRef.current)
    chipsMissDebounceRef.current = setTimeout(() => {
      const tsCode = basicInfo?.ts_code || (code ? toTsCode(code) : null)
      if (!tsCode) return

      // 检查 date 是否已在已拉/正在拉的任何区间内
      const inRange = (ranges: Array<{ start: string; end: string }>) =>
        ranges.some(r => date >= r.start && date <= r.end)
      if (inRange(fetchedChipsRanges) || inRange(inflightChipsRangesRef.current)) {
        return
      }

      // 以 date 为中心取 ±45 天窗口
      const centerDate = new Date(date + 'T00:00:00')
      const winStart = new Date(centerDate); winStart.setDate(winStart.getDate() - 45)
      const winEnd = new Date(centerDate); winEnd.setDate(winEnd.getDate() + 45)
      const fmt = (d: Date) =>
        `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
      const reqStart = fmt(winStart)
      const reqEnd = fmt(winEnd)

      inflightChipsRangesRef.current.push({ start: reqStart, end: reqEnd })
      apiClient.getChipsDistributionHistory(tsCode, reqStart, reqEnd).then(newHistory => {
        // 合并到 chipsHistory（不覆盖已有键）；触发 date 所在天若仍无数据，写入空数组作为"已确认无数据"标记
        // 这样子组件再 hover 该日时 historyMap.has(date)=true、bucket=[]，badge 显示"无数据"而非"加载中"
        setChipsHistory(prev => {
          const merged = new Map(prev)
          newHistory.forEach((v, k) => {
            if (!merged.has(k)) merged.set(k, v)
          })
          if (!merged.has(date)) merged.set(date, [])
          return merged
        })
        setFetchedChipsRanges(prev => [...prev, { start: reqStart, end: reqEnd }])
      }).finally(() => {
        inflightChipsRangesRef.current = inflightChipsRangesRef.current.filter(
          r => !(r.start === reqStart && r.end === reqEnd)
        )
      })
    }, 300)
  }

  const toTsCode = (c: string) => {
    if (c.includes('.')) return c.toUpperCase()
    if (c.startsWith('6')) return `${c}.SH`
    if (c.startsWith('4') || c.startsWith('8')) return `${c}.BJ`
    return `${c}.SZ`
  }

  const loadStockInfo = async () => {
    if (!code) return
    try {
      setIsLoading(true)
      setError(null)
      const [stockInfoData, basicInfoData, quotePanelData] = await Promise.all([
        apiClient.getStock(code),
        apiClient.getStockBasicInfo(code),
        apiClient.getStockQuotePanel(code),
      ])
      setStockInfo(stockInfoData)
      setBasicInfo(basicInfoData)
      setQuotePanel(quotePanelData)
    } catch (err: any) {
      setError(err.message || '加载股票数据失败')
      console.error('Failed to load stock data:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const openHotMoneyDialog = () => {
    setHotMoneyContent('')
    setDataCollectionContent('')
    setMidlineContent('')
    setLongtermContent('')
    setCioContent('')
    setHotMoneyLoading(true)
    setDataCollectionLoading(true)
    setMidlineLoading(true)
    setLongtermLoading(true)
    setCioLoading(true)
    setHotMoneyOpen(true)
    const vars = { stock_name: stockInfo?.name ?? '', stock_code: code ?? '' }
    const currentTsCode = basicInfo?.ts_code || (code ? toTsCode(code) : '')
    Promise.all([
      apiClient.getPromptTemplateByKey('top_speculative_investor_v1', { ...vars, ts_code: currentTsCode }),
      apiClient.getPromptTemplateByKey('stock_data_collection_v1', vars),
      apiClient.getPromptTemplateByKey('midline_industry_expert_v1', { ...vars, ts_code: currentTsCode }),
      apiClient.getPromptTemplateByKey('longterm_value_watcher_v1', { ...vars, ts_code: currentTsCode }),
      apiClient.getPromptTemplateByKey('cio_directive_v1', { ...vars, ts_code: currentTsCode }),
    ]).then(([hotRes, dataRes, midRes, ltRes, cioRes]) => {
      const toPrompt = (res: any) => {
        if (res?.code === 200 && res.data?.user_prompt_template) {
          return [res.data.system_prompt, res.data.user_prompt_template].filter(Boolean).join('\n\n')
        }
        return '加载失败，请重试'
      }
      setHotMoneyContent(toPrompt(hotRes))
      setDataCollectionContent(toPrompt(dataRes))
      setMidlineContent(toPrompt(midRes))
      setLongtermContent(toPrompt(ltRes))
      setCioContent(toPrompt(cioRes))
    }).catch(() => {
      setHotMoneyContent('加载失败，请重试')
      setDataCollectionContent('加载失败，请重试')
      setMidlineContent('加载失败，请重试')
      setLongtermContent('加载失败，请重试')
      setCioContent('加载失败，请重试')
    }).finally(() => {
      setHotMoneyLoading(false)
      setDataCollectionLoading(false)
      setMidlineLoading(false)
      setLongtermLoading(false)
      setCioLoading(false)
    })
  }

  // 使用 useMemo 稳定 codes 数组引用，避免重复触发刷新
  const codes = useMemo(() => code ? [code] : undefined, [code])

  // 智能刷新：刷新实时行情 + 行情面板
  useSmartRefresh(
    async () => {
      if (!code) return
      await apiClient.syncRealtimeQuotes({ codes: [code], batch_size: 1 })
      const [stockInfoData, quotePanelData] = await Promise.all([
        apiClient.getStock(code),
        apiClient.getStockQuotePanel(code),
      ])
      setStockInfo(stockInfoData)
      setQuotePanel(quotePanelData)
    },
    codes,
    true
  )

  if (!code) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">股票分析</h1>
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <p className="mt-4 text-gray-600 dark:text-gray-400">请从股票列表选择股票</p>
              <a href="/stocks" className="mt-4 inline-block text-blue-600 hover:text-blue-900 dark:text-blue-400 dark:hover:text-blue-300 hover:underline">
                前往股票列表
              </a>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">股票分析</h1>
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-300 border-t-blue-600"></div>
              <p className="mt-4 text-gray-600 dark:text-gray-400">加载中...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">股票分析</h1>
        <Card>
          <CardContent className="p-0">
            <Alert className="bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 rounded-none">
              <AlertDescription className="text-red-800 dark:text-red-200">{error}</AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </div>
    )
  }

  const tsCode = basicInfo?.ts_code || (code ? toTsCode(code) : '')

  return (
    <div className="space-y-6">
      {/* 页面标题 */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
              {stockInfo?.name}（{stockInfo?.code}）
            </h1>
            <StatusBadges basic={basicInfo} />
          </div>
          {basicInfo?.fullname && basicInfo.fullname !== basicInfo?.name && (
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{basicInfo.fullname}</p>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 pt-1">
          <button
            onClick={openHotMoneyDialog}
            className="text-xs px-3 py-1.5 rounded border border-yellow-400 text-yellow-600 hover:bg-yellow-50 dark:border-yellow-500 dark:text-yellow-400 dark:hover:bg-yellow-900/20 transition-colors"
          >
            AI 分析
          </button>
        </div>
      </div>

      <HotMoneyViewDialog
        open={hotMoneyOpen}
        onClose={() => setHotMoneyOpen(false)}
        stockName={stockInfo?.name ?? ''}
        stockCode={code ?? ''}
        tsCode={tsCode}
        promptContent={hotMoneyContent}
        promptLoading={hotMoneyLoading}
        dataCollectionPrompt={dataCollectionContent}
        dataCollectionPromptLoading={dataCollectionLoading}
        midlinePrompt={midlineContent}
        midlinePromptLoading={midlineLoading}
        longtermPrompt={longtermContent}
        longtermPromptLoading={longtermLoading}
        cioPrompt={cioContent}
        cioPromptLoading={cioLoading}
        onSaved={() => { if (code) apiClient.getStock(code).then(setStockInfo).catch(() => {}) }}
      />

      {/* 行情卡片 */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between gap-3">
            <CardTitle className="text-base">行情数据</CardTitle>
            <FreshnessChip tradeTime={quotePanel?.trade_time} isTrading={isTrading} />
          </div>
        </CardHeader>
        <CardContent>
          {quotePanel ? (
            <QuotePanel q={quotePanel} stock={stockInfo} />
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400">暂无行情数据</p>
          )}
        </CardContent>
      </Card>

      {/* 基本信息卡片 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">基本信息</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-x-6 gap-y-4">
            <InfoItem label="股票代码" value={basicInfo?.ts_code || stockInfo?.code} />
            <InfoItem label="股票名称" value={basicInfo?.name || stockInfo?.name} />
            <InfoItem label="拼音缩写" value={basicInfo?.cnspell} />
            <InfoItem label="市场" value={basicInfo?.market || stockInfo?.market} />
            <InfoItem label="交易所" value={
              basicInfo?.exchange === 'SSE' ? '上交所(SSE)'
              : basicInfo?.exchange === 'SZSE' ? '深交所(SZSE)'
              : basicInfo?.exchange === 'BSE' ? '北交所(BSE)'
              : basicInfo?.exchange
            } />
            <InfoItem label="行业" value={basicInfo?.industry || stockInfo?.industry} />
            <InfoItem label="地区" value={basicInfo?.area || stockInfo?.area} />
            <InfoItem label="上市日期" value={basicInfo?.list_date || stockInfo?.list_date} />
            {basicInfo?.delist_date && <InfoItem label="退市日期" value={basicInfo.delist_date} />}
            <InfoItem label="上市状态" value={
              basicInfo?.list_status === 'L' ? '上市'
              : basicInfo?.list_status === 'D' ? '退市'
              : basicInfo?.list_status === 'P' ? '暂停上市'
              : basicInfo?.list_status === 'G' ? '过会未交易'
              : basicInfo?.list_status
            } />
            <InfoItem label="沪深港通" value={
              basicInfo?.is_hs === 'H' ? '沪股通'
              : basicInfo?.is_hs === 'S' ? '深股通'
              : basicInfo?.is_hs === 'N' ? '否'
              : basicInfo?.is_hs
            } />
            <InfoItem label="交易货币" value={basicInfo?.curr_type} />
            {basicInfo?.act_name && <InfoItem label="实控人" value={basicInfo.act_name} />}
            {basicInfo?.act_ent_type && <InfoItem label="实控人性质" value={basicInfo.act_ent_type} />}
            {basicInfo?.enname && (
              <div className="col-span-2 md:col-span-3 lg:col-span-4">
                <InfoItem label="英文名称" value={basicInfo.enname} />
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* 图表区域（筹码分布已嵌入 K 线主图右侧，鼠标 hover K 线切换到对应日期） */}
      <StockPriceCard
        stockCode={code}
        stockName={stockInfo?.name}
        defaultChartType="daily"
        showHeader={true}
        chipsData={chipsData}
        chipsHistory={chipsHistory}
        chipsFetchedRanges={fetchedChipsRanges}
        onChipsDateMiss={onChipsDateMiss}
      />

      {/* 资金流向（4 档分布 + N 日主力净流入） */}
      {tsCode && <MoneyflowCard tsCode={tsCode} />}
    </div>
  )
}

export default function AnalysisPage() {
  return (
    <Suspense fallback={
      <div className="space-y-6">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white">股票分析</h1>
        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-gray-300 border-t-blue-600"></div>
              <p className="mt-4 text-gray-600 dark:text-gray-400">加载中...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    }>
      <AnalysisContent />
    </Suspense>
  )
}
