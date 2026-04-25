'use client'

import React from 'react'
import { renderBold } from './text-utils'

/** 评分色块。色阶为 ≥8 红 / ≥6 黄 / 其余灰 — 弹窗历史评分块沿用此红/黄/灰，
 *  与卡②/卡④头部用的 score-* 紫金蓝色阶并存（StructuredAnalysisContent 内的"综合评分"区块走此色阶）。 */
export function ScoreBadge({ score, rating }: { score: number; rating?: string }) {
  const colorCls = score >= 8
    ? 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400'
    : score >= 6
    ? 'bg-yellow-50 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400'
    : 'bg-gray-50 text-gray-600 dark:bg-gray-800 dark:text-gray-300'
  return (
    <span className="flex items-center gap-2 flex-wrap">
      <span className={`font-bold px-2 py-0.5 rounded text-base tabular-nums ${colorCls}`}>
        {score} / 10
      </span>
      {rating && <span className="text-sm text-gray-600 dark:text-gray-300">{rating}</span>}
    </span>
  )
}

/** 带 +/− 前缀的列表（优势/劣势） */
export function ProsConsList({ items, variant }: { items: string[]; variant: 'pros' | 'cons' }) {
  if (!items.length) return null
  const icon = variant === 'pros'
    ? <span className="text-green-500 shrink-0">+</span>
    : <span className="text-red-400 shrink-0">−</span>
  return (
    <ul className="mt-0.5 space-y-0.5 pl-1">
      {items.map((item, i) => (
        <li key={i} className="flex gap-1.5">{icon}<span>{renderBold(item)}</span></li>
      ))}
    </ul>
  )
}

/** 一个分析维度节（蓝色标题 + 正文） — 兼容旧 schema dimensions */
export function DimensionSection({ title, content }: { title: string; content: string }) {
  return (
    <section>
      <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-1">{title}</h3>
      <div className="text-sm leading-relaxed">
        {content.split('\n').map((line, i) =>
          line.trim() ? <p key={i} className="mb-0.5">{renderBold(line)}</p> : null,
        )}
      </div>
    </section>
  )
}

/** 渲染单个字段的值（支持嵌套对象、数组、字符串、next_day_scenarios 特殊结构）*/
export function FieldValue({ value }: { value: any }): React.ReactElement | null {
  if (value == null || value === '') return <span className="text-gray-400 dark:text-gray-600">-</span>

  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-gray-400 dark:text-gray-600">-</span>
    return (
      <ul className="mt-0.5 space-y-0.5">
        {value.map((item, i) => (
          <li key={i} className="flex gap-1.5">
            <span className="text-gray-400 dark:text-gray-600 shrink-0">·</span>
            <span>{renderBold(String(item ?? '-'))}</span>
          </li>
        ))}
      </ul>
    )
  }

  if (typeof value === 'object') {
    if ('probability' in value || 'trigger_condition' in value) {
      return (
        <span>
          <strong className="text-base">{renderBold(String(value.probability ?? '-'))}</strong>
          {value.trigger_condition && (
            <span className="text-gray-600 dark:text-gray-400 ml-2 text-xs">
              ／ {renderBold(String(value.trigger_condition))}
            </span>
          )}
        </span>
      )
    }
    const entries = Object.entries(value).filter(([, v]) => v != null && v !== '')
    if (entries.length === 0) return <span className="text-gray-400 dark:text-gray-600">-</span>
    return (
      <div className="mt-0.5 space-y-0.5">
        {entries.map(([k, v]) => (
          <div key={k} className="text-xs">
            <span className="text-gray-500 dark:text-gray-400">{k.replace(/_/g, ' ')}：</span>
            <span>{renderBold(String(v ?? '-'))}</span>
          </div>
        ))}
      </div>
    )
  }

  return <span>{renderBold(String(value))}</span>
}

