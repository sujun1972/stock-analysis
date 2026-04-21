'use client'

import { useEffect, useMemo, useState } from 'react'
import { PageHeader } from '@/components/common/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { DataTable, Column } from '@/components/common/DataTable'
import { DatePicker } from '@/components/ui/date-picker'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { BulkOpsButtons } from '@/components/common/BulkOpsButtons'
import { useDataPage } from '@/hooks/useDataPage'
import {
  macroIndicatorsApi,
  MACRO_INDICATOR_LABELS,
  type MacroIndicatorItem,
  type MacroIndicatorListResponse,
  type MacroSnapshotResponse,
  type MacroSnapshotLatest,
} from '@/lib/api'
import { toDateStr } from '@/lib/date-utils'
import { ListFilter, RefreshCw, Calendar, BarChart3, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'

const INDICATOR_OPTIONS = Object.entries(MACRO_INDICATOR_LABELS).map(([code, meta]) => ({
  code, ...meta,
}))

const DEFAULT_CHART_INDICATOR = 'cpi_yoy'

// 快照卡片只展示 7 个宏观核心指标（Shibor 3 档放列表，保证卡片区不拥挤）
const SNAPSHOT_KEYS = ['cpi_yoy', 'ppi_yoy', 'pmi_manu', 'pmi_nonmanu', 'm2_yoy', 'new_credit_month', 'gdp_yoy']


function formatNum(v: number | null | undefined, digits: number = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: digits, maximumFractionDigits: digits })
}


function formatSigned(v: number | null | undefined, unit: string, digits: number = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—'
  const sign = v > 0 ? '+' : ''
  return `${sign}${Number(v).toFixed(digits)}${unit}`
}


