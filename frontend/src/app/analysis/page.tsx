'use client'

import { useEffect, useState, Suspense, useMemo, useRef } from 'react'
import dynamic from 'next/dynamic'
import { useSearchParams } from 'next/navigation'
import { apiClient } from '@/lib/api-client'
import type { StockInfo, StockQuotePanel } from '@/types'
import * as echarts from 'echarts'
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

/** 涨跌颜色 */
function priceColor(pct?: number | null) {
  if (pct === null || pct === undefined) return 'text-gray-900 dark:text-white'
  if (pct > 0) return 'text-red-600 dark:text-red-400'
  if (pct < 0) return 'text-green-600 dark:text-green-400'
  return 'text-gray-900 dark:text-white'
}

// ─────────────────────────────────────────
// 行情卡片
// ─────────────────────────────────────────

function QuotePanel({ q }: { q: StockQuotePanel }) {
  const pc = q.pct_change
  const color = priceColor(pc)

  const items: { label: string; value: string; color?: string }[] = [
    { label: '最新价',   value: fmt(q.latest_price), color },
    { label: '涨跌幅',   value: pc != null ? `${pc > 0 ? '+' : ''}${pc.toFixed(2)}%` : '-', color },
    { label: '涨跌额',   value: fmt(q.change_amount), color },
    { label: '今开',     value: fmt(q.open) },
    { label: '最高',     value: fmt(q.high) },
    { label: '最低',     value: fmt(q.low) },
    { label: '昨收',     value: fmt(q.pre_close) },
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
  ]

  return (
    <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-7 gap-x-4 gap-y-3">
      {items.map(({ label, value, color: c }) => (
        <div key={label}>
          <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
          <p className={`text-sm font-semibold ${c ?? 'text-gray-900 dark:text-white'}`}>{value}</p>
        </div>
      ))}
      {q.daily_date && (
        <div className="col-span-full mt-1">
          <p className="text-xs text-gray-400 dark:text-gray-600">估值数据日期：{q.daily_date}</p>
        </div>
      )}
    </div>
  )
}

// ─────────────────────────────────────────
// 筹码分布图
// ─────────────────────────────────────────

interface ChipItem { price: number; percent: number; trade_date?: string }

