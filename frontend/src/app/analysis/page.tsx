'use client'

import { useCallback, useEffect, useState, Suspense, useMemo, useRef } from 'react'
import dynamic from 'next/dynamic'
import { useSearchParams } from 'next/navigation'
import { apiClient } from '@/lib/api-client'
import { getLatestStockAnalysis } from '@/lib/api/stocks'
import { useAuthStore } from '@/stores/auth-store'
import type { StockInfo, StockQuotePanel } from '@/types'
import { MoneyflowCard } from '@/components/stocks/MoneyflowCard'
import { BillboardCard } from '@/components/stocks/BillboardCard'
import { FinancialBriefCard } from '@/components/stocks/FinancialBriefCard'
import { ValuationCard } from '@/components/stocks/ValuationCard'
import {
  ExpertSummaryCard,
  CioDecisionCard,
  DataCollectionCard,
  ExpertDetailCard,
  EXPERTS,
  type ExpertMeta,
  type LatestAnalysisRecord,
} from '@/components/stocks/analysis'
import { AddToListDialog } from '@/app/stocks/components/AddToListDialog'
import { useToast } from '@/hooks/use-toast'
import { useMultiAnalysisTask } from '@/hooks/useMultiAnalysisTask'
import { Bookmark, Share2 } from 'lucide-react'

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
    t === 'info'    ? 'bg-primary/10 text-primary border-primary/25'
    : t === 'warning' ? 'bg-warning-soft text-warning border-warning/30'
    :                   'bg-muted text-muted-foreground border-border'

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

// ─────────────────────────────────────────
// 行情卡片
// ─────────────────────────────────────────

