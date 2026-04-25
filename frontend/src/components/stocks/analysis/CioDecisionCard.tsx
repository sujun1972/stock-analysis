'use client'

import React, { useState } from 'react'
import { Brain, ChevronDown, ChevronUp } from 'lucide-react'
import { renderBold } from './text-utils'
import { GenericSection, FollowupTriggersSection } from './sections'
import { safeParseJSON, scoreToneClass, extractScore, extractKeyQuote } from './expert-meta'

export interface CioDecisionCardProps {
  /** 最新一条 cio_directive 的 analysis_text；null 显示空态 */
  analysisText: string | null
  /** 默认是否展开（雷达图点击 CIO 节点时主页可设为 true） */
  defaultOpen?: boolean
  /** 唯一的"展开"绑定锚点 id，配合外部 scrollIntoView 使用 */
  id?: string
}

/**
 * CIO 综合决策详情卡（卡 ③）
 * 默认折叠：仅显示头部（评分 + 行动指令）；展开后显示完整 5 个 section + 复查触发器。
 *
 * 与弹窗内 CIO Tab 的差异：
 * - 多维度扫描三栏并排（弹窗里堆叠）
 * - core_drivers / core_risks 双栏对照（弹窗里上下堆叠）
 * - rating_and_action 高亮卡（按 action 关键词配色）
 */
export function CioDecisionCard({ analysisText, defaultOpen = false, id }: CioDecisionCardProps) {
  const [open, setOpen] = useState(defaultOpen)
  const parsed = safeParseJSON(analysisText)

  if (!parsed) {
    return (
      <section id={id} className="rounded-lg border border-gray-200 dark:border-gray-700 bg-card p-5">
        <header className="flex items-center gap-2">
          <Brain className="h-5 w-5 text-expert-cio" aria-hidden />
          <h2 className="text-base font-semibold">CIO 综合决策</h2>
          <span className="ml-2 text-xs text-gray-500 dark:text-gray-400">尚未生成</span>
        </header>
      </section>
    )
  }

  const score = extractScore(parsed)
  const keyQuote = extractKeyQuote(parsed)
  const ra = parsed.rating_and_action as Record<string, any> | undefined
  const md = parsed.multi_dimension_scan as Record<string, any> | undefined
  const cd = parsed.cross_dimension_analysis as Record<string, any> | undefined
  const drivers = parsed.core_drivers
  const risks = parsed.core_risks
  const triggers = parsed.followup_triggers as Record<string, any> | undefined

  return (
    <section
      id={id}
      className="rounded-lg border border-gray-200 dark:border-gray-700 bg-card overflow-hidden"
    >
      {/* 折叠头：始终可见 */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-3 px-5 py-3 hover:bg-gray-50 dark:hover:bg-gray-800/40 transition-colors duration-fast text-left focus-ring"
        aria-expanded={open}
        aria-controls={id ? `${id}-body` : undefined}
      >
        <Brain className="h-5 w-5 text-expert-cio shrink-0" aria-hidden />
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2 flex-wrap">
            <h2 className="text-base font-semibold">CIO 综合决策</h2>
            {score != null && (
              <span className={`text-base font-bold tabular-nums ${scoreToneClass(score)}`}>
                {Number.isInteger(score) ? score.toFixed(1) : score}
              </span>
            )}
            {ra?.rating && (
              <span className="text-sm text-gray-700 dark:text-gray-300">{String(ra.rating)}</span>
            )}
          </div>
          {keyQuote && !open && (
            <p className="text-xs text-gray-600 dark:text-gray-400 mt-0.5 line-clamp-1" title={keyQuote}>
              "{keyQuote}"
            </p>
          )}
        </div>
        {open ? <ChevronUp className="h-4 w-4 text-gray-400" aria-hidden /> : <ChevronDown className="h-4 w-4 text-gray-400" aria-hidden />}
      </button>

      {/* 展开正文 */}
      {open && (
        <div id={id ? `${id}-body` : undefined} className="border-t border-gray-100 dark:border-gray-800 p-5 space-y-5">
          {/* key_quote 高亮（展开后改为完整文案） */}
          {keyQuote && (
            <p className="px-3 py-2 rounded bg-expert-cio/10 dark:bg-expert-cio/20 text-sm font-medium text-expert-cio dark:text-expert-cio">
              {renderBold(keyQuote)}
            </p>
          )}

          {/* 多维度快速扫描：三栏 */}
          {md && (
            <MultiDimensionScan data={md} />
          )}

          {/* 跨维度共振/矛盾 */}
          {cd && Object.keys(cd).length > 0 && (
            <GenericSection
              title="跨维度共振/矛盾"
              data={cd}
              labels={{
                consensus_or_conflict: '方向一致性',
                conflict_essence: '矛盾本质',
                cio_resolution: 'CIO 取舍',
              }}
            />
          )}

          {/* 核心驱动 / 核心风险：双栏对照 */}
          <DriversRisksGrid drivers={drivers} risks={risks} />

          {/* 综合评级与行动指令：高亮卡 */}
          {ra && <RatingActionCard data={ra} />}

          {/* 复查触发器 */}
          {triggers && <FollowupTriggersSection triggers={triggers} />}
        </div>
      )}
    </section>
  )
}

/** 三栏并排展示短/中/长线扫描结果 */
function MultiDimensionScan({ data }: { data: Record<string, any> }) {
  const dims: { key: string; title: string }[] = [
    { key: 'short_term', title: '短线（1-5 日）' },
    { key: 'mid_term', title: '中线（1-3 月）' },
    { key: 'long_term', title: '长线（1-3 年）' },
  ]
  return (
    <section>
      <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-2">多维度快速扫描</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {dims.map(({ key, title }) => {
          const v = data[key]
          if (v == null) return null
          if (typeof v === 'string') {
            return (
              <div key={key} className="rounded border border-gray-200 dark:border-gray-700 p-3 bg-background">
                <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1.5">{title}</div>
                <p className="text-sm">{renderBold(v)}</p>
              </div>
            )
          }
          // 对象：list 渲染所有字段
          const entries = Object.entries(v).filter(([, val]) => val != null && val !== '')
          return (
            <div key={key} className="rounded border border-gray-200 dark:border-gray-700 p-3 bg-background">
              <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1.5">{title}</div>
              <ul className="text-xs space-y-1">
                {entries.map(([k, val]) => (
                  <li key={k}>
                    <span className="text-gray-500 dark:text-gray-400">{k.replace(/_/g, ' ')}：</span>
                    <span>{renderBold(String(val ?? '-'))}</span>
                  </li>
                ))}
              </ul>
            </div>
          )
        })}
      </div>
    </section>
  )
}