function ChipsDistributionCard({ tsCode, latestPrice }: { tsCode: string; latestPrice?: number | null }) {
  const chartRef = useRef<HTMLDivElement>(null)
  const chartInstance = useRef<echarts.ECharts | null>(null)
  const [dataDate, setDataDate] = useState<string | null>(null)
  // null = 加载中，[] = 已加载但无数据，有元素 = 正常数据
  const [chips, setChips] = useState<ChipItem[] | null>(null)
  const [loading, setLoading] = useState(true)

  // 获取筹码数据（后端会自动同步缺失/过期数据）
  useEffect(() => {
    if (!tsCode) return
    let cancelled = false
    setLoading(true)
    setChips(null)
    apiClient.getChipsDistribution(tsCode).then((items) => {
      if (cancelled) return
      setLoading(false)
      if (items && items.length > 0 && items[0].trade_date) {
        setDataDate(items[0].trade_date)
      }
      setChips(items ?? [])
    })
    return () => { cancelled = true }
  }, [tsCode])

  // chips state 变化后渲染图表；此时 React 已将容器高度写入 DOM，
  // 再用 requestAnimationFrame 延一帧确保浏览器完成布局，ECharts 可读到正确尺寸
  useEffect(() => {
    if (!chips || chips.length === 0 || !chartRef.current) return

    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current)
    }
    const chart = chartInstance.current

    const sorted = [...chips].sort((a, b) => a.price - b.price)
    const prices = sorted.map(d => d.price)
    const percents = sorted.map(d => d.percent)

    // 按盈亏分区着色：绿色=盈利，红色=亏损，黄色=当前价附近（±1%）
    const barColors = prices.map(p => {
      if (latestPrice == null) return '#60a5fa'
      if (p < latestPrice * 0.99) return '#22c55e'
      if (p > latestPrice * 1.01) return '#ef4444'
      return '#facc15'
    })

    // 当前价标注线（定位到最接近的价格档位）
    const markLineData = latestPrice != null ? (() => {
      const closestIdx = prices.reduce((best, p, i) =>
        Math.abs(p - latestPrice) < Math.abs(prices[best] - latestPrice) ? i : best, 0)
      return [{
        yAxis: closestIdx,
        lineStyle: { color: '#f59e0b', width: 1.5, type: 'dashed' as const },
        label: { show: true, formatter: `现价 ${latestPrice.toFixed(2)}`, color: '#f59e0b', fontSize: 10 },
      }]
    })() : []

    requestAnimationFrame(() => {
      chart.setOption({
        backgroundColor: 'transparent',
        grid: { top: 8, bottom: 40, left: 60, right: 16 },
        tooltip: {
          trigger: 'axis',
          axisPointer: { type: 'shadow' },
          formatter: (params: { dataIndex: number }[]) => {
            const idx = params[0].dataIndex
            return `价格：${prices[idx].toFixed(2)}<br/>占比：${percents[idx].toFixed(2)}%`
          },
        },
        xAxis: {
          type: 'value',
          name: '占比(%)',
          nameLocation: 'end',
          nameTextStyle: { color: '#9ca3af', fontSize: 11 },
          axisLabel: { color: '#9ca3af', fontSize: 11, formatter: (v: number) => v + '%' },
          axisLine: { lineStyle: { color: '#374151' } },
          splitLine: { lineStyle: { color: '#1f2937', type: 'dashed' } },
        },
        yAxis: {
          type: 'category',
          data: prices.map(p => p.toFixed(2)),
          axisLabel: { color: '#9ca3af', fontSize: 10 },
          axisLine: { lineStyle: { color: '#374151' } },
          splitLine: { show: false },
        },
        series: [{
          type: 'bar',
          data: percents.map((v, i) => ({ value: v, itemStyle: { color: barColors[i] } })),
          barMaxWidth: 12,
          emphasis: { itemStyle: { opacity: 0.8 } },
          markLine: { silent: true, symbol: 'none', data: markLineData },
        }],
      })
      chart.resize()
    })
  }, [chips, latestPrice])

  // 响应窗口大小变化；组件卸载时销毁图表实例
  useEffect(() => {
    const handleResize = () => chartInstance.current?.resize()
    window.addEventListener('resize', handleResize)
    return () => {
      window.removeEventListener('resize', handleResize)
      chartInstance.current?.dispose()
      chartInstance.current = null
    }
  }, [])

  const isEmpty = !loading && chips !== null && chips.length === 0

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center justify-between">
          <span>筹码分布</span>
          {dataDate && (
            <span className="text-xs font-normal text-gray-400">
              数据日期：{dataDate.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3')}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        {loading && (
          <div className="flex items-center justify-center h-48 text-sm text-gray-500 dark:text-gray-400">
            加载筹码数据中...
          </div>
        )}
        {isEmpty && (
          <div className="flex items-center justify-center h-48 text-sm text-gray-500 dark:text-gray-400">
            暂无筹码分布数据
          </div>
        )}
        {/*
          容器始终存在于 DOM，通过 height 切换显隐而非条件渲染，
          避免 ECharts 初始化时读到 clientHeight=0 的问题
        */}
        <div
          ref={chartRef}
          style={{ height: !loading && !isEmpty ? 420 : 0, overflow: 'hidden' }}
          className="w-full"
        />
        {!loading && !isEmpty && (
          <div className="mt-2 flex gap-4 text-xs text-gray-500 dark:text-gray-400">
            <span className="flex items-center gap-1"><span className="inline-block w-3 h-3 rounded-sm bg-green-500" />盈利筹码</span>
            <span className="flex items-center gap-1"><span className="inline-block w-3 h-3 rounded-sm bg-red-500" />亏损筹码</span>
            <span className="flex items-center gap-1"><span className="inline-block w-3 h-3 rounded-sm bg-yellow-400" />当前价附近</span>
          </div>
        )}
      </CardContent>
    </Card>
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

  // ── 游资观点弹窗 ──
  const [hotMoneyOpen, setHotMoneyOpen] = useState(false)
  const [hotMoneyContent, setHotMoneyContent] = useState('')
  const [hotMoneyLoading, setHotMoneyLoading] = useState(false)
  const [latestAnalysis, setLatestAnalysis] = useState<{ score: number | null; version: number } | null>(null)

  useEffect(() => {
    setLatestAnalysis(null)
    if (code) {
      loadStockInfo()
    } else {
      setIsLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code])

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
      // 加载最新游资分析摘要（非阻塞，不影响主加载流程）
      const tsCode = stockInfoData?.ts_code || toTsCode(code)
      refreshLatestAnalysis(tsCode)
    } catch (err: any) {
      setError(err.message || '加载股票数据失败')
      console.error('Failed to load stock data:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const refreshLatestAnalysis = (ts: string) => {
    apiClient.getLatestStockAnalysis(ts, 'hot_money_view')
      .then((res) => {
        setLatestAnalysis(res?.code === 200 && res.data
          ? { score: res.data.score, version: res.data.version }
          : null)
      })
      .catch(() => { setLatestAnalysis(null) })
  }

  const openHotMoneyDialog = async () => {
    setHotMoneyContent('')
    setHotMoneyLoading(true)
    setHotMoneyOpen(true)
    try {
      const res = await apiClient.getPromptTemplateByKey(
        'top_speculative_investor_v1',
        { stock_name: stockInfo?.name ?? '', stock_code: code ?? '' }
      )
      if (res?.code === 200 && res.data?.user_prompt_template) {
        const parts = [res.data.system_prompt, res.data.user_prompt_template].filter(Boolean)
        setHotMoneyContent(parts.join('\n\n'))
      }
    } catch {
      setHotMoneyContent('加载失败，请重试')
    } finally {
      setHotMoneyLoading(false)
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
          {latestAnalysis?.score != null && (
            <span className={`text-sm font-semibold px-2 py-0.5 rounded ${
              latestAnalysis.score >= 8 ? 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400'
              : latestAnalysis.score >= 6 ? 'bg-yellow-50 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400'
              : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
            }`}>
              游资 {latestAnalysis.score}
            </span>
          )}
          <button
            onClick={openHotMoneyDialog}
            className="text-xs px-3 py-1.5 rounded border border-yellow-400 text-yellow-600 hover:bg-yellow-50 dark:border-yellow-500 dark:text-yellow-400 dark:hover:bg-yellow-900/20 transition-colors"
          >
            游资观点
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
        onSaved={() => refreshLatestAnalysis(tsCode)}
      />

      {/* 行情卡片 */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">行情数据</CardTitle>
        </CardHeader>
        <CardContent>
          {quotePanel ? (
            <QuotePanel q={quotePanel} />
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

      {/* 筹码分布 */}
      {(basicInfo?.ts_code || stockInfo?.code) && (
        <ChipsDistributionCard
          tsCode={basicInfo?.ts_code || stockInfo!.code}
          latestPrice={quotePanel?.latest_price}
        />
      )}

      {/* 图表区域 */}
      <StockPriceCard
        stockCode={code}
        stockName={stockInfo?.name}
        defaultChartType="daily"
        showHeader={true}
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
