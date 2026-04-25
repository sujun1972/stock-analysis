'use client'

import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { StockInfo, StockQuotePanel } from '@/types'

// ─────────────────────────────────────────
// 估值数据卡 —— 从行情卡拆出，聚合所有"估值类"指标
// 包括：① 公开估值（PE/PB/PS/股息率，daily_basic 来源）
//       ② 价值度量（ROC/EY/安全边际，魔法公式 + 格雷厄姆 IV，stock_value_metrics 来源）
// 规模（市值/股本）属于"公司体量"，留在行情卡。
// ─────────────────────────────────────────

function fmt(v: number | null | undefined, decimals = 2, suffix = '') {
  if (v === null || v === undefined) return '-'
  return v.toFixed(decimals) + suffix
}

function fmtPct(v?: number | null, decimals = 1) {
  if (v == null || !isFinite(v)) return '-'
  return (v * 100).toFixed(decimals) + '%'
}

/** 估值快照日期 "20260424" → "2026-04-24" */
function fmtDailyDate(s?: string | null): string {
  if (!s) return '-'
  if (/^\d{8}$/.test(s)) return `${s.slice(0, 4)}-${s.slice(4, 6)}-${s.slice(6, 8)}`
  return s
}

/**
 * 价值度量色阶（ROC / EY / 安全边际）
 * 用 score-* 蓝→金→紫色阶，避免与行情红绿混淆。负值统一 muted（不借用行情绿）。
 * 各指标语境不同，调用方传 [mid, high] 阈值（小数：0.15 = 15%）。
 */
function valueScaleColor(v: number | null | undefined, mid: number, high: number) {
  if (v == null || !isFinite(v)) return ''
  if (v < 0) return 'text-muted-foreground'
  if (v >= high) return 'text-score-high'
  if (v >= mid) return 'text-score-mid'
  return 'text-score-low'
}

interface MetricItem {
  label: string
  value: string
  /** 数值文本的色阶 class（仅价值度量行用；公开估值不染色） */
  color?: string
  /** hover 显示完整解释 */
  title?: string
}

/** 一行：组名 + 多个 chip，单元格"标签：值"垂直对齐；与行情卡 ChipGroup 视觉同源但单独维护，避免跨文件耦合 */
function MetricRow({ title, items }: { title: string; items: MetricItem[] }) {
  const visible = items.filter((it) => it.value && it.value !== '-')
  if (visible.length === 0) return null
  return (
    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1.5">
      <span className="text-xs text-gray-400 dark:text-gray-500 shrink-0 min-w-[36px]">{title}</span>
      {visible.map((it, i) => (
        <span key={it.label} className="inline-flex items-baseline gap-1 text-xs" title={it.title || undefined}>
          <span className="text-gray-500 dark:text-gray-400">{it.label}</span>
          <span className={`font-semibold tabular-nums ${it.color ?? 'text-gray-900 dark:text-white'}`}>
            {it.value}
          </span>
          {i < visible.length - 1 && <span className="ml-1 text-gray-300 dark:text-gray-700">│</span>}
        </span>
      ))}
    </div>
  )
}

export interface ValuationCardProps {
  q: StockQuotePanel
  stock: StockInfo | null
}

/**
 * 估值数据卡。
 * - "估值"（PE/PB/PS/股息率）：daily_basic 表，每日收盘后更新
 * - "价值"（ROC/EY/安全边际）：stock_value_metrics 表，由 ValueMetricsService 每 5 分钟合批 + 每日 16:30 兜底
 * 头部右侧显示快照日期（priority: daily_date 优先，否则不显示）
 */
export function ValuationCard({ q, stock }: ValuationCardProps) {
  const vm = stock?.value_metrics ?? null

  const valuationItems: MetricItem[] = [
    { label: 'PE(TTM)', value: fmt(q.pe_ttm), title: '滚动市盈率（最近 4 个季度）' },
    { label: 'PE',      value: fmt(q.pe),     title: '静态市盈率' },
    { label: 'PB',      value: fmt(q.pb),     title: '市净率' },
    { label: 'PS(TTM)', value: fmt(q.ps_ttm), title: '滚动市销率' },
    { label: '股息率',  value: fmt(q.dv_ttm ?? q.dv_ratio, 2, '%'), title: '股息率 TTM' },
  ]

  const valueItems: MetricItem[] = [
    {
      label: 'ROC',
      value: fmtPct(vm?.roc),
      color: valueScaleColor(vm?.roc, 0.15, 0.30),
      title: '资本收益率 ROC = EBIT / (净营运资本 + 净固定资产)；≥30% 优秀，≥15% 良好',
    },
    {
      label: '收益率',
      value: fmtPct(vm?.earnings_yield),
      color: valueScaleColor(vm?.earnings_yield, 0.10, 0.20),
      title: '收益率 EY = EBIT / EV（企业价值收益率）；≥20% 显著低估，≥10% 偏低',
    },
    {
      label: '安全边际',
      value: fmtPct(vm?.intrinsic_margin, 0),
      color: valueScaleColor(vm?.intrinsic_margin, 0.30, 1.00),
      title:
        vm?.intrinsic_value != null
          ? `格雷厄姆内在价值 ${vm.intrinsic_value.toFixed(2)} 元（g=${((vm.g_rate ?? 0) * 100).toFixed(1)}% · 来源:${vm.g_source ?? 'na'}）`
          : '格雷厄姆内在价值数据不足（缺 EPS 或增长率推算依据）',
    },
  ]

  // 全部为空时降级显示提示文案；保留卡壳不破坏页面节奏
  const hasAny =
    valuationItems.some((it) => it.value && it.value !== '-') ||
    valueItems.some((it) => it.value && it.value !== '-')

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-base">估值数据</CardTitle>
          {q.daily_date && (
            <span
              className="text-[11px] text-gray-400 dark:text-gray-600 tabular-nums"
              title="daily_basic 表的快照日期（每日收盘后更新；PE/PB/股息率以此日为准）"
            >
              快照 · {fmtDailyDate(q.daily_date)}
            </span>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {hasAny ? (
          <div className="space-y-2">
            <MetricRow title="估值" items={valuationItems} />
            <MetricRow title="价值" items={valueItems} />
          </div>
        ) : (
          <p className="text-sm text-gray-500 dark:text-gray-400">暂无估值数据</p>
        )}
      </CardContent>
    </Card>
  )
}