export default function MacroIndicatorsPage() {
  const [indicatorCode, setIndicatorCode] = useState<string>('ALL')
  const [startDate, setStartDate] = useState<Date | undefined>(undefined)
  const [endDate, setEndDate] = useState<Date | undefined>(undefined)

  // 快照 + 序列图
  const [snapshot, setSnapshot] = useState<MacroSnapshotResponse | null>(null)
  const [snapshotLoading, setSnapshotLoading] = useState(false)
  const [chartIndicator, setChartIndicator] = useState<string>(DEFAULT_CHART_INDICATOR)
  const [chartLookback, setChartLookback] = useState<12 | 24 | 36>(24)

  const dp = useDataPage<MacroIndicatorItem, MacroIndicatorListResponse>({
    apiCall: (params) => macroIndicatorsApi.getData(params),
    syncFn: () => macroIndicatorsApi.syncAsync(),
    taskName: 'tasks.sync_macro_indicators',
    bulkOps: {
      tableKey: 'macro_indicators',
      syncFn: (p) => macroIndicatorsApi.syncFullHistory(p),
      taskName: 'tasks.sync_macro_indicators_full_history',
    },
    paginationMode: 'page',
    pageSize: 50,
    buildParams: () => {
      const p: Record<string, unknown> = {}
      if (indicatorCode !== 'ALL') p.indicator_code = indicatorCode
      if (startDate) p.start_date = toDateStr(startDate)
      if (endDate) p.end_date = toDateStr(endDate)
      return p
    },
    syncSuccessMessage: '宏观经济指标增量同步完成',
  })

  // 加载快照（首次 + 每次同步完成后）
  const loadSnapshot = async () => {
    setSnapshotLoading(true)
    try {
      const res = await macroIndicatorsApi.getSnapshot(chartLookback)
      setSnapshot(res.data || null)
    } catch {
      setSnapshot(null)
    } finally {
      setSnapshotLoading(false)
    }
  }

  useEffect(() => {
    loadSnapshot()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chartLookback])

  // 图表数据（单指标时序，period_date 正序）
  const chartData = useMemo(() => {
    if (!snapshot?.series) return []
    const series = snapshot.series[chartIndicator] || []
    return [...series]
      .reverse() // 后端降序，前端正序展示
      .map((it) => ({
        date: it.period_date,
        value: it.value ?? null,
        yoy: it.yoy ?? null,
      }))
  }, [snapshot, chartIndicator])

  const chartUnit = MACRO_INDICATOR_LABELS[chartIndicator]?.unit || ''
  const chartLabel = MACRO_INDICATOR_LABELS[chartIndicator]?.label || chartIndicator

  const columns: Column<MacroIndicatorItem>[] = [
    {
      key: 'indicator_code',
      header: '指标',
      accessor: (row) => {
        const meta = MACRO_INDICATOR_LABELS[row.indicator_code]
        return (
          <div>
            <div className="font-medium">{meta?.label || row.indicator_code}</div>
            <div className="text-xs text-gray-500">{row.indicator_code}</div>
          </div>
        )
      },
      width: 160,
      cellClassName: 'whitespace-nowrap',
    },
    {
      key: 'period_date',
      header: '报告期',
      accessor: (row) => row.period_date,
      width: 110,
      cellClassName: 'whitespace-nowrap text-center',
    },
    {
      key: 'value',
      header: '数值',
      accessor: (row) => {
        const unit = MACRO_INDICATOR_LABELS[row.indicator_code]?.unit || ''
        return <span className="tabular-nums">{formatNum(row.value)} {unit}</span>
      },
      width: 120,
      cellClassName: 'text-right whitespace-nowrap',
    },
    {
      key: 'yoy',
      header: '同比',
      accessor: (row) => {
        if (row.yoy === null || row.yoy === undefined) return <span className="text-gray-400">—</span>
        const cls = row.yoy > 0 ? 'text-red-600' : row.yoy < 0 ? 'text-green-600' : 'text-gray-500'
        return <span className={`tabular-nums ${cls}`}>{formatSigned(row.yoy, '%')}</span>
      },
      width: 100,
      cellClassName: 'text-right whitespace-nowrap',
    },
    {
      key: 'mom',
      header: '环比',
      accessor: (row) => {
        if (row.mom === null || row.mom === undefined) return <span className="text-gray-400">—</span>
        const cls = row.mom > 0 ? 'text-red-600' : row.mom < 0 ? 'text-green-600' : 'text-gray-500'
        return <span className={`tabular-nums ${cls}`}>{formatSigned(row.mom, '%')}</span>
      },
      width: 100,
      cellClassName: 'text-right whitespace-nowrap',
    },
    {
      key: 'publish_date',
      header: '披露日',
      accessor: (row) => row.publish_date || '—',
      width: 110,
      cellClassName: 'whitespace-nowrap text-center text-gray-500',
    },
    {
      key: 'source',
      header: '来源',
      accessor: (row) => row.source,
      width: 90,
      cellClassName: 'whitespace-nowrap text-center text-xs text-gray-500',
    },
  ]

  const mobileCard = (item: MacroIndicatorItem) => {
    const meta = MACRO_INDICATOR_LABELS[item.indicator_code]
    const unit = meta?.unit || ''
    return (
      <div className="space-y-2">
        <div className="flex justify-between items-start pb-2 border-b">
          <div>
            <div className="font-medium">{meta?.label || item.indicator_code}</div>
            <div className="text-xs text-gray-500">{item.indicator_code}</div>
          </div>
          <span className="text-xs text-gray-500 whitespace-nowrap">{item.period_date}</span>
        </div>
        <div className="flex justify-between text-sm">
          <div>数值：<span className="font-medium">{formatNum(item.value)} {unit}</span></div>
          {item.yoy !== null && item.yoy !== undefined && (
            <div>同比：<span className="tabular-nums">{formatSigned(item.yoy, '%')}</span></div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="宏观经济指标"
        description="CPI / PPI / PMI / M2 / 社融 / GDP / Shibor 等量化宏观指标，供宏观风险专家和 CIO 引用"
        details={
          <>
            <div>数据源：AkShare 免费宏观接口（macro_china_cpi_monthly / macro_china_pmi 等 7 个接口 → 10 个 indicator_code）</div>
            <div className="text-xs text-gray-500 mt-1">接口无日期参数，每次拉完整历史序列并 UPSERT；同比/环比来自 AkShare 原始字段</div>
          </>
        }
        actions={
          <div className="flex gap-2">
            <Button onClick={() => dp.handleSyncDirect({})} disabled={dp.syncing}>
              {dp.syncing ? (
                <><RefreshCw className="h-4 w-4 mr-1 animate-spin" />同步中...</>
              ) : (
                <><RefreshCw className="h-4 w-4 mr-1" />增量同步</>
              )}
            </Button>
            <BulkOpsButtons
              onFullSync={dp.handleFullSync}
              onClearConfirm={dp.handleClear}
              isClearDialogOpen={dp.isClearDialogOpen}
              setIsClearDialogOpen={dp.setIsClearDialogOpen}
              fullSyncing={dp.fullSyncing}
              isClearing={dp.isClearing}
              earliestHistoryDate={dp.earliestHistoryDate}
              tableName="宏观经济指标"
            />
          </div>
        }
      />

      {/* 快照卡片：7 个核心指标最新值 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BarChart3 className="h-5 w-5" /> 最新快照
            {snapshotLoading && <RefreshCw className="h-4 w-4 animate-spin text-gray-400" />}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-7 gap-3">
            {SNAPSHOT_KEYS.map((code) => {
              const latest: MacroSnapshotLatest | undefined = snapshot?.latest?.[code]
              const meta = MACRO_INDICATOR_LABELS[code]
              if (!meta) return null
              const val = latest?.value
              const yoy = latest?.yoy
              const TrendIcon = yoy == null ? Minus : yoy > 0 ? TrendingUp : yoy < 0 ? TrendingDown : Minus
              const trendCls = yoy == null ? 'text-gray-400'
                : yoy > 0 ? 'text-red-600' : yoy < 0 ? 'text-green-600' : 'text-gray-500'
              return (
                <div key={code} className="border rounded-lg p-3 hover:border-blue-300 transition-colors">
                  <div className="text-xs text-gray-500 truncate" title={meta.desc}>{meta.label}</div>
                  <div className="mt-1 flex items-baseline gap-1">
                    <span className="text-xl font-semibold tabular-nums">{formatNum(val)}</span>
                    <span className="text-xs text-gray-400">{meta.unit}</span>
                  </div>
                  <div className={`mt-1 flex items-center gap-1 text-xs ${trendCls}`}>
                    <TrendIcon className="h-3 w-3" />
                    <span className="tabular-nums">同比 {formatSigned(yoy, '%')}</span>
                  </div>
                  <div className="mt-1 text-xs text-gray-400">
                    报告期 {latest?.period_date || '—'}
                    {latest?.lag_days != null && <span className="ml-1">(滞后 {latest.lag_days} 天)</span>}
                  </div>
                </div>
              )
            })}
          </div>
          {!snapshot && !snapshotLoading && (
            <div className="text-center text-gray-500 py-8 text-sm">
              暂无数据。请先执行"增量同步"拉取 AkShare 宏观指标。
            </div>
          )}
        </CardContent>
      </Card>

      {/* 时序图：单指标折线 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5" /> 时间序列
            </div>
            <div className="flex items-center gap-2">
              <Select value={chartIndicator} onValueChange={setChartIndicator}>
                <SelectTrigger className="w-44 h-8"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {INDICATOR_OPTIONS.map((opt) => (
                    <SelectItem key={opt.code} value={opt.code}>
                      {opt.label}（{opt.code}）
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={String(chartLookback)} onValueChange={(v) => setChartLookback(Number(v) as 12 | 24 | 36)}>
                <SelectTrigger className="w-28 h-8"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="12">近 12 期</SelectItem>
                  <SelectItem value="24">近 24 期</SelectItem>
                  <SelectItem value="36">近 36 期</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {chartData.length === 0 ? (
            <div className="text-center text-gray-500 py-12 text-sm">
              {snapshotLoading ? '加载中...' : `${chartLabel} 暂无数据`}
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={340}>
              <LineChart data={chartData} margin={{ top: 10, right: 30, left: 10, bottom: 30 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  angle={-40}
                  textAnchor="end"
                  height={60}
                />
                <YAxis
                  tick={{ fontSize: 11 }}
                  label={{ value: chartUnit, angle: -90, position: 'insideLeft', fontSize: 12 }}
                  domain={['auto', 'auto']}
                />
                <Tooltip
                  formatter={(v) => [`${Number(v).toFixed(2)} ${chartUnit}`, chartLabel] as [string, string]}
                  labelFormatter={(l) => `报告期：${l}`}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  name={chartLabel}
                  stroke="#2563eb"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>

      {/* 数据查询 + 列表 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ListFilter className="h-5 w-5" /> 数据查询
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 items-end">
            <div>
              <label className="text-sm font-medium mb-1 block">指标</label>
              <Select value={indicatorCode} onValueChange={setIndicatorCode}>
                <SelectTrigger><SelectValue placeholder="全部" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="ALL">全部指标</SelectItem>
                  {INDICATOR_OPTIONS.map((opt) => (
                    <SelectItem key={opt.code} value={opt.code}>
                      {opt.label}（{opt.code}）
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm font-medium mb-1 flex items-center gap-1">
                <Calendar className="h-3.5 w-3.5" /> 报告期起
              </label>
              <DatePicker date={startDate} onDateChange={setStartDate} />
            </div>
            <div>
              <label className="text-sm font-medium mb-1 block">报告期止</label>
              <DatePicker date={endDate} onDateChange={setEndDate} />
            </div>
            <div>
              <Button onClick={() => dp.handleQuery()} className="w-full">查询</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            数据列表
            <span className="ml-2 text-sm font-normal text-gray-500">共 {dp.total} 条</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={columns}
            data={dp.data}
            loading={dp.isLoading}
            pagination={{
              page: dp.page,
              pageSize: dp.pageSize,
              total: dp.total,
              onPageChange: dp.handlePageChange,
            }}
            sort={{
              key: dp.sortKey,
              direction: dp.sortDirection,
              onSort: dp.handleSort,
            }}
            mobileCard={mobileCard}
          />
        </CardContent>
      </Card>
    </div>
  )
}