function QuotePanel({ q }: { q: StockQuotePanel }) {
  const pc = q.pct_change
  const priceTone = priceColor(pc)
  const preClose = resolvePreClose(q)

  // 涨跌徽章配色：红底白字（涨）/ 绿底白字（跌）/ 灰（平/无）
  const badgeBg = pc == null ? 'bg-gray-200 dark:bg-gray-700' : pc > 0 ? 'bg-positive' : pc < 0 ? 'bg-negative' : 'bg-gray-200 dark:bg-gray-700'
  const badgeText = pc == null || pc === 0 ? 'text-gray-700 dark:text-gray-200' : 'text-white'
  const arrow = pc == null ? '' : pc > 0 ? '▲' : pc < 0 ? '▼' : '·'
  const pctText = pc == null ? '-' : `${pc > 0 ? '+' : ''}${pc.toFixed(2)}%`
  const changeText = q.change_amount == null ? '-' : `${q.change_amount > 0 ? '+' : ''}${q.change_amount.toFixed(2)}`

  // 规模组（市值/股本）— PE/PB/PS/股息率/ROC/EY/安全边际 已拆到 ValuationCard
  const scaleItems = [
    { label: '总市值',   value: fmtMv(q.total_mv) },
    { label: '流通',     value: fmtMv(q.circ_mv) },
    { label: '总股本',   value: fmtShare(q.total_share) },
    { label: '流通股本', value: fmtShare(q.float_share) },
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

      {/* 规模 chip 列表（PE/PB/PS/股息率/ROC/EY/安全边际 已拆到 ValuationCard） */}
      <div className="space-y-2 pt-3 border-t border-gray-100 dark:border-gray-800">
        <ChipGroup title="规模" items={scaleItems} />
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

  // ── §13 自选 / 分享 ──
  const [addToListOpen, setAddToListOpen] = useState(false)
  const { toast } = useToast()

  const isAuthenticated = useAuthStore(s => s.isAuthenticated)

  // ── 4 专家最新分析（驱动主页 AI 决策摘要卡 / CIO 详情卡 / 三专家详情卡） ──
  const [latestByExpert, setLatestByExpert] = useState<Record<ExpertMeta['key'], LatestAnalysisRecord | null>>({
    cio: null,
    hot_money: null,
    midline: null,
    longterm: null,
  })
  const [expertsLoading, setExpertsLoading] = useState(false)
  const [expertsRefreshKey, setExpertsRefreshKey] = useState(0)
  const [activeExpertTab, setActiveExpertTab] = useState<Exclude<ExpertMeta['key'], 'cio'>>('hot_money')
  const [cioOpen, setCioOpen] = useState(false)
  const [regeneratingKey, setRegeneratingKey] = useState<ExpertMeta['key'] | null>(null)
  const cioCardRef = useRef<HTMLDivElement | null>(null)
  const detailCardRef = useRef<HTMLDivElement | null>(null)

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

  // ── 拉取 4 专家最新一条分析（驱动 AI 决策卡 / CIO 详情卡 / 三专家详情卡） ──
  // refreshKey 自增 → 重新拉取（一键分析 / 单专家重新分析完成时触发）
  useEffect(() => {
    const tsCode = basicInfo?.ts_code || (code ? toTsCode(code) : null)
    if (!tsCode || !isAuthenticated) {
      setLatestByExpert({ cio: null, hot_money: null, midline: null, longterm: null })
      return
    }
    let cancelled = false
    setExpertsLoading(true)
    Promise.all(
      EXPERTS.map((e) =>
        getLatestStockAnalysis(tsCode, e.analysisType)
          .then((res) => ({ key: e.key, record: ((res as any)?.data ?? null) as LatestAnalysisRecord | null }))
          .catch(() => ({ key: e.key, record: null as LatestAnalysisRecord | null })),
      ),
    ).then((results) => {
      if (cancelled) return
      const next: Record<ExpertMeta['key'], LatestAnalysisRecord | null> = {
        cio: null, hot_money: null, midline: null, longterm: null,
      }
      for (const r of results) next[r.key] = r.record
      setLatestByExpert(next)
    }).finally(() => {
      if (!cancelled) setExpertsLoading(false)
    })
    return () => { cancelled = true }
  }, [basicInfo?.ts_code, code, isAuthenticated, expertsRefreshKey])

  // 一键分析任务: 提交 / 轮询 / 探活 / 终态收尾全部由 hook 接管。
  // enableProbe=true 让 mount 后每 3s 探一次活跃任务, 与 /stocks 批量分析的状态同步。
  const tsCodeForTask = basicInfo?.ts_code || (code ? toTsCode(code) : null)
  const {
    generating: multiGenerating,
    message: multiMessage,
    start: handleMultiGenerate,
  } = useMultiAnalysisTask({
    tsCode: tsCodeForTask,
    stockName: stockInfo?.name ?? null,
    stockCode: code ?? null,
    enableProbe: true,
    enabled: isAuthenticated,
    onFinish: () => setExpertsRefreshKey((k) => k + 1),
  })

  // 单专家重新分析: 走 toast 单独通知, 不与一键分析(multiMessage) 共用 UI 槽位
  const handleRegenerateExpert = useCallback(async (expert: ExpertMeta) => {
    const tsCode = basicInfo?.ts_code || (code ? toTsCode(code) : null)
    const stockName = stockInfo?.name
    if (!tsCode || !stockName || !code) return
    setRegeneratingKey(expert.key)
    try {
      const res = await apiClient.generateStockAnalysis({
        ts_code: tsCode,
        stock_name: stockName,
        stock_code: code,
        analysis_type: expert.analysisType,
        template_key: expert.templateKey,
      })
      if (res?.code === 200 && res.data?.analysis_text) {
        toast({ title: '已完成', description: `${expert.label}专家分析完成` })
        setExpertsRefreshKey((k) => k + 1)
      } else {
        toast({ title: '失败', description: res?.message || `${expert.label}分析失败`, variant: 'destructive' })
      }
    } catch (e: any) {
      toast({ title: '失败', description: e?.response?.data?.message || `${expert.label}分析失败`, variant: 'destructive' })
    } finally {
      setRegeneratingKey(null)
    }
  }, [basicInfo?.ts_code, code, stockInfo?.name, toast])

  const handleExpertSummarySelect = useCallback((key: ExpertMeta['key']) => {
    if (key === 'cio') {
      setCioOpen(true)
      requestAnimationFrame(() => {
        cioCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      })
      return
    }
    setActiveExpertTab(key)
    requestAnimationFrame(() => {
      detailCardRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    })
  }, [])


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

  function toTsCode(c: string): string {
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
              <a href="/stocks" className="mt-4 inline-block text-primary hover:underline">
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
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-border border-t-primary"></div>
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
            <Alert className="bg-destructive/10 border-destructive/30 rounded-none">
              <AlertDescription className="text-destructive">{error}</AlertDescription>
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
          {/* §13 分享：复制当前页 URL */}
          <button
            type="button"
            onClick={() => {
              if (typeof navigator === 'undefined' || !navigator.clipboard) return
              navigator.clipboard.writeText(window.location.href).then(
                () => toast({ title: '链接已复制', description: window.location.href }),
                () => toast({ title: '复制失败', description: '请手动复制地址栏链接', variant: 'destructive' })
              )
            }}
            className="inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded border border-border text-muted-foreground hover:bg-surface-hover hover:text-foreground transition-colors duration-fast focus-ring"
            aria-label="复制当前股票分享链接"
            title="复制当前页面链接"
          >
            <Share2 className="h-3.5 w-3.5" />
            分享
          </button>
          {/* §13 自选：仅登录态可用，调起 AddToListDialog 选择列表 */}
          {isAuthenticated && tsCode && (
            <button
              type="button"
              onClick={() => setAddToListOpen(true)}
              className="inline-flex items-center gap-1 text-xs px-3 py-1.5 rounded border border-primary/30 text-primary hover:bg-primary/10 transition-colors duration-fast focus-ring"
              aria-label="添加到自选列表"
              title="添加到自选列表"
            >
              <Bookmark className="h-3.5 w-3.5" />
              自选
            </button>
          )}
        </div>
      </div>

      {/* §13 自选弹窗：复用 /stocks 页面同款组件 */}
      {tsCode && (
        <AddToListDialog
          open={addToListOpen}
          onClose={() => setAddToListOpen(false)}
          selectedCodes={[tsCode]}
          onSuccess={() => {
            toast({ title: '已添加到自选', description: `${stockInfo?.name ?? tsCode} 已加入选定列表` })
            setAddToListOpen(false)
          }}
        />
      )}

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
            <QuotePanel q={quotePanel} />
          ) : (
            <p className="text-sm text-gray-500 dark:text-gray-400">暂无行情数据</p>
          )}
        </CardContent>
      </Card>

      {/* 估值数据卡（PE/PB/PS/股息率 + ROC/EY/安全边际，从行情卡拆出来；公开数据，未登录可见） */}
      {quotePanel && <ValuationCard q={quotePanel} stock={stockInfo} />}

      {/* AI 决策三联卡（仅登录态可见，4 专家数据需鉴权） */}
      {isAuthenticated && (
        <>
          {/* 卡 ②：决策摘要 */}
          <ExpertSummaryCard
            latestByExpert={latestByExpert}
            loading={expertsLoading}
            onExpertSelect={handleExpertSummarySelect}
            onMultiGenerate={handleMultiGenerate}
            multiGenerating={multiGenerating}
            multiMessage={multiMessage}
          />

          {/* 卡 ③：CIO 综合决策（默认折叠；摘要卡点 CIO 时展开并滚到此处） */}
          {/*  历史翻页 + 编辑 / 删除 / 源代码 全部内嵌到卡片头部  */}
          <div ref={cioCardRef}>
            <CioDecisionCard
              tsCode={tsCode}
              defaultOpen={cioOpen}
              refreshKey={expertsRefreshKey}
              onChange={() => setExpertsRefreshKey((k) => k + 1)}
              key={`cio-${cioOpen}-${tsCode}`}
              id="cio-decision-card"
            />
          </div>

          {/* 卡 ④：三专家详情（嵌入式 Tab + 原报告/复盘 子段控件） */}
          <div ref={detailCardRef}>
            <ExpertDetailCard
              tsCode={tsCode}
              stockName={stockInfo?.name ?? ''}
              stockCode={code ?? ''}
              activeExpert={activeExpertTab}
              onActiveExpertChange={setActiveExpertTab}
              onRegenerate={handleRegenerateExpert}
              regeneratingKey={regeneratingKey}
              refreshKey={expertsRefreshKey}
              onChange={() => setExpertsRefreshKey((k) => k + 1)}
              id="expert-detail-card"
            />
          </div>

          {/* 卡 ⑤：数据收集（"AI 看到的原料"，默认折叠；翻页 / 编辑 / 删除 / 源代码 内嵌） */}
          <DataCollectionCard
            tsCode={tsCode}
            stockName={stockInfo?.name ?? ''}
            refreshKey={expertsRefreshKey}
            onChange={() => setExpertsRefreshKey((k) => k + 1)}
            id="data-collection-card"
          />
        </>
      )}

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

      {/* 财报简报折叠卡（默认收起，标题行显示最新一期摘要） */}
      {tsCode && <FinancialBriefCard tsCode={tsCode} />}

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

      {/* 近 60 日龙虎榜（含席位明细折叠） */}
      {tsCode && <BillboardCard tsCode={tsCode} />}
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
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-4 border-border border-t-primary"></div>
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