/** 渲染一个 section：标题 + 带字段标签的条目列表 */
export function GenericSection({
  title,
  data,
  labels,
}: {
  title: string
  data: Record<string, any>
  labels?: Record<string, string>
}) {
  const entries = Object.entries(data).filter(([, v]) => v != null && v !== '')
  if (entries.length === 0) return null
  return (
    <section>
      <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-1">{title}</h3>
      <ul className="space-y-1 pl-1">
        {entries.map(([key, val]) => {
          const label = labels?.[key] ?? key.replace(/_/g, ' ')
          return (
            <li key={key} className="flex gap-1.5">
              <span className="text-gray-400 dark:text-gray-600 shrink-0">·</span>
              <span className="flex-1">
                <span className="text-gray-500 dark:text-gray-400">{label}：</span>
                <FieldValue value={val} />
              </span>
            </li>
          )
        })}
      </ul>
    </section>
  )
}

/**
 * CIO 复查触发器 section
 * 价位带方向箭头 + 锚定依据 + 有效期分列展示
 */
export function FollowupTriggersSection({ triggers }: { triggers: Record<string, any> }) {
  const timeList = Array.isArray(triggers.time_triggers) ? triggers.time_triggers : []
  const priceList = Array.isArray(triggers.price_triggers) ? triggers.price_triggers : []
  const horizon = triggers.review_horizon_days
  if (timeList.length === 0 && priceList.length === 0 && horizon == null) return null

  const priorityBadge = (p?: string) => {
    if (!p) return null
    const cls = p === 'high'
      ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
      : p === 'medium'
      ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-300'
      : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
    return <span className={`ml-1 text-[10px] px-1.5 py-0.5 rounded ${cls}`}>{p}</span>
  }

  return (
    <section className="border-t border-gray-100 dark:border-gray-700 pt-3">
      <h3 className="text-sm font-semibold text-blue-700 dark:text-blue-400 mb-2">
        复查触发器
        {horizon != null && (
          <span className="ml-2 text-xs font-normal text-gray-600 dark:text-gray-300">窗口 {horizon} 天</span>
        )}
      </h3>

      {priceList.length > 0 && (
        <div className="mb-2">
          <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">价位触发</div>
          <ul className="space-y-1 pl-1">
            {priceList.map((pt: any, i: number) => {
              const isUp = pt?.direction === 'break_up'
              const arrow = isUp ? '▲' : '▼'
              const colorCls = isUp ? 'text-positive' : 'text-negative'
              const priceText = pt?.price != null ? Number(pt.price).toFixed(2) : '暂无'
              return (
                <li key={i} className="text-xs flex gap-2 items-start">
                  <span className={`font-bold shrink-0 tabular-nums ${colorCls}`}>{arrow} {priceText}</span>
                  <div className="flex-1">
                    {pt?.price_basis && (
                      <div className="text-gray-600 dark:text-gray-300">
                        {renderBold(String(pt.price_basis))}
                      </div>
                    )}
                    {pt?.action_hint && (
                      <div className="text-gray-500 dark:text-gray-400 mt-0.5">
                        → {renderBold(String(pt.action_hint))}
                      </div>
                    )}
                    {(pt?.valid_until || pt?.priority) && (
                      <div className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5">
                        {pt?.valid_until && <span>有效期 {pt.valid_until}</span>}
                        {priorityBadge(pt?.priority)}
                      </div>
                    )}
                  </div>
                </li>
              )
            })}
          </ul>
        </div>
      )}

      {timeList.length > 0 && (
        <div>
          <div className="text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">事件/日期触发</div>
          <ul className="space-y-1 pl-1">
            {timeList.map((tt: any, i: number) => (
              <li key={i} className="text-xs flex gap-2 items-start">
                <span className="text-blue-600 dark:text-blue-400 font-bold shrink-0">⏱</span>
                <div className="flex-1">
                  <div className="text-gray-700 dark:text-gray-300">
                    {tt?.expected_date && <span className="font-semibold tabular-nums">{tt.expected_date}</span>}
                    {tt?.event_ref && (
                      <span className="ml-1 text-gray-600 dark:text-gray-400">· {tt.event_ref}</span>
                    )}
                    {tt?.days_from_today != null && (
                      <span className="ml-1 text-gray-500 dark:text-gray-400 tabular-nums">(距今 {tt.days_from_today} 天)</span>
                    )}
                    {priorityBadge(tt?.priority)}
                  </div>
                  {tt?.reason && (
                    <div className="text-gray-500 dark:text-gray-400 mt-0.5">
                      {renderBold(String(tt.reason))}
                    </div>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
