'use client'

import { useEffect, useState, Suspense, useMemo, useRef } from 'react'
import dynamic from 'next/dynamic'
import { useSearchParams } from 'next/navigation'
import { apiClient } from '@/lib/api-client'
import type { StockInfo, StockQuotePanel } from '@/types'
import { HotMoneyViewDialog } from '@/components/stocks/HotMoneyViewDialog'

// 动态导入StockPriceCard组件（统一的图表组件）
const StockPriceCard = dynamic(() => import('@/components/StockPriceCard'), {
  ssr: false,
  loading: () => <div className="flex items-center justify-center h-[600px] bg-gray-50 dark:bg-gray-900 rounded-lg">加载图表中...</div>
})
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useSmartRefresh } from '@/hooks/useMarketStatus'

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

/** 价值度量配色（ROC/EY/安全边际：正数红、负数绿、0 黑） */
function valueMetricColor(v?: number | null) {
  if (v == null || !isFinite(v)) return ''
  if (v > 0) return 'text-positive'
  if (v < 0) return 'text-negative'
  return ''
}

/** 评分色阶（与共享 ScoreBadge 对齐：≥8 红、≥6 黄、其余灰） */
function scoreColor(s?: number | null) {
  if (s == null) return 'text-gray-400 dark:text-gray-500'
  if (s >= 8) return 'text-red-600 dark:text-red-400'
  if (s >= 6) return 'text-yellow-600 dark:text-yellow-500'
  return 'text-gray-500 dark:text-gray-400'
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

// 昨收兜底：stock_realtime.pre_close 在数据同步层偶有 0 值（Tushare 增量回补延迟），
// 此时用 latest_price - change_amount 推算，避免卡片出现 "-"
function resolvePreClose(q: StockQuotePanel): number | null {
  if (q.pre_close != null && q.pre_close > 0) return q.pre_close
  if (q.latest_price != null && q.change_amount != null) return q.latest_price - q.change_amount
  return null
}

// ─────────────────────────────────────────
// 行情卡片
// ─────────────────────────────────────────

function QuotePanel({ q, stock }: { q: StockQuotePanel; stock: StockInfo | null }) {
  const pc = q.pct_change
  const color = priceColor(pc)
  const preClose = resolvePreClose(q)

  const vm = stock?.value_metrics ?? null
  // CIO 复查触发器：time_triggers 取最近一个 expected_date；price_triggers 分上/下方向
  const triggers = stock?.latest_analysis_cio?.followup_triggers
  const nearestTime = triggers?.time_triggers
    ?.filter(t => !!t.expected_date)
    .sort((a, b) => String(a.expected_date).localeCompare(String(b.expected_date)))[0]
  const breakUp = triggers?.price_triggers?.find(t => t.direction === 'break_up' && t.price != null)
  const breakDown = triggers?.price_triggers?.find(t => t.direction === 'break_down' && t.price != null)
  const followupPriceDisplay = breakUp || breakDown
    ? [
        breakUp ? `▲ ${breakUp.price?.toFixed(2)}` : null,
        breakDown ? `▼ ${breakDown.price?.toFixed(2)}` : null,
      ].filter(Boolean).join(' / ')
    : '-'

  const items: { label: string; value: string; color?: string; title?: string }[] = [
    { label: '最新价',   value: fmt(q.latest_price), color },
    { label: '涨跌幅',   value: pc != null ? `${pc > 0 ? '+' : ''}${pc.toFixed(2)}%` : '-', color },
    { label: '涨跌额',   value: fmt(q.change_amount), color },
    { label: '今开',     value: fmt(q.open) },
    { label: '最高',     value: fmt(q.high) },
    { label: '最低',     value: fmt(q.low) },
    { label: '昨收',     value: fmt(preClose) },
    { label: '振幅',     value: fmt(q.amplitude, 2, '%') },
    { label: '成交量',   value: fmtVol(q.volume) },
    { label: '成交额',   value: fmtAmt(q.amount) },
    { label: '换手率',   value: fmt(q.turnover_rate ?? q.turnover, 2, '%') },
    { label: '量比',     value: fmt(q.volume_ratio) },
    { label: '市盈率(静)', value: fmt(q.pe) },
    { label: '市盈率(TTM)', value: fmt(q.pe_ttm) },
    { label: '市净率',   value: fmt(q.pb) },
    { label: '市销率(TTM)', value: fmt(q.ps_ttm) },
    { label: '股息率',   value: fmt(q.dv_ttm ?? q.dv_ratio, 2, '%') },
    { label: '总市值',   value: fmtMv(q.total_mv) },
    { label: '流通市值', value: fmtMv(q.circ_mv) },
    { label: '总股本',   value: fmtShare(q.total_share) },
    { label: '流通股本', value: fmtShare(q.float_share) },
    {
      label: 'ROC',
      value: fmtPct(vm?.roc),
      color: valueMetricColor(vm?.roc),
      title: '资本收益率 ROC = EBIT / (净营运资本 + 净固定资产)',
    },
    {
      label: '收益率',
      value: fmtPct(vm?.earnings_yield),
      color: valueMetricColor(vm?.earnings_yield),
      title: '收益率 EY = EBIT / EV',
    },
    {
      label: '安全边际',
      value: fmtPct(vm?.intrinsic_margin, 0),
      color: valueMetricColor(vm?.intrinsic_margin),
      title: vm?.intrinsic_value != null
        ? `格雷厄姆内在价值 ${vm.intrinsic_value.toFixed(2)} 元（g=${((vm.g_rate ?? 0) * 100).toFixed(1)}%）`
        : '格雷厄姆内在价值数据不足',
    },
    {
      label: '关注时间',
      value: nearestTime?.expected_date ? `⏱ ${nearestTime.expected_date}` : '-',
      title: nearestTime?.reason ?? '',
    },
    {
      label: '关注价格',
      value: followupPriceDisplay,
      title: [breakUp?.price_basis, breakDown?.price_basis].filter(Boolean).join(' / '),
    },
  ]

  // 四专家评分独立成行（游资 / 中线 / 价值 / CIO）
  const scoreRow: { label: string; score?: number | null }[] = [
    { label: '游资评分', score: stock?.latest_analysis_hot_money?.score },
    { label: '中线评分', score: stock?.latest_analysis_midline?.score },
    { label: '价值评分', score: stock?.latest_analysis_longterm?.score },
    { label: 'CIO评分',  score: stock?.latest_analysis_cio?.score },
  ]

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-7 gap-x-4 gap-y-3">
        {items.map(({ label, value, color: c, title }) => (
          <div key={label} title={title || undefined}>
            <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
            <p className={`text-sm font-semibold tabular-nums ${c ?? 'text-gray-900 dark:text-white'}`}>{value}</p>
          </div>
        ))}
        {q.daily_date && (
          <div className="col-span-full mt-1">
            <p className="text-xs text-gray-400 dark:text-gray-600">估值数据日期：{q.daily_date}</p>
          </div>
        )}
      </div>
      <div className="grid grid-cols-4 gap-x-4 gap-y-3 pt-3 border-t border-gray-100 dark:border-gray-800">
        {scoreRow.map(({ label, score }) => (
          <div key={label}>
            <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
            <p className={`text-sm font-semibold tabular-nums ${scoreColor(score)}`}>{fmtScore(score)}</p>
          </div>
        ))}
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
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            {stockInfo?.name}（{stockInfo?.code}）
          </h1>
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
          <CardTitle className="text-base">行情数据</CardTitle>
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