/** 核心驱动 / 核心风险双栏对照
 *  CIO schema 中 core_drivers / core_risks 是 [{name, description, ...}] 数组，
 *  也兼容字符串数组或换行分隔的单字符串。
 */
function DriversRisksGrid({ drivers, risks }: { drivers: any; risks: any }) {
  type Item = { name?: string; description?: string; raw?: string }
  const toList = (v: any): Item[] => {
    if (Array.isArray(v)) {
      return v.map((x) => {
        if (typeof x === 'string') return { raw: x }
        if (x && typeof x === 'object') {
          const name = x.name ?? x.factor ?? x.title
          const description = x.description ?? x.desc ?? x.reason ?? x.evidence
          if (name || description) return { name, description }
          // 末了兜底：取第一个非空 value 当 raw
          const firstVal = Object.values(x).find((vv) => vv != null && vv !== '')
          return { raw: firstVal != null ? String(firstVal) : '' }
        }
        return { raw: String(x ?? '') }
      }).filter((it) => it.name || it.description || it.raw)
    }
    if (typeof v === 'string' && v.trim()) {
      return v.split('\n').filter((s) => s.trim()).map((raw) => ({ raw }))
    }
    return []
  }
  const dList = toList(drivers)
  const rList = toList(risks)
  if (dList.length === 0 && rList.length === 0) return null

  const renderItem = (item: Item, idx: number, sign: '+' | '−') => {
    const signCls = sign === '+' ? 'text-emerald-500' : 'text-red-400'
    return (
      <li key={idx} className="flex gap-1.5">
        <span className={`shrink-0 ${signCls}`} aria-hidden>{sign}</span>
        <span className="flex-1">
          {item.name && (
            <span className="font-semibold text-gray-900 dark:text-gray-100">
              {renderBold(item.name)}
            </span>
          )}
          {item.name && item.description && <span className="text-gray-500 dark:text-gray-400">：</span>}
          {item.description && (
            <span className="text-gray-700 dark:text-gray-300">{renderBold(item.description)}</span>
          )}
          {item.raw && !item.name && !item.description && (
            <span>{renderBold(item.raw)}</span>
          )}
        </span>
      </li>
    )
  }

  return (
    <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div>
        <h3 className="text-sm font-semibold text-emerald-600 dark:text-emerald-400 mb-1.5 flex items-center gap-1.5">
          <span aria-hidden>▲</span>核心驱动因子
        </h3>
        {dList.length > 0 ? (
          <ul className="space-y-1 pl-1">
            {dList.map((it, i) => renderItem(it, i, '+'))}
          </ul>
        ) : (
          <p className="text-xs text-gray-400 dark:text-gray-500">—</p>
        )}
      </div>
      <div>
        <h3 className="text-sm font-semibold text-red-600 dark:text-red-400 mb-1.5 flex items-center gap-1.5">
          <span aria-hidden>▼</span>核心风险因子
        </h3>
        {rList.length > 0 ? (
          <ul className="space-y-1 pl-1">
            {rList.map((it, i) => renderItem(it, i, '−'))}
          </ul>
        ) : (
          <p className="text-xs text-gray-400 dark:text-gray-500">—</p>
        )}
      </div>
    </section>
  )
}

/** 综合评级与行动指令：单独 highlight 卡，按 action 关键词配色 */
function RatingActionCard({ data }: { data: Record<string, any> }) {
  const action = String(data.action ?? '')
  // 按 action 关键词配色（这是允许借涨跌色的位置——它本质就是"建议是否多头"）
  const tone = /加仓|买入|看多|建仓|逢低/i.test(action)
    ? 'positive'
    : /减仓|禁飞|看空|卖出|清仓|警惕/i.test(action)
    ? 'negative'
    : 'neutral'
  const toneCls = tone === 'positive'
    ? 'border-positive/40 bg-positive-soft text-positive'
    : tone === 'negative'
    ? 'border-negative/40 bg-negative-soft text-negative'
    : 'border-gray-200 dark:border-gray-700 bg-muted text-foreground'

  return (
    <section>
      <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-2">综合评级与行动指令</h3>
      <div className={`rounded-lg border p-4 ${toneCls}`}>
        <div className="flex flex-wrap items-baseline gap-3 mb-1">
          {data.rating && <span className="text-base font-bold">{String(data.rating)}</span>}
          {data.action && <span className="text-sm font-medium">{String(data.action)}</span>}
        </div>
        {data.price_reference && (
          <div className="text-xs mt-2 opacity-90">
            <span className="font-semibold">价位区间参考：</span>
            <span className="tabular-nums">{String(data.price_reference)}</span>
          </div>
        )}
        {data.rating_logic && (
          <p className="text-xs mt-2 opacity-90 leading-relaxed">
            {renderBold(String(data.rating_logic))}
          </p>
        )}
      </div>
    </section>
  )
}
